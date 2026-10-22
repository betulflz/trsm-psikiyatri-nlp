import io
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask
from PIL import Image, ImageDraw, ImageFont

from trsm.mobile_api import blueprint, ocr
from trsm.mobile_api.auth import issue_token, make_serializer


def photo():
    output = io.BytesIO()
    image = Image.new("RGB", (1000, 200), "white")
    ImageDraw.Draw(image).text((30, 60), "PATIENT REPORT 12345", fill="black", font=ImageFont.load_default(size=48))
    image.save(output, format="PNG")
    return output.getvalue()


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv("TRSM_OCR_BACKEND", "tesseract")
    monkeypatch.setenv("TRSM_OCR_LANG", "eng")
    monkeypatch.setenv("TRSM_TESSERACT_CMD", "tesseract")


def test_real_tesseract():
    if not shutil.which("tesseract"):
        pytest.skip("Tesseract kurulu değil")
    assert "PATIENT REPORT 12345" in ocr.read_report(photo())["metin"]


def test_cleanup_and_resource_limits(monkeypatch):
    seen = []

    def run(args, **kwargs):
        seen.append(Path(args[1]))
        with Image.open(args[1]) as image:
            assert max(image.size) <= 2000
        assert kwargs["timeout"] == 45
        assert kwargs["env"]["OMP_THREAD_LIMIT"] == "1"
        return SimpleNamespace(stdout=" test metni \n")

    monkeypatch.setattr(ocr.subprocess, "run", run)
    assert ocr.read_report(photo())["metin"] == "test metni"
    assert not seen[0].exists()


@pytest.mark.parametrize("error,code", [(FileNotFoundError(), 503), (subprocess.TimeoutExpired("ocr", 45), 504), (subprocess.CalledProcessError(1, "ocr"), 503)])
def test_engine_errors_release_slot(monkeypatch, error, code):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(ocr.subprocess, "run", fail)
    with pytest.raises(ocr.OcrError) as raised:
        ocr.read_report(photo())
    assert raised.value.status == code
    assert ocr._slot.acquire(blocking=False)
    ocr._slot.release()


@pytest.mark.parametrize("data,status", [(b"not a photo", 400), (b"", 413), (b"x" * (ocr.MAX_IMAGE_BYTES + 1), 413)])
def test_invalid_upload(data, status):
    with pytest.raises(ocr.OcrError) as raised:
        ocr.read_report(data)
    assert raised.value.status == status


def test_busy():
    ocr._slot.acquire()
    try:
        with pytest.raises(ocr.OcrError) as raised:
            ocr.read_report(photo())
        assert raised.value.status == 429
    finally:
        ocr._slot.release()


@pytest.fixture
def api(monkeypatch):
    # OCR veri tabanına yazmaz; yalnızca oturum/rol doğrulaması için bağlantı kullanır.
    monkeypatch.setattr(blueprint, "get_connection", lambda _: MagicMock())
    monkeypatch.setattr(blueprint, "create_schema", lambda _: None)
    monkeypatch.setattr(blueprint, "get_user", lambda _, uid: {"id": uid, "rol": "doktor" if uid == 1 else "admin"})
    app = Flask(__name__)
    app.register_blueprint(blueprint.create_mobile_blueprint("fake", "secret"))
    return app.test_client()


def headers(uid=1):
    return {"Authorization": "Bearer " + issue_token(make_serializer("secret"), uid)}


def test_endpoint_auth_and_validation(api):
    assert api.post("/api/m/rapor/ocr").status_code == 401
    assert api.post("/api/m/rapor/ocr", headers=headers(2)).status_code == 403
    assert api.post("/api/m/rapor/ocr", headers=headers()).status_code == 400
    response = api.post("/api/m/rapor/ocr", headers=headers(), data={"foto": (io.BytesIO(b"invalid"), "x.jpg")})
    assert response.status_code == 400
    assert response.json["kod"] == "ocr_hatasi"


def test_endpoint_multipart(api, monkeypatch):
    monkeypatch.setattr(blueprint, "read_report", lambda data: {"metin": "Rapor", "motor": "test", "dil": "eng"})
    response = api.post("/api/m/rapor/ocr", headers=headers(), data={"foto": (io.BytesIO(photo()), "x.png")})
    assert response.status_code == 200
    assert response.json["metin"] == "Rapor"


def test_request_size_limit(api):
    response = api.post("/api/m/rapor/ocr", headers=headers(), data={"foto": (io.BytesIO(b"x" * (ocr.MAX_IMAGE_BYTES + 70_000)), "x.jpg")})
    assert response.status_code == 413
    assert response.is_json

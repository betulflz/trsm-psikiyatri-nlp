import io
from unittest.mock import MagicMock

import pytest
from flask import Flask
from PIL import Image

from trsm.mobile_api import blueprint, ocr
from trsm.mobile_api.auth import issue_token, make_serializer


def photo(size=(3000, 600)):
    output = io.BytesIO()
    Image.new("RGB", size, "white").save(output, format="PNG")
    return output.getvalue()


def test_prepare_image_shrinks_to_jpeg():
    jpeg = ocr.prepare_image(photo())
    with Image.open(io.BytesIO(jpeg)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == ocr.MAX_SIDE


@pytest.mark.parametrize("data,status", [(b"not a photo", 400), (b"", 413), (b"x" * (ocr.MAX_IMAGE_BYTES + 1), 413)])
def test_invalid_upload(data, status):
    with pytest.raises(ocr.OcrError) as raised:
        ocr.prepare_image(data)
    assert raised.value.status == status


def test_read_with_qwen_sends_image(monkeypatch):
    client = MagicMock()
    client.chat.return_value = {"message": {"content": " Sertralin 50 mg \n"}}
    monkeypatch.setattr(ocr, "get_ollama_client", lambda timeout: client)
    monkeypatch.setenv("TRSM_LLM_THINK", "false")
    assert ocr.read_with_qwen(b"jpeg") == "Sertralin 50 mg"
    kwargs = client.chat.call_args.kwargs
    assert kwargs["messages"][0]["images"] == [b"jpeg"]
    assert kwargs["think"] is False


def test_read_with_qwen_connection_error(monkeypatch):
    client = MagicMock()
    client.chat.side_effect = ConnectionError()
    monkeypatch.setattr(ocr, "get_ollama_client", lambda timeout: client)
    with pytest.raises(ocr.OcrError):
        ocr.read_with_qwen(b"jpeg")


def test_queue_order_and_result():
    jobs = ocr.OcrQueue(reader=lambda jpeg: "okunan metin", start_worker=False)
    first = jobs.submit(photo(), owner_id=1)
    second = jobs.submit(photo(), owner_id=1)
    assert (first["durum"], first["sira"], second["sira"]) == ("sirada", 0, 1)
    jobs.run_pending()
    done = jobs.status(first["is_id"], 1)
    assert done["durum"] == "bitti" and done["metin"] == "okunan metin"


def test_queue_hides_other_users_jobs():
    jobs = ocr.OcrQueue(reader=lambda jpeg: "x", start_worker=False)
    job = jobs.submit(photo(), owner_id=1)
    assert jobs.status(job["is_id"], 2) is None
    assert jobs.status("yok", 1) is None


def test_queue_reports_errors():
    def fail(jpeg):
        raise ocr.OcrError("Qwen kapalı")
    jobs = ocr.OcrQueue(reader=fail, start_worker=False)
    job = jobs.submit(photo(), owner_id=1)
    jobs.run_pending()
    assert jobs.status(job["is_id"], 1)["hata"] == "Qwen kapalı"


def test_queue_limit():
    jobs = ocr.OcrQueue(reader=lambda jpeg: "x", max_waiting=1, start_worker=False)
    jobs.submit(photo(), owner_id=1)
    with pytest.raises(ocr.OcrError) as raised:
        jobs.submit(photo(), owner_id=1)
    assert raised.value.status == 429


@pytest.fixture
def jobs():
    return ocr.OcrQueue(reader=lambda jpeg: "Rapor", start_worker=False)


@pytest.fixture
def api(monkeypatch, jobs):
    # OCR veri tabanına yazmaz; yalnızca oturum/rol doğrulaması için bağlantı kullanır.
    monkeypatch.setattr(blueprint, "get_connection", lambda _: MagicMock())
    monkeypatch.setattr(blueprint, "create_schema", lambda _: None)
    monkeypatch.setattr(blueprint, "get_user", lambda _, uid: {"id": uid, "rol": "admin" if uid == 2 else "doktor"})
    app = Flask(__name__)
    app.register_blueprint(blueprint.create_mobile_blueprint("fake", "secret", ocr_queue=jobs))
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


def test_endpoint_submit_then_poll(api, jobs):
    response = api.post("/api/m/rapor/ocr", headers=headers(), data={"foto": (io.BytesIO(photo()), "x.png")})
    assert response.status_code == 202
    job_id = response.json["is_id"]
    assert api.get(f"/api/m/rapor/ocr/{job_id}", headers=headers()).json["durum"] == "sirada"
    jobs.run_pending()
    assert api.get(f"/api/m/rapor/ocr/{job_id}", headers=headers()).json["metin"] == "Rapor"
    assert api.get(f"/api/m/rapor/ocr/{job_id}", headers=headers(3)).status_code == 404


def test_request_size_limit(api):
    response = api.post("/api/m/rapor/ocr", headers=headers(), data={"foto": (io.BytesIO(b"x" * (ocr.MAX_IMAGE_BYTES + 70_000)), "x.jpg")})
    assert response.status_code == 413
    assert response.is_json

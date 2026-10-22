from contextlib import closing
from datetime import date

import pytest
from flask import Flask

from tests.mobile_fixtures import build_fixture_db
from tests.pg import fresh_database_url
from trsm.db import get_connection
from trsm.mobile_api import create_mobile_blueprint
from trsm.mobile_api.auth import issue_token, make_serializer
from trsm.mobile_api.users import ensure_user

SECRET = "test-anahtari"


@pytest.fixture
def ctx():
    path = fresh_database_url()
    ids = build_fixture_db(path)
    app = Flask(__name__)
    app.register_blueprint(create_mobile_blueprint(
        path, SECRET, today=lambda: date(2026, 10, 12),
        status_extra=lambda: {"semptom_indeksi": True, "ollama": False},
    ))
    with closing(get_connection(path)) as conn:
        for role in ("doktor", "hemsire", "admin"):
            ensure_user(conn, role, f"Demo {role}", role, f"{role}-sifre")
    return app.test_client(), ids


def _login(client, role):
    response = client.post("/api/m/giris", json={"kullanici_adi": role, "sifre": f"{role}-sifre"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_health_needs_no_token(ctx):
    client, _ = ctx
    assert client.get("/api/m/saglik").get_json() == {"durum": "ok"}


def test_login_success_and_me(ctx):
    client, _ = ctx
    response = client.post("/api/m/giris", json={"kullanici_adi": "doktor", "sifre": "doktor-sifre"})
    body = response.get_json()
    assert body["kullanici"] == {
        "id": 1, "kullanici_adi": "doktor", "ad_soyad": "Demo doktor", "rol": "doktor", "google_bagli": False,
    }
    me = client.get("/api/m/ben", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.get_json()["rol"] == "doktor"


@pytest.mark.parametrize("payload, status, kod", [
    ({"kullanici_adi": "doktor", "sifre": "yanlis"}, 401, "hatali_giris"),
    ({"kullanici_adi": "yok", "sifre": "x"}, 401, "hatali_giris"),
    ({"kullanici_adi": "doktor"}, 400, "eksik_bilgi"),
    (None, 400, "eksik_bilgi"),
])
def test_login_failures(ctx, payload, status, kod):
    client, _ = ctx
    response = client.post("/api/m/giris", json=payload) if payload is not None else client.post("/api/m/giris")
    assert response.status_code == status
    assert response.get_json()["kod"] == kod


@pytest.mark.parametrize("header", [None, "Bearer bozuk", "Token x"])
def test_missing_or_bad_token_is_401(ctx, header):
    client, _ = ctx
    headers = {"Authorization": header} if header else {}
    response = client.get("/api/m/ben", headers=headers)
    assert response.status_code == 401
    assert response.get_json() == {"hata": "Oturum geçersiz ya da süresi doldu.", "kod": "oturum_gecersiz"}


def test_token_for_deleted_user_is_401(ctx):
    client, _ = ctx
    token = issue_token(make_serializer(SECRET), 999)
    assert client.get("/api/m/ben", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("role, path, status", [
    ("admin", "/api/m/ozet", 403),
    ("admin", "/api/m/hastalar", 403),
    ("admin", "/api/m/hastalar/1", 403),
    ("admin", "/api/m/hastalar/1/notlar", 403),
    ("doktor", "/api/m/sistem", 403),
    ("hemsire", "/api/m/kullanicilar", 403),
    ("doktor", "/api/m/ozet", 200),
    ("hemsire", "/api/m/hastalar", 200),
    ("admin", "/api/m/sistem", 200),
    ("admin", "/api/m/kullanicilar", 200),
])
def test_role_matrix(ctx, role, path, status):
    client, _ = ctx
    response = client.get(path, headers=_login(client, role))
    assert response.status_code == status
    if status == 403:
        assert response.get_json()["kod"] == "yetki_yok"


def test_clinical_payloads(ctx):
    client, ids = ctx
    headers = _login(client, "doktor")
    assert client.get("/api/m/ozet", headers=headers).get_json()["toplam_dosya"] == 3
    patients = client.get("/api/m/hastalar", headers=headers).get_json()["hastalar"]
    assert [p["ad"] for p in patients] == ["Ayşe Kaya", "Boş Dosya", "İsmail Işık"]
    detail = client.get(f"/api/m/hastalar/{ids['ayse']}", headers=headers).get_json()
    assert detail["dosya_no"] == "#0001"
    notes = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?limit=2", headers=headers).get_json()
    assert notes["sonraki"] == ids["v2"]
    rest = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?limit=2&once={notes['sonraki']}", headers=headers)
    assert rest.get_json()["sonraki"] is None


def test_unknown_patient_is_404(ctx):
    client, _ = ctx
    headers = _login(client, "doktor")
    assert client.get("/api/m/hastalar/999", headers=headers).get_json()["kod"] == "dosya_yok"
    assert client.get("/api/m/hastalar/999/notlar", headers=headers).status_code == 404


@pytest.mark.parametrize("query", ["once=abc", "limit=xyz"])
def test_notes_bad_params_are_400(ctx, query):
    client, ids = ctx
    response = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?{query}", headers=_login(client, "doktor"))
    assert response.status_code == 400


def test_notes_invalid_cursor_is_400(ctx):
    client, ids = ctx
    response = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?once={ids['v5']}", headers=_login(client, "doktor"))
    assert response.status_code == 400
    assert response.get_json()["kod"] == "gecersiz_imlec"


def test_limit_is_clamped(ctx):
    client, ids = ctx
    response = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?limit=0", headers=_login(client, "doktor"))
    assert len(response.get_json()["notlar"]) == 1


def test_admin_payloads(ctx):
    client, _ = ctx
    headers = _login(client, "admin")
    system = client.get("/api/m/sistem", headers=headers).get_json()
    assert system["tablolar"]["kullanici"] == 3
    assert system["semptom_indeksi"] is True and system["ollama"] is False
    users = client.get("/api/m/kullanicilar", headers=headers).get_json()["kullanicilar"]
    assert [u["rol"] for u in users] == ["doktor", "hemsire", "admin"]
    assert all("sifre_hash" not in u for u in users)


HUGE = "99999999999999999999"


@pytest.mark.parametrize("path, status, kod", [
    (f"/api/m/hastalar/1/notlar?once={HUGE}", 400, "gecersiz_parametre"),
    (f"/api/m/hastalar/1/notlar?once=0", 400, "gecersiz_imlec"),
    (f"/api/m/hastalar/{HUGE}", 404, "dosya_yok"),
    (f"/api/m/hastalar/{HUGE}/notlar", 404, "dosya_yok"),
])
def test_out_of_range_ids_are_client_errors_not_500(ctx, path, status, kod):
    client, _ = ctx
    response = client.get(path, headers=_login(client, "doktor"))
    assert response.status_code == status
    assert response.get_json()["kod"] == kod


@pytest.mark.parametrize("body", [[1], "metin", 5, None])
def test_login_with_non_object_json_is_400(ctx, body):
    client, _ = ctx
    response = client.post("/api/m/giris", json=body)
    assert response.status_code == 400
    assert response.get_json()["kod"] == "eksik_bilgi"

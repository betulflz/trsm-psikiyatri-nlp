"""Örneklerin hepsi uydurmadır."""
from contextlib import closing

import pytest

from tests.test_mobile_endpoints import _login, ctx  # noqa: F401  (pytest fixture)
from trsm.db import get_connection

SAYFA = ("Ad Soyad: Ayşe Örnek TC: 12345678901\n"
         "Şikayet: 2 aydır uykusuzluk ve mutsuzluk var, iştahı azalmış\n"
         "Tedavi: Sertralin 50 mg 1x1 başlandı")


def _body(**extra):
    return {"yas": 34, "cinsiyet": "K", "ziyaret_tarihi": "2026-10-01", "sayfalar": [SAYFA], "kimlik_onayi": True, **extra}


def _seed_dictionary(client_ctx):
    with closing(get_connection(client_ctx)) as conn:
        sid = conn.execute("INSERT INTO ilac_sozluk (resmi_ad) VALUES ('Sertralin') RETURNING id").fetchone()[0]
        conn.execute("INSERT INTO ilac_varyasyon (ilac_sozluk_id, varyasyon) VALUES (%s, 'sertralin')", (sid,))
        conn.commit()


def test_saves_record_without_identity(ctx, monkeypatch):  # noqa: F811
    client, _ = ctx
    response = client.post("/api/m/kayit/anonim", json=_body(), headers=_login(client, "doktor"))
    assert response.status_code == 201
    body = response.get_json()
    assert body["kod"].startswith("ANON-") and body["ziyaret_sayisi"] == 1
    assert body["kayit_oncesi_temizlenen"] == {"ad": 1, "tc": 1}


def test_stored_rows_hold_no_identity(ctx):  # noqa: F811
    client, _ = ctx
    database_url = client.application.config["TRSM_TEST_DB"]
    _seed_dictionary(database_url)
    body = client.post("/api/m/kayit/anonim", json=_body(), headers=_login(client, "doktor")).get_json()
    assert body["ilaclar"] == ["Sertralin"]
    assert body["semptom_sayisi"] >= 1
    with closing(get_connection(database_url)) as conn:
        hasta = conn.execute("SELECT cinsiyet, dogum_tarihi, dogum_tarihi_kaynagi FROM hasta WHERE dosya_adi = %s",
                             (body["kod"],)).fetchone()
        assert hasta == ("Kadın", "01.07.1992", "mobil_anonim_yas")
        stored = " ".join(r[0] for r in conn.execute(
            "SELECT z.ham_mudahale_metni FROM ziyaret z JOIN hasta h ON h.id = z.hasta_id WHERE h.dosya_adi = %s",
            (body["kod"],)).fetchall())
        assert "Ayşe" not in stored and "12345678901" not in stored and "Sertralin 50 mg" in stored


@pytest.mark.parametrize("change,kod", [
    ({"kimlik_onayi": False}, "onay_gerekli"),
    ({"yas": 9}, "yas_gecersiz"),
    ({"yas": "34"}, "yas_gecersiz"),
    ({"cinsiyet": "X"}, "cinsiyet_gecersiz"),
    ({"sayfalar": []}, "sayfa_gecersiz"),
    ({"sayfalar": ["  "]}, "sayfa_gecersiz"),
    ({"ziyaret_tarihi": "2030-01-01"}, "tarih_gecersiz"),
    ({"ziyaret_tarihi": "01.10.2026"}, "tarih_gecersiz"),
])
def test_rejects_invalid_input(ctx, change, kod):  # noqa: F811
    client, _ = ctx
    response = client.post("/api/m/kayit/anonim", json=_body(**change), headers=_login(client, "doktor"))
    assert response.status_code == 400
    assert response.get_json()["kod"] == kod


def test_only_clinical_roles(ctx):  # noqa: F811
    client, _ = ctx
    assert client.post("/api/m/kayit/anonim", json=_body()).status_code == 401
    assert client.post("/api/m/kayit/anonim", json=_body(), headers=_login(client, "admin")).status_code == 403
    assert client.post("/api/m/kayit/anonim", json=_body(), headers=_login(client, "hemsire")).status_code == 201

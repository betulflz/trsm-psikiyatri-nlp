from contextlib import closing
from datetime import date

import pytest

from tests.mobile_fixtures import build_fixture_db
from tests.pg import fresh_database_url
from trsm.db import get_connection
from trsm.mobile_api.queries import (
    list_patients,
    patient_detail,
    patient_notes,
    summary,
    system_status,
)

TODAY = date(2026, 10, 12)


@pytest.fixture
def db():
    url = fresh_database_url()
    ids = build_fixture_db(url)
    with closing(get_connection(url)) as conn:
        yield conn, ids, url


def test_summary_counts(db):
    conn, _, _ = db
    result = summary(conn, 90)
    assert result["toplam_dosya"] == 3
    assert result["toplam_not"] == 5
    assert result["ilacli_not"] == 3
    assert result["yillik_not"] == [
        {"yil": 2021, "sayi": 1}, {"yil": 2022, "sayi": 0}, {"yil": 2023, "sayi": 2},
        {"yil": 2024, "sayi": 0}, {"yil": 2025, "sayi": 1},
    ]
    assert result["cinsiyet"] == {"erkek": 1, "kadin": 1, "bilinmiyor": 1}
    assert result["en_sik_ilaclar"] == [{"ilac": "Depakin", "sayi": 2}, {"ilac": "Abilify", "sayi": 1}]
    assert result["okunmamis_rapor"] == 0


def test_list_patients_density_and_order(db):
    conn, ids, _ = db
    patients = list_patients(conn, TODAY)
    assert [p["ad"] for p in patients] == ["Ayşe Kaya", "Boş Dosya", "İsmail Işık"]
    ayse, bos, ismail = patients
    assert ayse["yas"] == 37 and ismail["yas"] == 36 and bos["yas"] is None
    assert ayse["not_sayisi"] == 4 and ayse["son_ziyaret"] == "2023-06-10"
    assert ayse["yogunluk"] == [2] + [0] * 10 + [3]
    assert ismail["yogunluk"] == [0] * 11 + [3]
    assert bos["yogunluk"] == [0] * 12 and bos["son_ziyaret"] is None and bos["not_sayisi"] == 0
    assert ayse["okunmamis"] is False


def test_patient_detail(db):
    conn, ids, _ = db
    detail = patient_detail(conn, ids["ayse"], TODAY, 90)
    assert detail == {
        "id": ids["ayse"], "ad": "Ayşe Kaya", "cinsiyet": "Kadın", "yas": 37,
        "dosya_no": "#0001", "tc_maskeli": None, "not_sayisi": 4, "ilac_sayisi": 2,
        "ilk_kayit": "2021-03-01", "son_kayit": "2023-06-10",
    }
    assert patient_detail(conn, 999, TODAY, 90) is None


def test_note_content_and_highlights(db):
    conn, ids, _ = db
    notes = patient_notes(conn, ids["ayse"], 90, limit=10)["notlar"]
    v1 = next(n for n in notes if n["id"] == ids["v1"])
    assert v1["metin"] == "Depakin 500 2x1 başlandı\n\nUykusuzluk var"
    assert v1["vurgular"] == [{"bas": 0, "son": 7, "tur": "ilac"}, {"bas": 26, "son": 36, "tur": "belirti"}]
    assert v1["ilaclar"] == [{"ad": "Depakin", "doz": "500", "siklik": "2x1"}]
    assert v1["belirti_sayisi"] == 1 and v1["gorsel_var"] is False and v1["sayfa_no"] == 1
    v2 = next(n for n in notes if n["id"] == ids["v2"])
    assert [i["ad"] for i in v2["ilaclar"]] == ["Abilify"]  # güveni 80 olan Lityum dışarıda
    v4 = next(n for n in notes if n["id"] == ids["v4"])
    assert v4["metin"] == "Baş ağrısı var"  # NFD → NFC
    assert v4["vurgular"] == [{"bas": 0, "son": 10, "tur": "belirti"}]


def test_notes_paginate_with_undated_last(db):
    conn, ids, _ = db
    first = patient_notes(conn, ids["ayse"], 90, limit=2)
    assert [n["id"] for n in first["notlar"]] == [ids["v3"], ids["v2"]]
    assert first["sonraki"] == ids["v2"]
    second = patient_notes(conn, ids["ayse"], 90, before_id=first["sonraki"], limit=2)
    assert [n["id"] for n in second["notlar"]] == [ids["v1"], ids["v4"]]
    assert second["notlar"][1]["tarih"] is None
    assert second["sonraki"] is None


def test_notes_cursor_from_other_patient_raises(db):
    conn, ids, _ = db
    with pytest.raises(ValueError):
        patient_notes(conn, ids["ayse"], 90, before_id=ids["v5"])


def test_system_status(db):
    conn, _, _ = db
    status = system_status(conn)
    assert status["tablolar"]["hasta"] == 3
    assert status["tablolar"]["ziyaret"] == 5
    assert status["tablolar"]["kullanici"] == 0
    assert status["db_boyutu_mb"] > 0

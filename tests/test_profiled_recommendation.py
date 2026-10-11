import pytest

from trsm.db import create_schema, get_connection
from trsm.profiled_recommendation import compute_profiled_recommendation, normalize_profile


def _insert_historical_visit(conn, filename, birth_date, gender, visit_date, drug):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO hasta
           (dosya_adi, dogum_tarihi, dogum_tarihi_kaynagi, cinsiyet, cinsiyet_kaynagi)
           VALUES (?, ?, 'manual_review', ?, 'manual_review')""",
        (filename, birth_date, gender),
    )
    patient_id = cur.lastrowid
    cur.execute("INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, ?, 1)", (patient_id, visit_date))
    visit_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, eslesme_guveni)
           VALUES (?, ?, ?, 100)""",
        (visit_id, drug, drug),
    )
    conn.commit()
    return visit_id


def test_profiled_recommendation_uses_same_gender_and_historical_age_group_only():
    conn = get_connection(":memory:")
    create_schema(conn)
    matching = _insert_historical_visit(conn, "matching.pdf", "01.01.1999", "Erkek", "2024-02-01", "Akineton")
    wrong_gender = _insert_historical_visit(conn, "female.pdf", "01.01.1999", "Kadın", "2024-02-01", "Depakin")
    wrong_age = _insert_historical_visit(conn, "older.pdf", "01.01.1980", "Erkek", "2024-02-01", "Lithium")

    result = compute_profiled_recommendation(
        conn,
        [
            {"ziyaret_id": matching, "benzerlik": 0.9},
            {"ziyaret_id": matching, "benzerlik": 0.8},
            {"ziyaret_id": wrong_gender, "benzerlik": 0.9},
            {"ziyaret_id": wrong_age, "benzerlik": 0.9},
        ],
        age=25,
        gender="Erkek",
        min_visits=1,
        min_patients=1,
    )

    assert result["yas_grubu"] == "18-29"
    assert result["uyumlu_ziyaret_sayisi"] == 1
    assert result["uyumlu_hasta_sayisi"] == 1
    assert result["ilaclar"] == [{"ilac": "Akineton", "sayi": 1, "yuzde": 100.0}]
    assert result["durum"] == "yeterli_veri"


def test_profile_input_is_required_and_validated():
    assert normalize_profile("25", "Kadın") == {"yas": 25, "yas_grubu": "18-29", "cinsiyet": "Kadın"}
    with pytest.raises(ValueError):
        normalize_profile(14, "Kadın")
    with pytest.raises(ValueError):
        normalize_profile(25, "Belirtmek istemiyorum")

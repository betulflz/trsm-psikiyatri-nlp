from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.demographic_extraction import (
    calculate_age_at_visit,
    extract_birth_date,
    extract_gender,
    is_valid_birth_date,
    run_demographic_extraction,
)


def test_extract_birth_date_finds_date():
    assert extract_birth_date("MUĞLA\n15.07.1983\nCinsiyet: ...") == "15.07.1983"


def test_extract_birth_date_none_present():
    assert extract_birth_date("Cüneyt Karadırslan\nTC Kimlik No") is None


def test_extract_birth_date_rejects_invalid_ocr_year():
    assert extract_birth_date("28.03.7989") is None


def test_birth_date_validation_requires_adulthood_on_earliest_visit():
    assert is_valid_birth_date("15.07.1983", "2021-01-01") is True
    assert is_valid_birth_date("15.07.2008", "2025-01-01") is False


def test_calculate_age_at_visit_uses_month_and_day():
    assert calculate_age_at_visit("15.07.1983", "2021-07-14") == 37
    assert calculate_age_at_visit("15.07.1983", "2021-07-15") == 38


def test_extract_gender_erkek_checked():
    assert extract_gender("Cinsiyet: ☐ Kadın ☑ Erkek") == "Erkek"


def test_extract_gender_kadin_checked():
    assert extract_gender("Cinsiyet: ☑ Kadın ☐ Erkek") == "Kadın"


def test_extract_gender_both_checked_is_ambiguous():
    assert extract_gender("Cinsiyet: ☑ Kadın ☑ Erkek") is None


def test_extract_gender_neither_checked_is_ambiguous():
    assert extract_gender("Cinsiyet: ☐ Kadın ☐ Erkek") is None


def test_extract_gender_field_absent():
    assert extract_gender("Ev: Cep: 5358554724") is None


def _insert_hasta(conn, dosya_adi="hasta.pdf"):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (%s) RETURNING id", (dosya_adi,))
    conn.commit()
    return cur.fetchone()[0]


def _insert_ziyaret(conn, hasta_id, sayfa_no, mudahale, sonuc):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (hasta_id, sayfa_no, mudahale, sonuc),
    )
    conn.commit()
    return cur.fetchone()[0]


def test_run_demographic_extraction_fills_clean_page():
    conn = fresh_connection()
    create_schema(conn)
    hasta_id = _insert_hasta(conn)
    _insert_ziyaret(conn, hasta_id, 9, "RH.FR.002", "Yayın Tarihi")
    _insert_ziyaret(conn, hasta_id, 9, "Cüneyt Karadırslan", "TC Kimlik No")
    _insert_ziyaret(conn, hasta_id, 9, "MUĞLA", None)
    _insert_ziyaret(conn, hasta_id, 9, "15.07.1983", "Cinsiyet: ☐ Kadın ☑ Erkek")

    run_demographic_extraction(conn)

    cur = conn.cursor()
    cur.execute("SELECT cinsiyet, dogum_tarihi FROM hasta WHERE id = %s", (hasta_id,))
    assert cur.fetchone() == ("Erkek", "15.07.1983")

    cur.execute(
        "SELECT cinsiyet_kaynagi, dogum_tarihi_kaynagi FROM hasta WHERE id = %s",
        (hasta_id,),
    )
    assert cur.fetchone() == ("RH.FR.002_checkbox", "RH.FR.002_ocr_ve_yas_kurali")


def test_run_demographic_extraction_leaves_hasta_without_form_untouched():
    conn = fresh_connection()
    create_schema(conn)
    hasta_id = _insert_hasta(conn)
    _insert_ziyaret(conn, hasta_id, 3, "Bireysel görüşme yapıldı", None)

    run_demographic_extraction(conn)

    cur = conn.cursor()
    cur.execute("SELECT cinsiyet, dogum_tarihi FROM hasta WHERE id = %s", (hasta_id,))
    assert cur.fetchone() == (None, None)


def test_run_demographic_extraction_leaves_conflicting_form_values_unset():
    conn = fresh_connection()
    create_schema(conn)
    hasta_id = _insert_hasta(conn)
    _insert_ziyaret(conn, hasta_id, 5, "RH.FR.002", "Yayın Tarihi")
    _insert_ziyaret(conn, hasta_id, 5, "15.07.1983", "Cinsiyet: ☐ Kadın ☑ Erkek")
    _insert_ziyaret(conn, hasta_id, 12, "RH.FR.002", "Yayın Tarihi")
    _insert_ziyaret(conn, hasta_id, 12, "01.01.1990", "Cinsiyet: ☑ Kadın ☐ Erkek")

    run_demographic_extraction(conn)

    cur = conn.cursor()
    cur.execute("SELECT cinsiyet, dogum_tarihi FROM hasta WHERE id = %s", (hasta_id,))
    assert cur.fetchone() == (None, None)


def test_run_demographic_extraction_ambiguous_checkbox_leaves_gender_none():
    conn = fresh_connection()
    create_schema(conn)
    hasta_id = _insert_hasta(conn)
    _insert_ziyaret(conn, hasta_id, 15, "RH.FR.002", "Yayın Tarihi")
    _insert_ziyaret(conn, hasta_id, 15, "Ev:", "Cep:")
    _insert_ziyaret(conn, hasta_id, 15, "Aydın/makro", "Fatih mah.")

    run_demographic_extraction(conn)

    cur = conn.cursor()
    cur.execute("SELECT cinsiyet, dogum_tarihi FROM hasta WHERE id = %s", (hasta_id,))
    assert cur.fetchone() == (None, None)


def test_run_demographic_extraction_rejects_date_for_non_adult_at_earliest_visit():
    conn = fresh_connection()
    create_schema(conn)
    hasta_id = _insert_hasta(conn)
    _insert_ziyaret(conn, hasta_id, 4, "RH.FR.002", "Yayın Tarihi")
    _insert_ziyaret(conn, hasta_id, 4, "15.07.2008", "Cinsiyet: ☑ Kadın ☐ Erkek")
    conn.execute("UPDATE ziyaret SET tarih = '2025-01-01' WHERE hasta_id = %s", (hasta_id,))
    conn.commit()

    run_demographic_extraction(conn)

    cur = conn.cursor()
    cur.execute("SELECT cinsiyet, dogum_tarihi FROM hasta WHERE id = %s", (hasta_id,))
    assert cur.fetchone() == ("Kadın", None)


def test_run_demographic_extraction_preserves_manual_review_values():
    conn = fresh_connection()
    create_schema(conn)
    hasta_id = _insert_hasta(conn)
    _insert_ziyaret(conn, hasta_id, 4, "RH.FR.002", "15.07.1983 Cinsiyet: ☐ Kadın ☑ Erkek")
    conn.execute(
        """UPDATE hasta SET cinsiyet='Kadın', cinsiyet_kaynagi='manual_review',
           dogum_tarihi='01.01.1980', dogum_tarihi_kaynagi='manual_review' WHERE id=%s""",
        (hasta_id,),
    )
    conn.commit()

    run_demographic_extraction(conn)

    row = conn.execute(
        """SELECT cinsiyet, dogum_tarihi, cinsiyet_kaynagi, dogum_tarihi_kaynagi
           FROM hasta WHERE id=%s""",
        (hasta_id,),
    ).fetchone()
    assert row == ("Kadın", "01.01.1980", "manual_review", "manual_review")

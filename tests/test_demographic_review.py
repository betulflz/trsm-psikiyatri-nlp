import csv

from trsm.db import create_schema, get_connection
from trsm.demographic_review import (
    apply_manual_demographic_overrides,
    build_demographic_review_rows,
    write_demographic_override_sheet,
    write_demographic_review_csv,
)


def _insert_form_patient(conn, birth_date="15.07.1983", gender="☑ Kadın ☐ Erkek"):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES ('hasta.pdf')")
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, 'RH.FR.002', ?)""",
        (hasta_id, f"{birth_date} Cinsiyet: {gender}"),
    )
    conn.commit()
    return hasta_id


def test_build_review_rows_includes_ambiguous_ocr_values():
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_form_patient(conn, birth_date="28.03.7989", gender="☐ Kadın ☐ Erkek")

    rows = build_demographic_review_rows(conn)

    assert len(rows) == 1
    assert "takvim/yaş" in rows[0]["inceleme_nedeni"]
    assert "Cinsiyet kutusu" in rows[0]["inceleme_nedeni"]


def test_write_review_csv_uses_semicolon_delimiter(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_form_patient(conn, birth_date="28.03.7989")

    output = tmp_path / "review.csv"
    count = write_demographic_review_csv(conn, output)

    with open(output, encoding="utf-8") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    assert count == 1
    assert rows[0]["dosya_adi"] == "hasta.pdf"


def test_apply_manual_override_records_manual_source(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    hasta_id = _insert_form_patient(conn, birth_date="28.03.7989")
    override = tmp_path / "overrides.csv"
    override.write_text("dosya_adi;dogum_tarihi;cinsiyet\nhasta.pdf;15.07.1983;Kadın\n", encoding="utf-8")

    assert apply_manual_demographic_overrides(conn, override) == 1

    row = conn.execute(
        """SELECT dogum_tarihi, cinsiyet, dogum_tarihi_kaynagi, cinsiyet_kaynagi
           FROM hasta WHERE id = ?""",
        (hasta_id,),
    ).fetchone()
    assert row == ("15.07.1983", "Kadın", "manual_review", "manual_review")


def test_override_sheet_has_blank_editable_demographic_columns(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_form_patient(conn, birth_date="28.03.7989")

    output = tmp_path / "overrides.csv"
    count = write_demographic_override_sheet(conn, output)

    with open(output, encoding="utf-8") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    assert count == 1
    assert rows[0]["dosya_adi"] == "hasta.pdf"
    assert rows[0]["dogum_tarihi"] == ""
    assert rows[0]["cinsiyet"] == ""

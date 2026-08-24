from trsm.db import get_connection, create_schema
from trsm.medication_pipeline import (
    extract_medications_from_text,
    run_medication_extraction,
)


def test_extract_medications_from_text_finds_drug_dose_and_frequency():
    index = {"Stilizan": "Stilizan"}
    text = "Stilizan 5mg tb -> 3x1"

    results = extract_medications_from_text(text, index)

    assert len(results) == 1
    assert results[0]["ilac_adi_normalize"] == "Stilizan"
    assert results[0]["ilac_adi_ham"] == "Stilizan"
    assert results[0]["doz"] == "5mg"
    assert results[0]["siklik"] == "3x1"


def test_extract_medications_from_text_empty_text_returns_empty_list():
    assert extract_medications_from_text(None, {}) == []
    assert extract_medications_from_text("", {}) == []


def test_run_medication_extraction_writes_rows_to_db():
    conn = get_connection(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')")
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, 'Stilizan 5mg tb -> 3x1', NULL)""",
        (hasta_id,),
    )
    conn.commit()

    index = {"Stilizan": "Stilizan"}
    run_medication_extraction(conn, index)

    cur.execute("SELECT ilac_adi_normalize, doz, siklik FROM ilac_kullanimi")
    rows = cur.fetchall()
    assert rows == [("Stilizan", "5mg", "3x1")]

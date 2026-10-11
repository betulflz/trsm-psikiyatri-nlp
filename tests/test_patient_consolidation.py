from pathlib import Path

from trsm.db import create_schema, get_connection
from trsm.patient_consolidation import consolidate_patients_by_source_folders


def _insert_document_patient(conn, filename, birth_date, gender, visit_text):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO hasta
           (dosya_adi, dogum_tarihi, dogum_tarihi_kaynagi, cinsiyet, cinsiyet_kaynagi)
           VALUES (?, ?, 'manual_review', ?, 'manual_review')""",
        (filename, birth_date, gender),
    )
    patient_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret
           (hasta_id, tarih, sayfa_no, ham_mudahale_metni)
           VALUES (?, '2024-01-01', 1, ?)""",
        (patient_id, visit_text),
    )
    conn.commit()
    return patient_id


def _create_pdf_path(root, folder, filename):
    path = Path(root) / folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_consolidation_merges_documents_preserves_visits_and_traces(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    first_id = _insert_document_patient(conn, "Dilan Konyar 1.pdf", "15.07.1983", "Kadın", "ilk")
    _insert_document_patient(conn, "Dilan Konyar 2.pdf", "15.07.1983", "Kadın", "ikinci")
    _create_pdf_path(tmp_path, "Dilan Konyar", "Dilan Konyar 1.pdf")
    _create_pdf_path(tmp_path, "Dilan Konyar", "Dilan Konyar 2.pdf")

    report = consolidate_patients_by_source_folders(conn, [tmp_path])

    assert report["person_count"] == 1
    assert report["demographic_conflicts"] == []
    row = conn.execute(
        "SELECT id, dosya_adi, dogum_tarihi, cinsiyet FROM hasta"
    ).fetchone()
    assert row == (first_id, "Dilan Konyar", "15.07.1983", "Kadın")
    visits = conn.execute(
        "SELECT hasta_id, kaynak_dosya_adi FROM ziyaret ORDER BY id"
    ).fetchall()
    assert visits == [
        (first_id, "Dilan Konyar 1.pdf"),
        (first_id, "Dilan Konyar 2.pdf"),
    ]
    assert conn.execute("SELECT COUNT(*) FROM hasta_dosya").fetchone()[0] == 2


def test_consolidation_aborts_before_mutating_when_a_document_is_unmapped(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_document_patient(conn, "Eksik.pdf", "15.07.1983", "Kadın", "not")

    try:
        consolidate_patients_by_source_folders(conn, [tmp_path])
    except ValueError as error:
        assert "eşleşmeyen PDF" in str(error)
    else:
        raise AssertionError("Eşleşmeyen kaynak için ValueError bekleniyordu")
    assert conn.execute("SELECT COUNT(*) FROM hasta").fetchone()[0] == 1

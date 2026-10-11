from datetime import datetime

from openpyxl import Workbook

from trsm.db import create_schema, get_connection
from trsm.manual_demographic_import import import_manual_demographics
from trsm.patient_consolidation import consolidate_patients_by_source_folders


def _insert_patient(conn, filename, visit_date="2024-01-01"):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (filename,))
    patient_id = cur.lastrowid
    cur.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, ?, 1)",
        (patient_id, visit_date),
    )
    conn.commit()
    return patient_id


def _write_excel(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["dosya_adi", "dogum_tarihi", "cinsiyet"])
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def test_manual_import_uses_valid_complete_values_and_normalizes_filename(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = _insert_patient(conn, "Ali Öztürk 1.pdf")
    path = tmp_path / "manual.xlsx"
    _write_excel(path, [("Ali Öztürk 1 .pdf", datetime(1980, 7, 15), "erkek")])

    report = import_manual_demographics(conn, path)

    assert report["eslesen_hasta"] == 1
    assert report["tam_dogum_tarihi"] == 1
    assert report["cinsiyet"] == 1
    row = conn.execute(
        """SELECT dogum_tarihi, dogum_tarihi_kaynagi, cinsiyet, cinsiyet_kaynagi
           FROM hasta WHERE id=?""",
        (patient_id,),
    ).fetchone()
    assert row == ("15.07.1980", "manual_review", "Erkek", "manual_review")


def test_manual_import_excludes_question_mark_dates_but_keeps_gender(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = _insert_patient(conn, "Ayşe.pdf")
    conn.execute(
        """UPDATE hasta SET dogum_tarihi='01.01.1980',
           dogum_tarihi_kaynagi='RH.FR.002_ocr_ve_yas_kurali' WHERE id=?""",
        (patient_id,),
    )
    conn.commit()
    path = tmp_path / "manual.xlsx"
    _write_excel(path, [("Ayşe.pdf", "?.?.1983", "kadın")])

    report = import_manual_demographics(conn, path)

    assert report["eksik_dogum_tarihi"] == 1
    row = conn.execute(
        "SELECT dogum_tarihi, dogum_tarihi_kaynagi, cinsiyet FROM hasta WHERE id=?",
        (patient_id,),
    ).fetchone()
    assert row == (None, "manual_incomplete", "Kadın")


def test_manual_import_reports_invalid_year_and_unmatched_filename(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_patient(conn, "Ahmet.pdf", visit_date="2024-01-01")
    path = tmp_path / "manual.xlsx"
    _write_excel(path, [
        ("Ahmet.pdf", datetime(3000, 1, 1), "erkek"),
        ("Yok.pdf", datetime(1980, 1, 1), "kadın"),
    ])

    report = import_manual_demographics(conn, path)

    assert report["gecersiz_dogum_tarihi"] == 1
    assert report["eslesen_hasta"] == 1
    assert len(report["inceleme_satirlari"]) == 2


def test_manual_import_combines_multiple_pdf_rows_for_one_consolidated_person(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_patient(conn, "Dilan 1.pdf")
    _insert_patient(conn, "Dilan 2.pdf")
    for filename in ("Dilan 1.pdf", "Dilan 2.pdf"):
        path = tmp_path / "Dilan" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    consolidate_patients_by_source_folders(conn, [tmp_path])
    path = tmp_path / "manual.xlsx"
    _write_excel(path, [
        ("Dilan 1.pdf", "?.?.1983", "kadın"),
        ("Dilan 2.pdf", datetime(1983, 7, 15), "kadın"),
    ])

    report = import_manual_demographics(conn, path)

    assert report["eslesen_hasta"] == 1
    assert report["tam_dogum_tarihi"] == 1
    assert report["eksik_dogum_tarihi"] == 0
    row = conn.execute(
        "SELECT dogum_tarihi, cinsiyet FROM hasta"
    ).fetchone()
    assert row == ("15.07.1983", "Kadın")


def test_manual_import_joins_source_sibling_and_confirmed_spelling_alias(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_patient(conn, "Dilan 1.pdf")
    _insert_patient(conn, "Begüm Arslan Mert.pdf")
    for folder, filename in (
        ("Dilan", "Dilan 1.pdf"),
        ("Dilan", "Dilan 2.pdf"),
        ("Begüm Arslan Mert", "Begüm Arslan Mert.pdf"),
    ):
        path = tmp_path / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    consolidate_patients_by_source_folders(conn, [tmp_path])
    path = tmp_path / "manual.xlsx"
    _write_excel(path, [
        ("Dilan 2.pdf", datetime(1983, 7, 15), "kadın"),
        ("Begüm Aslan Mert.pdf", datetime(1980, 1, 1), "kadın"),
    ])

    report = import_manual_demographics(conn, path, source_roots=[tmp_path])

    assert report["eslesen_hasta"] == 2
    assert not report["inceleme_satirlari"]
    assert conn.execute("SELECT COUNT(*) FROM hasta WHERE dogum_tarihi IS NOT NULL").fetchone()[0] == 2


def test_manual_import_marks_source_only_person_as_out_of_analysis(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    source_pdf = tmp_path / "Kaynakta Var" / "Kaynakta Var.pdf"
    source_pdf.parent.mkdir(parents=True)
    source_pdf.touch()
    path = tmp_path / "manual.xlsx"
    _write_excel(path, [("Kaynakta Var.pdf", datetime(1980, 1, 1), "erkek")])

    report = import_manual_demographics(conn, path, source_roots=[tmp_path])

    assert report["eslesen_hasta"] == 0
    assert report["inceleme_satirlari"][0]["neden"] == (
        "Kaynak PDF bulundu; toplu veritabanında ziyaret kaydı yok, analiz dışı bırakıldı"
    )

import csv

from trsm.db import get_connection, create_schema
from trsm.validation_export import export_validation_sample, export_validation_sample_with_predictions


def _insert_hasta_with_ziyaret(conn, dosya):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (dosya,))
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, 'not', 'sonuc')""",
        (hasta_id,),
    )
    conn.commit()


def test_export_validation_sample_writes_csv_with_header_and_rows(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_hasta_with_ziyaret(conn, "a.pdf")
    _insert_hasta_with_ziyaret(conn, "b.pdf")

    output_csv = tmp_path / "sample.csv"
    export_validation_sample(conn, str(output_csv), sample_size=10)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == [
        "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
        "manuel_ilac_notu", "manuel_semptom_notu",
    ]
    assert len(rows) == 3


def test_export_validation_sample_sanitizes_formula_like_fields(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')")
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, '=1+1', 'normal metin')""",
        (hasta_id,),
    )
    conn.commit()

    output_csv = tmp_path / "sample.csv"
    export_validation_sample(conn, str(output_csv), sample_size=10)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    data_row = rows[1]
    ham_mudahale_metni = data_row[2]
    assert not ham_mudahale_metni.startswith("=")
    assert ham_mudahale_metni.startswith("'")


def test_export_validation_sample_respects_sample_size(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    for i in range(5):
        _insert_hasta_with_ziyaret(conn, f"hasta{i}.pdf")

    output_csv = tmp_path / "sample.csv"
    export_validation_sample(conn, str(output_csv), sample_size=2)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert len(rows) == 3


def test_export_validation_sample_with_predictions_includes_system_findings(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')")
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, 'Stilizan 5mg tb -> 3x1. Uyku bozuk.', NULL)""",
        (hasta_id,),
    )
    ziyaret_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
           VALUES (?, 'Stilizan', 'Stilizan', '5mg', '3x1', 100)""",
        (ziyaret_id,),
    )
    cur.execute(
        "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (?, 'Uyku bozuk', 'cluster_0')",
        (ziyaret_id,),
    )
    conn.commit()

    output_csv = tmp_path / "sample.csv"
    export_validation_sample_with_predictions(conn, str(output_csv), sample_size=10)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == [
        "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
        "sistem_ilac_bulgusu", "ilac_dogru_mu",
        "sistem_semptom_bulgusu", "semptom_dogru_mu",
    ]
    data_row = rows[1]
    assert "Stilizan (100" in data_row[4]
    assert data_row[5] == ""
    assert "Uyku bozuk" in data_row[6]
    assert data_row[7] == ""


def test_export_validation_sample_with_predictions_blank_when_no_findings(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_hasta_with_ziyaret(conn, "a.pdf")

    output_csv = tmp_path / "sample.csv"
    export_validation_sample_with_predictions(conn, str(output_csv), sample_size=10)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    data_row = rows[1]
    assert data_row[4] == ""
    assert data_row[6] == ""

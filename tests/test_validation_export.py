import csv

from trsm.db import get_connection, create_schema
from trsm.validation_export import export_validation_sample


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

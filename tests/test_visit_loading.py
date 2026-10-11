import pandas as pd
from trsm.db import get_connection, create_schema
from trsm.visit_loading import load_visits


def test_load_visits_creates_one_hasta_per_unique_dosya():
    conn = get_connection(":memory:")
    create_schema(conn)
    df = pd.DataFrame({
        "Dosya": ["a.pdf", "a.pdf", "b.pdf"],
        "Sayfa": [1, 2, 1],
        "Müdahale": ["not1", None, "not3"],
        "Sonuç": ["sonuc1", "sonuc2", None],
        "tarih_normalize": ["2024-01-01", "2024-01-02", "2024-02-01"],
    })

    load_visits(conn, df)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hasta")
    assert cur.fetchone()[0] == 2
    cur.execute("SELECT COUNT(*) FROM ziyaret")
    assert cur.fetchone()[0] == 3


def test_load_visits_preserves_null_text_as_null():
    conn = get_connection(":memory:")
    create_schema(conn)
    df = pd.DataFrame({
        "Dosya": ["a.pdf"],
        "Sayfa": [1],
        "Müdahale": [None],
        "Sonuç": ["sonuc1"],
        "tarih_normalize": ["2024-01-01"],
    })

    load_visits(conn, df)

    cur = conn.cursor()
    cur.execute("SELECT ham_mudahale_metni, ham_sonuc_metni FROM ziyaret")
    row = cur.fetchone()
    assert row[0] is None
    assert row[1] == "sonuc1"

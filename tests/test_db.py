import sqlite3
from trsm.db import get_connection, create_schema


def test_create_schema_creates_all_tables():
    conn = get_connection(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    expected = {
        "hasta", "ziyaret", "ilac_sozluk", "ilac_varyasyon",
        "ilac_kullanimi", "semptom_kaydi",
    }
    assert expected.issubset(tables)


def test_get_connection_enables_foreign_keys():
    conn = get_connection(":memory:")
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys")
    assert cur.fetchone()[0] == 1

import pytest

from trsm.db import create_schema, drop_schema, table_columns, table_exists
from tests.pg import fresh_connection


def test_create_schema_creates_all_tables():
    conn = fresh_connection()
    create_schema(conn)
    expected = {
        "hasta", "ziyaret", "ilac_sozluk", "ilac_varyasyon",
        "ilac_kullanimi", "semptom_kaydi", "hasta_dosya", "kullanici",
    }
    assert all(table_exists(conn, table) for table in expected)
    assert "kaynak_dosya_adi" in table_columns(conn, "ziyaret")


def test_create_schema_is_idempotent():
    conn = fresh_connection()
    create_schema(conn)
    create_schema(conn)
    assert table_exists(conn, "hasta")


def test_foreign_keys_are_enforced():
    import psycopg

    conn = fresh_connection()
    create_schema(conn)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute("INSERT INTO ziyaret (hasta_id) VALUES (999)")


def test_drop_schema_removes_project_tables():
    conn = fresh_connection()
    create_schema(conn)
    drop_schema(conn)
    assert not table_exists(conn, "hasta")

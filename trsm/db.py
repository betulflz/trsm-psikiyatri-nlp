import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path, check_same_thread=True):
    conn = sqlite3.connect(db_path, check_same_thread=check_same_thread)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn):
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()

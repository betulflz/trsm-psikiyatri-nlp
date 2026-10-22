"""Testler için yalıtılmış PostgreSQL şemaları.

Her çağrı `trsm_test` veritabanında boş bir şema açar ve bağlantı adresine
`search_path` ekler; böylece testler birbirini ve gerçek veriyi etkilemez.
"""
import uuid
from urllib.parse import quote

from trsm.db import database_url, get_connection

SCHEMA_PREFIX = "pytest_"


def test_database_url():
    return database_url("TEST_DATABASE_URL")


def fresh_database_url():
    schema = f"{SCHEMA_PREFIX}{uuid.uuid4().hex[:12]}"
    with get_connection(test_database_url(), autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA {schema}")
    separator = "&" if "?" in test_database_url() else "?"
    return f"{test_database_url()}{separator}options={quote(f'-csearch_path={schema}')}"


def fresh_connection():
    return get_connection(fresh_database_url())


def drop_test_schemas():
    with get_connection(test_database_url(), autocommit=True) as conn:
        # Kapatılmamış test bağlantıları tablo kilidi tutar; DROP beklemesin.
        conn.execute(
            """SELECT pg_terminate_backend(pid) FROM pg_stat_activity
               WHERE datname = current_database() AND pid <> pg_backend_pid()"""
        )
        schemas = conn.execute(
            "SELECT nspname FROM pg_namespace WHERE starts_with(nspname, %s)",
            (SCHEMA_PREFIX,),
        ).fetchall()
        for (schema,) in schemas:
            conn.execute(f"DROP SCHEMA {schema} CASCADE")

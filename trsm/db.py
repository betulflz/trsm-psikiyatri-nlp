import os
from pathlib import Path

import psycopg

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _read_env_file(path=ENV_PATH):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def database_url(name="DATABASE_URL"):
    """Read the PostgreSQL address from the environment, then from `.env`."""
    url = os.environ.get(name) or _read_env_file().get(name)
    if not url:
        raise RuntimeError(
            f"{name} tanımlı değil. Proje kökündeki .env dosyasını oluşturun "
            "(cp .env.example .env) ve PostgreSQL'i başlatın: docker compose up -d"
        )
    return url


def get_connection(url=None, autocommit=False):
    return psycopg.connect(url or database_url(), autocommit=autocommit)


def create_schema(conn):
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def table_exists(conn, table):
    return conn.execute("SELECT to_regclass(%s) IS NOT NULL", (table,)).fetchone()[0]


def table_columns(conn, table):
    rows = conn.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema = current_schema() AND table_name = %s""",
        (table,),
    ).fetchall()
    return {row[0] for row in rows}


SCHEMA_TABLES = (
    "ilac_kullanimi", "semptom_kaydi", "ilac_varyasyon", "hasta_dosya",
    "ziyaret", "ilac_sozluk", "hasta", "kullanici",
)


def drop_schema(conn):
    """Drop every project table; used only by an explicit pipeline overwrite."""
    conn.execute(f"DROP TABLE IF EXISTS {', '.join(SCHEMA_TABLES)} CASCADE")
    conn.commit()

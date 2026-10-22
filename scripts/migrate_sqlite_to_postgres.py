"""Eski SQLite veritabanını (trsm.db) PostgreSQL'e birebir taşır.

Çalıştırma:
    uv run python scripts/migrate_sqlite_to_postgres.py trsm.db

- SQLite dosyası salt-okunur açılır; hiçbir şekilde değiştirilmez.
- Kopyalama tek bir işlem (transaction) içinde yapılır: bir tablo bile
  başarısız olursa PostgreSQL'e hiçbir şey yazılmaz.
- `id` değerleri korunur; böylece tablolar arası ilişkiler ve dışa
  aktarılmış dosyalardaki kişi kodları geçerli kalır.
- Bittikten sonra her tablodaki her satır iki veritabanında tek tek
  karşılaştırılır; tek bir fark bile varsa betik hata verir.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trsm.db import create_schema, get_connection, table_columns

# Yabancı anahtar sırasına göre: önce başvurulan tablolar.
TABLES = (
    "hasta",
    "ilac_sozluk",
    "kullanici",
    "ziyaret",
    "hasta_dosya",
    "ilac_varyasyon",
    "ilac_kullanimi",
    "semptom_kaydi",
)


def _sqlite_tables(source):
    rows = source.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def _sqlite_columns(source, table):
    return [row[1] for row in source.execute(f"PRAGMA table_info({table})")]


def _check_structure(source, target):
    """Stop before copying if the two schemas do not describe the same data."""
    problems = []
    unknown = _sqlite_tables(source) - set(TABLES)
    if unknown:
        problems.append(f"SQLite'ta taşıma listesinde olmayan tablolar var: {sorted(unknown)}")
    present = _sqlite_tables(source)
    for table in TABLES:
        if table not in present:
            continue
        source_columns = set(_sqlite_columns(source, table))
        target_columns = table_columns(target, table)
        if source_columns != target_columns:
            problems.append(
                f"{table}: sütunlar farklı. Yalnızca SQLite'ta: "
                f"{sorted(source_columns - target_columns)}, yalnızca PostgreSQL'de: "
                f"{sorted(target_columns - source_columns)}"
            )
    if problems:
        raise MigrationError("Taşıma durduruldu:\n- " + "\n- ".join(problems))


def _target_has_data(target):
    return any(
        target.execute(f"SELECT EXISTS (SELECT 1 FROM {table})").fetchone()[0]
        for table in TABLES
    )


def _copy_table(source, target, table):
    columns = _sqlite_columns(source, table)
    column_list = ", ".join(columns)
    rows = source.execute(f"SELECT {column_list} FROM {table} ORDER BY id")
    count = 0
    with target.cursor().copy(f"COPY {table} ({column_list}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)
            count += 1
    # Kimlik sayacını en büyük id'nin ardına taşı; yeni kayıtlar çakışmasın.
    target.execute(
        f"""SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                          COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"""
    )
    return count


def _verify_table(source, target, table):
    columns = _sqlite_columns(source, table)
    column_list = ", ".join(columns)
    query = f"SELECT {column_list} FROM {table} ORDER BY id"
    source_rows = source.execute(query).fetchall()
    target_rows = [tuple(row) for row in target.execute(query).fetchall()]
    if len(source_rows) != len(target_rows):
        return f"{table}: satır sayısı farklı ({len(source_rows)} ≠ {len(target_rows)})"
    for source_row, target_row in zip(source_rows, target_rows):
        if source_row != target_row:
            return f"{table}: id={source_row[0]} satırı farklı"
    return None


class MigrationError(RuntimeError):
    pass


def migrate(sqlite_path, database_url=None, replace=False):
    """Copy every table and verify it row by row; return {table: row_count}."""
    sqlite_path = Path(sqlite_path).resolve()
    if not sqlite_path.exists():
        raise MigrationError(f"SQLite dosyası bulunamadı: {sqlite_path}")
    source = sqlite3.connect(f"{sqlite_path.as_uri()}?mode=ro", uri=True)
    target = get_connection(database_url)
    try:
        create_schema(target)
        _check_structure(source, target)
        if _target_has_data(target):
            if not replace:
                raise MigrationError(
                    "Hedef PostgreSQL veritabanında zaten veri var. Üzerine yazmak "
                    "istiyorsanız --replace ile tekrar çalıştırın."
                )
            target.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")

        present = _sqlite_tables(source)
        copied = {}
        for table in TABLES:
            if table in present:
                copied[table] = _copy_table(source, target, table)
        target.commit()

        problems = [p for table in copied if (p := _verify_table(source, target, table))]
        target.rollback()  # doğrulama yalnızca okudu; açık okuma işlemini kapat
        if problems:
            raise MigrationError("DOĞRULAMA BAŞARISIZ:\n- " + "\n- ".join(problems))
        return copied
    except BaseException:
        target.rollback()
        raise
    finally:
        target.close()
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sqlite_path", help="Kaynak SQLite dosyası (örn. trsm.db)")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Hedef PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Hedefte veri varsa önce tüm tabloları boşalt (dikkat: geri alınamaz)",
    )
    args = parser.parse_args()

    try:
        copied = migrate(args.sqlite_path, args.database_url, replace=args.replace)
    except MigrationError as exc:
        raise SystemExit(str(exc))
    print(f"{'Tablo':<16} {'Satır':>8}")
    for table, count in copied.items():
        print(f"{table:<16} {count:>8}")
    print("Doğrulama başarılı: tüm satırlar iki veritabanında birebir aynı.")


if __name__ == "__main__":
    main()

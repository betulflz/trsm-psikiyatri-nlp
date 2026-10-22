"""Mobil uygulamanın üç demo hesabını oluşturur (varsa dokunmaz).

Çalıştırma: uv run python scripts/seed_mobile_users.py [--database-url postgresql://...]
Şifreler TRSM_SEED_PASSWORD_DOKTOR / _HEMSIRE / _ADMIN ortam
değişkenlerinden okunur; verilmezse trsm/mobile_api/seed.py'deki demo
şifreleri kullanılır.
"""
import argparse
import os
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trsm.db import create_schema, get_connection
from trsm.mobile_api.seed import seed_demo_users


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    args = parser.parse_args()
    with closing(get_connection(args.database_url)) as conn:
        create_schema(conn)
        results = seed_demo_users(conn, os.environ)
    for username, created in results.items():
        print(f"{username}: {'oluşturuldu' if created else 'zaten var, dokunulmadı'}")


if __name__ == "__main__":
    main()

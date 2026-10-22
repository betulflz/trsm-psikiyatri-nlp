import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.validation_export import export_validation_sample


def main():
    parser = argparse.ArgumentParser(
        description="TRSM manuel doğrulama örneklemini CSV olarak dışa aktarır"
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    parser.add_argument("output_csv", help="Oluşturulacak CSV dosyasının yolu")
    parser.add_argument(
        "--sample-size", type=int, default=30, help="Örneklem büyüklüğü (varsayılan: 30)"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Rastgele örnekleme için tohum (varsayılan: 42)"
    )
    args = parser.parse_args()

    conn = get_connection(args.database_url)
    try:
        export_validation_sample(
            conn, args.output_csv, sample_size=args.sample_size, seed=args.seed
        )
    finally:
        conn.close()

    print(f"Doğrulama örneklemi dışa aktarıldı: {args.output_csv}")


if __name__ == "__main__":
    main()

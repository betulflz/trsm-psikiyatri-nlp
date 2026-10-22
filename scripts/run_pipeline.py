import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="TRSM veri temizleme ve varlık çıkarımı pipeline'ı"
    )
    parser.add_argument("excel_path", help="Ham OCR Excel dosyasının yolu")
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Veritabanı zaten doluysa tüm tabloları silip yeniden oluştur",
    )
    args = parser.parse_args()

    run_pipeline(args.excel_path, args.database_url, overwrite=args.overwrite)
    print("Pipeline tamamlandı.")


if __name__ == "__main__":
    main()

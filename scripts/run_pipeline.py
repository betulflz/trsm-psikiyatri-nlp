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
    parser.add_argument("db_path", help="Oluşturulacak SQLite veritabanı dosyasının yolu")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Belirtilen veritabanı dosyası zaten mevcutsa üzerine yaz",
    )
    args = parser.parse_args()

    run_pipeline(args.excel_path, args.db_path, overwrite=args.overwrite)
    print(f"Pipeline tamamlandı: {args.db_path}")


if __name__ == "__main__":
    main()

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.demographic_extraction import run_demographic_extraction
from trsm.demographic_review import (
    apply_manual_demographic_overrides,
    write_demographic_override_sheet,
    write_demographic_review_csv,
)


def main():
    parser = argparse.ArgumentParser(
        description="RH.FR.002 formlarından denetlenebilir demografik veri çıkarır"
    )
    parser.add_argument("db_path", help="Mevcut SQLite veritabanı")
    parser.add_argument(
        "--review-csv",
        default="data/demographic_ocr_review.csv",
        help="OCR belirsizlikleri için yerel inceleme CSV'si",
    )
    parser.add_argument(
        "--overrides-csv",
        help="Kullanıcı tarafından doğrulanmış yerel düzeltme CSV'si",
    )
    parser.add_argument(
        "--override-sheet",
        default="data/demographic_manual_overrides.csv",
        help="Doldurulmaya hazır yerel manuel doğrulama sayfası",
    )
    args = parser.parse_args()

    review_path = Path(args.review_csv)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(args.db_path)
    try:
        run_demographic_extraction(conn)
        if args.overrides_csv:
            applied = apply_manual_demographic_overrides(conn, args.overrides_csv)
            print(f"Manuel düzeltme uygulanan hasta: {applied}")
        review_count = write_demographic_review_csv(conn, review_path)
        override_path = Path(args.override_sheet)
        if not override_path.exists():
            override_path.parent.mkdir(parents=True, exist_ok=True)
            write_demographic_override_sheet(conn, override_path)
            print(f"Doldurulmaya hazır manuel doğrulama sayfası: {override_path}")
        else:
            print(f"Mevcut manuel doğrulama sayfası korunuyor: {override_path}")
    finally:
        conn.close()
    print(f"İncelenmesi gereken OCR kaydı: {review_count}")
    print(f"Yerel inceleme dosyası: {review_path}")


if __name__ == "__main__":
    main()

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.manual_demographic_import import (
    import_manual_demographics,
    write_import_review_csv,
)


def main():
    parser = argparse.ArgumentParser(
        description="Manuel doğrulanmış doğum tarihi/cinsiyet Excel'ini içe aktarır"
    )
    parser.add_argument("excel_path", help="dosya_adi, dogum_tarihi, cinsiyet başlıklı Excel")
    parser.add_argument("db_path", help="Güncellenecek SQLite veritabanı")
    parser.add_argument(
        "--review-csv",
        default="data/manual_demographic_import_review.csv",
        help="Eşleşmeyen veya geçersiz satırlar için yerel inceleme CSV'si",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        help="PDF kişi klasörlerinin kökü; birden fazla kez verilebilir",
    )
    args = parser.parse_args()

    review_path = Path(args.review_csv)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(args.db_path)
    try:
        report = import_manual_demographics(
            conn, args.excel_path, source_roots=args.source_root
        )
    finally:
        conn.close()
    write_import_review_csv(report, review_path)
    for key in (
        "excel_satiri", "eslesen_hasta", "tam_dogum_tarihi",
        "eksik_dogum_tarihi", "gecersiz_dogum_tarihi", "cinsiyet",
    ):
        print(f"{key}: {report[key]}")
    print(f"İnceleme satırı: {len(report['inceleme_satirlari'])}")
    print(f"İnceleme CSV'si: {review_path}")


if __name__ == "__main__":
    main()

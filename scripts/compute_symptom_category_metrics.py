"""Score MiniLM or Qwen labels against completed clinician consensus."""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.symptom_validation import compute_symptom_category_metrics, format_symptom_category_report


def main():
    parser = argparse.ArgumentParser(
        description="Uzman uzlaşı etiketlerine göre semptom kategori metriklerini hesaplar"
    )
    parser.add_argument("csv_path", help="Doldurulmuş ; ayrımlı doğrulama CSV'si")
    parser.add_argument(
        "--prediction-column", default="sistem_kategoriler",
        help="Ölçülecek tahmin sütunu: sistem_kategoriler veya qwen_kategoriler",
    )
    parser.add_argument(
        "--prediction-csv",
        help="Tahmin sütunu uzman uzlaşı dosyasında değilse ornek_id ile birleştirilecek ayrı tahmin CSV'si",
    )
    parser.add_argument(
        "--report-dir", default="docs/validation_reports",
        help="Markdown rapor klasörü",
    )
    args = parser.parse_args()

    result = compute_symptom_category_metrics(
        args.csv_path, args.prediction_column, prediction_csv=args.prediction_csv
    )
    report = format_symptom_category_report(result, args.csv_path)
    print(report)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / f"semptom_kategori_{args.prediction_column}_{date.today().isoformat()}.md"
    output.write_text(report, encoding="utf-8")
    print(f"Rapor yazıldı: {output}")


if __name__ == "__main__":
    main()

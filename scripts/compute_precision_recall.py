import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.validation_metrics import compute_drug_precision_recall, format_report

DEFAULT_REPORT_DIR = Path(__file__).parent.parent / "docs" / "validation_reports"


def main():
    parser = argparse.ArgumentParser(
        description="Doğrulama CSV'sinden ilaç çıkarımı precision/recall hesaplar"
    )
    parser.add_argument("csv_path", help="Doğrulama CSV dosyasının yolu (ilac_dogru_mu dolu)")
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help=f"Rapor dosyasının yazılacağı klasör (varsayılan: {DEFAULT_REPORT_DIR})",
    )
    args = parser.parse_args()

    result = compute_drug_precision_recall(args.csv_path)
    report = format_report(result, source_csv=args.csv_path)

    print(report)

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"ilac_precision_recall_{date.today().isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Rapor yazıldı: {report_path}")


if __name__ == "__main__":
    main()

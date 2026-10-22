"""Write an automatic, non-clinical quality audit of symptom category behaviour."""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.symptom_quality_audit import format_symptom_quality_audit, run_symptom_quality_audit


def main():
    parser = argparse.ArgumentParser(description="Semptom kategori sistemi için otomatik kalite denetimi üretir")
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    parser.add_argument("--sample-size", type=int, default=5000, help="Rastgele incelenecek ifade sayısı")
    parser.add_argument("--seed", type=int, default=42, help="Tekrarlanabilir örnekleme tohumu")
    parser.add_argument("--report-dir", default="docs/analysis_reports", help="Markdown rapor klasörü")
    args = parser.parse_args()

    conn = get_connection(args.database_url)
    try:
        result = run_symptom_quality_audit(conn, args.sample_size, args.seed)
    finally:
        conn.close()
    report = format_symptom_quality_audit(result)
    print(report)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / f"semptom_kalite_denetimi_{date.today().isoformat()}.md"
    output.write_text(report, encoding="utf-8")
    print(f"Rapor yazıldı: {output}")


if __name__ == "__main__":
    main()

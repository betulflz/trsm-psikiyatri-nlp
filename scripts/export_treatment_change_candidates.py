"""Export non-identifying candidates for clinical review of medication changes."""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.treatment_timeline import list_treatment_change_candidates


def main():
    parser = argparse.ArgumentParser(
        description="Gözlenen ilaç listesi değişimi olan hastaları kimliksiz CSV olarak dışa aktarır"
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    parser.add_argument("output_csv", help="Oluşturulacak ; ayrımlı CSV")
    parser.add_argument("--confidence", type=float, default=90, help="Minimum OCR ilaç eşleşme güveni")
    args = parser.parse_args()

    conn = get_connection(args.database_url)
    try:
        candidates = list_treatment_change_candidates(conn, args.confidence)
    finally:
        conn.close()
    with open(args.output_csv, "w", encoding="utf-8", newline="") as handle:
        fields = ["hasta_id", "tarihli_ilac_kaydi_gun_sayisi", "gozlenen_degisim_sayisi", "ilk_tarih", "son_tarih"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(candidates)
    print(f"{len(candidates)} aday dışa aktarıldı: {args.output_csv}")


if __name__ == "__main__":
    main()

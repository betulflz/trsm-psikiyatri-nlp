import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.patient_consolidation import consolidate_patients_by_source_folders


def main():
    parser = argparse.ArgumentParser(
        description="Aynı klasördeki PDF kayıtlarını tek gerçek hastada birleştirir"
    )
    parser.add_argument("db_path", help="Güncellenecek SQLite veritabanı")
    parser.add_argument("source_roots", nargs="+", help="Hasta klasörlerini içeren kök dizinler")
    args = parser.parse_args()

    conn = get_connection(args.db_path)
    try:
        report = consolidate_patients_by_source_folders(conn, args.source_roots)
    finally:
        conn.close()
    print(f"Zaten birleştirilmiş: {report['already_consolidated']}")
    print(f"Kaynak PDF: {report['document_count']}")
    print(f"Gerçek kişi: {report['person_count']}")
    print(f"Demografik çakışma: {len(report['demographic_conflicts'])}")


if __name__ == "__main__":
    main()

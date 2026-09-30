import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.symptom_similarity import build_symptom_index


def main():
    parser = argparse.ArgumentParser(
        description="Semptom benzerlik indeksini (embedding) trsm.db'den inşa eder"
    )
    parser.add_argument("db_path", help="Dolu trsm.db dosyasının yolu")
    parser.add_argument("index_path", help="Oluşturulacak .npz indeks dosyasının yolu")
    args = parser.parse_args()

    conn = get_connection(args.db_path)
    try:
        result = build_symptom_index(conn, args.index_path)
    finally:
        conn.close()

    print(
        f"Semptom indeksi oluşturuldu: {args.index_path} "
        f"({result['indekse_alinan_aktif_semptom']} aktif ifade, "
        f"{result['haric_tutulan_kayit']} belirti dışı/olumsuz kayıt hariç tutuldu)"
    )


if __name__ == "__main__":
    main()

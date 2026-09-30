"""Create a blinded, stratified CSV for clinical symptom-theme review."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.symptom_validation import export_symptom_category_validation_sample


def main():
    parser = argparse.ArgumentParser(
        description="Semptom kategori doğrulaması için iki değerlendiricili CSV oluşturur"
    )
    parser.add_argument("db_path", help="Dolu SQLite veritabanı")
    parser.add_argument("output_csv", help="Oluşturulacak ; ayrımlı CSV")
    parser.add_argument("--per-category", type=int, default=25, help="Her tema için hedef örnek sayısı")
    parser.add_argument("--uncertain", type=int, default=50, help="Sistem temaya bağlayamadığı hedef örnek sayısı")
    parser.add_argument("--candidate-pool", type=int, default=5000, help="Rastgele taranacak ifade havuzu")
    parser.add_argument("--seed", type=int, default=42, help="Tekrarlanabilir örnekleme tohumu")
    args = parser.parse_args()

    conn = get_connection(args.db_path)
    try:
        result = export_symptom_category_validation_sample(
            conn, args.output_csv, sample_per_category=args.per_category,
            uncertain_sample_size=args.uncertain, candidate_pool_size=args.candidate_pool,
            seed=args.seed,
        )
    finally:
        conn.close()

    print(f"Doğrulama dosyası oluşturuldu: {args.output_csv}")
    print(f"Sistem tahminleri (değerlendiricilere gösterilmeyecek): {result['sistem_tahmin_dosyasi']}")
    print(f"Toplam örnek: {result['toplam']} | Belirsiz: {result['belirsiz_sayisi']} | Aday havuzu: {result['aday_havuzu']}")
    for category, count in result["kategori_sayilari"].items():
        print(f"- {category}: {count}")


if __name__ == "__main__":
    main()

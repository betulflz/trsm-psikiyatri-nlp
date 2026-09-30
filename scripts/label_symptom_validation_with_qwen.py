"""Create a Qwen-labelled copy of a clinician validation sheet."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.qwen_symptom_labeling import label_validation_csv_with_qwen


def main():
    parser = argparse.ArgumentParser(
        description="Doğrulama CSV'sine yerel Qwen aday etiketleri ekler; kaynak dosyayı değiştirmez"
    )
    parser.add_argument("input_csv", help="Uzman etiketleri henüz boş olabilen kaynak CSV")
    parser.add_argument("output_csv", help="Qwen sütunları eklenmiş yeni CSV")
    args = parser.parse_args()

    result = label_validation_csv_with_qwen(args.input_csv, args.output_csv)
    print(f"Qwen aday etiketleri yazıldı: {args.output_csv} ({result['toplam']} ifade, model: {result['model']})")


if __name__ == "__main__":
    main()

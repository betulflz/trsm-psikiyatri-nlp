"""Export one pseudonymous patient's descriptive medication/theme timeline."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from trsm.db import get_connection
from trsm.treatment_timeline import build_patient_treatment_timeline
from trsm.transparent_symptom_query import build_category_seed_embeddings


def main():
    parser = argparse.ArgumentParser(
        description="Bir hasta için gözlemsel ilaç değişimi ve geniş semptom tema zaman çizelgesi dışa aktarır"
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL adresi (varsayılan: .env içindeki DATABASE_URL)",
    )
    parser.add_argument("patient_id", type=int, help="Kimliksiz hasta ID'si")
    parser.add_argument("output_json", help="Oluşturulacak yerel JSON dosyası")
    args = parser.parse_args()

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    seed_embeddings = build_category_seed_embeddings(model)
    conn = get_connection(args.database_url)
    try:
        timeline = build_patient_treatment_timeline(
            conn, args.patient_id, model=model, seed_embeddings=seed_embeddings,
        )
    finally:
        conn.close()
    Path(args.output_json).write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Zaman çizelgesi yazıldı: {args.output_json}")
    print(f"Gözlenen ilaç listesi değişimi: {len(timeline['gozlenen_ilac_degisimleri'])}")


if __name__ == "__main__":
    main()

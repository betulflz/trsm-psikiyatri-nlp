"""Build aggregate, non-causal before/after theme statistics for medication changes."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from trsm.db import get_connection
from trsm.transparent_symptom_query import build_category_seed_embeddings
from trsm.treatment_response_analysis import (
    build_patient_transition_analysis,
    summarize_transition_analyses,
)
from trsm.treatment_timeline import build_theme_details_for_patients, list_treatment_change_candidates


def main():
    parser = argparse.ArgumentParser(
        description="İlaç değişimleri sonrası kayıtlardaki geniş semptom tema değişimlerinin gözlemsel özetini üretir"
    )
    parser.add_argument("db_path", help="Dolu SQLite veritabanı")
    parser.add_argument("output_json", help="Toplulaştırılmış çıktı JSON dosyası")
    parser.add_argument("--max-follow-up-days", type=int, default=90, help="Sonraki semptom kaydı için maksimum gün")
    parser.add_argument("--max-patients", type=int, help="Hızlı deneme için en fazla hasta sayısı")
    args = parser.parse_args()

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    seed_embeddings = build_category_seed_embeddings(model)
    conn = get_connection(args.db_path)
    try:
        candidates = list_treatment_change_candidates(conn)
        patient_ids = [row["hasta_id"] for row in candidates]
        if args.max_patients:
            patient_ids = patient_ids[:args.max_patients]
        print(f"{len(patient_ids)} hastanın semptom tema geçmişi toplu olarak hazırlanıyor...")
        theme_details = build_theme_details_for_patients(
            conn, patient_ids, model, seed_embeddings,
        )
        analyses = []
        for index, patient_id in enumerate(patient_ids, start=1):
            analyses.append(build_patient_transition_analysis(
                conn, patient_id, model, seed_embeddings,
                max_follow_up_days=args.max_follow_up_days,
                precomputed_theme_details=theme_details.get(patient_id, {}),
            ))
            if index % 25 == 0 or index == len(patient_ids):
                print(f"{index}/{len(patient_ids)} hasta işlendi")
    finally:
        conn.close()
    summary = summarize_transition_analyses(analyses)
    output = {
        "analiz_edilen_hasta_sayisi": len(patient_ids),
        "takip_penceresi_gun": args.max_follow_up_days,
        "gecisler": summary,
        "sinirlilik_notu": (
            "Bu özet, ilaç düzeni değişiminden önce ve sonraki ziyaret notlarında kaydedilen "
            "geniş semptom tema varlığını karşılaştırır. İlaç etkisi, iyileşme, kötüleşme veya "
            "nedensellik kanıtı değildir."
        ),
    }
    Path(args.output_json).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Toplulaştırılmış geçiş istatistiği yazıldı: {args.output_json} ({len(summary)} geçiş grubu)")


if __name__ == "__main__":
    main()

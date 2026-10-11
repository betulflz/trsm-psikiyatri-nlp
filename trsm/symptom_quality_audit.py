"""Automatic consistency audit for the symptom-theme pipeline.

This reports software quality signals (coverage, negation holds, semantic
ambiguity), not clinical accuracy. Clinical accuracy needs an external gold
standard and is intentionally not inferred here.
"""

import random
from collections import Counter

from .transparent_symptom_query import build_category_seed_embeddings, classify_symptom_phrases


def run_symptom_quality_audit(conn, sample_size=5000, seed=42, model=None):
    rows = conn.execute(
        "SELECT ifade_ham FROM semptom_kaydi WHERE trim(ifade_ham) != '' ORDER BY id"
    ).fetchall()
    rng = random.Random(seed)
    rng.shuffle(rows)
    phrases = [row[0] for row in rows[:sample_size]]
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    classified = classify_symptom_phrases(
        phrases, model, build_category_seed_embeddings(model)
    )
    quality = Counter(row["kalite_sinyali"]["durum"] for row in classified)
    match_type = Counter(
        item["eslesme_turu"] for row in classified for item in row["kategoriler"]
    )
    category_counts = Counter(
        item["kategori"] for row in classified for item in row["kategoriler"]
    )
    return {
        "incelenen_ifade_sayisi": len(classified),
        "ornekleme_tohumu": seed,
        "kalite_sinyalleri": dict(quality),
        "eslesme_turleri": dict(match_type),
        "kategori_etiket_sayilari": dict(category_counts),
        "sinirlilik_notu": (
            "Bu sonuçlar otomatik sistem davranışını ölçer; klinik doğruluk, "
            "duyarlılık veya özgüllük ölçümü değildir."
        ),
    }


def format_symptom_quality_audit(result):
    lines = [
        "# Otomatik Semptom Kategori Kalite Denetimi",
        "",
        f"- İncelenen ifade: {result['incelenen_ifade_sayisi']}",
        f"- Rastgelelik tohumu: {result['ornekleme_tohumu']}",
        "",
        "## Kalite sinyalleri",
        "",
    ]
    for name, count in sorted(result["kalite_sinyalleri"].items()):
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Eşleşme türleri", ""])
    for name, count in sorted(result["eslesme_turleri"].items()):
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Tema etiket sayıları", ""])
    for name, count in sorted(result["kategori_etiket_sayilari"].items()):
        lines.append(f"- {name}: {count}")
    lines.extend(["", result["sinirlilik_notu"]])
    return "\n".join(lines)

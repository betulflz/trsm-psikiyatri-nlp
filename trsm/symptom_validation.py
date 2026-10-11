"""Human-grounded validation tools for broad symptom theme labels.

The live application never treats these labels as a diagnosis.  This module
creates a blinded, reproducible review sample and scores a system only against
clinician consensus labels recorded in that sample.
"""

import csv
import random
from collections import defaultdict
from pathlib import Path

from .symptom_categories import KATEGORILER
from .transparent_symptom_query import (
    build_category_seed_embeddings,
    classify_symptom_phrases,
)


CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
LABEL_SEPARATOR = "|"
COMPLETED_VALUES = {"evet", "yes", "true", "1", "tamam"}


def _sanitize_csv_field(value):
    if isinstance(value, str) and value.startswith(CSV_FORMULA_PREFIXES):
        return "'" + value
    return value


def _label_set(value):
    """Parse a pipe-separated multi-label cell; blank means no selected theme."""
    if not value:
        return set()
    return {
        label.strip()
        for label in str(value).split(LABEL_SEPARATOR)
        if label.strip() and label.strip().casefold() != "belirsiz"
    }


def _format_labels(labels):
    return LABEL_SEPARATOR.join(labels)


def _candidate_rows(conn):
    """Return one reproducible unit per source symptom row, without patient IDs."""
    return conn.execute(
        "SELECT id, ifade_ham FROM semptom_kaydi WHERE trim(ifade_ham) != '' ORDER BY id"
    ).fetchall()


def export_symptom_category_validation_sample(
    conn,
    output_csv,
    sample_per_category=25,
    uncertain_sample_size=50,
    candidate_pool_size=5000,
    seed=42,
    model=None,
    system_predictions_csv=None,
):
    """Export a stratified, blinded review sheet for two independent raters.

    The random candidate pool and seed are recorded in the sheet.  No patient
    name, file name, visit ID or raw full note is exported: a reviewer sees the
    symptom expression and the system's prediction only.  A separate clinical
    reviewer can consult the source record inside the authorised local system
    for a genuinely ambiguous expression.
    """
    if sample_per_category < 1 or uncertain_sample_size < 0 or candidate_pool_size < 1:
        raise ValueError("Örneklem boyutları pozitif olmalı; belirsiz örneklem sıfır olabilir.")

    rows = _candidate_rows(conn)
    rng = random.Random(seed)
    rng.shuffle(rows)
    candidates = rows[:candidate_pool_size]
    if not candidates:
        candidates = []

    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    predictions = classify_symptom_phrases(
        [row[1] for row in candidates], model, build_category_seed_embeddings(model)
    )

    by_category = defaultdict(list)
    uncertain = []
    for source_row, prediction in zip(candidates, predictions):
        labels = [item["kategori"] for item in prediction["kategoriler"]]
        record = {
            "source_id": source_row[0],
            "ifade": prediction["ifade"],
            "sistem_kategoriler": _format_labels(labels),
            "sistem_eslesme_turleri": _format_labels(
                item["eslesme_turu"] for item in prediction["kategoriler"]
            ),
            "sistem_en_yuksek_benzerlik": max(
                (item["benzerlik"] for item in prediction["kategoriler"]), default=""
            ),
        }
        if labels:
            for category in labels:
                by_category[category].append(record)
        else:
            uncertain.append(record)

    selected = []
    selected_ids = set()
    category_counts = {}
    for category in KATEGORILER:
        options = by_category[category]
        rng.shuffle(options)
        chosen = []
        for record in options:
            if record["source_id"] in selected_ids:
                continue
            chosen.append(record)
            selected.append(record)
            selected_ids.add(record["source_id"])
            if len(chosen) == sample_per_category:
                break
        category_counts[category] = len(chosen)

    rng.shuffle(uncertain)
    uncertain_count = 0
    for record in uncertain:
        if record["source_id"] in selected_ids:
            continue
        selected.append(record)
        selected_ids.add(record["source_id"])
        uncertain_count += 1
        if uncertain_count == uncertain_sample_size:
            break

    rng.shuffle(selected)
    review_header = [
        "ornek_id", "ifade", "degerlendirici_1_kategoriler",
        "degerlendirici_2_kategoriler", "uzlasim_kategoriler",
        "uzlasim_tamamlandi", "degerlendirme_notu",
    ]
    output_path = Path(output_csv)
    prediction_path = Path(system_predictions_csv) if system_predictions_csv else output_path.with_name(
        f"{output_path.stem}_sistem{output_path.suffix}"
    )
    with open(output_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(review_header)
        for index, record in enumerate(selected, start=1):
            writer.writerow([
                f"SYM-{index:04d}",
                _sanitize_csv_field(record["ifade"]),
                "", "", "", "", "",
            ])

    with open(prediction_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ornek_id", "sistem_kategoriler", "sistem_eslesme_turleri", "sistem_en_yuksek_benzerlik"],
            delimiter=";",
        )
        writer.writeheader()
        for index, record in enumerate(selected, start=1):
            writer.writerow({
                "ornek_id": f"SYM-{index:04d}",
                "sistem_kategoriler": record["sistem_kategoriler"],
                "sistem_eslesme_turleri": record["sistem_eslesme_turleri"],
                "sistem_en_yuksek_benzerlik": record["sistem_en_yuksek_benzerlik"],
            })

    return {
        "toplam": len(selected),
        "kategori_sayilari": category_counts,
        "belirsiz_sayisi": uncertain_count,
        "aday_havuzu": len(candidates),
        "seed": seed,
        "sistem_tahmin_dosyasi": str(prediction_path),
    }


def _safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _binary_kappa(first, second):
    """Cohen's kappa for one category across completed multi-label rows."""
    n = len(first)
    if not n:
        return None
    both_yes = sum(a and b for a, b in zip(first, second))
    both_no = sum(not a and not b for a, b in zip(first, second))
    observed = (both_yes + both_no) / n
    first_yes = sum(first) / n
    second_yes = sum(second) / n
    expected = first_yes * second_yes + (1 - first_yes) * (1 - second_yes)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def compute_symptom_category_metrics(csv_path, prediction_column="sistem_kategoriler", prediction_csv=None):
    """Score multi-label predictions against completed clinician consensus rows."""
    with open(csv_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    if prediction_column not in (rows[0] if rows else []) and prediction_csv:
        with open(prediction_csv, encoding="utf-8", newline="") as handle:
            prediction_rows = list(csv.DictReader(handle, delimiter=";"))
        predictions_by_id = {
            row["ornek_id"]: row.get(prediction_column, "") for row in prediction_rows
        }
        for row in rows:
            row[prediction_column] = predictions_by_id.get(row.get("ornek_id"), "")
    required = {"uzlasim_kategoriler", "uzlasim_tamamlandi", prediction_column}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"CSV'de eksik sütunlar: {', '.join(sorted(missing))}")

    completed = [
        row for row in rows
        if str(row.get("uzlasim_tamamlandi", "")).strip().casefold() in COMPLETED_VALUES
    ]
    category_metrics = {}
    aggregate_tp = aggregate_fp = aggregate_fn = 0
    invalid_gold_labels = set()
    invalid_prediction_labels = set()
    exact_matches = 0
    for category in KATEGORILER:
        tp = fp = fn = 0
        for row in completed:
            predicted = _label_set(row[prediction_column])
            gold = _label_set(row["uzlasim_kategoriler"])
            if category in predicted and category in gold:
                tp += 1
            elif category in predicted:
                fp += 1
            elif category in gold:
                fn += 1
        precision = _safe_divide(tp, tp + fp)
        recall = _safe_divide(tp, tp + fn)
        f1 = _safe_divide(2 * precision * recall, precision + recall)
        category_metrics[category] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
        }
        aggregate_tp += tp
        aggregate_fp += fp
        aggregate_fn += fn

    first_labels = []
    second_labels = []
    for row in completed:
        predicted = _label_set(row[prediction_column])
        gold = _label_set(row["uzlasim_kategoriler"])
        invalid_gold_labels.update(gold - set(KATEGORILER))
        invalid_prediction_labels.update(predicted - set(KATEGORILER))
        if predicted == gold:
            exact_matches += 1
        first = row.get("degerlendirici_1_kategoriler", "")
        second = row.get("degerlendirici_2_kategoriler", "")
        if first.strip() and second.strip():
            first_labels.append(_label_set(first))
            second_labels.append(_label_set(second))

    micro_precision = _safe_divide(aggregate_tp, aggregate_tp + aggregate_fp)
    micro_recall = _safe_divide(aggregate_tp, aggregate_tp + aggregate_fn)
    micro_f1 = _safe_divide(2 * micro_precision * micro_recall, micro_precision + micro_recall)
    macro_f1 = _safe_divide(sum(row["f1"] for row in category_metrics.values()), len(category_metrics))
    agreement = {
        "cift_etiketli_ornek_sayisi": len(first_labels),
        "tam_set_uyumu": _safe_divide(
            sum(first == second for first, second in zip(first_labels, second_labels)), len(first_labels)
        ),
        "kategori_kappa": {
            category: _binary_kappa(
                [category in labels for labels in first_labels],
                [category in labels for labels in second_labels],
            )
            for category in KATEGORILER
        },
    }
    return {
        "tamamlanan_ornek_sayisi": len(completed),
        "toplam_satir_sayisi": len(rows),
        "prediction_column": prediction_column,
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        "macro_f1": macro_f1,
        "tam_set_dogrulugu": _safe_divide(exact_matches, len(completed)),
        "kategori_metrikleri": category_metrics,
        "degerlendiriciler_arasi_uyum": agreement,
        "gecersiz_uzlasim_etiketleri": sorted(invalid_gold_labels),
        "gecersiz_tahmin_etiketleri": sorted(invalid_prediction_labels),
    }


def format_symptom_category_report(result, source_csv):
    lines = [
        "# Semptom Kategori Doğrulama Raporu",
        "",
        f"Kaynak: `{source_csv}`",
        "",
        f"- Tamamlanan uzman uzlaşı örneği: {result['tamamlanan_ornek_sayisi']} / {result['toplam_satir_sayisi']}",
        f"- Değerlendirilen tahmin sütunu: `{result['prediction_column']}`",
        f"- Micro precision / recall / F1: {result['micro_precision']:.3f} / {result['micro_recall']:.3f} / {result['micro_f1']:.3f}",
        f"- Macro F1: {result['macro_f1']:.3f}",
        f"- Tam etiket kümesi doğruluğu: {result['tam_set_dogrulugu']:.3f}",
        "",
        "## Kategori bazında sonuçlar",
        "",
        "| Kategori | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for category, metrics in result["kategori_metrikleri"].items():
        lines.append(
            f"| {category} | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} | "
            f"{metrics['precision']:.3f} | {metrics['recall']:.3f} | {metrics['f1']:.3f} |"
        )
    agreement = result["degerlendiriciler_arasi_uyum"]
    lines.extend([
        "",
        "## Değerlendiriciler arası uyum",
        "",
        f"- Çift etiketli örnek: {agreement['cift_etiketli_ornek_sayisi']}",
        f"- Tam etiket kümesi uyumu: {agreement['tam_set_uyumu']:.3f}",
    ])
    for category, kappa in agreement["kategori_kappa"].items():
        if kappa is not None:
            lines.append(f"- {category}: Cohen's kappa {kappa:.3f}")
    if result["gecersiz_uzlasim_etiketleri"] or result["gecersiz_tahmin_etiketleri"]:
        lines.extend(["", "## Kontrol gerektiren etiketler", ""])
        if result["gecersiz_uzlasim_etiketleri"]:
            lines.append("- Uzlaşı: " + ", ".join(result["gecersiz_uzlasim_etiketleri"]))
        if result["gecersiz_tahmin_etiketleri"]:
            lines.append("- Tahmin: " + ", ".join(result["gecersiz_tahmin_etiketleri"]))
    return "\n".join(lines)

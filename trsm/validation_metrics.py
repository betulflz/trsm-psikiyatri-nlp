import csv
import re

from .drug_matching import build_surface_form_index, match_drug

MISSING_DRUGS_PATTERN = re.compile(r"^yanlış[,\s]+(.+?)\s+eksik$", re.IGNORECASE)


def parse_missing_drugs(note):
    if not note or not note.strip():
        return []
    match = MISSING_DRUGS_PATTERN.match(note.strip())
    if not match:
        return None
    drugs_part = match.group(1)
    return [d.strip() for d in drugs_part.split(",") if d.strip()]


def _drugs_in_row(sistem_ilac_bulgusu):
    if not sistem_ilac_bulgusu.strip():
        return set()
    names = set()
    for entry in sistem_ilac_bulgusu.split(" | "):
        name = re.sub(r"\s*\([^)]*\)\s*$", "", entry).strip()
        if name:
            names.add(name)
    return names


def _resolve_official_name(noted_name, surface_form_index):
    if not surface_form_index:
        return noted_name
    match = match_drug(noted_name, surface_form_index)
    return match[0] if match else noted_name


def compute_drug_precision_recall(csv_path, drug_dictionary=None):
    surface_form_index = (
        build_surface_form_index(drug_dictionary) if drug_dictionary else None
    )

    tp = 0
    fp = 0
    fn = 0
    missing_drugs = []
    unparseable_notes = []

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))

    for row in rows:
        note = row["ilac_dogru_mu"]
        found_drugs = _drugs_in_row(row["sistem_ilac_bulgusu"])
        noted_missing = parse_missing_drugs(note)
        if noted_missing is None:
            unparseable_notes.append(note)
            continue

        tp += len(found_drugs)
        for noted_name in noted_missing:
            official_name = _resolve_official_name(noted_name, surface_form_index)
            if official_name in found_drugs:
                # Already fixed since the note was written (e.g. a later
                # dictionary/pipeline update now matches it under its
                # official name) - the system's finding already counted
                # toward tp above, so this is not a current miss.
                continue
            fn += 1
            missing_drugs.append(noted_name)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "missing_drugs": missing_drugs,
        "unparseable_notes": unparseable_notes,
    }


def format_report(result, source_csv):
    lines = [
        "# İlaç Çıkarımı Precision/Recall Raporu",
        "",
        f"Kaynak: `{source_csv}`",
        "",
        f"- True Positive: {result['tp']}",
        f"- False Positive: {result['fp']}",
        f"- False Negative: {result['fn']}",
        f"- Precision: {result['precision']:.2f}",
        f"- Recall: {result['recall']:.2f}",
        f"- F1: {result['f1']:.2f}",
        "",
    ]

    if result["missing_drugs"]:
        lines.append("## Sistemde eksik bulunan ilaçlar")
        lines.append("")
        for drug in result["missing_drugs"]:
            lines.append(f"- {drug}")
        lines.append("")

    if result["unparseable_notes"]:
        lines.append("## Ayrıştırılamayan notlar (elle kontrol gerekiyor)")
        lines.append("")
        for note in result["unparseable_notes"]:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)

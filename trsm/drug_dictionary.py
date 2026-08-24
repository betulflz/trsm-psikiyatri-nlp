import csv


def load_drug_dictionary(csv_path):
    entries = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resmi_ad = row["resmi_ad"].strip()
            variations = [resmi_ad]
            raw_variations = (row.get("varyasyonlar") or "").strip()
            if raw_variations:
                variations.extend(
                    v.strip() for v in raw_variations.split("|") if v.strip()
                )
            entries[resmi_ad] = variations
    return entries

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


def load_drug_dictionary_into_db(conn, drug_dictionary):
    cur = conn.cursor()
    for resmi_ad, variations in drug_dictionary.items():
        cur.execute(
            "INSERT OR IGNORE INTO ilac_sozluk (resmi_ad) VALUES (?)", (resmi_ad,)
        )
        cur.execute("SELECT id FROM ilac_sozluk WHERE resmi_ad = ?", (resmi_ad,))
        ilac_sozluk_id = cur.fetchone()[0]
        for varyasyon in variations:
            cur.execute(
                """INSERT INTO ilac_varyasyon (ilac_sozluk_id, varyasyon)
                   VALUES (?, ?)""",
                (ilac_sozluk_id, varyasyon),
            )
    conn.commit()

import csv
import random

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_field(value):
    if isinstance(value, str) and value.startswith(CSV_FORMULA_PREFIXES):
        return "'" + value
    return value


def export_validation_sample(conn, output_csv, sample_size=30, seed=42):
    cur = conn.cursor()
    cur.execute("SELECT id FROM hasta")
    hasta_ids = [row[0] for row in cur.fetchall()]
    random.Random(seed).shuffle(hasta_ids)
    sample_ids = hasta_ids[:sample_size]

    rows = []
    if sample_ids:
        placeholders = ",".join("?" * len(sample_ids))
        cur.execute(
            f"""SELECT h.dosya_adi, z.tarih, z.ham_mudahale_metni, z.ham_sonuc_metni
                FROM ziyaret z JOIN hasta h ON h.id = z.hasta_id
                WHERE z.hasta_id IN ({placeholders})
                ORDER BY h.dosya_adi, z.tarih""",
            sample_ids,
        )
        rows = cur.fetchall()

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
            "manuel_ilac_notu", "manuel_semptom_notu",
        ])
        for row in rows:
            sanitized = [_sanitize_csv_field(field) for field in row]
            writer.writerow(sanitized + ["", ""])


def export_validation_sample_with_predictions(conn, output_csv, sample_size=30, seed=42):
    """Like export_validation_sample, but includes the pipeline's own findings
    (matched drug names, extracted symptom phrases) alongside the raw text, so
    a reviewer only needs to check "does this word really appear in this text"
    (yes/no) rather than transcribe drug names from scratch — no clinical
    judgment required, only text verification."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM hasta")
    hasta_ids = [row[0] for row in cur.fetchall()]
    random.Random(seed).shuffle(hasta_ids)
    sample_ids = hasta_ids[:sample_size]

    rows = []
    if sample_ids:
        placeholders = ",".join("?" * len(sample_ids))
        cur.execute(
            f"""SELECT
                    h.dosya_adi,
                    z.tarih,
                    z.ham_mudahale_metni,
                    z.ham_sonuc_metni,
                    (SELECT group_concat(ik.ilac_adi_normalize || ' (' || ik.eslesme_guveni || ')', ' | ')
                     FROM ilac_kullanimi ik WHERE ik.ziyaret_id = z.id) as sistem_ilac_bulgusu,
                    (SELECT group_concat(sk.ifade_ham, ' | ')
                     FROM semptom_kaydi sk WHERE sk.ziyaret_id = z.id) as sistem_semptom_bulgusu
                FROM ziyaret z JOIN hasta h ON h.id = z.hasta_id
                WHERE z.hasta_id IN ({placeholders})
                ORDER BY h.dosya_adi, z.tarih""",
            sample_ids,
        )
        rows = cur.fetchall()

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
            "sistem_ilac_bulgusu", "ilac_dogru_mu",
            "sistem_semptom_bulgusu", "semptom_dogru_mu",
        ])
        for row in rows:
            dosya_adi, tarih, mudahale, sonuc, ilac_bulgusu, semptom_bulgusu = row
            sanitized = [_sanitize_csv_field(f) for f in (dosya_adi, tarih, mudahale, sonuc)]
            writer.writerow(sanitized + [
                _sanitize_csv_field(ilac_bulgusu) or "", "",
                _sanitize_csv_field(semptom_bulgusu) or "", "",
            ])

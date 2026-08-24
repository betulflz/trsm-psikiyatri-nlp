from .dose_extraction import extract_dose_frequency
from .drug_matching import extract_candidates, match_drug

WINDOW_SIZE = 40
PROXIMITY_GAP = 3


def extract_medications_from_text(text, surface_form_index, threshold=85):
    if not text:
        return []

    raw_matches = []
    for candidate, start, end in extract_candidates(text):
        match = match_drug(candidate, surface_form_index, threshold=threshold)
        if match is None:
            continue
        resmi_ad, score = match
        raw_matches.append({
            "ilac_adi_normalize": resmi_ad,
            "ilac_adi_ham": candidate,
            "start": start,
            "end": end,
            "eslesme_guveni": score,
        })

    raw_matches.sort(key=lambda m: (m["ilac_adi_normalize"], m["start"]))

    kept = []
    last_by_drug = {}
    for m in raw_matches:
        resmi_ad = m["ilac_adi_normalize"]
        prev = last_by_drug.get(resmi_ad)
        if prev is not None and m["start"] - prev["end"] <= PROXIMITY_GAP:
            if m["eslesme_guveni"] > prev["eslesme_guveni"]:
                kept[kept.index(prev)] = m
                last_by_drug[resmi_ad] = m
            # else: m is a weaker duplicate of prev, discard it
        else:
            kept.append(m)
            last_by_drug[resmi_ad] = m

    kept_by_start = sorted(kept, key=lambda m: m["start"])
    next_start_by_id = {
        id(kept_by_start[i]): kept_by_start[i + 1]["start"]
        for i in range(len(kept_by_start) - 1)
    }

    results = []
    for m in kept:
        max_end = m["end"] + WINDOW_SIZE
        next_start = next_start_by_id.get(id(m))
        if next_start is not None:
            max_end = min(max_end, next_start)
        window = text[m["end"] : max_end]
        doz, siklik = extract_dose_frequency(window)
        results.append({
            "ilac_adi_normalize": m["ilac_adi_normalize"],
            "ilac_adi_ham": m["ilac_adi_ham"],
            "doz": doz,
            "siklik": siklik,
            "eslesme_guveni": m["eslesme_guveni"],
        })
    return results


def run_medication_extraction(conn, surface_form_index, threshold=85):
    cur = conn.cursor()
    cur.execute("SELECT id, ham_mudahale_metni, ham_sonuc_metni FROM ziyaret")
    rows = cur.fetchall()

    for ziyaret_id, mudahale, sonuc in rows:
        combined_text = " ".join(t for t in [mudahale, sonuc] if t)
        medications = extract_medications_from_text(
            combined_text, surface_form_index, threshold=threshold
        )
        for med in medications:
            cur.execute(
                """INSERT INTO ilac_kullanimi
                   (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ziyaret_id,
                    med["ilac_adi_normalize"],
                    med["ilac_adi_ham"],
                    med["doz"],
                    med["siklik"],
                    med["eslesme_guveni"],
                ),
            )
    conn.commit()

"""Privacy-preserving symptom search constrained by a user demographic profile."""

from .demographic_analysis import (
    VERIFIED_BIRTH_DATE_SOURCES,
    VERIFIED_GENDER_SOURCES,
    age_group_for_age,
)
from .demographic_extraction import calculate_age_at_visit
from .recommendation import compute_drug_statistics


MIN_COMPATIBLE_VISITS = 20
MIN_COMPATIBLE_PATIENTS = 5
VALID_GENDERS = {"Erkek", "Kadın"}


def normalize_profile(age, gender):
    """Validate public user input and derive the non-identifying age group."""
    try:
        age = int(age)
    except (TypeError, ValueError) as exc:
        raise ValueError("Yaş 15 ile 120 arasında tam sayı olmalı.") from exc
    if not 15 <= age <= 120:
        raise ValueError("Yaş 15 ile 120 arasında olmalı.")
    if gender not in VALID_GENDERS:
        raise ValueError("Cinsiyet Kadın veya Erkek seçilmeli.")
    return {"yas": age, "yas_grubu": age_group_for_age(age), "cinsiyet": gender}


def _best_similarity_by_visit(similar_matches):
    """Collapse multiple matching phrases from a visit to its best score."""
    best_scores = {}
    for match in similar_matches:
        visit_id = match["ziyaret_id"]
        score = float(match["benzerlik"])
        best_scores[visit_id] = max(score, best_scores.get(visit_id, float("-inf")))
    return best_scores


def profile_matched_visits(conn, similar_matches, age, gender):
    """Keep semantically similar visits only when historical profile matches.

    Historical gender and birth dates must be verified.  Age is calculated at
    the historical visit date, then compared as a broad pre-defined age group
    rather than as an unreliable exact-age match.  No raw historical symptom
    text leaves this function.
    """
    profile = normalize_profile(age, gender)
    best_scores = _best_similarity_by_visit(similar_matches)
    if not best_scores:
        return profile, [], 0

    placeholders = ",".join("?" * len(best_scores))
    rows = conn.execute(
        f"""SELECT z.id, z.hasta_id, z.tarih, h.cinsiyet,
                   h.cinsiyet_kaynagi, h.dogum_tarihi, h.dogum_tarihi_kaynagi
              FROM ziyaret z JOIN hasta h ON h.id = z.hasta_id
              WHERE z.id IN ({placeholders})""",
        list(best_scores),
    ).fetchall()
    compatible = []
    for visit_id, patient_id, visit_date, historical_gender, gender_source, birth_date, birth_source in rows:
        if historical_gender != profile["cinsiyet"] or gender_source not in VERIFIED_GENDER_SOURCES:
            continue
        if birth_source not in VERIFIED_BIRTH_DATE_SOURCES:
            continue
        historical_age = calculate_age_at_visit(birth_date, visit_date)
        if age_group_for_age(historical_age) != profile["yas_grubu"]:
            continue
        compatible.append({
            "ziyaret_id": visit_id,
            "hasta_id": patient_id,
            "benzerlik": best_scores[visit_id],
        })
    return profile, compatible, len(best_scores)


def compute_profiled_recommendation(
    conn, similar_matches, age, gender, guven_esigi=90,
    min_visits=MIN_COMPATIBLE_VISITS, min_patients=MIN_COMPATIBLE_PATIENTS,
):
    """Return aggregate medication patterns for symptom + demographic matches.

    The return value intentionally contains no patient names or historical raw
    symptom phrases.  It is an observational summary, never a prescription.
    """
    profile, compatible, semantic_visit_count = profile_matched_visits(
        conn, similar_matches, age, gender
    )
    visit_ids = [row["ziyaret_id"] for row in compatible]
    patient_count = len({row["hasta_id"] for row in compatible})
    statistics = compute_drug_statistics(conn, visit_ids, guven_esigi=guven_esigi)
    is_small_sample = len(visit_ids) < min_visits or patient_count < min_patients
    if not visit_ids:
        status = "demografik_eslesme_yok"
    elif is_small_sample:
        status = "kucuk_orneklem"
    elif not statistics:
        status = "ilac_kaydi_yok"
    else:
        status = "yeterli_veri"
    return {
        **profile,
        "semantik_eslesen_ziyaret_sayisi": semantic_visit_count,
        "uyumlu_ziyaret_sayisi": len(visit_ids),
        "uyumlu_hasta_sayisi": patient_count,
        "en_yuksek_benzerlik": round(max((row["benzerlik"] for row in compatible), default=0), 3),
        "kucuk_orneklem": is_small_sample,
        "durum": status,
        "ilaclar": statistics,
    }

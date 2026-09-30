"""Descriptive medication analysis by validated demographic attributes."""

import pandas as pd

from .demographic_extraction import calculate_age_at_visit

AGE_GROUPS = (
    (15, 17, "15-17"),
    (18, 29, "18-29"),
    (30, 44, "30-44"),
    (45, 59, "45-59"),
    (60, None, "60+"),
)
VERIFIED_BIRTH_DATE_SOURCES = {"RH.FR.002_ocr_ve_yas_kurali", "manual_review"}
VERIFIED_GENDER_SOURCES = {"RH.FR.002_checkbox", "manual_review"}
OUTPUT_COLUMNS = [
    "demografik_grup", "ilac", "sayi", "yuzde",
    "ziyaret_sayisi", "hasta_sayisi", "kucuk_orneklem",
]
PATIENT_OUTPUT_COLUMNS = [
    "demografik_grup", "ilac", "ilaci_olan_hasta_sayisi",
    "grupta_ilac_kaydi_olan_hasta_sayisi", "hasta_yuzdesi",
    "kucuk_orneklem",
]


def age_group_for_age(age):
    if age is None:
        return None
    for minimum, maximum, label in AGE_GROUPS:
        if age >= minimum and (maximum is None or age <= maximum):
            return label
    return None


def demographic_medication_records(conn, guven_esigi=90):
    """Return medication records enriched only with validated demographics.

    Medication occurrences are retained to match the project's existing drug
    statistics. `yas` is calculated on the visit date, never at run time.
    """
    query = """
        SELECT h.id, h.cinsiyet, h.cinsiyet_kaynagi,
               h.dogum_tarihi, h.dogum_tarihi_kaynagi,
               z.id, z.tarih, ik.ilac_adi_normalize
        FROM ilac_kullanimi ik
        JOIN ziyaret z ON z.id = ik.ziyaret_id
        JOIN hasta h ON h.id = z.hasta_id
        WHERE ik.eslesme_guveni >= ?
    """
    rows = conn.execute(query, (guven_esigi,)).fetchall()
    records = []
    for (
        hasta_id, cinsiyet, cinsiyet_kaynagi,
        dogum_tarihi, dogum_tarihi_kaynagi,
        ziyaret_id, ziyaret_tarihi, ilac,
    ) in rows:
        age = None
        if dogum_tarihi_kaynagi in VERIFIED_BIRTH_DATE_SOURCES and ziyaret_tarihi:
            age = calculate_age_at_visit(dogum_tarihi, ziyaret_tarihi)
        verified_gender = (
            cinsiyet if cinsiyet_kaynagi in VERIFIED_GENDER_SOURCES else None
        )
        records.append({
            "hasta_id": hasta_id,
            "ziyaret_id": ziyaret_id,
            "ziyaret_tarihi": ziyaret_tarihi,
            "ilac": ilac,
            "yas": age,
            "yas_grubu": age_group_for_age(age),
            "cinsiyet": verified_gender,
        })
    return pd.DataFrame(records)


def demographic_drug_distribution(conn, demographic_dimension, guven_esigi=90, top_n=10, small_sample_threshold=20):
    """Compute within-group medication percentages for a demographic dimension.

    `demographic_dimension` can be `yas_grubu` or `cinsiyet`. Percentages
    describe medication records in that group, not treatment effectiveness or
    population prevalence.
    """
    if demographic_dimension not in {"yas_grubu", "cinsiyet"}:
        raise ValueError("demographic_dimension 'yas_grubu' veya 'cinsiyet' olmalı.")

    records = demographic_medication_records(conn, guven_esigi)
    if records.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    records = records.dropna(subset=[demographic_dimension])
    if records.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    group_totals = records.groupby(demographic_dimension).size().rename("toplam_kayit")
    group_visits = records.groupby(demographic_dimension)["ziyaret_id"].nunique().rename("ziyaret_sayisi")
    group_patients = records.groupby(demographic_dimension)["hasta_id"].nunique().rename("hasta_sayisi")
    result = (
        records.groupby([demographic_dimension, "ilac"]).size().rename("sayi").reset_index()
        .join(group_totals, on=demographic_dimension)
        .join(group_visits, on=demographic_dimension)
        .join(group_patients, on=demographic_dimension)
    )
    result["yuzde"] = (100 * result["sayi"] / result["toplam_kayit"]).round(1)
    # Repeated visits from a handful of people should not make a demographic
    # group appear well-powered. Both visit and patient counts must clear the
    # threshold for an unflagged descriptive comparison.
    result["kucuk_orneklem"] = (
        (result["ziyaret_sayisi"] < small_sample_threshold)
        | (result["hasta_sayisi"] < small_sample_threshold)
    )
    result = result.sort_values(
        [demographic_dimension, "sayi", "ilac"], ascending=[True, False, True]
    )
    if top_n is not None:
        result = result.groupby(demographic_dimension, group_keys=False).head(top_n)
    return result.rename(columns={demographic_dimension: "demografik_grup"})[OUTPUT_COLUMNS].reset_index(drop=True)


def demographic_patient_drug_distribution(
    conn, demographic_dimension, guven_esigi=90, top_n=10,
    small_sample_threshold=20,
):
    """Show the share of unique patients with at least one drug record.

    This complementary measure counts a patient once per drug and demographic
    group, preventing repeat visits from inflating a medication's prominence.
    The denominator is patients with at least one high-confidence medication
    record in that group, so it describes the observed TRSM records only.
    """
    if demographic_dimension not in {"yas_grubu", "cinsiyet"}:
        raise ValueError("demographic_dimension 'yas_grubu' veya 'cinsiyet' olmalı.")

    records = demographic_medication_records(conn, guven_esigi)
    records = records.dropna(subset=[demographic_dimension])
    if records.empty:
        return pd.DataFrame(columns=PATIENT_OUTPUT_COLUMNS)

    group_patients = (
        records.groupby(demographic_dimension)["hasta_id"].nunique()
        .rename("grupta_ilac_kaydi_olan_hasta_sayisi")
    )
    result = (
        records.drop_duplicates([demographic_dimension, "hasta_id", "ilac"])
        .groupby([demographic_dimension, "ilac"])["hasta_id"].nunique()
        .rename("ilaci_olan_hasta_sayisi")
        .reset_index()
        .join(group_patients, on=demographic_dimension)
    )
    result["hasta_yuzdesi"] = (
        100 * result["ilaci_olan_hasta_sayisi"]
        / result["grupta_ilac_kaydi_olan_hasta_sayisi"]
    ).round(1)
    result["kucuk_orneklem"] = (
        result["grupta_ilac_kaydi_olan_hasta_sayisi"] < small_sample_threshold
    )
    result = result.sort_values(
        [demographic_dimension, "ilaci_olan_hasta_sayisi", "ilac"],
        ascending=[True, False, True],
    )
    if top_n is not None:
        result = result.groupby(demographic_dimension, group_keys=False).head(top_n)
    return result.rename(columns={demographic_dimension: "demografik_grup"})[
        PATIENT_OUTPUT_COLUMNS
    ].reset_index(drop=True)


def demographic_coverage_summary(conn):
    """Summarize patients eligible for each demographic analysis."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hasta")
    total_patients = cur.fetchone()[0]
    cur.execute(
        """SELECT COUNT(*) FROM hasta
           WHERE dogum_tarihi IS NOT NULL
             AND dogum_tarihi_kaynagi IN ('RH.FR.002_ocr_ve_yas_kurali', 'manual_review')"""
    )
    birth_date_patients = cur.fetchone()[0]
    cur.execute(
        """SELECT COUNT(*) FROM hasta
           WHERE cinsiyet IS NOT NULL
             AND cinsiyet_kaynagi IN ('RH.FR.002_checkbox', 'manual_review')"""
    )
    gender_patients = cur.fetchone()[0]
    cur.execute(
        """SELECT COUNT(DISTINCT h.id)
           FROM hasta h JOIN ziyaret z ON z.hasta_id = h.id
           WHERE h.dogum_tarihi IS NOT NULL
             AND h.dogum_tarihi_kaynagi IN ('RH.FR.002_ocr_ve_yas_kurali', 'manual_review')
             AND z.tarih IS NOT NULL"""
    )
    age_eligible_patients = cur.fetchone()[0]
    return {
        "toplam_hasta": total_patients,
        "dogum_tarihi_dogrulanmis_hasta": birth_date_patients,
        "yas_analizine_uygun_hasta": age_eligible_patients,
        "cinsiyet_dogrulanmis_hasta": gender_patients,
    }

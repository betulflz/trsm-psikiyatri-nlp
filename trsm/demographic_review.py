"""Local review and manual-correction support for demographic OCR data."""

import csv

from .demographic_extraction import (
    BIRTH_DATE_PATTERN,
    _earliest_visit_date,
    _form_pages_for_patient,
    _page_text,
    extract_gender,
    is_valid_birth_date,
)

VALID_GENDERS = {"Kadın", "Erkek"}


def build_demographic_review_rows(conn):
    """Return only RH.FR.002 records that need an OCR/manual decision.

    The output deliberately records the file name so the project owner can
    locate the source document locally. It must not be committed or shared.
    """
    cur = conn.cursor()
    cur.execute(
        """SELECT id, dosya_adi, dogum_tarihi, cinsiyet
           FROM hasta ORDER BY id"""
    )
    rows = []
    for hasta_id, dosya_adi, dogum_tarihi, cinsiyet in cur.fetchall():
        pages = _form_pages_for_patient(conn, hasta_id)
        if not pages:
            continue

        earliest_visit = _earliest_visit_date(conn, hasta_id)
        raw_dates = []
        valid_dates = []
        gender_values = []
        for page in pages:
            text = _page_text(conn, hasta_id, page)
            page_dates = BIRTH_DATE_PATTERN.findall(text)
            raw_dates.extend(page_dates)
            valid_dates.extend(
                value for value in page_dates
                if is_valid_birth_date(value, earliest_visit)
            )
            gender = extract_gender(text)
            if gender:
                gender_values.append(gender)

        unique_valid_dates = list(dict.fromkeys(valid_dates))
        unique_genders = list(dict.fromkeys(gender_values))
        notes = []
        if dogum_tarihi is None:
            if not raw_dates:
                notes.append("Doğum tarihi OCR metninde yok")
            elif not unique_valid_dates:
                notes.append("Tarih adayları takvim/yaş kuralını geçmedi")
            else:
                notes.append("Birden fazla farklı makul doğum tarihi var")
        if cinsiyet is None:
            if not unique_genders:
                notes.append("Cinsiyet kutusu okunamadı veya işaret belirsiz")
            else:
                notes.append("Birden fazla farklı cinsiyet işareti var")
        if dogum_tarihi is not None and earliest_visit is None:
            notes.append("Yaş analizi için tarihli ziyaret bulunamadı")

        if notes:
            rows.append({
                "hasta_id": hasta_id,
                "dosya_adi": dosya_adi,
                "form_sayfalari": " | ".join(map(str, pages)),
                "en_erken_tarihli_ziyaret": earliest_visit or "",
                "dogum_tarihi_ocr_adaylari": " | ".join(dict.fromkeys(raw_dates)),
                "yas_kuralini_gecen_adaylar": " | ".join(unique_valid_dates),
                "cinsiyet_ocr_adaylari": " | ".join(unique_genders),
                "inceleme_nedeni": "; ".join(notes),
            })
    return rows


def write_demographic_review_csv(conn, path):
    fieldnames = [
        "hasta_id", "dosya_adi", "form_sayfalari", "en_erken_tarihli_ziyaret",
        "dogum_tarihi_ocr_adaylari", "yas_kuralini_gecen_adaylar",
        "cinsiyet_ocr_adaylari", "inceleme_nedeni",
    ]
    rows = build_demographic_review_rows(conn)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def write_demographic_override_sheet(conn, path):
    """Create a ready-to-fill local worksheet for manual verification."""
    review_rows = build_demographic_review_rows(conn)
    fieldnames = [
        "dosya_adi", "dogum_tarihi", "cinsiyet", "form_sayfalari",
        "en_erken_tarihli_ziyaret", "dogum_tarihi_ocr_adaylari",
        "cinsiyet_ocr_adaylari", "inceleme_nedeni",
    ]
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in review_rows:
            writer.writerow({
                "dosya_adi": row["dosya_adi"],
                "dogum_tarihi": "",
                "cinsiyet": "",
                "form_sayfalari": row["form_sayfalari"],
                "en_erken_tarihli_ziyaret": row["en_erken_tarihli_ziyaret"],
                "dogum_tarihi_ocr_adaylari": row["dogum_tarihi_ocr_adaylari"],
                "cinsiyet_ocr_adaylari": row["cinsiyet_ocr_adaylari"],
                "inceleme_nedeni": row["inceleme_nedeni"],
            })
    return len(review_rows)


def apply_manual_demographic_overrides(conn, path):
    """Apply explicit, user-reviewed corrections from a local CSV.

    Expected columns: dosya_adi, dogum_tarihi, cinsiyet. Blank fields leave
    the existing value unchanged. The source is persisted as manual_review.
    """
    cur = conn.cursor()
    applied = 0
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")
        required = {"dosya_adi", "dogum_tarihi", "cinsiyet"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Düzeltme CSV'si dosya_adi, dogum_tarihi ve cinsiyet kolonlarını içermeli.")
        for row in reader:
            dosya_adi = (row.get("dosya_adi") or "").strip()
            if not dosya_adi:
                continue
            cur.execute("SELECT id FROM hasta WHERE dosya_adi = ?", (dosya_adi,))
            found = cur.fetchone()
            if found is None:
                raise ValueError(f"Düzeltme CSV'sindeki hasta bulunamadı: {dosya_adi}")
            hasta_id = found[0]
            birth_date = (row.get("dogum_tarihi") or "").strip() or None
            gender = (row.get("cinsiyet") or "").strip() or None
            if birth_date and not is_valid_birth_date(birth_date, _earliest_visit_date(conn, hasta_id)):
                raise ValueError(f"Geçersiz doğum tarihi düzeltmesi: {dosya_adi}")
            if gender and gender not in VALID_GENDERS:
                raise ValueError(f"Geçersiz cinsiyet düzeltmesi: {dosya_adi}")
            if birth_date:
                cur.execute(
                    "UPDATE hasta SET dogum_tarihi=?, dogum_tarihi_kaynagi='manual_review' WHERE id=?",
                    (birth_date, hasta_id),
                )
            if gender:
                cur.execute(
                    "UPDATE hasta SET cinsiyet=?, cinsiyet_kaynagi='manual_review' WHERE id=?",
                    (gender, hasta_id),
                )
            if birth_date or gender:
                applied += 1
    conn.commit()
    return applied

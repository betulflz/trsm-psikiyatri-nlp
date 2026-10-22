import re
from datetime import date, datetime

FORM_TAG = "RH.FR.002"
BIRTH_DATE_PATTERN = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
GENDER_CHECKBOX_PATTERN = re.compile(r"([☑☐])\s*(Kadın|Erkek)")
MIN_BIRTH_YEAR = 1900
MAX_BIRTH_YEAR = 2008
MAX_PLAUSIBLE_AGE = 120


def _parse_birth_date(value):
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        return None


def _parse_visit_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def calculate_age_at_visit(birth_date, visit_date):
    """Return the completed age on a visit date, or None for invalid dates."""
    birth = _parse_birth_date(birth_date)
    visit = _parse_visit_date(visit_date)
    if birth is None or visit is None or birth > visit:
        return None
    return visit.year - birth.year - ((visit.month, visit.day) < (birth.month, birth.day))


def is_valid_birth_date(candidate, earliest_visit_date=None):
    """Validate an OCR date as a plausible adult patient's birth date.

    The adult requirement is assessed on the patient's earliest dated visit,
    rather than against today's date. This prevents document/revision dates
    from being mistaken for birth dates and keeps the rule reproducible.
    """
    birth = _parse_birth_date(candidate)
    if birth is None or not MIN_BIRTH_YEAR <= birth.year <= MAX_BIRTH_YEAR:
        return False

    if earliest_visit_date is None:
        return True

    age = calculate_age_at_visit(candidate, earliest_visit_date)
    return age is not None and 18 <= age <= MAX_PLAUSIBLE_AGE


def extract_birth_date(text, earliest_visit_date=None):
    if not text:
        return None
    candidates = BIRTH_DATE_PATTERN.findall(text)
    valid_candidates = [
        candidate
        for candidate in candidates
        if is_valid_birth_date(candidate, earliest_visit_date)
    ]
    # A form page with multiple plausible historical dates is ambiguous. Do
    # not silently pick one; it belongs in the local OCR review list instead.
    unique_candidates = list(dict.fromkeys(valid_candidates))
    return unique_candidates[0] if len(unique_candidates) == 1 else None


def extract_gender(text):
    if not text:
        return None
    checked = [label for box, label in GENDER_CHECKBOX_PATTERN.findall(text) if box == "☑"]
    if len(checked) == 1:
        return checked[0]
    return None


def ensure_demographic_columns(conn):
    """Migrate pre-demographic local databases without rebuilding them."""
    for column in ("cinsiyet_kaynagi", "dogum_tarihi_kaynagi"):
        conn.execute(f"ALTER TABLE hasta ADD COLUMN IF NOT EXISTS {column} TEXT")
    conn.commit()


def _form_pages_for_patient(conn, hasta_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT DISTINCT sayfa_no FROM ziyaret
           WHERE hasta_id = %s
             AND (ham_mudahale_metni ILIKE %s OR ham_sonuc_metni ILIKE %s)
           ORDER BY sayfa_no""",
        (hasta_id, f"%{FORM_TAG}%", f"%{FORM_TAG}%"),
    )
    return [row[0] for row in cur.fetchall()]


def _page_text(conn, hasta_id, sayfa_no):
    cur = conn.cursor()
    cur.execute(
        """SELECT ham_mudahale_metni, ham_sonuc_metni FROM ziyaret
           WHERE hasta_id = %s AND sayfa_no = %s ORDER BY id""",
        (hasta_id, sayfa_no),
    )
    return " ".join(text for row in cur.fetchall() for text in row if text)


def _earliest_visit_date(conn, hasta_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT MIN(tarih) FROM ziyaret WHERE hasta_id = %s AND tarih IS NOT NULL",
        (hasta_id,),
    )
    return cur.fetchone()[0]


def run_demographic_extraction(conn):
    ensure_demographic_columns(conn)
    cur = conn.cursor()
    cur.execute(
        """SELECT DISTINCT hasta_id FROM ziyaret
           WHERE ham_mudahale_metni ILIKE %s OR ham_sonuc_metni ILIKE %s
           ORDER BY hasta_id""",
        (f"%{FORM_TAG}%", f"%{FORM_TAG}%"),
    )
    tagged_rows = cur.fetchall()

    for (hasta_id,) in tagged_rows:
        cur.execute(
            """SELECT cinsiyet, dogum_tarihi, cinsiyet_kaynagi, dogum_tarihi_kaynagi
               FROM hasta WHERE id = %s""",
            (hasta_id,),
        )
        existing_gender, existing_birth_date, existing_gender_source, existing_birth_source = cur.fetchone()
        earliest_visit = _earliest_visit_date(conn, hasta_id)
        birth_dates = []
        genders = []
        for sayfa_no in _form_pages_for_patient(conn, hasta_id):
            page_text = _page_text(conn, hasta_id, sayfa_no)
            birth_date = extract_birth_date(page_text, earliest_visit)
            gender = extract_gender(page_text)
            if birth_date:
                birth_dates.append(birth_date)
            if gender:
                genders.append(gender)

        unique_birth_dates = list(dict.fromkeys(birth_dates))
        unique_genders = list(dict.fromkeys(genders))
        dogum_tarihi = unique_birth_dates[0] if len(unique_birth_dates) == 1 else None
        cinsiyet = unique_genders[0] if len(unique_genders) == 1 else None
        birth_source = "RH.FR.002_ocr_ve_yas_kurali" if dogum_tarihi else None
        gender_source = "RH.FR.002_checkbox" if cinsiyet else None
        # Explicit local review (including a confirmed missing/incomplete
        # value) always wins over a later automatic rerun.
        if existing_birth_source and existing_birth_source.startswith("manual_"):
            dogum_tarihi, birth_source = existing_birth_date, existing_birth_source
        if existing_gender_source and existing_gender_source.startswith("manual_"):
            cinsiyet, gender_source = existing_gender, existing_gender_source
        cur.execute(
            """UPDATE hasta
               SET cinsiyet = %s, dogum_tarihi = %s,
                   cinsiyet_kaynagi = %s, dogum_tarihi_kaynagi = %s
               WHERE id = %s""",
            (
                cinsiyet,
                dogum_tarihi,
                gender_source,
                birth_source,
                hasta_id,
            ),
        )
    conn.commit()

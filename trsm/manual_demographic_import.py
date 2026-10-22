"""Import user-reviewed demographic data from the local Excel workbook."""

import csv
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime

from openpyxl import load_workbook

from .demographic_extraction import (
    _earliest_visit_date,
    ensure_demographic_columns,
    is_valid_birth_date,
)
from .db import table_exists
from .patient_consolidation import build_document_folder_map

REQUIRED_HEADERS = ["dosya_adi", "dogum_tarihi", "cinsiyet"]
VALID_GENDERS = {"erkek": "Erkek", "kadın": "Kadın"}

# These are explicit corrections confirmed during the manual-review process.
# They are deliberately not fuzzy matches: any new spelling discrepancy must
# be reviewed and added here only after confirmation.
APPROVED_FILENAME_ALIASES = {
    "begüm aslan mert.pdf": "Begüm Arslan Mert.pdf",
}


def _filename_key(value):
    text = unicodedata.normalize("NFC", str(value)).strip()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"\s*\.pdf$", ".pdf", text, flags=re.IGNORECASE).casefold()


def _stem_key(value):
    return re.sub(r"\.pdf$", "", _filename_key(value), flags=re.IGNORECASE)


def _person_key(value):
    return _stem_key(value)


def _patient_lookup(conn):
    has_trace_table = table_exists(conn, "hasta_dosya")
    trace_count = (
        conn.execute("SELECT COUNT(*) FROM hasta_dosya").fetchone()[0]
        if has_trace_table else 0
    )
    by_folder = {}
    if trace_count:
        rows = conn.execute(
            """SELECT hd.hasta_id, hd.dosya_adi, hd.kaynak_klasor, h.dosya_adi
               FROM hasta_dosya hd JOIN hasta h ON h.id = hd.hasta_id
               ORDER BY hd.id"""
        ).fetchall()
    else:
        rows = [(*row, None, row[1]) for row in conn.execute(
            "SELECT id, dosya_adi FROM hasta ORDER BY id"
        ).fetchall()]
    by_filename = {}
    by_stem = {}
    for hasta_id, filename, folder, canonical_filename in rows:
        match = (hasta_id, canonical_filename)
        by_filename[_filename_key(filename)] = match
        by_stem.setdefault(_stem_key(filename), []).append(match)
        if folder:
            folder_key = _person_key(folder)
            existing = by_folder.get(folder_key)
            # A folder is expected to represent one person.  Mark an
            # unexpected collision as ambiguous instead of choosing one.
            by_folder[folder_key] = match if existing in (None, match) else None
    return by_filename, by_stem, by_folder


def _match_patient(filename, by_filename, by_stem, by_folder, document_folders):
    alias_target = APPROVED_FILENAME_ALIASES.get(_filename_key(filename), filename)
    matched = by_filename.get(_filename_key(alias_target))
    if matched:
        return matched, None
    candidates = by_stem.get(_stem_key(alias_target), [])
    if len(candidates) == 1:
        return candidates[0], None

    # A workbook may refer to a PDF that exists in the source archive but was
    # absent from the original combined Excel.  Its source folder still lets
    # us join it to a consolidated person if that person has other visits.
    folder = document_folders.get(_filename_key(alias_target))
    if folder:
        matched = by_folder.get(_person_key(folder))
        if matched:
            return matched, None
        return None, "Kaynak PDF bulundu; toplu veritabanında ziyaret kaydı yok, analiz dışı bırakıldı"

    # Some entries omit the trailing document number (for example, a folder
    # has 'Kişi 1.pdf' but Excel contains 'Kişi.pdf').  This is safe only when
    # the normalized source-folder name maps to exactly one known person.
    matched = by_folder.get(_person_key(alias_target))
    if matched:
        return matched, None
    return None, "Veritabanında güvenli dosya adı eşleşmesi bulunamadı"


def _parse_manual_birth_date(value):
    if value is None or str(value).strip() == "":
        return None, "manual_incomplete"
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    text = str(value).strip()
    if "?" in text:
        return None, "manual_incomplete"
    try:
        return datetime.strptime(text, "%d.%m.%Y").date(), None
    except ValueError:
        return None, "manual_invalid"


def _normalize_gender(value):
    if value is None:
        return None
    text = unicodedata.normalize("NFC", str(value)).strip().casefold()
    return VALID_GENDERS.get(text)


def import_manual_demographics(conn, excel_path, source_roots=()):
    """Import reviewed values and return an audit report.

    A blank or question-mark date is an explicit manual finding: it clears an
    earlier automatic date and is marked `manual_incomplete`, so it cannot
    silently enter age analysis. A manually reviewed full date is the source
    of truth; only an invalid calendar/year value is rejected here. Visits
    occurring before age 15 are excluded later at analysis time, without
    discarding an otherwise valid birth date. Exact source-archive folder
    membership can join sibling PDFs after patient consolidation.  The sole
    spelling alias is an explicitly user-confirmed correction above.
    """
    ensure_demographic_columns(conn)
    workbook = load_workbook(excel_path, read_only=True, data_only=True)
    sheet = workbook.active
    headers = [sheet.cell(1, column).value for column in range(1, 4)]
    if headers != REQUIRED_HEADERS:
        raise ValueError(f"Beklenen Excel başlıkları: {REQUIRED_HEADERS}")

    by_filename, by_stem, by_folder = _patient_lookup(conn)
    document_folders = build_document_folder_map(source_roots) if source_roots else {}
    report = {
        "excel_satiri": 0,
        "eslesen_hasta": 0,
        "tam_dogum_tarihi": 0,
        "eksik_dogum_tarihi": 0,
        "gecersiz_dogum_tarihi": 0,
        "cinsiyet": 0,
        "inceleme_satirlari": [],
    }
    matched_rows = defaultdict(list)
    for excel_row, values in enumerate(
        sheet.iter_rows(min_row=2, max_col=3, values_only=True), start=2
    ):
        filename, raw_birth_date, raw_gender = values
        if not filename:
            continue
        report["excel_satiri"] += 1
        matched, unmatched_reason = _match_patient(
            filename, by_filename, by_stem, by_folder, document_folders
        )
        if matched is None:
            report["inceleme_satirlari"].append({
                "excel_satiri": excel_row,
                "dosya_adi": filename,
                "dogum_tarihi": raw_birth_date or "",
                "cinsiyet": raw_gender or "",
                "neden": unmatched_reason,
                "eslesen_dosya_adi": "",
            })
            continue
        hasta_id, matched_filename = matched
        matched_rows[hasta_id].append({
            "excel_satiri": excel_row,
            "dosya_adi": filename,
            "dogum_tarihi": raw_birth_date,
            "cinsiyet": raw_gender,
            "eslesen_dosya_adi": matched_filename,
        })

    cur = conn.cursor()
    for hasta_id, rows in matched_rows.items():
        report["eslesen_hasta"] += 1

        valid_birth_dates = set()
        invalid_birth_rows = []
        has_incomplete_birth_date = False
        genders = set()
        invalid_gender_rows = []
        for row in rows:
            birth_date, birth_status = _parse_manual_birth_date(row["dogum_tarihi"])
            if birth_date:
                formatted = birth_date.strftime("%d.%m.%Y")
                if is_valid_birth_date(formatted):
                    valid_birth_dates.add(formatted)
                else:
                    invalid_birth_rows.append((row, "Tarih takvim/yıl kuralını geçmiyor"))
            elif birth_status == "manual_incomplete":
                has_incomplete_birth_date = True
            else:
                invalid_birth_rows.append((row, "Doğum tarihi DD.MM.YYYY biçiminde değil"))

            gender = _normalize_gender(row["cinsiyet"])
            if gender:
                genders.add(gender)
            else:
                invalid_gender_rows.append(row)

        if len(valid_birth_dates) == 1:
            formatted_birth_date = valid_birth_dates.pop()
            birth_source = "manual_review"
            report["tam_dogum_tarihi"] += 1
        elif len(valid_birth_dates) > 1:
            formatted_birth_date = None
            birth_source = "manual_conflict"
            report["gecersiz_dogum_tarihi"] += 1
            invalid_birth_rows.append((
                rows[0],
                "Aynı kişi için birden fazla farklı manuel doğum tarihi var",
            ))
        elif invalid_birth_rows:
            formatted_birth_date = None
            birth_source = "manual_invalid"
            report["gecersiz_dogum_tarihi"] += 1
        else:
            formatted_birth_date = None
            birth_source = "manual_incomplete"
            report["eksik_dogum_tarihi"] += 1

        if len(genders) == 1:
            gender = genders.pop()
            gender_source = "manual_review"
            report["cinsiyet"] += 1
        elif len(genders) > 1:
            gender = None
            gender_source = "manual_conflict"
            invalid_gender_rows.append(rows[0])
        else:
            gender = None
            gender_source = "manual_invalid"

        for row, reason in invalid_birth_rows:
            report["inceleme_satirlari"].append({
                **row,
                "dogum_tarihi": row["dogum_tarihi"] or "",
                "cinsiyet": row["cinsiyet"] or "",
                "neden": reason,
            })
        for row in invalid_gender_rows:
            report["inceleme_satirlari"].append({
                **row,
                "dogum_tarihi": row["dogum_tarihi"] or "",
                "cinsiyet": row["cinsiyet"] or "",
                "neden": "Cinsiyet yalnızca kadın veya erkek olmalı",
            })

        cur.execute(
            """UPDATE hasta
               SET dogum_tarihi = %s, dogum_tarihi_kaynagi = %s,
                   cinsiyet = %s, cinsiyet_kaynagi = %s
               WHERE id = %s""",
            (formatted_birth_date, birth_source, gender, gender_source, hasta_id),
        )
    conn.commit()
    return report


def write_import_review_csv(report, output_path):
    fieldnames = [
        "excel_satiri", "dosya_adi", "dogum_tarihi", "cinsiyet",
        "neden", "eslesen_dosya_adi",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(report["inceleme_satirlari"])

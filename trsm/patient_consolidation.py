"""Consolidate document-level patient rows into real people using source folders."""

import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def _filename_key(value):
    text = unicodedata.normalize("NFC", str(value)).strip()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"\s*\.pdf$", ".pdf", text, flags=re.IGNORECASE).casefold()


def _person_key(value):
    text = unicodedata.normalize("NFC", str(value)).strip()
    return re.sub(r"\s+", " ", text).casefold()


def build_document_folder_map(source_roots):
    """Return an exact PDF filename -> source-folder (person) mapping.

    A PDF basename appearing under two different patient folders is ambiguous
    and therefore rejected instead of guessed.
    """
    folders_by_filename = defaultdict(set)
    display_filename = {}
    for root in map(Path, source_roots):
        for path in root.rglob("*.pdf"):
            if not path.is_file():
                continue
            filename_key = _filename_key(path.name)
            folders_by_filename[filename_key].add(
                unicodedata.normalize("NFC", path.parent.name).strip()
            )
            display_filename[filename_key] = unicodedata.normalize("NFC", path.name).strip()

    conflicts = {
        display_filename[key]: sorted(folders)
        for key, folders in folders_by_filename.items()
        if len(folders) > 1
    }
    if conflicts:
        raise ValueError(f"PDF adı birden fazla kişi klasöründe bulundu: {conflicts}")
    return {
        key: next(iter(folders))
        for key, folders in folders_by_filename.items()
    }


def ensure_document_trace_schema(conn):
    """Add traceability fields without rebuilding an existing database."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ziyaret)")
    visit_columns = {row[1] for row in cur.fetchall()}
    if "kaynak_dosya_adi" not in visit_columns:
        cur.execute("ALTER TABLE ziyaret ADD COLUMN kaynak_dosya_adi TEXT")
    cur.execute(
        """CREATE TABLE IF NOT EXISTS hasta_dosya (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_id INTEGER NOT NULL REFERENCES hasta(id),
            dosya_adi TEXT NOT NULL UNIQUE,
            kaynak_klasor TEXT NOT NULL
        )"""
    )
    conn.commit()


def _resolved_demographic(entries, value_index, source_index):
    """Choose a single person-level demographic value without guessing."""
    manual_values = {
        row[value_index]
        for row in entries
        if row[value_index] and row[source_index] == "manual_review"
    }
    if len(manual_values) == 1:
        return manual_values.pop(), "manual_review", None
    if len(manual_values) > 1:
        return None, "manual_conflict", sorted(manual_values)

    automatic_values = {row[value_index] for row in entries if row[value_index]}
    if len(automatic_values) == 1:
        return automatic_values.pop(), "consolidated_existing", None
    if len(automatic_values) > 1:
        return None, "consolidated_conflict", sorted(automatic_values)
    return None, None, None


def consolidate_patients_by_source_folders(conn, source_roots):
    """Merge PDF rows belonging to the same source folder into one patient.

    The original PDF name is retained both in `hasta_dosya` and every visit's
    `kaynak_dosya_adi`; no visit, medication, symptom, or raw text is lost.
    This operation is intentionally one-time: a database containing document
    trace rows is already consolidated and is left unchanged.
    """
    ensure_document_trace_schema(conn)
    existing_traces = conn.execute("SELECT COUNT(*) FROM hasta_dosya").fetchone()[0]
    if existing_traces:
        return {
            "already_consolidated": True,
            "document_count": existing_traces,
            "person_count": conn.execute("SELECT COUNT(*) FROM hasta").fetchone()[0],
            "demographic_conflicts": [],
        }

    document_map = build_document_folder_map(source_roots)
    rows = conn.execute(
        """SELECT id, dosya_adi, dogum_tarihi, dogum_tarihi_kaynagi,
                  cinsiyet, cinsiyet_kaynagi
           FROM hasta ORDER BY id"""
    ).fetchall()
    missing = [filename for _, filename, *_ in rows if _filename_key(filename) not in document_map]
    if missing:
        raise ValueError(
            "Kaynak klasörlerde eşleşmeyen PDF kayıtları var; birleştirme yapılmadı: "
            + ", ".join(missing)
        )

    grouped = defaultdict(list)
    folder_display = {}
    for row in rows:
        folder = document_map[_filename_key(row[1])]
        person_key = _person_key(folder)
        grouped[person_key].append((row, folder))
        folder_display[person_key] = folder

    cur = conn.cursor()
    conflicts = []
    for person_key, document_entries in grouped.items():
        entries = [row for row, _ in document_entries]
        target_id = min(row[0] for row in entries)
        canonical_name = folder_display[person_key]
        birth_date, birth_source, birth_conflict = _resolved_demographic(entries, 2, 3)
        gender, gender_source, gender_conflict = _resolved_demographic(entries, 4, 5)
        if birth_conflict or gender_conflict:
            conflicts.append({
                "hasta_adi": canonical_name,
                "dogum_tarihi_degerleri": birth_conflict or [],
                "cinsiyet_degerleri": gender_conflict or [],
            })

        for row, folder in document_entries:
            document_id, filename = row[0], row[1]
            cur.execute(
                "UPDATE ziyaret SET kaynak_dosya_adi=? WHERE hasta_id=?",
                (filename, document_id),
            )
            cur.execute(
                "UPDATE ziyaret SET hasta_id=? WHERE hasta_id=?",
                (target_id, document_id),
            )
            cur.execute(
                """INSERT INTO hasta_dosya (hasta_id, dosya_adi, kaynak_klasor)
                   VALUES (?, ?, ?)""",
                (target_id, filename, folder),
            )

        duplicate_ids = [row[0] for row in entries if row[0] != target_id]
        if duplicate_ids:
            placeholders = ",".join("?" * len(duplicate_ids))
            cur.execute(f"DELETE FROM hasta WHERE id IN ({placeholders})", duplicate_ids)
        cur.execute(
            """UPDATE hasta
               SET dosya_adi=?, dogum_tarihi=?, dogum_tarihi_kaynagi=?,
                   cinsiyet=?, cinsiyet_kaynagi=?
               WHERE id=?""",
            (canonical_name, birth_date, birth_source, gender, gender_source, target_id),
        )
    conn.commit()
    return {
        "already_consolidated": False,
        "document_count": len(rows),
        "person_count": len(grouped),
        "demographic_conflicts": conflicts,
    }

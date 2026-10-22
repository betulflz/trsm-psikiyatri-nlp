"""Mobil uygulamanın okuduğu salt-okunur sorgular."""
import unicodedata
from datetime import date, datetime

from trsm.mobile_api.highlights import find_highlights, turkish_fold

TREND_YEARS = tuple(range(2021, 2026))
DENSITY_BUCKETS = 12
STATUS_TABLES = ("hasta", "ziyaret", "ilac_kullanimi", "semptom_kaydi", "ilac_sozluk", "kullanici")
_GENDER_KEYS = {"Erkek": "erkek", "Kadın": "kadin"}
_ORDER_KEY = "COALESCE(tarih, '')"  # tarihsiz notlar en sona düşer


def _nfc(value):
    return unicodedata.normalize("NFC", value) if value else value


def parse_birth_date(value):
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def compute_age(birth, today):
    if birth is None:
        return None
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _parse_iso(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def density(dates):
    """İlk ve son tarihli not arasını 12 kovaya böler, her kovayı 0-3'e ölçekler."""
    days = sorted(d for d in dates if d is not None)
    buckets = [0] * DENSITY_BUCKETS
    if not days:
        return buckets
    first, span = days[0], (days[-1] - days[0]).days
    for day in days:
        if span == 0:
            index = DENSITY_BUCKETS - 1
        else:
            index = min(DENSITY_BUCKETS - 1, int((day - first).days / span * DENSITY_BUCKETS))
        buckets[index] += 1
    peak = max(buckets)

    def level(count):
        if count == 0:
            return 0
        if count * 3 >= peak * 2:
            return 3
        if count * 3 >= peak:
            return 2
        return 1

    return [level(count) for count in buckets]


def summary(conn, threshold):
    yearly = dict(conn.execute(
        "SELECT substr(tarih, 1, 4), COUNT(*) FROM ziyaret WHERE tarih IS NOT NULL GROUP BY 1"
    ).fetchall())
    genders = {"erkek": 0, "kadin": 0, "bilinmiyor": 0}
    for value, count in conn.execute("SELECT cinsiyet, COUNT(*) FROM hasta GROUP BY cinsiyet"):
        genders[_GENDER_KEYS.get(_nfc(value), "bilinmiyor")] += count
    top = conn.execute(
        """SELECT ilac_adi_normalize, COUNT(*) AS sayi FROM ilac_kullanimi
           WHERE eslesme_guveni >= %s AND ilac_adi_normalize IS NOT NULL
           GROUP BY ilac_adi_normalize ORDER BY sayi DESC, ilac_adi_normalize ASC LIMIT 5""",
        (threshold,),
    ).fetchall()
    return {
        "toplam_dosya": conn.execute("SELECT COUNT(*) FROM hasta").fetchone()[0],
        "toplam_not": conn.execute("SELECT COUNT(*) FROM ziyaret").fetchone()[0],
        "ilacli_not": conn.execute(
            "SELECT COUNT(DISTINCT ziyaret_id) FROM ilac_kullanimi WHERE eslesme_guveni >= %s", (threshold,)
        ).fetchone()[0],
        "yillik_not": [{"yil": year, "sayi": yearly.get(str(year), 0)} for year in TREND_YEARS],
        "cinsiyet": genders,
        "en_sik_ilaclar": [{"ilac": name, "sayi": count} for name, count in top],
        "okunmamis_rapor": 0,
    }


def list_patients(conn, today):
    dates_by_patient = {}
    for patient_id, tarih in conn.execute("SELECT hasta_id, tarih FROM ziyaret ORDER BY id"):
        dates_by_patient.setdefault(patient_id, []).append(_parse_iso(tarih))
    patients = []
    for patient_id, name, gender, birth in conn.execute("SELECT id, dosya_adi, cinsiyet, dogum_tarihi FROM hasta ORDER BY id"):
        dates = dates_by_patient.get(patient_id, [])
        dated = [d for d in dates if d is not None]
        patients.append({
            "id": patient_id,
            "ad": _nfc(name),
            "cinsiyet": _nfc(gender),
            "yas": compute_age(parse_birth_date(birth), today),
            "not_sayisi": len(dates),
            "son_ziyaret": max(dated).isoformat() if dated else None,
            "yogunluk": density(dates),
            "okunmamis": False,
        })
    patients.sort(key=lambda p: (turkish_fold(p["ad"] or ""), p["id"]))
    return patients


def patient_detail(conn, patient_id, today, threshold):
    row = conn.execute(
        "SELECT id, dosya_adi, cinsiyet, dogum_tarihi FROM hasta WHERE id = %s", (patient_id,)
    ).fetchone()
    if row is None:
        return None
    note_count, first, last = conn.execute(
        "SELECT COUNT(*), MIN(tarih), MAX(tarih) FROM ziyaret WHERE hasta_id = %s", (patient_id,)
    ).fetchone()
    drug_count = conn.execute(
        """SELECT COUNT(DISTINCT COALESCE(ik.ilac_adi_normalize, ik.ilac_adi_ham))
           FROM ilac_kullanimi ik JOIN ziyaret z ON z.id = ik.ziyaret_id
           WHERE z.hasta_id = %s AND ik.eslesme_guveni >= %s""",
        (patient_id, threshold),
    ).fetchone()[0]
    pid, name, gender, birth = row
    return {
        "id": pid,
        "ad": _nfc(name),
        "cinsiyet": _nfc(gender),
        "yas": compute_age(parse_birth_date(birth), today),
        "dosya_no": f"#{pid:04d}",
        "tc_maskeli": None,
        "not_sayisi": note_count,
        "ilac_sayisi": drug_count,
        "ilk_kayit": first,
        "son_kayit": last,
    }


def _build_note(conn, row, threshold):
    visit_id, tarih, page, intervention, result = row
    parts = (_nfc(intervention), _nfc(result))
    text = "\n\n".join(part.strip() for part in parts if part and part.strip())
    drugs = conn.execute(
        """SELECT ilac_adi_ham, ilac_adi_normalize, doz, siklik FROM ilac_kullanimi
           WHERE ziyaret_id = %s AND eslesme_guveni >= %s ORDER BY id""",
        (visit_id, threshold),
    ).fetchall()
    symptoms = [r[0] for r in conn.execute(
        "SELECT ifade_ham FROM semptom_kaydi WHERE ziyaret_id = %s ORDER BY id", (visit_id,)
    )]
    medicines, seen = [], set()
    for raw, normalized, dose, frequency in drugs:
        name = normalized or raw
        if name in seen:
            continue
        seen.add(name)
        medicines.append({"ad": name, "doz": dose, "siklik": frequency})
    return {
        "id": visit_id,
        "tarih": tarih,
        "sayfa_no": page,
        "metin": text,
        "vurgular": find_highlights(text, [d[0] for d in drugs], symptoms),
        "ilaclar": medicines,
        "belirti_sayisi": len(symptoms),
        "gorsel_var": False,
    }


def patient_notes(conn, patient_id, threshold, before_id=None, limit=20):
    where, params = "hasta_id = %s", [patient_id]
    if before_id is not None:
        cursor = conn.execute(
            f"SELECT {_ORDER_KEY} FROM ziyaret WHERE id = %s AND hasta_id = %s", (before_id, patient_id)
        ).fetchone()
        if cursor is None:
            raise ValueError("İmleç bu dosyaya ait değil.")
        where += f" AND ({_ORDER_KEY} < %s OR ({_ORDER_KEY} = %s AND id < %s))"
        params += [cursor[0], cursor[0], before_id]
    rows = conn.execute(
        f"""SELECT id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni FROM ziyaret
            WHERE {where} ORDER BY {_ORDER_KEY} DESC, id DESC LIMIT %s""",
        (*params, limit + 1),
    ).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "notlar": [_build_note(conn, row, threshold) for row in rows],
        "sonraki": rows[-1][0] if has_more else None,
    }


def system_status(conn):
    size = conn.execute("SELECT pg_database_size(current_database())").fetchone()[0]
    return {
        "tablolar": {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in STATUS_TABLES},
        "db_boyutu_mb": round(size / 1_048_576, 1),
    }

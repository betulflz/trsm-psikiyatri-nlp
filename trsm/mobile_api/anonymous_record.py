"""Doktorun onayladığı OCR metnini kimliksiz bir hasta kaydı olarak yazar.

Sunucuda ad, TC, dosya numarası ya da tam doğum tarihi tutulmaz. Hasta rastgele bir
koddan ibarettir; kodun kime ait olduğunu yalnızca doktor bilir. Yaş, doğum yılına
yuvarlanır (1 Temmuz kabulü), böylece mevcut yaş hesabı ve analizler değişmeden çalışır.
"""
import secrets
from datetime import date

from trsm.deidentification import deidentify
from trsm.drug_matching import build_surface_form_index_from_db
from trsm.medication_pipeline import extract_medications_from_text
from trsm.symptom_extraction import is_probable_symptom, split_into_phrases

KAYNAK = "mobil_anonim"
CINSIYETLER = {"K": "Kadın", "E": "Erkek"}
MIN_YAS, MAX_YAS = 15, 100
MAX_SAYFA, MAX_KARAKTER = 20, 20_000


class RecordError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate(body, today):
    if not isinstance(body, dict):
        body = {}
    if body.get("kimlik_onayi") is not True:
        raise RecordError("onay_gerekli", "Metinde kimlik bilgisi kalmadığını onaylayın.")
    yas = body.get("yas")
    if not isinstance(yas, int) or isinstance(yas, bool) or not MIN_YAS <= yas <= MAX_YAS:
        raise RecordError("yas_gecersiz", f"Yaş {MIN_YAS}–{MAX_YAS} arasında bir sayı olmalı.")
    cinsiyet = CINSIYETLER.get(body.get("cinsiyet"))
    if cinsiyet is None:
        raise RecordError("cinsiyet_gecersiz", "Cinsiyet K ya da E olmalı.")
    pages = body.get("sayfalar")
    if (not isinstance(pages, list) or not 1 <= len(pages) <= MAX_SAYFA
            or not all(isinstance(p, str) and p.strip() and len(p) <= MAX_KARAKTER for p in pages)):
        raise RecordError("sayfa_gecersiz", f"1–{MAX_SAYFA} sayfa metni gerekli (sayfa başına en fazla {MAX_KARAKTER} karakter).")
    raw_date = body.get("ziyaret_tarihi") or today.isoformat()
    try:
        visit_date = date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        raise RecordError("tarih_gecersiz", "Ziyaret tarihi YYYY-AA-GG biçiminde olmalı.") from None
    if visit_date > today:
        raise RecordError("tarih_gecersiz", "Ziyaret tarihi ileri bir tarih olamaz.")
    return yas, cinsiyet, pages, visit_date


def save_anonymous_record(conn, body, today):
    yas, cinsiyet, pages, visit_date = validate(body, today)
    # Doktor metni düzenlemiş olabilir; kayıttan önce temizlik yeniden yapılır.
    cleaned = [deidentify(page) for page in pages]
    surface_forms = build_surface_form_index_from_db(conn)
    code = "ANON-" + secrets.token_hex(4).upper()
    birth = f"01.07.{visit_date.year - yas}"

    cur = conn.cursor()
    cur.execute(
        """INSERT INTO hasta (dosya_adi, cinsiyet, dogum_tarihi, cinsiyet_kaynagi, dogum_tarihi_kaynagi)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (code, cinsiyet, birth, KAYNAK, KAYNAK + "_yas"),
    )
    hasta_id = cur.fetchone()[0]
    drugs, symptom_count, removed = [], 0, {}
    for page_no, page in enumerate(cleaned, start=1):
        text = page["metin"]
        for kind, count in page["temizlenen"].items():
            removed[kind] = removed.get(kind, 0) + count
        cur.execute(
            """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, kaynak_dosya_adi, ham_mudahale_metni)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (hasta_id, visit_date.isoformat(), page_no, KAYNAK, text),
        )
        ziyaret_id = cur.fetchone()[0]
        meds = extract_medications_from_text(text, surface_forms)
        cur.executemany(
            """INSERT INTO ilac_kullanimi (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(ziyaret_id, m["ilac_adi_normalize"], m["ilac_adi_ham"], m["doz"], m["siklik"], m["eslesme_guveni"]) for m in meds],
        )
        drugs += [m["ilac_adi_normalize"] for m in meds]
        phrases = [p for p in split_into_phrases(text) if is_probable_symptom(p, surface_forms)]
        cur.executemany(
            "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (%s, %s, %s)",
            [(ziyaret_id, phrase, None) for phrase in phrases],
        )
        symptom_count += len(phrases)
    conn.commit()
    return {
        "kod": code,
        "ziyaret_sayisi": len(cleaned),
        "ilaclar": sorted(set(drugs)),
        "semptom_sayisi": symptom_count,
        "kayit_oncesi_temizlenen": removed,
    }

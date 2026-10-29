"""Gerçek hasta verisi olmadan sunucu demosu için sahte (sentetik) veri üretir.

Çalıştırma: uv run python scripts/seed_synthetic_demo.py [--hasta 300] [--database-url ...]

Boş bir veritabanına şema, ilaç sözlüğü ve uydurma hasta/ziyaret/semptom/ilaç
kayıtları yazar. Hasta adları "DEMO-0001" biçimindedir; hiçbir kayıt gerçek bir
kişiye ait değildir. Veritabanında hasta varsa dokunmadan çıkar.
"""
import argparse
import random
import sys
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trsm.db import create_schema, get_connection
from trsm.drug_dictionary import load_drug_dictionary, load_drug_dictionary_into_db

SEED_CSV = Path(__file__).resolve().parents[1] / "data" / "ilac_sozluk_seed.csv"
SOURCE = "manual_review"

# Her tablo: o tabloya uyan semptom ifadeleri ve sık yazılan ilaçlar.
PROFILES = {
    "depresif": (
        ["mutsuzluk", "isteksizlik", "iştahsızlık", "uykusuzluk", "ağlama nöbetleri",
         "hiçbir şeyden zevk alamama", "yorgunluk", "umutsuzluk", "içe kapanma"],
        ["Lustral", "Prozac", "Cedrina", "Efexor", "Wellbutrin", "Duxet", "Citoles"],
    ),
    "anksiyete": (
        ["sıkıntı", "kaygı", "çarpıntı", "huzursuzluk", "gerginlik", "nefes darlığı",
         "panik atak", "kötü bir şey olacak hissi", "titreme"],
        ["Xanax", "Rivotril", "Lustral", "Cedrina", "Lustral", "Selectra"],
    ),
    "psikotik": (
        ["sesler duyma", "şüphecilik", "takip edildiğini düşünme", "dağınık konuşma",
         "kendi kendine konuşma", "garip davranışlar", "uykusuzluk", "sinirlilik"],
        ["Risperdal", "Abilify", "Olanzapin", "Quetiapin", "Xeplion", "Solian", "Akineton"],
    ),
    "bipolar": (
        ["aşırı konuşma", "uykuya ihtiyaç duymama", "taşkınlık", "sinirlilik",
         "aşırı para harcama", "kendini çok güçlü hissetme", "huzursuzluk"],
        ["Lithium", "Depakin", "Lamictal", "Quetiapin", "Abilify", "Olanzapin"],
    ),
    "obsesif": (
        ["takıntılı düşünceler", "sürekli el yıkama", "kontrol etme ihtiyacı",
         "kafasından atamadığı düşünceler", "sıkıntı", "kaygı"],
        ["Prozac", "Lustral", "Clonex", "Anipe", "Lustral"],
    ),
}
DOSES = ["5 mg", "10 mg", "20 mg", "25 mg", "50 mg", "100 mg", "200 mg"]
FREQUENCIES = ["1x1", "2x1", "1x1 akşam", "1x1/2", "2x1/2"]


def build_patients(rng, count):
    patients = []
    for i in range(1, count + 1):
        birth = date(rng.randint(1950, 2005), rng.randint(1, 12), rng.randint(1, 28))
        patients.append({
            "dosya_adi": f"DEMO-{i:04d}",
            "cinsiyet": rng.choice(["Erkek", "Kadın"]),
            "dogum_tarihi": birth.strftime("%d.%m.%Y"),  # OCR çıktısıyla aynı biçim
            "profil": rng.choice(list(PROFILES)),
        })
    return patients


def insert_patient(cur, rng, patient):
    cur.execute(
        """INSERT INTO hasta (dosya_adi, cinsiyet, dogum_tarihi, cinsiyet_kaynagi, dogum_tarihi_kaynagi)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (patient["dosya_adi"], patient["cinsiyet"], patient["dogum_tarihi"], SOURCE, SOURCE),
    )
    hasta_id = cur.fetchone()[0]
    symptoms, drugs = PROFILES[patient["profil"]]
    visit_day = date(2021, 1, 1) + timedelta(days=rng.randint(0, 1300))
    current = rng.sample(drugs, k=rng.randint(1, 2))
    for page in range(1, rng.randint(2, 6) + 1):
        if visit_day > date(2025, 12, 31):
            break
        if rng.random() < 0.3:  # tedavi değişikliği
            current = rng.sample(drugs, k=rng.randint(1, 2))
        chosen = rng.sample(symptoms, k=rng.randint(1, 3))
        cur.execute(
            """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, kaynak_dosya_adi, ham_mudahale_metni, ham_sonuc_metni)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (hasta_id, visit_day.isoformat(), page, f"{patient['dosya_adi']}.pdf",
             "Hasta " + ", ".join(chosen) + " şikayetiyle geldi.", "Tedavi düzenlendi."),
        )
        ziyaret_id = cur.fetchone()[0]
        cur.executemany(
            "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (%s, %s, %s)",
            [(ziyaret_id, phrase, None) for phrase in chosen],
        )
        cur.executemany(
            """INSERT INTO ilac_kullanimi (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(ziyaret_id, drug, drug, rng.choice(DOSES), rng.choice(FREQUENCIES), 100.0) for drug in current],
        )
        visit_day += timedelta(days=rng.randint(20, 120))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--hasta", type=int, default=300, help="Üretilecek sahte hasta sayısı")
    parser.add_argument("--tohum", type=int, default=42, help="Tekrarlanabilirlik için rastgelelik tohumu")
    args = parser.parse_args()

    rng = random.Random(args.tohum)
    with closing(get_connection(args.database_url)) as conn:
        create_schema(conn)
        if conn.execute("SELECT count(*) FROM hasta").fetchone()[0]:
            print("Veritabanında zaten hasta var; sahte veri eklenmedi.")
            return
        if not conn.execute("SELECT count(*) FROM ilac_sozluk").fetchone()[0]:
            load_drug_dictionary_into_db(conn, load_drug_dictionary(SEED_CSV))
        with conn.cursor() as cur:
            for patient in build_patients(rng, args.hasta):
                insert_patient(cur, rng, patient)
        conn.commit()
        counts = {
            table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("hasta", "ziyaret", "semptom_kaydi", "ilac_kullanimi")
        }
    print("Sahte veri yazıldı:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()

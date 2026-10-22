"""Mobil API testleri için küçük, tamamen uydurma veritabanı."""
import unicodedata
from contextlib import closing

from trsm.db import create_schema, get_connection


def _visit(conn, patient_id, tarih, mudahale, sonuc=None, drugs=(), symptoms=()):
    visit_id = conn.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (%s, %s, 1, %s, %s) RETURNING id""",
        (patient_id, tarih, mudahale, sonuc),
    ).fetchone()[0]
    for ham, normalize, doz, siklik, guven in drugs:
        conn.execute(
            """INSERT INTO ilac_kullanimi
               (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (visit_id, normalize, ham, doz, siklik, guven),
        )
    for ifade in symptoms:
        conn.execute("INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham) VALUES (%s, %s)", (visit_id, ifade))
    return visit_id


def build_fixture_db(database_url):
    with closing(get_connection(database_url)) as conn:
        create_schema(conn)
        ayse = conn.execute(
            "INSERT INTO hasta (dosya_adi, cinsiyet, dogum_tarihi) VALUES ('Ayşe Kaya', 'Kadın', '07.01.1989') RETURNING id"
        ).fetchone()[0]
        ismail = conn.execute(
            "INSERT INTO hasta (dosya_adi, cinsiyet, dogum_tarihi) VALUES ('İsmail Işık', 'Erkek', '1990-05-20') RETURNING id"
        ).fetchone()[0]
        conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('Boş Dosya')")
        ids = {
            "v1": _visit(conn, ayse, "2021-03-01", "Depakin 500 2x1 başlandı", "Uykusuzluk var",
                         drugs=[("Depakin", "Depakin", "500", "2x1", 95)], symptoms=["uykusuzluk"]),
            "v2": _visit(conn, ayse, "2023-06-10", "Abilify 10mg eklendi",
                         drugs=[("Abilify", "Abilify", "10mg", None, 100), ("Lityum", "Lithium", None, None, 80)]),
            "v3": _visit(conn, ayse, "2023-06-10", "Kontrol"),
            "v4": _visit(conn, ayse, None, unicodedata.normalize("NFD", "Baş ağrısı var"),
                         symptoms=["baş ağrısı"]),
            "v5": _visit(conn, ismail, "2025-01-15", "İLAÇ: DEPAKİN devam. Huzursuzluk",
                         drugs=[("Depakin", "Depakin", None, None, 92)], symptoms=["huzursuzluk"]),
        }
        conn.commit()
    return {"ayse": ayse, "ismail": ismail, "bos": 3, **ids}

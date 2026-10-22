import pandas as pd


def load_visits(conn, df):
    cur = conn.cursor()
    hasta_id_cache = {}

    for record in df.to_dict("records"):
        dosya = record["Dosya"]
        if dosya not in hasta_id_cache:
            cur.execute("INSERT INTO hasta (dosya_adi) VALUES (%s) ON CONFLICT DO NOTHING", (dosya,))
            cur.execute("SELECT id FROM hasta WHERE dosya_adi = %s", (dosya,))
            hasta_id_cache[dosya] = cur.fetchone()[0]
        hasta_id = hasta_id_cache[dosya]

        mudahale = record.get("Müdahale")
        sonuc = record.get("Sonuç")
        cur.execute(
            """INSERT INTO ziyaret
               (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                hasta_id,
                record.get("tarih_normalize"),
                record.get("Sayfa"),
                None if pd.isna(mudahale) else mudahale,
                None if pd.isna(sonuc) else sonuc,
            ),
        )
    conn.commit()

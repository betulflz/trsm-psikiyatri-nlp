LLM_MODEL_NAME = "gemma2:2b"

VERI_YOK_MESAJI = "Bu semptoma yeterince benzer geçmiş veri bulunamadı."


def compute_drug_statistics(conn, ziyaret_ids, guven_esigi=90):
    if not ziyaret_ids:
        return []

    placeholders = ",".join("?" * len(ziyaret_ids))
    query = f"""
        SELECT ilac_adi_normalize, COUNT(*) as sayi
        FROM ilac_kullanimi
        WHERE ziyaret_id IN ({placeholders}) AND eslesme_guveni >= ?
        GROUP BY ilac_adi_normalize
        ORDER BY sayi DESC
    """
    cur = conn.cursor()
    cur.execute(query, list(ziyaret_ids) + [guven_esigi])
    rows = cur.fetchall()

    toplam = sum(sayi for _, sayi in rows)
    if toplam == 0:
        return []

    return [
        {"ilac": ilac, "sayi": sayi, "yuzde": round(100 * sayi / toplam, 1)}
        for ilac, sayi in rows
    ]


def generate_summary(query_text, statistics, client=None):
    if not statistics:
        return VERI_YOK_MESAJI

    stat_lines = "\n".join(f"- {s['ilac']}: %{s['yuzde']}" for s in statistics)
    prompt = (
        f"Bir hasta '{query_text}' şikayetiyle başvurdu. Geçmişte benzer semptomlu "
        f"ziyaretlerde yazılan reçete kayıtlarının ilaç bazında dağılımı:\n{stat_lines}\n\n"
        "Bu istatistiği 2-3 cümlelik doğal bir Türkçe özet haline getir. "
        "Sadece verilen sayıları kullan, yeni bilgi uydurma."
    )

    if client is None:
        import ollama
        client = ollama

    response = client.chat(model=LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]

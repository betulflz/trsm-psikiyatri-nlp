from .symptom_clustering import cluster_phrases, embed_phrases
from .symptom_extraction import split_into_phrases


def run_symptom_extraction(conn, min_cluster_size=5, model=None):
    cur = conn.cursor()
    cur.execute("SELECT id, ham_mudahale_metni, ham_sonuc_metni FROM ziyaret")
    rows = cur.fetchall()

    ziyaret_ids = []
    phrases = []
    for ziyaret_id, mudahale, sonuc in rows:
        combined = " ".join(t for t in [mudahale, sonuc] if t)
        for phrase in split_into_phrases(combined):
            ziyaret_ids.append(ziyaret_id)
            phrases.append(phrase)

    if not phrases:
        return

    embeddings = embed_phrases(phrases, model=model)
    labels = cluster_phrases(embeddings, min_cluster_size=min_cluster_size)

    for ziyaret_id, phrase, label in zip(ziyaret_ids, phrases, labels):
        kategori = "kategorisiz" if label == -1 else f"cluster_{label}"
        cur.execute(
            "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (?, ?, ?)",
            (ziyaret_id, phrase, kategori),
        )
    conn.commit()

import numpy as np

from .symptom_clustering import embed_phrases


def build_symptom_index(conn, index_path, model=None):
    cur = conn.cursor()
    cur.execute("SELECT ziyaret_id, ifade_ham FROM semptom_kaydi")
    rows = cur.fetchall()

    ziyaret_ids = [row[0] for row in rows]
    phrases = [row[1] for row in rows]

    embeddings = np.asarray(embed_phrases(phrases, model=model))

    np.savez(
        index_path,
        embeddings=embeddings,
        ziyaret_ids=np.array(ziyaret_ids),
        phrases=np.array(phrases, dtype=object),
    )


def load_symptom_index(index_path):
    # allow_pickle=True is required because `phrases` is saved as a dtype=object
    # array (variable-length strings). Safe here: index_path is always a file
    # this same codebase wrote via build_symptom_index from local trsm.db data —
    # never an externally supplied or untrusted file.
    data = np.load(index_path, allow_pickle=True)
    return data["embeddings"], data["ziyaret_ids"].tolist(), data["phrases"].tolist()


def find_similar_phrases(query_embedding, embeddings, ziyaret_ids, phrases, top_n=50, min_similarity=0.5):
    if embeddings.shape[0] == 0:
        return []

    query_norm = query_embedding / np.linalg.norm(query_embedding)
    embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    similarities = embeddings_norm @ query_norm

    order = np.argsort(-similarities)[:top_n]

    results = []
    for i in order:
        score = float(similarities[i])
        if score < min_similarity:
            continue
        results.append({
            "ziyaret_id": ziyaret_ids[i],
            "ifade": phrases[i],
            "benzerlik": score,
        })
    return results

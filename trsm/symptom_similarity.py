import numpy as np

from .symptom_clustering import embed_phrases
from .drug_matching import build_surface_form_index_from_db
from .symptom_extraction import classify_record_phrase


def build_symptom_index(conn, index_path, model=None, surface_form_index=None):
    """Build a retrieval index from active symptom expressions only.

    ``semptom_kaydi`` is retained as a raw, traceable extraction table.  The
    index is stricter: non-symptom documentation and explicit "no current
    symptom" statements are excluded from similarity search.
    """
    cur = conn.cursor()
    cur.execute("SELECT ziyaret_id, ifade_ham FROM semptom_kaydi ORDER BY id")
    rows = cur.fetchall()

    surface_form_index = surface_form_index or build_surface_form_index_from_db(conn)
    accepted = [
        row for row in rows
        if classify_record_phrase(row[1], surface_form_index) == "semptom"
    ]
    ziyaret_ids = [row[0] for row in accepted]
    phrases = [row[1] for row in accepted]

    if phrases:
        embeddings = np.asarray(embed_phrases(phrases, model=model))
    else:
        embeddings = np.empty((0, 0))

    np.savez(
        index_path,
        embeddings=embeddings,
        ziyaret_ids=np.array(ziyaret_ids),
        phrases=np.array(phrases, dtype=object),
    )
    return {
        "toplam_ham_kayit": len(rows),
        "indekse_alinan_aktif_semptom": len(phrases),
        "haric_tutulan_kayit": len(rows) - len(phrases),
    }


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

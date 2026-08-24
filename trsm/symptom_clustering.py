from sklearn.cluster import HDBSCAN

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def embed_phrases(phrases, model=None):
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    return model.encode(phrases)


def cluster_phrases(embeddings, min_cluster_size=5):
    n_samples = len(embeddings)
    effective_min_cluster_size = max(2, min(min_cluster_size, n_samples))
    clusterer = HDBSCAN(min_cluster_size=effective_min_cluster_size)
    return clusterer.fit_predict(embeddings)

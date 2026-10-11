import numpy as np
from sklearn.cluster import HDBSCAN

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def embed_phrases(phrases, model=None):
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    return model.encode(phrases)


def cluster_phrases(embeddings, min_cluster_size=5):
    n_samples = len(embeddings)
    # HDBSCAN requires at least 2 samples; with 0 or 1, there's nothing to
    # cluster, so every point (if any) is unclustered ("kategorisiz" upstream).
    if n_samples < 2:
        return np.full(n_samples, -1)
    # Only clamp when there are fewer samples than requested cluster size; otherwise
    # pass min_cluster_size through unchanged so HDBSCAN's own validation still applies.
    effective_min_cluster_size = (
        max(2, n_samples) if n_samples < min_cluster_size else min_cluster_size
    )
    clusterer = HDBSCAN(min_cluster_size=effective_min_cluster_size)
    return clusterer.fit_predict(embeddings)

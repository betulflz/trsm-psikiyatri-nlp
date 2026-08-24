from sklearn.cluster import HDBSCAN

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def embed_phrases(phrases, model=None):
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    return model.encode(phrases)


def cluster_phrases(embeddings, min_cluster_size=5):
    clusterer = HDBSCAN(min_cluster_size=min_cluster_size)
    return clusterer.fit_predict(embeddings)

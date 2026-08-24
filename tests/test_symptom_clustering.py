import numpy as np

from trsm.symptom_clustering import cluster_phrases, embed_phrases


class FakeModel:
    def encode(self, phrases):
        return [[float(len(p)), 0.0] for p in phrases]


def test_embed_phrases_uses_provided_model():
    result = embed_phrases(["abc", "abcdef"], model=FakeModel())
    assert list(result[0]) == [3.0, 0.0]
    assert list(result[1]) == [6.0, 0.0]


def test_cluster_phrases_groups_similar_vectors():
    embeddings = np.array([
        [1.0, 0.0],
        [1.0, 0.1],
        [0.0, 1.0],
        [0.0, 1.1],
    ])

    labels = cluster_phrases(embeddings, min_cluster_size=2)

    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]

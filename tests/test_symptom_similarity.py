import numpy as np

from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.symptom_similarity import (
    build_symptom_index,
    find_similar_phrases,
    load_symptom_index,
)


class FakeModel:
    def encode(self, phrases):
        # "Aaaaa" ile başlayanlar bir vektör bölgesinde, "Bbbbb" ile
        # başlayanlar başka bir bölgede kümelenir.
        return [[1.0, 0.0] if p.startswith("Aaaaa") else [0.0, 1.0] for p in phrases]


def _insert_semptom(conn, dosya, ifade):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (%s) RETURNING id", (dosya,))
    hasta_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (%s, '2024-01-01', 1) RETURNING id",
        (hasta_id,),
    )
    ziyaret_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (%s, %s, 'kategorisiz')",
        (ziyaret_id, ifade),
    )
    conn.commit()
    return ziyaret_id


def test_build_and_load_symptom_index_round_trips(tmp_path):
    conn = fresh_connection()
    create_schema(conn)
    zid_a = _insert_semptom(conn, "a.pdf", "Aaaaa bir durum")
    zid_b = _insert_semptom(conn, "b.pdf", "Bbbbb iki durum")

    index_path = tmp_path / "index.npz"
    build_symptom_index(conn, str(index_path), model=FakeModel())

    embeddings, ziyaret_ids, phrases = load_symptom_index(str(index_path))
    assert embeddings.shape == (2, 2)
    assert ziyaret_ids == [zid_a, zid_b]
    assert phrases == ["Aaaaa bir durum", "Bbbbb iki durum"]


def test_symptom_index_excludes_administrative_and_negative_status_records(tmp_path):
    conn = fresh_connection()
    create_schema(conn)
    kept = _insert_semptom(conn, "kept.pdf", "uykusuzluk var")
    _insert_semptom(conn, "admin.pdf", "Hasta ile bireysel görüşme yapıldı")
    _insert_semptom(conn, "status.pdf", "Aktif ruhsal yakınması yok")

    index_path = tmp_path / "filtered-index.npz"
    result = build_symptom_index(conn, str(index_path), model=FakeModel())
    _, ziyaret_ids, phrases = load_symptom_index(str(index_path))

    assert ziyaret_ids == [kept]
    assert phrases == ["uykusuzluk var"]
    assert result["haric_tutulan_kayit"] == 2


def test_find_similar_phrases_returns_closest_above_threshold():
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]])
    ziyaret_ids = [10, 20, 30]
    phrases = ["Aaaaa", "Bbbbb", "Aaaaa yakın"]

    query_embedding = np.array([1.0, 0.0])
    results = find_similar_phrases(
        query_embedding, embeddings, ziyaret_ids, phrases, top_n=50, min_similarity=0.5
    )

    result_ziyaret_ids = [r["ziyaret_id"] for r in results]
    assert 10 in result_ziyaret_ids
    assert 30 in result_ziyaret_ids
    assert 20 not in result_ziyaret_ids


def test_find_similar_phrases_respects_top_n():
    embeddings = np.array([[1.0, 0.0], [0.99, 0.01], [0.98, 0.02]])
    ziyaret_ids = [1, 2, 3]
    phrases = ["a", "b", "c"]

    query_embedding = np.array([1.0, 0.0])
    results = find_similar_phrases(
        query_embedding, embeddings, ziyaret_ids, phrases, top_n=2, min_similarity=0.0
    )

    assert len(results) == 2


def test_find_similar_phrases_empty_embeddings_returns_empty_list():
    embeddings = np.zeros((0, 2))
    results = find_similar_phrases(np.array([1.0, 0.0]), embeddings, [], [])
    assert results == []

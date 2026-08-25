from trsm.db import get_connection, create_schema
from trsm.symptom_pipeline import run_symptom_extraction


class FakeModel:
    def encode(self, phrases):
        return [[0.0, 0.0] if p.startswith("Aaaaa") else [10.0, 10.0] for p in phrases]


def _insert_ziyaret(conn, dosya, mudahale):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (dosya,))
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, ?, NULL)""",
        (hasta_id, mudahale),
    )
    conn.commit()


def test_run_symptom_extraction_writes_rows_with_consistent_categories():
    conn = get_connection(":memory:")
    create_schema(conn)
    # Two unique phrases per category (plus a repeat of each across visits) so
    # that after deduplication there are still >= min_cluster_size unique
    # points per category for HDBSCAN to split into two clusters.
    _insert_ziyaret(conn, "a.pdf", "Aaaaa bir durum, Aaaaa iki durum, Bbbbb bir durum, Bbbbb iki durum.")
    _insert_ziyaret(conn, "b.pdf", "Aaaaa bir durum, Aaaaa iki durum, Bbbbb bir durum, Bbbbb iki durum.")

    run_symptom_extraction(conn, min_cluster_size=2, model=FakeModel())

    cur = conn.cursor()
    cur.execute("SELECT ifade_ham, kategori FROM semptom_kaydi")
    rows = cur.fetchall()

    assert len(rows) == 8
    categories_by_phrase = {}
    for ifade, kategori in rows:
        categories_by_phrase.setdefault(ifade, set()).add(kategori)

    for kategoriler in categories_by_phrase.values():
        assert len(kategoriler) == 1

    aaaaa_kategori = next(k for i, k in rows if i.startswith("Aaaaa"))
    bbbbb_kategori = next(k for i, k in rows if i.startswith("Bbbbb"))
    assert aaaaa_kategori != bbbbb_kategori


class CountingFakeModel:
    def __init__(self):
        self.encoded_phrases = []

    def encode(self, phrases):
        self.encoded_phrases.extend(phrases)
        return [[0.0, 0.0] for _ in phrases]


def test_run_symptom_extraction_deduplicates_identical_phrases_before_clustering():
    conn = get_connection(":memory:")
    create_schema(conn)
    # "Uyku iyi" repeats across both visits; "Devam ediyor" is a second unique
    # phrase so there are >= min_cluster_size unique points for HDBSCAN.
    _insert_ziyaret(conn, "a.pdf", "Uyku iyi, Devam ediyor.")
    _insert_ziyaret(conn, "b.pdf", "Uyku iyi.")

    model = CountingFakeModel()
    run_symptom_extraction(conn, min_cluster_size=2, model=model)

    assert len(model.encoded_phrases) == 2
    assert sorted(model.encoded_phrases) == ["Devam ediyor", "Uyku iyi"]

    cur = conn.cursor()
    cur.execute("SELECT ifade_ham, kategori FROM semptom_kaydi")
    rows = cur.fetchall()

    assert len(rows) == 3
    uyku_kategoriler = {kategori for ifade, kategori in rows if ifade == "Uyku iyi"}
    assert len(uyku_kategoriler) == 1


def test_run_symptom_extraction_filters_out_non_symptom_phrases():
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_ziyaret(
        conn,
        "a.pdf",
        "Aaaaa bir durum, Aaaaa iki durum, 005 Yayın Tarihi, Bbbbb bir durum, Bbbbb iki durum.",
    )
    _insert_ziyaret(
        conn,
        "b.pdf",
        "Aaaaa bir durum, Aaaaa iki durum, 005 Yayın Tarihi, Bbbbb bir durum, Bbbbb iki durum.",
    )

    run_symptom_extraction(conn, min_cluster_size=2, model=FakeModel())

    cur = conn.cursor()
    cur.execute("SELECT ifade_ham FROM semptom_kaydi")
    ifadeler = [row[0] for row in cur.fetchall()]

    assert "005 Yayın Tarihi" not in ifadeler
    assert ifadeler.count("Aaaaa bir durum") == 2

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
    _insert_ziyaret(conn, "a.pdf", "Aaaaa bir durum, Bbbbb iki durum.")
    _insert_ziyaret(conn, "b.pdf", "Aaaaa bir durum, Bbbbb iki durum.")

    run_symptom_extraction(conn, min_cluster_size=2, model=FakeModel())

    cur = conn.cursor()
    cur.execute("SELECT ifade_ham, kategori FROM semptom_kaydi")
    rows = cur.fetchall()

    assert len(rows) == 4
    categories_by_phrase = {}
    for ifade, kategori in rows:
        categories_by_phrase.setdefault(ifade, set()).add(kategori)

    for kategoriler in categories_by_phrase.values():
        assert len(kategoriler) == 1

    aaaaa_kategori = next(k for i, k in rows if i.startswith("Aaaaa"))
    bbbbb_kategori = next(k for i, k in rows if i.startswith("Bbbbb"))
    assert aaaaa_kategori != bbbbb_kategori

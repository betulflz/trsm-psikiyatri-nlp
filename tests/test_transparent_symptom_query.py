import numpy as np

from trsm.db import create_schema, get_connection
from trsm.transparent_symptom_query import (
    analyze_transparent_symptom_query,
    classify_symptom_clauses,
    split_user_symptoms,
)


class FakeModel:
    def encode(self, values):
        single_value = isinstance(values, str)
        values = [values] if single_value else values
        vectors = []
        for value in values:
            lowered = value.casefold()
            if "uyuyamıyor" in lowered:
                vectors.append([1.0, 0.0])
            elif "kayg" in lowered:
                vectors.append([0.0, 1.0])
            elif "tanımlayamad" in lowered:
                vectors.append([-1.0, -1.0])
            else:
                vectors.append([0.1, 0.1])
        result = np.asarray(vectors)
        return result[0] if single_value else result


SEED_EMBEDDINGS = {
    "vectors": np.asarray([[1.0, 0.0], [0.0, 1.0]]),
    "categories": ["Uyku bozukluğu", "Anksiyete / gerginlik"],
}


def _insert_visit(conn, filename, drug):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO hasta
           (dosya_adi, dogum_tarihi, dogum_tarihi_kaynagi, cinsiyet, cinsiyet_kaynagi)
           VALUES (?, '01.01.1999', 'manual_review', 'Erkek', 'manual_review')""",
        (filename,),
    )
    patient_id = cur.lastrowid
    cur.execute("INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, '2024-02-01', 1)", (patient_id,))
    visit_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, eslesme_guveni)
           VALUES (?, ?, ?, 100)""",
        (visit_id, drug, drug),
    )
    conn.commit()
    return visit_id


def test_split_and_classification_keep_user_clauses_and_explain_anchor_match():
    text = "Hasta bunalmış, geceleri uyuyamıyor; gelecek kaygıları yaşıyor."
    assert split_user_symptoms(text) == [
        "Hasta bunalmış", "geceleri uyuyamıyor", "gelecek kaygıları yaşıyor",
    ]

    classified = classify_symptom_clauses(text, FakeModel(), SEED_EMBEDDINGS)

    sleep = classified[1]["kategoriler"]
    anxiety = classified[2]["kategoriler"]
    assert sleep == [{"kategori": "Uyku bozukluğu", "benzerlik": 1.0, "eslesme_turu": "ifade"}]
    assert anxiety == [{"kategori": "Anksiyete / gerginlik", "benzerlik": 1.0, "eslesme_turu": "ifade"}]


def test_split_keeps_commas_inside_a_single_symptom_statement():
    text = (
        "Aklına kötü, istenmeyen düşünceler geliyor; geceleri uyuyamıyor, "
        "stresten kusuyor."
    )

    assert split_user_symptoms(text) == [
        "Aklına kötü, istenmeyen düşünceler geliyor",
        "geceleri uyuyamıyor",
        "stresten kusuyor",
    ]


def test_visible_broad_labels_cover_negative_thoughts_and_sudden_laughter_without_diagnosis():
    classified = classify_symptom_clauses(
        "Hastanın aklına kötü düşünceler geliyor, bir anda kahkaha krizleri başlıyor",
        FakeModel(),
    )

    assert classified[0]["kategoriler"][0]["kategori"] == "İstenmeyen / olumsuz düşünceler"
    assert classified[1]["kategoriler"][0]["kategori"] == "Ani duygusal tepkiler"


def test_explicit_negation_withholds_the_negated_theme_from_automatic_labelling():
    classified = classify_symptom_clauses("Hastada uykusuzluk yok", FakeModel(), SEED_EMBEDDINGS)

    assert classified[0]["kategoriler"] == []
    assert classified[0]["kalite_sinyali"]["durum"] == "olumsuzlama_kontrolu"
    assert classified[0]["kalite_sinyali"]["olumsuzlanan_kategoriler"] == ["Uyku bozukluğu"]


def test_transparent_query_returns_theme_and_combined_aggregate_without_historical_text():
    conn = get_connection(":memory:")
    create_schema(conn)
    sleep_visit = _insert_visit(conn, "sleep.pdf", "Akineton")
    anxiety_visit = _insert_visit(conn, "anxiety.pdf", "Depakin")

    def search(query_embedding, *_args, **_kwargs):
        visit_id = sleep_visit if query_embedding[0] > query_embedding[1] else anxiety_visit
        return [{"ziyaret_id": visit_id, "ifade": "PRIVATE HISTORICAL TEXT", "benzerlik": 0.9}]

    result = analyze_transparent_symptom_query(
        conn,
        "geceleri uyuyamıyor, gelecek kaygıları yaşıyor",
        25,
        "Erkek",
        FakeModel(),
        np.zeros((1, 2)), [], [],
        seed_embeddings=SEED_EMBEDDINGS,
        search_function=search,
    )

    assert [row["kategori"] for row in result["kategoriler"]] == [
        "Uyku bozukluğu", "Anksiyete / gerginlik",
    ]
    assert result["birlesik"]["uyumlu_ziyaret_sayisi"] == 2
    assert {row["ilac"] for row in result["birlesik"]["ilaclar"]} == {"Akineton", "Depakin"}
    assert "PRIVATE HISTORICAL TEXT" not in str(result)


def test_unclassified_clause_is_still_included_in_combined_semantic_evidence():
    conn = get_connection(":memory:")
    create_schema(conn)
    visit_id = _insert_visit(conn, "unclassified.pdf", "Akineton")

    def search(*_args, **_kwargs):
        return [{"ziyaret_id": visit_id, "ifade": "PRIVATE HISTORICAL TEXT", "benzerlik": 0.9}]

    result = analyze_transparent_symptom_query(
        conn, "Tanımlayamadığı bir iç sıkıntısı yaşıyor", 25, "Erkek", FakeModel(),
        np.zeros((1, 2)), [], [], seed_embeddings=SEED_EMBEDDINGS, search_function=search,
    )

    assert result["kategoriler"] == []
    assert result["birlesik"]["uyumlu_ziyaret_sayisi"] == 1
    assert result["kategori_disinda_semantik_arama"][0]["ifade"] == "Tanımlayamadığı bir iç sıkıntısı yaşıyor"
    assert "PRIVATE HISTORICAL TEXT" not in str(result)


def test_high_risk_expression_does_not_produce_medication_pattern():
    conn = get_connection(":memory:")
    create_schema(conn)
    result = analyze_transparent_symptom_query(
        conn, "Kendime zarar vermek istiyorum", 25, "Erkek", FakeModel(),
        np.zeros((1, 2)), [], [], seed_embeddings=SEED_EMBEDDINGS,
    )

    assert result["guvenlik_uyarisi"]
    assert result["birlesik"]["ilaclar"] == []

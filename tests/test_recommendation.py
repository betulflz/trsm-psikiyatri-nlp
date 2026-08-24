from trsm.db import get_connection, create_schema
from trsm.recommendation import compute_drug_statistics, generate_summary


def _insert_medication(conn, ziyaret_id_seed, ilac_adi, eslesme_guveni):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (f"hasta{ziyaret_id_seed}.pdf",))
    hasta_id = cur.lastrowid
    cur.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, '2024-01-01', 1)",
        (hasta_id,),
    )
    ziyaret_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
           VALUES (?, ?, ?, NULL, NULL, ?)""",
        (ziyaret_id, ilac_adi, ilac_adi, eslesme_guveni),
    )
    conn.commit()
    return ziyaret_id


def test_compute_drug_statistics_computes_percentages_and_orders_by_count():
    conn = get_connection(":memory:")
    create_schema(conn)
    z1 = _insert_medication(conn, 1, "Stilizan", 100)
    z2 = _insert_medication(conn, 2, "Stilizan", 95)
    z3 = _insert_medication(conn, 3, "Akineton", 90)

    stats = compute_drug_statistics(conn, [z1, z2, z3])

    assert stats[0]["ilac"] == "Stilizan"
    assert stats[0]["sayi"] == 2
    assert stats[0]["yuzde"] == round(100 * 2 / 3, 1)
    assert stats[1]["ilac"] == "Akineton"
    assert stats[1]["sayi"] == 1


def test_compute_drug_statistics_respects_guven_esigi():
    conn = get_connection(":memory:")
    create_schema(conn)
    z1 = _insert_medication(conn, 1, "Stilizan", 60)

    stats = compute_drug_statistics(conn, [z1], guven_esigi=90)

    assert stats == []


def test_compute_drug_statistics_empty_ziyaret_ids_returns_empty_list():
    conn = get_connection(":memory:")
    create_schema(conn)
    assert compute_drug_statistics(conn, []) == []


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat(self, model, messages):
        self.calls.append((model, messages))
        return {"message": {"content": "Sahte özet metni."}}


def test_generate_summary_calls_client_with_statistics_in_prompt():
    client = FakeClient()
    statistics = [{"ilac": "Stilizan", "sayi": 2, "yuzde": 66.7}]

    result = generate_summary("halsizim", statistics, client=client)

    assert result == "Sahte özet metni."
    assert len(client.calls) == 1
    model, messages = client.calls[0]
    prompt = messages[0]["content"]
    assert "Stilizan" in prompt
    assert "66.7" in prompt
    assert "halsizim" in prompt


def test_generate_summary_returns_fixed_message_without_calling_client_when_no_data():
    client = FakeClient()

    result = generate_summary("nadir bir semptom", [], client=client)

    assert "bulunamadı" in result
    assert len(client.calls) == 0

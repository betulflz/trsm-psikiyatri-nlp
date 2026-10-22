import pytest

from trsm.db import create_schema
from tests.pg import fresh_connection

QUERIES = {
    "ziyaret.hasta_id": "SELECT id FROM ziyaret WHERE hasta_id = 1",
    "ilac_kullanimi.ziyaret_id": "SELECT id FROM ilac_kullanimi WHERE ziyaret_id = 1",
    "semptom_kaydi.ziyaret_id": "SELECT id FROM semptom_kaydi WHERE ziyaret_id = 1",
}


@pytest.mark.parametrize("name", list(QUERIES))
def test_per_note_lookups_use_an_index(name):
    conn = fresh_connection()
    create_schema(conn)
    # Boş tabloda planlayıcı zaten sıralı taramayı seçer; kapatınca indeks
    # yoksa yine sıralı tarama görülür, varsa indeks kullanılır.
    conn.execute("SET enable_seqscan = off")
    plan = " ".join(row[0] for row in conn.execute("EXPLAIN " + QUERIES[name]))
    assert "Index" in plan, f"{name}: {plan}"

from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.drug_dictionary import load_drug_dictionary, load_drug_dictionary_into_db


def test_load_drug_dictionary_includes_official_name_as_variation(tmp_path):
    csv_path = tmp_path / "sozluk.csv"
    csv_path.write_text("resmi_ad,varyasyonlar\nStilizan,\n", encoding="utf-8")

    result = load_drug_dictionary(str(csv_path))

    assert result["Stilizan"] == ["Stilizan"]


def test_load_drug_dictionary_splits_pipe_separated_variations(tmp_path):
    csv_path = tmp_path / "sozluk.csv"
    csv_path.write_text(
        "resmi_ad,varyasyonlar\nVenerys,Venegres|Venerus\n", encoding="utf-8"
    )

    result = load_drug_dictionary(str(csv_path))

    assert result["Venerys"] == ["Venerys", "Venegres", "Venerus"]


def test_load_drug_dictionary_into_db_populates_tables():
    conn = fresh_connection()
    create_schema(conn)

    load_drug_dictionary_into_db(conn, {"Venerys": ["Venerys", "Venegres"]})

    cur = conn.cursor()
    cur.execute("SELECT id, resmi_ad FROM ilac_sozluk")
    sozluk_rows = cur.fetchall()
    assert len(sozluk_rows) == 1
    ilac_sozluk_id, resmi_ad = sozluk_rows[0]
    assert resmi_ad == "Venerys"

    cur.execute(
        "SELECT varyasyon, ilac_sozluk_id FROM ilac_varyasyon ORDER BY varyasyon"
    )
    varyasyon_rows = cur.fetchall()
    assert varyasyon_rows == [
        ("Venegres", ilac_sozluk_id),
        ("Venerys", ilac_sozluk_id),
    ]

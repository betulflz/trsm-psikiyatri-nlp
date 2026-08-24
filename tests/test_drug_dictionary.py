from trsm.drug_dictionary import load_drug_dictionary


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

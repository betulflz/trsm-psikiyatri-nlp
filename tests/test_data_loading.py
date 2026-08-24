import pandas as pd
import pytest
from trsm.data_loading import load_raw_excel


def test_load_raw_excel_returns_expected_columns(tmp_path):
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "Dosya": ["a.pdf"],
        "Sayfa": [1],
        "Tarih": ["09.08.2024"],
        "Müdahale": ["not"],
        "Sonuç": ["ilaç"],
    })
    df.to_excel(excel_path, index=False)

    result = load_raw_excel(str(excel_path))

    assert list(result.columns) == ["Dosya", "Sayfa", "Tarih", "Müdahale", "Sonuç"]
    assert len(result) == 1


def test_load_raw_excel_raises_on_missing_columns(tmp_path):
    excel_path = tmp_path / "bad.xlsx"
    pd.DataFrame({"Dosya": ["a.pdf"]}).to_excel(excel_path, index=False)

    with pytest.raises(ValueError, match="eksik"):
        load_raw_excel(str(excel_path))

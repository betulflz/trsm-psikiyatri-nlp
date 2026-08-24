import datetime

import pandas as pd
from trsm.cleaning import parse_tarih, fill_missing_dates


def test_parse_tarih_dot_format():
    assert parse_tarih("09.08.2024") == "2024-08-09"


def test_parse_tarih_slash_format():
    assert parse_tarih("15/06/2021") == "2021-06-15"


def test_parse_tarih_missing_returns_none():
    assert parse_tarih(None) is None
    assert parse_tarih(float("nan")) is None


def test_parse_tarih_unparseable_returns_none():
    assert parse_tarih("bilinmeyen") is None


def test_parse_tarih_datetime_object():
    assert parse_tarih(datetime.datetime(2024, 8, 9)) == "2024-08-09"


def test_parse_tarih_pandas_timestamp():
    assert parse_tarih(pd.Timestamp("2024-08-09")) == "2024-08-09"


def test_fill_missing_dates_forward_fills_per_patient():
    df = pd.DataFrame({
        "Dosya": ["a.pdf", "a.pdf", "a.pdf", "b.pdf"],
        "Tarih": ["01.01.2024", None, None, "02.02.2024"],
    })

    result = fill_missing_dates(df)

    assert result["tarih_normalize"].tolist() == [
        "2024-01-01", "2024-01-01", "2024-01-01", "2024-02-02",
    ]

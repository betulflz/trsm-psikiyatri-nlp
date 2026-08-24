from datetime import datetime

import pandas as pd

DATE_PATTERNS = ["%d.%m.%Y", "%d/%m/%Y"]


def parse_tarih(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def fill_missing_dates(df):
    df = df.copy()
    df["tarih_normalize"] = df["Tarih"].apply(parse_tarih)
    df["tarih_normalize"] = df.groupby("Dosya")["tarih_normalize"].transform(
        lambda s: s.ffill()
    )
    return df

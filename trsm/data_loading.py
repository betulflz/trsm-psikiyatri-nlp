import pandas as pd

REQUIRED_COLUMNS = ["Dosya", "Sayfa", "Tarih", "Müdahale", "Sonuç"]


def load_raw_excel(path):
    df = pd.read_excel(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Excel dosyasında beklenen kolonlar eksik: {missing}")
    return df

import sqlite3

import pandas as pd

from trsm.pipeline import run_pipeline


class FakeModel:
    def encode(self, phrases):
        return [[float(len(p)), 0.0] for p in phrases]


def test_run_pipeline_end_to_end(tmp_path):
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "Dosya": ["test.pdf", "test.pdf"],
        "Sayfa": [1, 1],
        "Tarih": ["09.08.2024", None],
        "Müdahale": [
            "Stilizan 5mg tb -> 3x1. Uyku iyi.",
            "Devam eden görüşme notu burada.",
        ],
        "Sonuç": ["Devam", None],
    })
    df.to_excel(excel_path, index=False)

    db_path = tmp_path / "trsm.db"
    run_pipeline(str(excel_path), str(db_path), symptom_model=FakeModel())

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM hasta")
    assert cur.fetchone()[0] == 1

    cur.execute("SELECT COUNT(*) FROM ziyaret")
    assert cur.fetchone()[0] == 2

    cur.execute("SELECT ilac_adi_normalize, doz, siklik FROM ilac_kullanimi")
    assert ("Stilizan", "5mg", "3x1") in cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM semptom_kaydi")
    assert cur.fetchone()[0] > 0

    conn.close()

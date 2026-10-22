import pandas as pd
import pytest

from tests.pg import fresh_database_url
from trsm.db import get_connection
from trsm.pipeline import DatabaseNotEmptyError, run_pipeline


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

    db_url = fresh_database_url()
    run_pipeline(str(excel_path), db_url, symptom_model=FakeModel())

    conn = get_connection(db_url)
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


def test_run_pipeline_rerun_without_overwrite_raises(tmp_path):
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "Dosya": ["test.pdf"],
        "Sayfa": [1],
        "Tarih": ["09.08.2024"],
        "Müdahale": ["Stilizan 5mg tb -> 3x1. Uyku iyi."],
        "Sonuç": ["Devam"],
    })
    df.to_excel(excel_path, index=False)

    db_url = fresh_database_url()
    run_pipeline(str(excel_path), db_url, symptom_model=FakeModel())

    with pytest.raises(DatabaseNotEmptyError):
        run_pipeline(str(excel_path), db_url, symptom_model=FakeModel())


def test_run_pipeline_rerun_with_overwrite_does_not_duplicate(tmp_path):
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "Dosya": ["test.pdf"],
        "Sayfa": [1],
        "Tarih": ["09.08.2024"],
        "Müdahale": ["Stilizan 5mg tb -> 3x1. Uyku iyi."],
        "Sonuç": ["Devam"],
    })
    df.to_excel(excel_path, index=False)

    db_url = fresh_database_url()
    run_pipeline(str(excel_path), db_url, symptom_model=FakeModel())
    run_pipeline(
        str(excel_path), db_url, symptom_model=FakeModel(), overwrite=True
    )

    conn = get_connection(db_url)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM hasta")
    assert cur.fetchone()[0] == 1

    cur.execute("SELECT COUNT(*) FROM ziyaret")
    assert cur.fetchone()[0] == 1

    cur.execute("SELECT COUNT(*) FROM ilac_kullanimi")
    assert cur.fetchone()[0] == 1

    conn.close()

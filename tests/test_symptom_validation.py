import csv

import numpy as np

from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.symptom_validation import (
    compute_symptom_category_metrics,
    export_symptom_category_validation_sample,
    format_symptom_category_report,
)


class ZeroModel:
    def encode(self, values):
        single = isinstance(values, str)
        values = [values] if single else values
        vectors = np.zeros((len(values), 2))
        return vectors[0] if single else vectors


def _insert_phrase(conn, phrase):
    cur = conn.cursor()
    suffix = conn.execute("SELECT COUNT(*) FROM hasta").fetchone()[0]
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (%s) RETURNING id", (f"a{suffix}.pdf",))
    patient_id = cur.fetchone()[0]
    cur.execute("INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (%s, '2024-01-01', 1) RETURNING id", (patient_id,))
    visit_id = cur.fetchone()[0]
    cur.execute("INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (%s, %s, 'cluster_1')", (visit_id, phrase))
    conn.commit()


def test_export_symptom_validation_sample_is_blinded_and_contains_predictions(tmp_path):
    conn = fresh_connection()
    create_schema(conn)
    _insert_phrase(conn, "geceleri uyuyamıyor")
    _insert_phrase(conn, "gelecek kaygısı")
    _insert_phrase(conn, "tanımlayamadığı bir durum")

    path = tmp_path / "semptom_dogrulama.csv"
    result = export_symptom_category_validation_sample(
        conn, path, sample_per_category=1, uncertain_sample_size=1,
        candidate_pool_size=10, model=ZeroModel(), seed=9,
    )

    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    with open(result["sistem_tahmin_dosyasi"], encoding="utf-8", newline="") as handle:
        system_rows = list(csv.DictReader(handle, delimiter=";"))
    assert result["toplam"] == len(rows)
    assert rows[0]["ornek_id"].startswith("SYM-")
    assert "dosya_adi" not in rows[0]
    assert "sistem_kategoriler" not in rows[0]
    assert any(row["sistem_kategoriler"] == "Uyku bozukluğu" for row in system_rows)
    assert any(row["sistem_kategoriler"] == "" for row in system_rows)


def _write_review_csv(tmp_path):
    path = tmp_path / "semptom_dogrulama.csv"
    headers = [
        "ornek_id", "ifade", "sistem_kategoriler", "degerlendirici_1_kategoriler",
        "degerlendirici_2_kategoriler", "uzlasim_kategoriler", "uzlasim_tamamlandi",
    ]
    rows = [
        ["SYM-0001", "x", "Uyku bozukluğu", "Uyku bozukluğu", "Uyku bozukluğu", "Uyku bozukluğu", "evet"],
        ["SYM-0002", "y", "Anksiyete / gerginlik", "Depresif belirtiler", "Depresif belirtiler", "Depresif belirtiler", "evet"],
        ["SYM-0003", "z", "", "", "", "", "evet"],
        ["SYM-0004", "not completed", "Uyku bozukluğu", "", "", "", ""],
    ]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def test_symptom_category_metrics_uses_only_completed_consensus_rows(tmp_path):
    result = compute_symptom_category_metrics(_write_review_csv(tmp_path))

    assert result["tamamlanan_ornek_sayisi"] == 3
    assert result["kategori_metrikleri"]["Uyku bozukluğu"]["tp"] == 1
    assert result["kategori_metrikleri"]["Anksiyete / gerginlik"]["fp"] == 1
    assert result["kategori_metrikleri"]["Depresif belirtiler"]["fn"] == 1
    assert result["micro_f1"] == 0.5
    assert result["degerlendiriciler_arasi_uyum"]["cift_etiketli_ornek_sayisi"] == 2


def test_symptom_category_metrics_can_join_blinded_review_with_separate_predictions(tmp_path):
    review_path = _write_review_csv(tmp_path)
    with open(review_path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        review_rows = list(reader)
        fields = [field for field in reader.fieldnames if field != "sistem_kategoriler"]
    # Write a reviewer copy without system labels, and a separate prediction file.
    blinded_path = tmp_path / "blinded.csv"
    with open(blinded_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for row in review_rows:
            row.pop("sistem_kategoriler")
            writer.writerow(row)
    prediction_path = tmp_path / "predictions.csv"
    with open(prediction_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ornek_id", "sistem_kategoriler"], delimiter=";")
        writer.writeheader()
        writer.writerows([
            {"ornek_id": "SYM-0001", "sistem_kategoriler": "Uyku bozukluğu"},
            {"ornek_id": "SYM-0002", "sistem_kategoriler": "Anksiyete / gerginlik"},
            {"ornek_id": "SYM-0003", "sistem_kategoriler": ""},
            {"ornek_id": "SYM-0004", "sistem_kategoriler": "Uyku bozukluğu"},
        ])

    result = compute_symptom_category_metrics(blinded_path, prediction_csv=prediction_path)

    assert result["tamamlanan_ornek_sayisi"] == 3
    assert result["micro_f1"] == 0.5


def test_symptom_category_report_includes_core_metrics(tmp_path):
    result = compute_symptom_category_metrics(_write_review_csv(tmp_path))
    report = format_symptom_category_report(result, "semptom_dogrulama.csv")
    assert "Micro precision / recall / F1" in report
    assert "Uyku bozukluğu" in report
    assert "Cohen's kappa" in report

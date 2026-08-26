from trsm.validation_metrics import (
    compute_drug_precision_recall,
    format_report,
    parse_missing_drugs,
)


def test_parse_missing_drugs_blank_note_returns_empty_list():
    assert parse_missing_drugs("") == []
    assert parse_missing_drugs(None) == []


def test_parse_missing_drugs_single_drug_with_leading_comma():
    assert parse_missing_drugs("Yanlış,Paligis eksik") == ["Paligis"]


def test_parse_missing_drugs_single_drug_with_space():
    assert parse_missing_drugs("Yanlış Daprin eksik") == ["Daprin"]


def test_parse_missing_drugs_multiple_drugs_comma_separated():
    assert parse_missing_drugs("Yanlış,Olaxinn, Humira eksik") == ["Olaxinn", "Humira"]
    assert parse_missing_drugs("Yanlış Benvida,Klobazam eksik") == ["Benvida", "Klobazam"]


def test_parse_missing_drugs_unrecognized_pattern_returns_none():
    assert parse_missing_drugs("Bilinmiyor, kontrol et") is None


def _write_csv(tmp_path, rows):
    path = tmp_path / "validation.csv"
    header = [
        "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
        "sistem_ilac_bulgusu", "ilac_dogru_mu",
        "sistem_semptom_bulgusu", "semptom_dogru_mu",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        import csv

        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        for row in rows:
            writer.writerow([
                "a.pdf", "", "", "",
                row.get("sistem_ilac_bulgusu", ""),
                row.get("ilac_dogru_mu", ""),
                "", "",
            ])
    return path


def test_compute_drug_precision_recall_counts_blank_rows_as_true_positive(tmp_path):
    csv_path = _write_csv(tmp_path, [
        {"sistem_ilac_bulgusu": "Akineton (100.0) | Norodol (100.0)", "ilac_dogru_mu": ""},
    ])
    result = compute_drug_precision_recall(csv_path)
    assert result["tp"] == 2
    assert result["fn"] == 0
    assert result["recall"] == 1.0
    assert result["precision"] == 1.0


def test_compute_drug_precision_recall_counts_missing_drug_as_false_negative(tmp_path):
    csv_path = _write_csv(tmp_path, [
        {
            "sistem_ilac_bulgusu": "Akineton (100.0) | Norodol (100.0)",
            "ilac_dogru_mu": "Yanlış Daprin eksik",
        },
    ])
    result = compute_drug_precision_recall(csv_path)
    assert result["tp"] == 2
    assert result["fn"] == 1
    assert result["missing_drugs"] == ["Daprin"]
    assert result["recall"] == 2 / 3


def test_compute_drug_precision_recall_reports_unparseable_notes_separately(tmp_path):
    csv_path = _write_csv(tmp_path, [
        {"sistem_ilac_bulgusu": "Akineton (100.0)", "ilac_dogru_mu": "garip bir not"},
    ])
    result = compute_drug_precision_recall(csv_path)
    assert result["unparseable_notes"] == ["garip bir not"]
    assert result["tp"] == 0


def test_format_report_includes_key_metrics_and_missing_drugs():
    result = {
        "tp": 8, "fp": 0, "fn": 2,
        "precision": 1.0, "recall": 0.8, "f1": 0.888888,
        "missing_drugs": ["Daprin", "Campral"],
        "unparseable_notes": [],
    }
    report = format_report(result, source_csv="dogrulama_ornegi_guncel.csv")
    assert "Precision: 1.00" in report
    assert "Recall: 0.80" in report
    assert "Daprin" in report
    assert "Campral" in report
    assert "dogrulama_ornegi_guncel.csv" in report


def test_format_report_notes_unparseable_rows_when_present():
    result = {
        "tp": 1, "fp": 0, "fn": 0,
        "precision": 1.0, "recall": 1.0, "f1": 1.0,
        "missing_drugs": [],
        "unparseable_notes": ["garip bir not"],
    }
    report = format_report(result, source_csv="x.csv")
    assert "garip bir not" in report

import csv
import json

from trsm.qwen_symptom_labeling import (
    compare_qwen_with_baseline,
    label_phrase_with_qwen,
    label_validation_csv_with_qwen,
)


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return {"message": {"content": json.dumps(self.payload)}}


def test_qwen_candidate_is_accepted_only_for_allowed_labels_and_verbatim_evidence():
    client = FakeClient({
        "kategoriler": ["Uyku bozukluğu"],
        "metinsel_kanit": "geceleri uyuyamıyor",
        "insan_incelemesi_gerekli": False,
    })
    result = label_phrase_with_qwen("Hasta geceleri uyuyamıyor", client=client)

    assert result["durum"] == "gecerli_qwen_adayi"
    assert result["kategoriler"] == ["Uyku bozukluğu"]
    assert client.calls[0]["options"] == {"temperature": 0}


def test_qwen_candidate_fails_closed_for_unknown_label_or_invented_evidence():
    unknown = FakeClient({
        "kategoriler": ["Bipolar bozukluk"], "metinsel_kanit": "x", "insan_incelemesi_gerekli": False,
    })
    invented = FakeClient({
        "kategoriler": ["Uyku bozukluğu"], "metinsel_kanit": "uykusuzluk", "insan_incelemesi_gerekli": False,
    })

    assert label_phrase_with_qwen("geceleri uyuyamıyor", client=unknown)["kategoriler"] == []
    assert label_phrase_with_qwen("geceleri uyuyamıyor", client=invented)["kategoriler"] == []


def test_qwen_csv_writer_creates_a_new_file_with_candidate_columns(tmp_path):
    input_path = tmp_path / "semptom_dogrulama.csv"
    output_path = tmp_path / "semptom_dogrulama_qwen.csv"
    with open(input_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ornek_id", "ifade"], delimiter=";")
        writer.writeheader()
        writer.writerow({"ornek_id": "SYM-0001", "ifade": "geceleri uyuyamıyor"})
    client = FakeClient({
        "kategoriler": ["Uyku bozukluğu"],
        "metinsel_kanit": "geceleri uyuyamıyor",
        "insan_incelemesi_gerekli": False,
    })

    result = label_validation_csv_with_qwen(input_path, output_path, client=client)

    with open(output_path, encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle, delimiter=";"))
    assert result["toplam"] == 1
    assert row["qwen_kategoriler"] == "Uyku bozukluğu"
    assert row["qwen_durum"] == "gecerli_qwen_adayi"


def test_qwen_comparison_marks_agreement_as_method_agreement_not_accuracy():
    classified = [{
        "ifade": "geceleri uyuyamıyor",
        "kategoriler": [{"kategori": "Uyku bozukluğu"}],
        "kalite_sinyali": {"durum": "acik_ifade"},
    }]
    client = FakeClient({
        "kategoriler": ["Uyku bozukluğu"],
        "metinsel_kanit": "geceleri uyuyamıyor",
        "insan_incelemesi_gerekli": False,
    })

    result = compare_qwen_with_baseline(classified, client=client)

    assert result["ifade_karsilastirmalari"][0]["durum"] == "otomatik_uyum"
    assert "doğruluk" in result["ifade_karsilastirmalari"][0]["mesaj"]


def test_qwen_comparison_skips_explicitly_negated_phrase():
    result = compare_qwen_with_baseline([{
        "ifade": "uykusuzluk yok",
        "kategoriler": [],
        "kalite_sinyali": {"durum": "olumsuzlama_kontrolu"},
    }])

    assert result["ifade_karsilastirmalari"][0]["durum"] == "atlanmis_olumsuzlama"

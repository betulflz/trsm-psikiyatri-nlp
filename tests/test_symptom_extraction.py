from trsm.drug_matching import build_surface_form_index
from trsm.symptom_extraction import is_probable_symptom, split_into_phrases

FAKE_DRUG_INDEX = build_surface_form_index({"Akineton": ["Akineton"]})


def test_split_into_phrases_splits_on_punctuation():
    text = "Uyku iyi. Anksiyete belirgin, huzursuzluk var."
    phrases = split_into_phrases(text)
    assert "Uyku iyi" in phrases
    assert "Anksiyete belirgin" in phrases
    assert "huzursuzluk var" in phrases


def test_split_into_phrases_filters_short_fragments():
    phrases = split_into_phrases("iyi. Anksiyete belirgin.")
    assert "iyi" not in phrases
    assert "Anksiyete belirgin" in phrases


def test_split_into_phrases_empty_text_returns_empty_list():
    assert split_into_phrases(None) == []
    assert split_into_phrases("") == []


def test_is_probable_symptom_rejects_form_boilerplate():
    assert is_probable_symptom("005 Yayın Tarihi") is False
    assert is_probable_symptom("HASTANIN ADI VE SOYADI İLETİŞİM TELEFONU") is False
    assert is_probable_symptom("[okunamadı]") is False


def test_is_probable_symptom_rejects_phone_numbers():
    assert is_probable_symptom("0 (530) 775 40 36 Yatış Yapan") is False


def test_is_probable_symptom_accepts_genuine_clinical_phrase():
    assert is_probable_symptom("Aktif ruhsal yakınması yok") is True
    assert is_probable_symptom("uykusuzluk ve huzursuzluk var") is True


def test_is_probable_symptom_rejects_known_drug_dose_line():
    assert is_probable_symptom("Akineton 2mg 2x1", FAKE_DRUG_INDEX) is False


def test_is_probable_symptom_keeps_dose_mention_without_known_drug():
    assert is_probable_symptom("Dozu 2x1'e çıkarıldı", FAKE_DRUG_INDEX) is True

import unicodedata

from trsm.mobile_api.highlights import find_highlights, turkish_fold


def test_turkish_fold_keeps_length_and_handles_dotted_i():
    assert turkish_fold("İLAÇ Işık") == "ilaç ışık"
    assert len(turkish_fold("İİII")) == 4


def test_finds_drug_and_symptom_case_insensitively():
    text = "İLAÇ: DEPAKİN devam. Huzursuzluk"
    assert find_highlights(text, ["Depakin"], ["huzursuzluk"]) == [
        {"bas": 6, "son": 13, "tur": "ilac"},
        {"bas": 21, "son": 32, "tur": "belirti"},
    ]


def test_marks_every_occurrence_and_skips_missing_or_empty_terms():
    text = "Depakin 500, sonra yine depakin"
    result = find_highlights(text, ["Depakin", "Abilify", "  "], [])
    assert [(r["bas"], r["son"]) for r in result] == [(0, 7), (24, 31)]


def test_drug_wins_over_overlapping_symptom():
    text = "lityum zehirlenmesi"
    result = find_highlights(text, ["lityum"], ["lityum zehirlenmesi"])
    assert result == [{"bas": 0, "son": 6, "tur": "ilac"}]


def test_nfd_term_matches_nfc_text():
    text = "Baş ağrısı var"
    term = unicodedata.normalize("NFD", "baş ağrısı")
    assert find_highlights(text, [], [term]) == [{"bas": 0, "son": 10, "tur": "belirti"}]


def test_offsets_are_utf16_units():
    text = "😀 Depakin"
    assert find_highlights(text, ["Depakin"], []) == [{"bas": 3, "son": 10, "tur": "ilac"}]


def test_uppercase_ascii_I_still_matches_drug_with_dotted_i():
    assert find_highlights("DEPAKIN 500", ["Depakin"], []) == [{"bas": 0, "son": 7, "tur": "ilac"}]
    assert find_highlights("Depakin 500", ["DEPAKİN"], []) == [{"bas": 0, "son": 7, "tur": "ilac"}]

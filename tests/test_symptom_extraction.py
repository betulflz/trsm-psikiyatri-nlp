from trsm.symptom_extraction import split_into_phrases


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

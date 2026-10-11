from trsm.drug_matching import extract_candidates, build_surface_form_index, match_drug


def test_extract_candidates_finds_single_word():
    candidates = extract_candidates("Stilizan 5mg tb")
    tokens = [c[0] for c in candidates]
    assert "Stilizan" in tokens


def test_extract_candidates_finds_multi_word_drug_name():
    candidates = extract_candidates("Abilify Maintena 400mg Enj")
    tokens = [c[0] for c in candidates]
    assert "Abilify Maintena" in tokens


def test_extract_candidates_returns_correct_span():
    candidates = extract_candidates("xx Stilizan yy")
    match = next(c for c in candidates if c[0] == "Stilizan")
    assert match[1] == 3
    assert match[2] == 11


def test_build_surface_form_index_maps_variations_to_official_name():
    dictionary = {"Venerys": ["Venerys", "Venegres"]}
    index = build_surface_form_index(dictionary)
    assert index["Venegres"] == "Venerys"
    assert index["Venerys"] == "Venerys"


def test_match_drug_exact_match_scores_100():
    index = {"Stilizan": "Stilizan"}
    result = match_drug("Stilizan", index)
    assert result == ("Stilizan", 100.0)


def test_match_drug_typo_still_matches_above_threshold():
    index = {"Venerys": "Venerys", "Venegres": "Venerys"}
    result = match_drug("Venegre", index, threshold=70)
    assert result is not None
    resmi_ad, score = result
    assert resmi_ad == "Venerys"
    assert score >= 70


def test_match_drug_below_threshold_returns_none():
    index = {"Stilizan": "Stilizan"}
    result = match_drug("tamamen alakasız kelime", index, threshold=90)
    assert result is None


def test_match_drug_short_fragment_does_not_false_positive_on_unrelated_drug():
    # Regression: WRatio's partial-ratio scoring previously matched "mg tb"
    # (a fragment of "Stilizan 5mg tb") to "Akineton" at score 85.5, above
    # the default threshold. Plain ratio must not produce this false positive.
    index = {"Akineton": "Akineton"}
    result = match_drug("mg tb", index)
    assert result is None

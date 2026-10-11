from trsm.dose_extraction import extract_dose_frequency


def test_extract_dose_frequency_finds_both():
    doz, siklik = extract_dose_frequency("5mg tb -> 3x1 sabah")
    assert doz == "5mg"
    assert siklik == "3x1"


def test_extract_dose_frequency_only_dose_present():
    doz, siklik = extract_dose_frequency("400mg (08.08.24)")
    assert doz == "400mg"
    assert siklik is None


def test_extract_dose_frequency_none_present():
    doz, siklik = extract_dose_frequency("Bireysel görüşme yapıldı")
    assert doz is None
    assert siklik is None

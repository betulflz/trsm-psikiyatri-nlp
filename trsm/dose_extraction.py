import re

DOSE_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s?(?:mg|mcg|ml)\b", re.IGNORECASE)
FREQUENCY_PATTERN = re.compile(r"\d+\s?x\s?\d+(?:/\d+)?", re.IGNORECASE)


def extract_dose_frequency(window_text):
    dose_match = DOSE_PATTERN.search(window_text)
    freq_match = FREQUENCY_PATTERN.search(window_text)
    doz = dose_match.group(0) if dose_match else None
    siklik = freq_match.group(0) if freq_match else None
    return doz, siklik

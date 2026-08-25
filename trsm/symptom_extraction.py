import re

from .drug_matching import extract_candidates, match_drug

SPLIT_PATTERN = re.compile(r"[.,;\n]|->|\s-\s")

BOILERPLATE_PATTERNS = (
    "yayın tarihi",
    "revizyon tarihi",
    "doküman no",
    "madde işaretleme",
    "amaç/hedef strateji",
    "hastanın adı ve soyadı",
    "iletişim telefonu",
    "boy kilo",
    "evet hayır",
    "[okunamadı]",
    "kontrolsüz kopyadır",
    "basılmış hali",
    "t.c. sağlık bakanlığı",
    "toplum ruh sağlığı merkezi",
    "sayfa:",
)

CONTACT_ID_PATTERN = re.compile(
    r"\b\d{10,11}\b|\(\d{3}\)\s*\d{3}\s*\d{2}\s*\d{2}|\btel\s*:|\bcep\s*:",
    re.IGNORECASE,
)

DOSE_PATTERN = re.compile(r"\d+\s*(mg|mcg|gr|ml)\b|\b\d\s*x\s*\d\b", re.IGNORECASE)


def split_into_phrases(text, min_length=6):
    if not text:
        return []
    parts = SPLIT_PATTERN.split(text)
    phrases = [p.strip() for p in parts]
    return [p for p in phrases if len(p) >= min_length]


def is_probable_symptom(phrase, surface_form_index=None):
    # Turkish 'İ'.lower() produces 'i' + a combining dot above (U+0307), which
    # would never match the plain 'i' in BOILERPLATE_PATTERNS; strip it.
    lowered = phrase.lower().replace("̇", "")
    if any(pattern in lowered for pattern in BOILERPLATE_PATTERNS):
        return False
    if CONTACT_ID_PATTERN.search(phrase):
        return False
    if surface_form_index and DOSE_PATTERN.search(phrase):
        for candidate, _, _ in extract_candidates(phrase):
            if match_drug(candidate, surface_form_index):
                return False
    return True

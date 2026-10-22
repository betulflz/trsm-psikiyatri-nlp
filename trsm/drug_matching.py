import re

from rapidfuzz import fuzz, process

WORD_PATTERN = re.compile(
    r"[A-Za-zÇĞİÖŞÜçğıöşü]+"
)


def extract_candidates(text):
    if not text:
        return []

    # Find all individual words with their positions
    words = []
    for m in WORD_PATTERN.finditer(text):
        words.append((m.group(0), m.start(), m.end()))

    # Extract all 1-3 word combinations
    candidates = []
    for i in range(len(words)):
        for length in range(1, min(4, len(words) - i + 1)):  # 1-3 words
            start = words[i][1]
            end = words[i + length - 1][2]
            text_token = ' '.join(w[0] for w in words[i:i + length])
            if len(text_token) >= 4:  # Filter by minimum length
                candidates.append((text_token, start, end))

    return candidates


def build_surface_form_index(drug_dictionary):
    index = {}
    for resmi_ad, variations in drug_dictionary.items():
        for form in variations:
            index[form] = resmi_ad
    return index


def build_surface_form_index_from_db(conn):
    """Load the local medication dictionary in the same form as the pipeline.

    Keeping this here lets later analysis steps recognise medication lines in
    the already-built database; those lines must not be used as symptom-search
    evidence simply because an OCR split created a separate phrase.
    """
    rows = conn.execute(
        """SELECT s.resmi_ad, v.varyasyon
           FROM ilac_sozluk s JOIN ilac_varyasyon v ON v.ilac_sozluk_id = s.id
           ORDER BY v.id"""
    ).fetchall()
    return {variation: official for official, variation in rows}


def match_drug(candidate, surface_form_index, threshold=85):
    choices = list(surface_form_index.keys())
    if not choices:
        return None
    # fuzz.ratio (not WRatio) is deliberate: WRatio's partial-ratio component
    # scores short fragments (e.g. "mg tb") as strong substring matches against
    # unrelated longer drug names (e.g. "Akineton"), producing false positives
    # that grow with dictionary size. Plain ratio requires the strings to be
    # similar in full, not just as a substring.
    best = process.extractOne(candidate, choices, scorer=fuzz.ratio)
    if best is None:
        return None
    matched_form, score, _ = best
    if score < threshold:
        return None
    return surface_form_index[matched_form], score

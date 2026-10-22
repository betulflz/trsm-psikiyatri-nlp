"""OCR notu içinde ilaç ve belirti ifadelerinin konumları.

DB konum saklamadığı için ifadeler metin içinde aranır. Türkçe katlama
karakter başına yapılır ve uzunluğu korur; böylece katlanmış metindeki
indeks orijinal metindeki indekse eşittir.
"""
import unicodedata


def _fold_char(ch):
    if ch == "İ":
        return "i"
    if ch == "I":
        return "ı"
    lowered = ch.lower()
    return lowered if len(lowered) == 1 else ch


def turkish_fold(text):
    return "".join(_fold_char(ch) for ch in text)


def _loose_fold(text):
    """Eşleştirme için: i / ı / İ / I hepsi 'i'. OCR büyük harfli ASCII 'DEPAKIN' yazabilir."""
    return turkish_fold(text).replace("ı", "i")


def _utf16_offsets(text):
    offsets = [0]
    for ch in text:
        offsets.append(offsets[-1] + (2 if ord(ch) > 0xFFFF else 1))
    return offsets


def find_highlights(text, drug_terms, symptom_terms):
    folded = _loose_fold(text)
    candidates = []
    for priority, kind, terms in ((0, "ilac", drug_terms), (1, "belirti", symptom_terms)):
        for term in terms:
            needle = _loose_fold(unicodedata.normalize("NFC", term or "").strip())
            if not needle:
                continue
            start = folded.find(needle)
            while start != -1:
                candidates.append((priority, start, start + len(needle), kind))
                start = folded.find(needle, start + len(needle))
    candidates.sort(key=lambda c: (c[0], c[1], c[1] - c[2]))
    taken = []
    for _, start, end, kind in candidates:
        if all(end <= s or start >= e for s, e, _ in taken):
            taken.append((start, end, kind))
    taken.sort()
    offsets = _utf16_offsets(text)
    return [{"bas": offsets[s], "son": offsets[e], "tur": kind} for s, e, kind in taken]

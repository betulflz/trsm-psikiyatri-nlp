"""OCR metninden doğrudan kimlik bilgilerini siler (KVKK için ilk savunma hattı değil, ikincisi).

Birinci hat telefonda fotoğrafın kimlik satırlarının karartılması, üçüncüsü doktorun onayıdır.
Silinen değerler hiçbir yerde tutulmaz; yalnızca hangi türden kaç tane silindiği döner.
Yaş, cinsiyet, ziyaret tarihi, şikâyet ve ilaçlar analiz için korunur.
"""
import re
from collections import Counter

_WORD = r"[A-Za-zÇĞİÖŞÜçğıöşü]"

# Etiket → tür. Etiketten sonraki değer, satır sonuna ya da bir sonraki "Etiket:"e kadar silinir.
_LABELS = [
    (r"t\.?\s?c\.?(?:\s*kimlik)?(?:\s*no\.?)?|kimlik\s*no\.?", "tc"),
    # "Baba adı" önce yakalanmalı; yoksa içindeki "adı" kişinin kendi adı sayılır.
    (r"baba\s*ad[ıi]|anne\s*ad[ıi]|yak[ıi]n[ıi]|refakat[çc]i|e[şs]i", "yakin"),
    (r"ad[ıi]?[\s\-]*soyad[ıi]?|hasta(?:n[ıi]n)?\s*ad[ıi]|isim|ad[ıi]|soyad[ıi]", "ad"),
    (r"(?:ev\s*|i[şs]\s*)?adres(?:i)?", "adres"),
    (r"tel(?:efon)?\.?|cep|gsm", "telefon"),
    (r"e[\-\s]?posta|e[\-\s]?mail|mail", "eposta"),
    (r"do[ğg]um\s*tarihi|d\.?\s?t\.?|do[ğg]\.?\s*tar\.?|do[ğg]um\s*yeri", "dogum"),
    (r"protokol(?:\s*no\.?)?|dosya\s*no\.?|sicil(?:\s*no\.?)?|hasta\s*no\.?|kay[ıi]t\s*no\.?", "dosya_no"),
]
# Değer bir sonraki bilinen etikette biter; "Ad: Ayşe Örnek Yaş: 34" içinde yaş korunur.
_CLINICAL_LABELS = (r"ya[şs][ıi]?|cinsiyet(?:i)?|tarih|tan[ıi]|[şs]ikayet(?:i)?|meslek(?:i)?|medeni\s*durum(?:u)?"
                    r"|e[ğg]itim(?:i)?|muayene|tedavi|ila[çc]lar?")
_ANY_LABEL = "|".join([pattern for pattern, _ in _LABELS] + [_CLINICAL_LABELS])
_NEXT_LABEL = rf"(?=\s+(?:{_ANY_LABEL})\s*[:=]|\s{{3,}}|$)"
_LABEL_RE = [
    (re.compile(rf"(?im)(?<!{_WORD})({pattern})(\s*[:=]\s*)(.+?){_NEXT_LABEL}"), kind)
    for pattern, kind in _LABELS
]

_PATTERNS = [
    (re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)"), "tc", "[TC]"),
    (re.compile(r"(?<!\d)(?:\+?90[\s\-]?|0)?\(?[2-5]\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"), "telefon", "[TELEFON]"),
    (re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"), "eposta", "[E-POSTA]"),
    (re.compile(rf"\b[A-ZÇĞİÖŞÜ]{_WORD[:-1]}]+(?:\s+[A-ZÇĞİÖŞÜ]{_WORD[:-1]}]+)?\s+(?:Han[ıi]m|Hn\.?|Bey|Bayan|Bay)\b"), "ad", "[İSİM]"),
]

TURLER = {
    "tc": "TC no", "ad": "ad", "yakin": "yakın adı", "adres": "adres", "telefon": "telefon",
    "eposta": "e-posta", "dogum": "doğum bilgisi", "dosya_no": "dosya no",
}


def deidentify(text):
    """``{"metin": temizlenmiş metin, "temizlenen": {tür: adet}}`` döner."""
    counts = Counter()

    for regex, kind in _LABEL_RE:
        def label(match, kind=kind):
            if match.group(3).strip() in ("", "[GİZLİ]"):
                return match.group(0)
            counts[kind] += 1
            return f"{match.group(1)}{match.group(2)}[GİZLİ]"
        text = regex.sub(label, text)

    for regex, kind, mask in _PATTERNS:
        text, found = regex.subn(mask, text)
        if found:
            counts[kind] += found

    return {"metin": text, "temizlenen": dict(counts)}

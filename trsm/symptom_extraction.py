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

# These are documentation, treatment or form fragments—not patient symptoms.
# They are intentionally kept explicit and reviewable.  A broad semantic model
# should never be asked to turn "Randevu verildi" or a drug name into a mental
# health theme merely to avoid an "unknown" label.
NON_SYMPTOM_PATTERNS = (
    "hasta ile bireysel görüşme", "bireysel görüşme yapıldı", "ilk görüşme yapıldı",
    "ev ziyareti", "randevu", "kontrole geldi", "kontrol randevusu",
    "aile ile görüşme", "hemşire", "bilgilendirme yapıldı", "izleme alındı",
    "ilaç raporu", "reçete", "tetkik", "tahlil", "laboratuvar", "hemogram",
    "biyokimya", "kan alındı", "ekg", "doz", "gıda alımında azalma:",
    "dd:", "ekt ", "eps olağan", "normal", "başvuru nedeni",
    "ilaçları düzenli kullanımı hakkında", "ilaçlarını düzenli kullanımı hakkında",
    "ilaçlarını düzenli kullanıyor", "ilaç kullanımına ilişkin",
)

# These are meaningful *status* statements, but they do not express an active
# symptom and therefore must not feed symptom-to-medication matching.
NEGATIVE_STATUS_PATTERNS = (
    "aktif ruhsal yakınma yok", "aktif ruhsal yakınması yok",
    "ruhsal yakınma yok", "ruhsal yakınması yok", "şikayet yok",
    "yakınma yok", "semptom yok", "belirti yok", "intihar girişimi yok",
    "intihar düşüncesi yok", "ötimik", "eutimic",
    "uyku iyi", "uyku düzenli", "iştah iyi", "iştah normal",
)

SLEEP_DURATION_STATUS_PATTERN = re.compile(
    r"\buyku\s*[:=]?\s*\d{1,2}\s*(?:-|–|ile)\s*\d{1,2}\s*saat\b",
    re.IGNORECASE,
)


def split_into_phrases(text, min_length=6):
    if not text:
        return []
    parts = SPLIT_PATTERN.split(text)
    phrases = [p.strip() for p in parts]
    return [p for p in phrases if len(p) >= min_length]


def classify_record_phrase(phrase, surface_form_index=None):
    """Classify an OCR phrase before it is treated as symptom evidence.

    Returns one of ``semptom``, ``olumsuz_bulgu`` or ``belirti_disi_kayit``.
    The distinction makes a visible unknown label useful: it should mean a
    real, as-yet-unmapped symptom expression—not a medicine, appointment or
    administrative OCR fragment.
    """
    # Turkish 'İ'.lower() produces 'i' + a combining dot above (U+0307), which
    # would never match the plain 'i' in the patterns; strip it.
    lowered = str(phrase or "").lower().replace("̇", "")
    if not lowered.strip():
        return "belirti_disi_kayit"
    if any(pattern in lowered for pattern in BOILERPLATE_PATTERNS):
        return "belirti_disi_kayit"
    if CONTACT_ID_PATTERN.search(str(phrase)):
        return "belirti_disi_kayit"
    if any(pattern in lowered for pattern in NEGATIVE_STATUS_PATTERNS):
        return "olumsuz_bulgu"
    if SLEEP_DURATION_STATUS_PATTERN.search(lowered):
        # A duration alone says that sleep was documented, not that there was
        # insomnia or hypersomnia.  It remains a non-active status signal.
        return "olumsuz_bulgu"
    if any(pattern in lowered for pattern in NON_SYMPTOM_PATTERNS):
        return "belirti_disi_kayit"
    if surface_form_index:
        for candidate, _, _ in extract_candidates(phrase):
            if match_drug(candidate, surface_form_index):
                return "belirti_disi_kayit"
    # A dose/frequency-only phrase documents treatment handling, not a symptom.
    if DOSE_PATTERN.search(str(phrase)):
        return "belirti_disi_kayit"
    return "semptom"


def is_probable_symptom(phrase, surface_form_index=None):
    """Backward-compatible boolean view of :func:`classify_record_phrase`."""
    return classify_record_phrase(phrase, surface_form_index) == "semptom"

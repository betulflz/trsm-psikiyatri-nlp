"""Versioned, broad symptom themes used for transparent query explanations."""

# These are broad descriptive themes, not diagnoses.  Each seed stays visible
# in code so it can be reviewed and revised with a clinical supervisor.
KATEGORILER = {
    "Uyku bozukluğu": ["uykusuzluk", "uykusuzluk problemi", "uyku düzensizliği", "aşırı uyku hali", "geceleri uyuyamıyor"],
    "Öfke / ajitasyon": ["öfke nöbeti", "ajitasyon", "saldırganlık", "huzursuzluk"],
    "Anksiyete / gerginlik": ["anksiyete", "gerginlik", "kaygı", "endişe hali", "bunalmış", "stres altında", "gelecek kaygısı", "gelecek kaygıları", "stresten kusma"],
    "Depresif belirtiler": ["çökkünlük", "isteksizlik", "mutsuzluk", "enerji azlığı", "ağlama", "üzüntü"],
    # The following labels deliberately describe the reported experience. They
    # must not be read as a diagnosis (for example OCD, psychosis or mania).
    "İstenmeyen / olumsuz düşünceler": [
        "kötü düşünceler", "aklına kötü düşünceler geliyor", "istenmeyen düşünceler",
        "olumsuz düşünceler", "rahatsız edici düşünceler", "takıntılı düşünceler",
    ],
    "Ani duygusal tepkiler": [
        "kahkaha krizi", "kahkaha krizleri", "bir anda kahkaha", "bir anda gülme",
        "ani gülme", "ani ağlama", "uygunsuz gülme", "duygudurum dalgalanması",
    ],
    "Manik / taşkın belirtiler": ["taşkınlık", "aşırı enerji", "hızlı konuşma", "elevasyon"],
    "Halüsinasyon / hezeyan": ["halüsinasyon", "sesler duyma", "hezeyan", "şüphecilik"],
    "İştah / kilo değişimi": ["iştahsızlık", "aşırı iştah", "kilo alımı", "kilo kaybı"],
    "Sosyal içe kapanma": ["içe kapanma", "sosyal izolasyon", "işlevsellik kaybı"],
    "Madde kullanımı": ["madde kullanımı", "alkol kullanımı", "bağımlılık"],
    "Tedaviye uyumsuzluk": ["ilaç bırakma", "düzensiz ilaç kullanımı", "tedaviyi reddetme"],
    "Somatik yakınmalar": ["mide bulantısı", "kusma", "stresten kusma", "çarpıntı", "nefes darlığı", "baş ağrısı"],
}

CREATE TABLE IF NOT EXISTS hasta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dosya_adi TEXT NOT NULL UNIQUE,
    cinsiyet TEXT,
    dogum_tarihi TEXT,
    cinsiyet_kaynagi TEXT,
    dogum_tarihi_kaynagi TEXT
);

CREATE TABLE IF NOT EXISTS ziyaret (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hasta_id INTEGER NOT NULL REFERENCES hasta(id),
    tarih TEXT,
    sayfa_no INTEGER,
    kaynak_dosya_adi TEXT,
    ham_mudahale_metni TEXT,
    ham_sonuc_metni TEXT
);

CREATE TABLE IF NOT EXISTS hasta_dosya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hasta_id INTEGER NOT NULL REFERENCES hasta(id),
    dosya_adi TEXT NOT NULL UNIQUE,
    kaynak_klasor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ilac_sozluk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resmi_ad TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ilac_varyasyon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ilac_sozluk_id INTEGER NOT NULL REFERENCES ilac_sozluk(id),
    varyasyon TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ilac_kullanimi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ziyaret_id INTEGER NOT NULL REFERENCES ziyaret(id),
    ilac_adi_normalize TEXT,
    ilac_adi_ham TEXT NOT NULL,
    doz TEXT,
    siklik TEXT,
    eslesme_guveni REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS semptom_kaydi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ziyaret_id INTEGER NOT NULL REFERENCES ziyaret(id),
    ifade_ham TEXT NOT NULL,
    kategori TEXT
);

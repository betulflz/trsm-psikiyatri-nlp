"""Örneklerin hepsi uydurmadır."""
import pytest

from trsm.deidentification import deidentify

SAYFA = """PSİKİYATRİ POLİKLİNİĞİ - MUAYENE NOTU
Ad Soyad: Ayşe Örnek TC: 12345678901
Tarih: 14.03.2025 Yaş: 34 Cinsiyet: K
Şikayet: 2 aydır uykusuzluk, mutsuzluk, iştahsızlık.
Tanı: Major depresif bozukluk
Tedavi: Sertralin 50 mg 1x1, Ketiapin 25 mg gece"""


def test_example_page_keeps_clinical_content():
    result = deidentify(SAYFA)
    text = result["metin"]
    assert "Ayşe" not in text and "Örnek" not in text and "12345678901" not in text
    assert "Ad Soyad: [GİZLİ] TC: [GİZLİ]" in text
    for kept in ("Tarih: 14.03.2025", "Yaş: 34", "Cinsiyet: K", "uykusuzluk", "Sertralin 50 mg", "Tanı: Major depresif"):
        assert kept in text
    assert result["temizlenen"] == {"ad": 1, "tc": 1}


@pytest.mark.parametrize("line,secret,kind", [
    ("Hastanın adı: Mehmet Deneme", "Mehmet", "ad"),
    ("Baba adı: Ali", "Ali", "yakin"),
    ("Adres: Menteşe Mah. 12. Sokak No 4", "Menteşe", "adres"),
    ("Doğum tarihi: 01.02.1990", "1990", "dogum"),
    ("D.T: 01.02.1990", "1990", "dogum"),
    ("Protokol no: 778899", "778899", "dosya_no"),
    ("T.C. Kimlik No: 98765432109", "98765432109", "tc"),
    ("Ad: Ayşe", "Ayşe", "ad"),
    ("Soyad: Örnek", "Örnek", "ad"),
    ("AD SOYAD: AYŞE ÖRNEK", "AYŞE", "ad"),
    ("ADI SOYADI: Ayşe Örnek", "Ayşe", "ad"),
    ("İsim: Ayşe", "Ayşe", "ad"),
    ("Ad Soyad: Ayşe      Örnek", "Örnek", "ad"),
])
def test_labeled_fields(line, secret, kind):
    result = deidentify(line)
    assert secret not in result["metin"]
    assert result["temizlenen"].get(kind) == 1


def test_unlabeled_identifiers():
    result = deidentify("Annesi 0532 123 45 67 numarasından aradı, Fatma Hanım eşlik etti. 98765432109 test@ornek.com")
    text = result["metin"]
    assert "[TELEFON]" in text and "[İSİM]" in text and "[TC]" in text and "[E-POSTA]" in text
    assert "Fatma" not in text and "0532" not in text


def test_split_tc_number():
    result = deidentify("Kimlik 123 456 789 01 ve 123-456-789-01")
    assert result["metin"] == "Kimlik [TC] ve [TC]"


def test_doses_dates_and_ages_are_not_identifiers():
    text = "Ketiapin 25 mg 1x1, kontrol 21.04.2025 10.05.2025, 3 ay sonra. 34 yaşında kadın. Lityum 300 mg 2x1"
    result = deidentify(text)
    assert result["metin"] == text
    assert result["temizlenen"] == {}


def test_clinical_words_containing_label_letters_are_kept():
    text = "Tanı: Anksiyete bozukluğu\nMuayene: Kaygılı, adımlarını sayıyor"
    assert deidentify(text)["metin"] == text

"""DENEME (spike): elle yazılmış referans metne karşı birebir OCR karşılaştırması.

Referans: PythonTest/Kitap1.xlsx ("Blok" sütunları = kullanıcının sayfadan
elle yazdığı metin). Görseller: ~/Desktop/TestData (ilk sütundaki adlarla eşleşir).
Yerel modeller bu görselleri okur; Excel'deki bulut/diğer araç sonuçları da aynı
ölçütle puanlanır. Ekrana YALNIZCA sayısal özet yazılır; okumalar
cikti/referans_sonuclar.json dosyasına kaydedilir (hasta verisi; git'e eklenmez).

Ölçütler (küçük harf, noktalama silinmiş, matbu form başlıkları atılmış metin üzerinde):
  - CER: karakter hata oranı (düşük iyi)
  - WER: kelime hata oranı (düşük iyi; test_hakemi.py ile aynı tanım)
  - kelime yakalama: referanstaki kelimelerin okumada geçme oranı (fazladan yazılan
    metinden etkilenmez; "doğru kelimeyi okuyabildi mi?" sorusu)

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 --with openpyxl python -u spikes/ocr_karsilastirma/referans_karsilastir.py
"""
import argparse
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import ollama
import pandas as pd
from PIL import Image
from rapidfuzz.distance import Levenshtein

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from calistir import MAX_SIDE, OUT, SOZLUK_EKI, TALIMAT  # noqa: E402
from trsm.db import get_connection  # noqa: E402

# Taşınan kurulumda test seti cikti/test_seti/ altındadır (Kitap1.xlsx + TestData/).
TEST_SETI = OUT / "test_seti"
EXCEL = TEST_SETI / "Kitap1.xlsx" if TEST_SETI.is_dir() else Path.home() / "Development/Projects/PythonTest/Kitap1.xlsx"
IMAGES = TEST_SETI / "TestData" if TEST_SETI.is_dir() else Path.home() / "Desktop/TestData"
RESULTS = OUT / "referans_sonuclar.json"
EXCEL_SUTUNLARI = {
    "Gemini": "Gemini_Sonuc", "Copilot": "Copilot_Sonuc", "Mistral": "MistralAi_Sonuc",
    "OlmOCR": "OlmOCR_Sonuc", "Tesseract": "Tesseract_Sonuc",
}
YEREL = [
    {"ad": "qwen3.5:4b + sözlük", "model": "qwen3.5:4b", "sozluk": True},
    {"ad": "qwen3.5:4b sözlüksüz", "model": "qwen3.5:4b", "sozluk": False},
    {"ad": "qwen3-vl:4b + sözlük", "model": "qwen3-vl:4b-instruct", "sozluk": True},
]
# test_hakemi.py'deki listeyle aynı: referansa yazılmayan matbu form başlıkları.
FORM_BASLIKLARI = [
    "TOPLUM RUH SAĞLIĞI MERKEZİ HASTA TAKİP FORMU", "T.C. SAĞLIK BAKANLIĞI",
    "MUĞLA EĞİTİM VE ARAŞTIRMA HASTANESİ", "Doküman No", "Yayın Tarihi", "Revizyon Tarihi",
    "Revizyon No", "Sayfa:", "1/1", "Hasta Adı-Soyadı", "TC Kimlik No", "Tanı", "TARIH",
    "MÜDAHALE", "SONUÇ", "BAB", "Bipolar",
]


def nfc(text):
    return unicodedata.normalize("NFC", str(text or ""))


def standardize(text, strip_form=True):
    text = re.sub(r"<[^>]+>", " ", nfc(text)).replace("[?]", " ")
    if strip_form:
        for header in FORM_BASLIKLARI:
            text = re.sub(re.escape(header), " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s]", " ", text.casefold())
    return " ".join(text.split())


def score(reference, hypothesis):
    ref_words, hyp_words = reference.split(), hypothesis.split()
    ref_counts, hyp_counts = Counter(ref_words), Counter(hyp_words)
    return {
        "cer": Levenshtein.distance(reference, hypothesis) / max(1, len(reference)),
        "wer": Levenshtein.distance(ref_words, hyp_words) / max(1, len(ref_words)),
        "yakalama": sum((ref_counts & hyp_counts).values()) / max(1, len(ref_words)),
    }


def prepared_image(source, index):
    target = OUT / "referans_gorseller" / f"ref_{index:02d}.jpg"
    target.parent.mkdir(exist_ok=True)
    image = Image.open(source).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    image.save(target, "JPEG", quality=90)
    return target


def load_pages():
    """Excel rows that have both a matching image and a handwritten reference."""
    df = pd.read_excel(EXCEL).fillna("")
    blocks = [c for c in df.columns if "blok" in str(c).casefold()]
    images = {nfc(p.name).casefold(): p for p in IMAGES.iterdir()}
    images.update({nfc(p.stem).casefold(): p for p in IMAGES.iterdir()})

    pages = []
    for i, row in df.iterrows():
        key = nfc(row.iloc[0]).strip().casefold()
        reference = " ".join(nfc(row[c]) for c in blocks if str(row[c]).strip())
        if key in images and reference.strip():
            pages.append({"no": i + 1, "kaynak": images[key], "referans": reference, "excel": {k: nfc(row.get(c, "")) for k, c in EXCEL_SUTUNLARI.items()}})
    return pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sadece-puanla", action="store_true", help="modelleri çalıştırma, kayıtlı okumaları puanla")
    args = parser.parse_args()

    pages = load_pages()
    print(f"Referanslı sayfa: {len(pages)}")

    saved = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    if not args.sadece_puanla:
        with get_connection() as conn:
            drug_names = [r[0] for r in conn.execute("SELECT resmi_ad FROM ilac_sozluk ORDER BY resmi_ad")]
        for config in YEREL:
            prompt = TALIMAT + (SOZLUK_EKI.format(ilaclar=", ".join(drug_names)) if config["sozluk"] else "")
            for page in pages:
                key = str(page["no"])
                if config["ad"] in saved.get(key, {}):
                    continue
                image = prepared_image(page["kaynak"], page["no"])
                start = time.time()
                response = ollama.chat(
                    model=config["model"],
                    messages=[{"role": "user", "content": prompt, "images": [str(image)]}],
                    options={"temperature": 0, "num_ctx": 8192, "num_predict": 1500},
                    think=False,
                )
                seconds = time.time() - start
                saved.setdefault(key, {})[config["ad"]] = {"metin": nfc(response["message"]["content"]).strip(), "sure": seconds}
                RESULTS.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"  {config['ad']}: sayfa {page['no']} {seconds:.0f} sn")
            ollama.generate(model=config["model"], prompt="", keep_alive=0)

    rows = {}
    names = list(EXCEL_SUTUNLARI) + [c["ad"] for c in YEREL]
    for name in names:
        per_page = []
        for page in pages:
            if name in EXCEL_SUTUNLARI:
                text = page["excel"][name]
            else:
                text = saved.get(str(page["no"]), {}).get(name, {}).get("metin", "")
            if not str(text).strip():
                continue
            per_page.append(score(standardize(page["referans"], strip_form=False), standardize(text)))
        if per_page:
            rows[name] = {
                "sayfa": len(per_page),
                "CER (%)": round(100 * sum(p["cer"] for p in per_page) / len(per_page), 1),
                "WER (%)": round(100 * sum(p["wer"] for p in per_page) / len(per_page), 1),
                "kelime yakalama (%)": round(100 * sum(p["yakalama"] for p in per_page) / len(per_page), 1),
            }
    for name in (c["ad"] for c in YEREL):
        times = [saved[str(p["no"])][name]["sure"] for p in pages if name in saved.get(str(p["no"]), {})]
        if times and name in rows:
            rows[name]["sn/sayfa"] = round(sum(times) / len(times))
    print("\n=== Referansa göre OCR (düşük CER/WER iyi, yüksek yakalama iyi) ===")
    for name, r in sorted(rows.items(), key=lambda kv: kv[1]["CER (%)"]):
        print(f"{name:<24} " + "  ".join(f"{k}: {v}" for k, v in r.items()))


if __name__ == "__main__":
    main()

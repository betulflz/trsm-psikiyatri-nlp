"""DENEME (spike), 2. tur: 4b + sözlük üzerine iki ek yapılandırma.

  - "şerit": sayfa yüksek çözünürlükte işlenip üst üste binen yatay şeritlere
    bölünür, her şerit ayrı okunur ve metinler birleştirilir.
  - "bağlam": talimata önceki sayfadaki (eski OCR'dan çıkarılmış) ilaçlar eklenir.

Okumalar sonuclar.json'daki aynı sayfalara yeni anahtar olarak eklenir; böylece
analiz.py ve etiketle.py onları da görür. Ekrana yalnızca sayfa no ve süre yazar.

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 python -u spikes/ocr_karsilastirma/calistir2.py
"""
import json
import sys
import time
from pathlib import Path

import ollama
import pypdfium2 as pdfium

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from analiz import previous_page_drugs, selected_pages  # noqa: E402
from calistir import OUT, SOZLUK_EKI, TALIMAT, drug_report, find_pdfs, nfc  # noqa: E402
from trsm.db import get_connection  # noqa: E402
from trsm.drug_matching import build_surface_form_index_from_db  # noqa: E402

MODEL = "qwen3-vl:4b-instruct"
SERIT_UZUN_KENAR = 2400
SERIT_SAYISI = 3
SERIT_ORTUSME = 0.12
BAGLAM_EKI = (
    "\n\nBu hastanın önceki ziyaretinde kayıtlı ilaçlar: {ilaclar}. İlaç "
    "değişmiş olabilir; yalnızca görüntüde gerçekten yazanı yaz."
)
SERIT_EKI = "\n\nBu görüntü sayfanın bir bölümüdür; kenarlarda kesik satırlar olabilir."


def strips(pdf_path, page_no, stem):
    page = pdfium.PdfDocument(pdf_path)[page_no - 1]
    width, height = page.get_size()
    image = page.render(scale=SERIT_UZUN_KENAR / max(width, height)).to_pil().convert("RGB")
    step = image.height / SERIT_SAYISI
    pad = int(step * SERIT_ORTUSME)
    paths = []
    for k in range(SERIT_SAYISI):
        top, bottom = max(0, int(k * step) - pad), min(image.height, int((k + 1) * step) + pad)
        path = OUT / "gorseller" / f"{stem}_serit_{k + 1}.jpg"
        image.crop((0, top, image.width, bottom)).save(path, "JPEG", quality=90)
        paths.append(path)
    return paths


def chat(prompt, image):
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt, "images": [str(image)]}],
        options={"temperature": 0, "num_ctx": 8192, "num_predict": 1500},
    )
    return nfc(response["message"]["content"]).strip()


def main():
    results_path = OUT / "sonuclar.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    with get_connection() as conn:
        index = build_surface_form_index_from_db(conn)
        drug_names = [r[0] for r in conn.execute("SELECT resmi_ad FROM ilac_sozluk ORDER BY resmi_ad")]
        chosen = selected_pages(conn, len(results))
        if [c[2] for c in chosen] != [r["eski_ocr"] for r in results]:
            sys.exit("Sayfa eşlemesi tutmadı; durduruldu.")
        context = [previous_page_drugs(conn, f, p) or set() for f, p, _ in chosen]
    pdfs = find_pdfs()
    base = TALIMAT + SOZLUK_EKI.format(ilaclar=", ".join(drug_names))

    def save(name, r, text, seconds):
        meds, strong, weak = drug_report(text, index)
        r["okumalar"][name] = {"metin": text, "sure": seconds, "ilaclar": meds, "guclu": sorted(strong), "zayif": sorted(weak)}
        results_path.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
        print(f"  {name}: sayfa {r['no']} {seconds:.0f} sn")

    for r, (filename, page_no, _) in zip(results, chosen):
        name = "qwen3-vl:4b + sözlük + şerit"
        if name not in r["okumalar"]:
            start = time.time()
            parts = [chat(base + SERIT_EKI, p) for p in strips(pdfs[nfc(filename)], page_no, f"sayfa_{r['no']:02d}")]
            save(name, r, "\n".join(parts), time.time() - start)

    for r, drugs in zip(results, context):
        name = "qwen3-vl:4b + sözlük + bağlam"
        if name not in r["okumalar"]:
            start = time.time()
            prompt = base + (BAGLAM_EKI.format(ilaclar=", ".join(sorted(drugs))) if drugs else "")
            save(name, r, chat(prompt, r["gorsel"]), time.time() - start)

    ollama.generate(model=MODEL, prompt="", keep_alive=0)
    print("Bitti.")


if __name__ == "__main__":
    main()

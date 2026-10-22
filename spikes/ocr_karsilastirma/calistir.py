"""DENEME (spike): yerel görüntü-dil modelleriyle el yazısı okuma karşılaştırması.

Kalıcı kod değildir. Arşivden rastgele sayfalar seçer, her sayfayı birkaç
yerel model/talimat yapılandırmasıyla okur ve:
  - ekrana YALNIZCA sayısal özet yazar (hasta adı/metni yazılmaz),
  - ayrıntıları fotoğraflarla birlikte cikti/rapor.html dosyasına koyar.
cikti/ klasörü hasta verisi içerir; git'e eklenmez, paylaşılmaz.

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 python spikes/ocr_karsilastirma/calistir.py --sayfa 12
"""
import argparse
import base64
import difflib
import html
import json
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

import ollama
import pypdfium2 as pdfium
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from trsm.db import get_connection  # noqa: E402
from trsm.drug_matching import build_surface_form_index_from_db  # noqa: E402
from trsm.medication_pipeline import extract_medications_from_text  # noqa: E402

OUT = Path(__file__).parent / "cikti"
# Windows ":" kabul etmediği için orada ikinci klasörün adı "TRSM-MUGLA"dır.
ARCHIVE_ROOTS = [Path.home() / "TRSM-devamı", Path.home() / "TRSM:MUGLA", Path.home() / "TRSM-MUGLA"]
MAX_SIDE = 1280
GUVEN_ESIGI = 90
# Referans (elle yazılmış) 10 sayfada en iyi yerel sonuç: CER %34,8, 50 sn/sayfa (19.10.2026).
VARSAYILAN_MODEL = "qwen3.5:4b"

TALIMAT = (
    "Bu görüntü bir psikiyatri polikliniğine ait, Türkçe el yazısıyla tutulmuş "
    "bir muayene/takip notudur. Görüntüdeki metni, gördüğün sırayla ve satır "
    "satır, olduğu gibi yaz. Düzeltme, özetleme veya yorum yapma; görmediğin "
    "hiçbir şeyi ekleme. Okuyamadığın ya da emin olmadığın kelimenin yerine "
    "[?] yaz. Yalnızca metni yaz."
)
SOZLUK_EKI = (
    "\n\nNotlarda geçebilecek ilaç adlarından bazıları şunlardır (yalnızca "
    "görüntüde gerçekten yazıyorsa kullan): {ilaclar}"
)

CONFIGS = [
    {"ad": "qwen3-vl:4b + sözlük", "model": "qwen3-vl:4b-instruct", "sozluk": True},
    {"ad": "qwen3-vl:2b + sözlük", "model": "qwen3-vl:2b-instruct", "sozluk": True},
    {"ad": "qwen3-vl:4b sözlüksüz", "model": "qwen3-vl:4b-instruct", "sozluk": False},
]


def nfc(text):
    return unicodedata.normalize("NFC", text or "")


def norm(text):
    return re.sub(r"\s+", " ", nfc(text).casefold()).strip()


def find_pdfs():
    by_name = {}
    for root in (r for r in ARCHIVE_ROOTS if r.is_dir()):
        for path in root.rglob("*.pdf"):
            by_name.setdefault(nfc(path.name), path)
    return by_name


def pick_pages(conn, pdfs, count, seed):
    rows = conn.execute(
        """SELECT kaynak_dosya_adi, sayfa_no,
                  string_agg(concat_ws(' ', ham_mudahale_metni, ham_sonuc_metni), E'\\n' ORDER BY id)
           FROM ziyaret WHERE kaynak_dosya_adi IS NOT NULL AND sayfa_no IS NOT NULL
           GROUP BY kaynak_dosya_adi, sayfa_no
           ORDER BY kaynak_dosya_adi, sayfa_no"""
    ).fetchall()
    rows = [r for r in rows if nfc(r[0]) in pdfs]
    random.Random(seed).shuffle(rows)
    return rows[:count]


def render(pdf_path, page_no, target):
    pdf = pdfium.PdfDocument(pdf_path)
    if not 1 <= page_no <= len(pdf):
        return False
    page = pdf[page_no - 1]
    width, height = page.get_size()
    image = page.render(scale=MAX_SIDE / max(width, height)).to_pil()
    image.convert("RGB").save(target, "JPEG", quality=90)
    return True


def read_page(config, image_path, drug_names):
    prompt = TALIMAT + (SOZLUK_EKI.format(ilaclar=", ".join(drug_names)) if config["sozluk"] else "")
    start = time.time()
    response = ollama.chat(
        model=config["model"],
        messages=[{"role": "user", "content": prompt, "images": [str(image_path)]}],
        options={"temperature": 0, "num_ctx": 8192, "num_predict": 1500},
    )
    return nfc(response["message"]["content"]).strip(), time.time() - start


def drug_report(text, index):
    meds = extract_medications_from_text(text, index)
    strong = {m["ilac_adi_normalize"] for m in meds if m["eslesme_guveni"] >= GUVEN_ESIGI}
    weak = {m["ilac_adi_normalize"] for m in meds if m["eslesme_guveni"] < GUVEN_ESIGI}
    return meds, strong, weak


def jaccard(a, b):
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def repeated_line_share(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return 0.0 if not lines else 1 - len(set(lines)) / len(lines)


def highlight(text, other, meds):
    """Words absent from the other model's reading are yellow; drugs are green."""
    words, other_words = text.split(), other.split()
    matcher = difflib.SequenceMatcher(a=[norm(w) for w in words], b=[norm(w) for w in other_words], autojunk=False)
    differs = set()
    for tag, i1, i2, _, _ in matcher.get_opcodes():
        if tag != "equal":
            differs.update(range(i1, i2))
    drug_words = {norm(w) for m in meds for w in m["ilac_adi_ham"].split()}
    out = []
    for i, word in enumerate(words):
        cls = "ilac" if norm(word) in drug_words else ("fark" if i in differs else "")
        out.append(f'<span class="{cls}">{html.escape(word)}</span>' if cls else html.escape(word))
    return " ".join(out).replace("[?]", '<span class="belirsiz">[?]</span>')


def write_html(results, summary):
    cards = []
    for r in results:
        image_b64 = base64.b64encode(Path(r["gorsel"]).read_bytes()).decode()
        cols = [f'<div class="kol"><h3>Eski OCR (veritabanı)</h3><p>{html.escape(r["eski_ocr"]).replace(chr(10), "<br>")}</p></div>']
        names = list(r["okumalar"])
        for name in names:
            other = r["okumalar"][names[1] if name == names[0] else names[0]]["metin"]
            reading = r["okumalar"][name]
            body = highlight(reading["metin"], other, reading["ilaclar"]).replace("\n", "<br>")
            cols.append(
                f'<div class="kol"><h3>{html.escape(name)} <small>{reading["sure"]:.0f} sn</small></h3>'
                f'<p>{body}</p><p class="ilaclar">İlaçlar: {html.escape(", ".join(sorted(reading["guclu"])) or "—")}</p></div>'
            )
        cards.append(
            f'<section><h2>Sayfa {r["no"]}</h2><div class="satir"><img src="data:image/jpeg;base64,{image_b64}">'
            f'<div class="kolonlar">{"".join(cols)}</div></div></section>'
        )
    rows = "".join(
        f"<tr><td>{html.escape(k)}</td>" + "".join(f"<td>{v}</td>" for v in s.values()) + "</tr>"
        for k, s in summary.items()
    )
    head = "".join(f"<th>{html.escape(k)}</th>" for k in next(iter(summary.values())))
    (OUT / "rapor.html").write_text(f"""<!doctype html><meta charset="utf-8">
<title>OCR deneme raporu</title>
<style>
body{{font-family:-apple-system,sans-serif;margin:16px;background:#fafafa;color:#222}}
table{{border-collapse:collapse;margin-bottom:24px}} td,th{{border:1px solid #ccc;padding:4px 8px;font-size:14px}}
section{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;margin-bottom:24px}}
.satir{{display:flex;gap:12px;align-items:flex-start}} img{{width:42%;position:sticky;top:8px;border:1px solid #ccc}}
.kolonlar{{display:flex;gap:8px;flex:1}} .kol{{flex:1;font-size:14px;line-height:1.5}} h3{{font-size:14px;margin:0 0 6px}}
.fark{{background:#ffe680}} .ilac{{background:#b7ebc0}} .belirsiz{{background:#ffb3b3}} .ilaclar{{color:#555;font-size:13px}}
</style>
<h1>OCR deneme raporu (yalnızca yerel — hasta verisi içerir, paylaşmayın)</h1>
<p>Sarı: iki modelin farklı okuduğu kelimeler · Yeşil: ilaç sözlüğüyle eşleşen kelimeler · Kırmızı: modelin “okuyamadım” dediği yerler</p>
<table><tr><th>Yapılandırma</th>{head}</tr>{rows}</table>
{"".join(cards)}""", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sayfa", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    (OUT / "gorseller").mkdir(exist_ok=True)

    with get_connection() as conn:
        index = build_surface_form_index_from_db(conn)
        drug_names = [r[0] for r in conn.execute("SELECT resmi_ad FROM ilac_sozluk ORDER BY resmi_ad")]
        pdfs = find_pdfs()
        pages = pick_pages(conn, pdfs, args.sayfa * 2, args.seed)

    results = []
    for filename, page_no, old_text in pages:
        if len(results) == args.sayfa:
            break
        image = OUT / "gorseller" / f"sayfa_{len(results) + 1:02d}.jpg"
        if not render(pdfs[nfc(filename)], page_no, image):
            continue
        results.append({"no": len(results) + 1, "gorsel": str(image), "eski_ocr": nfc(old_text), "okumalar": {}})
    print(f"{len(results)} sayfa hazırlandı.")

    for config in CONFIGS:  # model başına sırayla: bellekte aynı anda tek model
        for r in results:
            text, seconds = read_page(config, r["gorsel"], drug_names)
            meds, strong, weak = drug_report(text, index)
            r["okumalar"][config["ad"]] = {
                "metin": text, "sure": seconds, "ilaclar": meds,
                "guclu": sorted(strong), "zayif": sorted(weak),
            }
            print(f"  {config['ad']}: sayfa {r['no']} {seconds:.0f} sn")
        ollama.generate(model=config["model"], prompt="", keep_alive=0)  # belleği boşalt
        (OUT / "sonuclar.json").write_text(json.dumps(results, ensure_ascii=False, indent=1, default=list), encoding="utf-8")

    first, second = CONFIGS[0]["ad"], CONFIGS[1]["ad"]
    summary = {}
    for config in CONFIGS:
        name = config["ad"]
        rs = [r["okumalar"][name] for r in results]
        old_drugs = [drug_report(r["eski_ocr"], index)[1] for r in results]
        summary[name] = {
            "ort. süre (sn/sayfa)": round(sum(x["sure"] for x in rs) / len(rs), 1),
            "eski OCR ile benzerlik (%)": round(sum(fuzz.ratio(norm(x["metin"]), norm(r["eski_ocr"])) for x, r in zip(rs, results)) / len(rs), 1),
            "eski OCR ile ilaç uyumu (Jaccard)": round(sum(jaccard(set(x["guclu"]), o) for x, o in zip(rs, old_drugs)) / len(rs), 2),
            "güçlü ilaç eşleşmesi (toplam)": sum(len(x["guclu"]) for x in rs),
            "zayıf ilaç eşleşmesi (toplam)": sum(len(x["zayif"]) for x in rs),
            "[?] sayısı (toplam)": sum(x["metin"].count("[?]") for x in rs),
            "tekrar eden satır payı (%)": round(100 * sum(repeated_line_share(x["metin"]) for x in rs) / len(rs), 1),
            "ort. uzunluk / eski OCR": round(sum(len(x["metin"]) / max(1, len(r["eski_ocr"])) for x, r in zip(rs, results)) / len(rs), 2),
        }
    agreement = sum(fuzz.ratio(norm(r["okumalar"][first]["metin"]), norm(r["okumalar"][second]["metin"])) for r in results) / len(results)
    dict_effect = sum(fuzz.ratio(norm(r["okumalar"][first]["metin"]), norm(r["okumalar"][CONFIGS[2]["ad"]]["metin"])) for r in results) / len(results)
    eski_ilac = sum(len(drug_report(r["eski_ocr"], index)[1]) for r in results)

    write_html(results, summary)
    print("\n=== ÖZET (yalnızca sayılar) ===")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"4b ile 2b arasındaki uyum: %{agreement:.1f}")
    print(f"4b sözlüklü ile sözlüksüz arasındaki uyum: %{dict_effect:.1f}")
    print(f"Eski OCR'daki güçlü ilaç eşleşmesi (toplam): {eski_ilac}")
    print(f"Rapor: {OUT / 'rapor.html'}")


if __name__ == "__main__":
    main()

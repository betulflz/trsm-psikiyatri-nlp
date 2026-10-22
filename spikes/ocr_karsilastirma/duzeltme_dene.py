"""DENEME (spike): OCR çıktısını ikinci bir adımda bağlamla düzeltmek işe yarıyor mu?

İlk okuma: referans_sonuclar.json'daki "<VARSAYILAN_MODEL> + sözlük" okuması.
  A. metinden düzeltme: model görüntüyü görmez; taslak + ilaç sözlüğü ile düzeltir.
  B. görüntüyle düzeltme: model taslağı ve görüntüyü birlikte görür.
Her biri elle yazılmış referansa göre puanlanır. Ayrıca düzeltmenin DEĞİŞTİRDİĞİ
kelimeler sayılır: referansla eşleşen (iyi düzeltme), eşleşmeyen (uydurma) ve
taslakta doğruyken bozulan kelimeler. Ekrana YALNIZCA sayılar yazılır.

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 --with openpyxl python -u spikes/ocr_karsilastirma/duzeltme_dene.py
"""
import difflib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import ollama

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from calistir import OUT, VARSAYILAN_MODEL  # noqa: E402
from referans_karsilastir import RESULTS, load_pages, score, standardize  # noqa: E402
from trsm.db import get_connection  # noqa: E402

TASLAK = f"{VARSAYILAN_MODEL} + sözlük"
ORTAK = (
    "Bu metin, Türkçe el yazısıyla tutulmuş bir psikiyatri polikliniği takip notunun "
    "otomatik okunmuş (OCR) taslağıdır ve hatalı kelimeler içerir. Yanlış okunmuş ya da "
    "anlamsız kelimeleri bağlama göre düzelt. Yalnızca hatalı kelimeleri değiştir; doğru "
    "görünen kelimelere dokunma, cümle ekleme, özetleme, yorum yapma. Satır düzenini koru. "
    "İlaç adları şu listeden olabilir: {ilaclar}. Yalnızca düzeltilmiş metni yaz."
)
YONTEMLER = {
    "A. metinden düzeltme": {"ek": "", "gorsel": False},
    "B. görüntüyle düzeltme": {"ek": " Görüntüdeki el yazısına bakarak karar ver; görüntüde olmayan bir şey yazma.", "gorsel": True},
}
CIKTI = OUT / "duzeltme_sonuclar.json"


def change_report(reference, draft, corrected):
    """Count words the correction changed and whether each change matches the reference."""
    ref = Counter(reference.split())
    draft_words, new_words = draft.split(), corrected.split()
    good = bad = broken = 0
    matcher = difflib.SequenceMatcher(a=draft_words, b=new_words, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        for word in new_words[j1:j2]:
            if ref[word] > 0:
                good += 1
            else:
                bad += 1
        broken += sum(1 for word in draft_words[i1:i2] if ref[word] > 0 and word not in new_words[j1:j2])
    return good, bad, broken


def main():
    pages = load_pages()
    saved = json.loads(RESULTS.read_text(encoding="utf-8"))
    out = json.loads(CIKTI.read_text(encoding="utf-8")) if CIKTI.exists() else {}
    with get_connection() as conn:
        drug_names = [r[0] for r in conn.execute("SELECT resmi_ad FROM ilac_sozluk ORDER BY resmi_ad")]

    for name, method in YONTEMLER.items():
        prompt = ORTAK.format(ilaclar=", ".join(drug_names)) + method["ek"]
        for page in pages:
            key = str(page["no"])
            if name in out.get(key, {}):
                continue
            draft = saved[key][TASLAK]["metin"]
            message = {"role": "user", "content": f"{prompt}\n\nTASLAK:\n{draft}"}
            if method["gorsel"]:
                message["images"] = [str(OUT / "referans_gorseller" / f"ref_{page['no']:02d}.jpg")]
            start = time.time()
            response = ollama.chat(
                model=VARSAYILAN_MODEL, messages=[message],
                options={"temperature": 0, "num_ctx": 8192, "num_predict": 1500}, think=False,
            )
            out.setdefault(key, {})[name] = {"metin": response["message"]["content"].strip(), "sure": time.time() - start}
            CIKTI.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {name}: sayfa {page['no']} {out[key][name]['sure']:.0f} sn")
    ollama.generate(model=VARSAYILAN_MODEL, prompt="", keep_alive=0)

    print("\n=== Referansa göre (düşük CER/WER iyi, yüksek yakalama iyi) ===")
    rows = {"taslak (ilk okuma)": None, **{n: n for n in YONTEMLER}}
    for label, name in rows.items():
        scores, good, bad, broken = [], 0, 0, 0
        for page in pages:
            key = str(page["no"])
            reference = standardize(page["referans"], strip_form=False)
            draft = standardize(saved[key][TASLAK]["metin"])
            text = draft if name is None else standardize(out[key][name]["metin"])
            scores.append(score(reference, text))
            if name is not None:
                g, b, k = change_report(reference, draft, text)
                good, bad, broken = good + g, bad + b, broken + k
        line = (f"{label:<24} CER (%): {100 * sum(s['cer'] for s in scores) / len(scores):.1f}  "
                f"WER (%): {100 * sum(s['wer'] for s in scores) / len(scores):.1f}  "
                f"kelime yakalama (%): {100 * sum(s['yakalama'] for s in scores) / len(scores):.1f}")
        if name is not None:
            changed = good + bad
            line += (f"  | değişen kelime: {changed}, referansla eşleşen: {good}"
                     f" ({100 * good / max(1, changed):.0f}%), eşleşmeyen: {bad}, bozulan doğru kelime: {broken}"
                     f"  | {sum(out[str(p['no'])][name]['sure'] for p in pages) / len(pages):.0f} sn/sayfa")
        print(line)


if __name__ == "__main__":
    main()

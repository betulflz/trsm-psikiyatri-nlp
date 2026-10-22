"""DENEME (spike): alana özel kelime hazinesiyle OCR düzeltme (dil modeli yok).

Veritabanındaki ziyaret metinlerinden kelime sıklığı çıkarılır; en az ESIK kez geçen
kelimeler "bilinen" sayılır. OCR çıktısındaki bilinmeyen her kelime, RapidFuzz ile en
yakın bilinen kelimeye (benzerlik >= BENZERLIK) çevrilir; çevrilen kelime ürün
ekranında sarıyla işaretlenecek kelimedir. Elle yazılmış referansa göre puanlanır.
Ekrana YALNIZCA sayılar yazılır; hiçbir kelime yazdırılmaz.

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 --with openpyxl python spikes/ocr_karsilastirma/sozcuk_duzelt.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz, process

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from calistir import VARSAYILAN_MODEL  # noqa: E402
from duzeltme_dene import change_report  # noqa: E402
from referans_karsilastir import RESULTS, load_pages, score, standardize  # noqa: E402
from trsm.db import get_connection  # noqa: E402

TASLAK = f"{VARSAYILAN_MODEL} + sözlük"


def vocabulary(conn):
    counts = Counter()
    for mudahale, sonuc in conn.execute("SELECT ham_mudahale_metni, ham_sonuc_metni FROM ziyaret"):
        counts.update(standardize(f"{mudahale or ''} {sonuc or ''}", strip_form=False).split())
    for (name,) in conn.execute("SELECT resmi_ad FROM ilac_sozluk"):
        counts.update({w: 10**6 for w in standardize(name, strip_form=False).split()})
    return counts


def correct(text, known, known_list, similarity):
    out, flagged = [], 0
    for word in text.split():
        if word in known or len(word) < 3 or re.fullmatch(r"\d+", word):
            out.append(word)
            continue
        match = process.extractOne(word, known_list, scorer=fuzz.ratio, score_cutoff=similarity)
        if match:
            out.append(match[0])
            flagged += 1
        else:
            out.append(word)
    return " ".join(out), flagged


def main():
    pages = load_pages()
    saved = json.loads(RESULTS.read_text(encoding="utf-8"))
    with get_connection() as conn:
        counts = vocabulary(conn)
    print(f"Kelime hazinesi: {len(counts)} farklı kelime")

    rows = []
    drafts = {p["no"]: standardize(saved[str(p["no"])][TASLAK]["metin"]) for p in pages}
    refs = {p["no"]: standardize(p["referans"], strip_form=False) for p in pages}
    base = [score(refs[n], drafts[n]) for n in refs]
    unknown_share = sum(sum(w not in counts for w in d.split()) / max(1, len(d.split())) for d in drafts.values()) / len(drafts)
    print(f"Taslakta hazinede olmayan kelime payı: %{100 * unknown_share:.1f}")
    print(f"{'taslak':<22} CER %{100 * sum(s['cer'] for s in base) / len(base):.1f}  "
          f"WER %{100 * sum(s['wer'] for s in base) / len(base):.1f}  yakalama %{100 * sum(s['yakalama'] for s in base) / len(base):.1f}")

    for min_count in (5, 20, 100):
        known = {w for w, c in counts.items() if c >= min_count}
        known_list = sorted(known, key=lambda w: -counts[w])
        for similarity in (75, 85):
            scores, good, bad, broken, flagged = [], 0, 0, 0, 0
            for n in refs:
                text, f = correct(drafts[n], known, known_list, similarity)
                scores.append(score(refs[n], text))
                g, b, k = change_report(refs[n], drafts[n], text)
                good, bad, broken, flagged = good + g, bad + b, broken + k, flagged + f
            label = f"eşik {min_count}, benzerlik {similarity}"
            print(f"{label:<22} CER %{100 * sum(s['cer'] for s in scores) / len(scores):.1f}  "
                  f"WER %{100 * sum(s['wer'] for s in scores) / len(scores):.1f}  "
                  f"yakalama %{100 * sum(s['yakalama'] for s in scores) / len(scores):.1f}  "
                  f"| işaretlenen {flagged}, referansla eşleşen {good}, eşleşmeyen {bad}, bozulan doğru {broken}")


if __name__ == "__main__":
    main()

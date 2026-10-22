"""DENEME (spike): etiketler.json'a göre her okuma yapılandırmasının ilaç ve semptom teması başarısı.

Ekrana YALNIZCA sayısal özet yazar. Ayrıca "önceki sayfanın ilaç listesi bu
sayfadaki ilaçları ne kadar tahmin ediyor?" sorusunu ölçer (bağlam katmanı
için ilk kanıt). Önceki sayfa bilgisi eski OCR'dan geldiği için gürültülüdür.
Bir okumanın hiç etiketlenmemiş adayı olan sayfalar o okumanın ölçümüne alınmaz.

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 python spikes/ocr_karsilastirma/analiz.py
"""
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from calistir import GUVEN_ESIGI, OUT, find_pdfs, nfc, norm, pick_pages  # noqa: E402
from trsm.db import get_connection  # noqa: E402
from trsm.drug_matching import build_surface_form_index_from_db  # noqa: E402
from trsm.medication_pipeline import extract_medications_from_text  # noqa: E402

ESKI = "eski OCR"
BAGLAM_ICIN = "qwen3-vl:4b + sözlük"


def dose_key(dose):
    return norm(dose).replace(" ", "")


def selected_pages(conn, count, seed=42):
    """Reproduce calistir.py's page choice to get each result's source page."""
    pdfs = find_pdfs()
    chosen = []
    for filename, page_no, old_text in pick_pages(conn, pdfs, count * 2, seed):
        if len(chosen) == count:
            break
        if 1 <= page_no <= len(pdfium.PdfDocument(pdfs[nfc(filename)])):
            chosen.append((filename, page_no, nfc(old_text)))
    return chosen


def previous_page_drugs(conn, filename, page_no):
    row = conn.execute(
        "SELECT max(sayfa_no) FROM ziyaret WHERE kaynak_dosya_adi = %s AND sayfa_no < %s",
        (filename, page_no),
    ).fetchone()
    if row[0] is None:
        return None
    drugs = conn.execute(
        """SELECT DISTINCT k.ilac_adi_normalize FROM ilac_kullanimi k JOIN ziyaret z ON z.id = k.ziyaret_id
           WHERE z.kaynak_dosya_adi = %s AND z.sayfa_no = %s AND k.eslesme_guveni >= %s
             AND k.ilac_adi_normalize IS NOT NULL""",
        (filename, row[0], GUVEN_ESIGI),
    ).fetchall()
    return {d[0] for d in drugs}


def scores(pairs):
    """pairs: list of (predicted set, truth set) for labelled pages."""
    tp = sum(len(p & t) for p, t in pairs)
    predicted = sum(len(p) for p, _ in pairs)
    truth = sum(len(t) for _, t in pairs)
    return {
        "sayfa": len(pairs),
        "doğru": tp,
        "uydurma (yanlış pozitif)": predicted - tp,
        "kaçırılan": truth - tp,
        "isabet (%)": round(100 * tp / predicted, 1) if predicted else None,
        "yakalama (%)": round(100 * tp / truth, 1) if truth else None,
    }


def answered(section):
    return {name for name, d in (section or {}).items() if d.get("var") is not None}


def main():
    results = json.loads((OUT / "sonuclar.json").read_text(encoding="utf-8"))
    path = OUT / "etiketler.json"
    labels = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    done = [r for r in results if str(r["no"]) in labels]
    print(f"Etiketli sayfa: {len(done)}/{len(results)}")
    if not done:
        return

    truth, truth_dose, known_drugs, truth_themes, known_themes = {}, {}, {}, {}, {}
    for r in done:
        lab = labels[str(r["no"])]
        added = {x["ad"]: x["doz"] for x in lab.get("eklenen", [])}
        truth[r["no"]] = {a for a, d in lab["adaylar"].items() if d["var"]} | set(added)
        known_drugs[r["no"]] = answered(lab["adaylar"]) | set(added)
        doses = {a: d.get("doz") for a, d in lab["adaylar"].items() if d["var"]}
        doses.update(added)
        truth_dose[r["no"]] = {a: dose_key(d) for a, d in doses.items() if d and d.strip()}
        if "temalar" in lab:
            truth_themes[r["no"]] = {t for t, d in lab["temalar"].items() if d["var"]}
            known_themes[r["no"]] = answered(lab["temalar"])
    print(f"Gerçek ilaç (toplam): {sum(len(t) for t in truth.values())}; "
          f"tema etiketli sayfa: {len(truth_themes)}, gerçek tema (toplam): {sum(len(t) for t in truth_themes.values())}")

    with get_connection() as conn:
        index = build_surface_form_index_from_db(conn)
        readings = {}
        for r in done:
            per = {name: x["ilaclar"] for name, x in r["okumalar"].items()}
            per[ESKI] = extract_medications_from_text(r["eski_ocr"], index)
            readings[r["no"]] = per
        chosen = selected_pages(conn, len(results))
        same = sum(1 for r, c in zip(results, chosen) if c[2] == r["eski_ocr"])
        print(f"Sayfa eşlemesi doğrulandı: {same}/{len(results)}")
        context = {}
        if same == len(results):
            for r, (filename, page_no, _) in zip(results, chosen):
                context[r["no"]] = previous_page_drugs(conn, filename, page_no)

    names = list(dict.fromkeys(n for r in done for n in readings[r["no"]]))
    summary, waiting = {}, 0
    for name in names:
        for label, min_conf in (("güçlü", GUVEN_ESIGI), ("tümü", 0)):
            pairs, dose_ok, dose_total = [], 0, 0
            for r in done:
                if name not in readings[r["no"]]:
                    continue
                meds = [m for m in readings[r["no"]][name] if m["eslesme_guveni"] >= min_conf]
                predicted = {m["ilac_adi_normalize"] for m in meds}
                if predicted - known_drugs[r["no"]]:
                    waiting += label == "tümü"
                    continue
                pairs.append((predicted, truth[r["no"]]))
                for m in meds:
                    want = truth_dose[r["no"]].get(m["ilac_adi_normalize"])
                    if want:
                        dose_total += 1
                        dose_ok += dose_key(m["doz"] or "") == want
            s = scores(pairs)
            s["doz doğru (%)"] = round(100 * dose_ok / dose_total, 1) if dose_total else None
            summary[f"{name} [{label}]"] = s
    print("\n=== İlaç ===")
    if waiting:
        print(f"(Etiketlenmemiş yeni aday yüzünden ölçüm dışı kalan okuma-sayfa: {waiting})")
    print(json.dumps(summary, ensure_ascii=False, indent=1))

    if truth_themes:
        from etiketle import page_themes
        from trsm.model_loader import load_local_minilm
        from trsm.transparent_symptom_query import build_category_seed_embeddings

        model = load_local_minilm()
        seeds = build_category_seed_embeddings(model)
        theme_summary = {}
        for name in names:
            pairs = []
            for r in done:
                if r["no"] not in truth_themes or (name != ESKI and name not in r["okumalar"]):
                    continue
                text = r["eski_ocr"] if name == ESKI else r["okumalar"][name]["metin"]
                predicted = page_themes(text, model, seeds)
                if predicted - known_themes[r["no"]]:
                    continue
                pairs.append((predicted, truth_themes[r["no"]]))
            theme_summary[name] = scores(pairs)
        print("\n=== Semptom teması ===")
        print(json.dumps(theme_summary, ensure_ascii=False, indent=1))

    if context:
        with_ctx = [r for r in done if context[r["no"]] is not None]
        print(f"\n=== Bağlam: önceki sayfanın ilaçları ({len(with_ctx)}/{len(done)} sayfada önceki sayfa var) ===")
        if with_ctx:
            model_drugs = {
                r["no"]: {m["ilac_adi_normalize"] for m in readings[r["no"]][BAGLAM_ICIN] if m["eslesme_guveni"] >= GUVEN_ESIGI}
                for r in with_ctx
            }
            print("Yalnız önceki sayfa:", json.dumps(scores([(context[r["no"]], truth[r["no"]]) for r in with_ctx]), ensure_ascii=False))
            print(f"{BAGLAM_ICIN} [güçlü]:", json.dumps(scores([(model_drugs[r["no"]], truth[r["no"]]) for r in with_ctx]), ensure_ascii=False))
            print(f"{BAGLAM_ICIN} ∪ önceki sayfa:", json.dumps(scores([(model_drugs[r["no"]] | context[r["no"]], truth[r["no"]]) for r in with_ctx]), ensure_ascii=False))
            print(f"{BAGLAM_ICIN} ∩ önceki sayfa:", json.dumps(scores([(model_drugs[r["no"]] & context[r["no"]], truth[r["no"]]) for r in with_ctx]), ensure_ascii=False))
    else:
        print("Sayfa eşlemesi tutmadı; bağlam ölçümü atlandı.")


if __name__ == "__main__":
    main()

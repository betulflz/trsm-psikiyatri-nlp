"""Constrained local-Qwen candidate labels for the validation experiment.

This module intentionally does not write labels into the production database.
Its outputs are candidates to be measured against clinician consensus.
"""

import csv
import json
import os

from .symptom_categories import KATEGORILER
from .ollama_support import get_ollama_client


QWEN_LABEL_MODEL = os.getenv("TRSM_QWEN_LABEL_MODEL", "qwen2.5:3b")


def _empty_result(status):
    return {
        "kategoriler": [],
        "metinsel_kanit": "",
        "insan_incelemesi_gerekli": True,
        "durum": status,
    }


def build_qwen_label_prompt(phrase):
    categories = "\n".join(f"- {category}" for category in KATEGORILER)
    return (
        "Yerel bir klinik-NLP veri doğrulama yardımcısısın. Tanı, tedavi, ilaç, "
        "risk değerlendirmesi veya yeni klinik bilgi üretme. Yalnızca aşağıdaki "
        "ifadenin açıkça desteklediği geniş betimleyici temaları seç. Emin değilsen "
        "boş kategori listesi kullan ve insan incelemesi gerektiğini belirt.\n\n"
        "İzinli kategori listesi:\n"
        f"{categories}\n\n"
        f"İfade: {phrase}\n\n"
        "Yalnızca JSON döndür: kategoriler (izinli adlardan liste), metinsel_kanit "
        "(ifadeden aynen kısa alıntı veya boş metin), insan_incelemesi_gerekli (boolean)."
    )


def _is_substring_casefold(needle, haystack):
    return needle.casefold() in haystack.casefold()


def label_phrase_with_qwen(phrase, client=None):
    """Return validated, local-Qwen candidate labels; fail closed on bad output."""
    if not phrase or not str(phrase).strip():
        return _empty_result("bos_ifade")
    if client is None:
        client = get_ollama_client()
    if client is None:
        return _empty_result("qwen_python_paketi_yok")
    try:
        response = client.chat(
            model=QWEN_LABEL_MODEL,
            messages=[{"role": "user", "content": build_qwen_label_prompt(str(phrase))}],
            format={
                "type": "object",
                "properties": {
                    "kategoriler": {"type": "array", "items": {"type": "string"}},
                    "metinsel_kanit": {"type": "string"},
                    "insan_incelemesi_gerekli": {"type": "boolean"},
                },
                "required": ["kategoriler", "metinsel_kanit", "insan_incelemesi_gerekli"],
                "additionalProperties": False,
            },
            options={"temperature": 0},
        )
        payload = json.loads(response["message"]["content"])
        labels = payload["kategoriler"]
        evidence = payload["metinsel_kanit"].strip()
        review_required = payload["insan_incelemesi_gerekli"]
        if (
            not isinstance(labels, list)
            or not all(isinstance(label, str) and label in KATEGORILER for label in labels)
            or not isinstance(review_required, bool)
            or (evidence and not _is_substring_casefold(evidence, str(phrase)))
        ):
            return _empty_result("gecersiz_qwen_ciktisi")
        return {
            "kategoriler": list(dict.fromkeys(labels)),
            "metinsel_kanit": evidence,
            "insan_incelemesi_gerekli": review_required,
            "durum": "gecerli_qwen_adayi",
        }
    except Exception:
        return _empty_result("qwen_erisilemedi_veya_json_gecersiz")


def label_validation_csv_with_qwen(input_csv, output_csv, client=None):
    """Add Qwen candidates to a copy of a validation sheet, never overwrite it."""
    with open(input_csv, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    if "ifade" not in fieldnames:
        raise ValueError("CSV'de ifade sütunu bulunmalı.")
    extra_fields = [
        "qwen_kategoriler", "qwen_metinsel_kanit", "qwen_insan_incelemesi_gerekli", "qwen_durum",
    ]
    output_fields = fieldnames + [field for field in extra_fields if field not in fieldnames]
    with open(output_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, delimiter=";")
        writer.writeheader()
        for row in rows:
            result = label_phrase_with_qwen(row["ifade"], client=client)
            row.update({
                "qwen_kategoriler": "|".join(result["kategoriler"]),
                "qwen_metinsel_kanit": result["metinsel_kanit"],
                "qwen_insan_incelemesi_gerekli": "evet" if result["insan_incelemesi_gerekli"] else "hayır",
                "qwen_durum": result["durum"],
            })
            writer.writerow(row)
    return {"toplam": len(rows), "model": QWEN_LABEL_MODEL}


def compare_qwen_with_baseline(classified_phrases, client=None):
    """Compare Qwen candidates with MiniLM/rule labels without calling it truth.

    Agreement means only that two automated methods produced the same allowed
    broad label set. It is surfaced as a quality signal, never as accuracy.
    """
    comparisons = []
    for clause in classified_phrases:
        baseline = [item["kategori"] for item in clause.get("kategoriler", [])]
        quality = clause.get("kalite_sinyali", {})
        if quality.get("durum") == "olumsuzlama_kontrolu":
            comparisons.append({
                "ifade": clause["ifade"],
                "sistem_kategoriler": baseline,
                "qwen_kategoriler": [],
                "durum": "atlanmis_olumsuzlama",
                "mesaj": "Olumsuzlama işareti bulunan ifade Qwen ile otomatik karşılaştırılmadı.",
            })
            continue
        qwen = label_phrase_with_qwen(clause["ifade"], client=client)
        qwen_labels = qwen["kategoriler"]
        if qwen["durum"] != "gecerli_qwen_adayi":
            status = "qwen_belirsiz"
            message = "Qwen şemaya uygun aday üretemedi; insan incelemesi gerekir."
        elif set(baseline) == set(qwen_labels):
            status = "otomatik_uyum"
            message = "MiniLM/kural ve Qwen aynı geniş temaları önerdi; bu doğruluk kanıtı değildir."
        else:
            status = "otomatik_uyusmazlik"
            message = "İki otomatik yöntem farklı tema önerdi; sonuç kesin kabul edilmemeli."
        comparisons.append({
            "ifade": clause["ifade"],
            "sistem_kategoriler": baseline,
            "qwen_kategoriler": qwen_labels,
            "qwen_metinsel_kanit": qwen["metinsel_kanit"],
            "qwen_inceleme_gerekli": qwen["insan_incelemesi_gerekli"],
            "durum": status,
            "mesaj": message,
        })
    return {
        "ifade_karsilastirmalari": comparisons,
        "ozet": {
            "uyumlu": sum(row["durum"] == "otomatik_uyum" for row in comparisons),
            "uyusmayan": sum(row["durum"] == "otomatik_uyusmazlik" for row in comparisons),
            "qwen_belirsiz": sum(row["durum"] == "qwen_belirsiz" for row in comparisons),
            "atlanmis_olumsuzlama": sum(row["durum"] == "atlanmis_olumsuzlama" for row in comparisons),
        },
        "sinirlilik_notu": "Yöntemler arası uyum, klinik doğruluk veya tedavi uygunluğu anlamına gelmez.",
    }

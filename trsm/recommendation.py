import os
import re
import json

from .ollama_support import get_ollama_client


LLM_MODEL_NAME = os.getenv("TRSM_LLM_MODEL", "qwen2.5:3b")

VERI_YOK_MESAJI = "Bu semptoma yeterince benzer geçmiş veri bulunamadı."
TIBBI_UYARI = (
    "Bu istatistiksel bir özet olup tıbbi tavsiye veya reçete değildir; "
    "tedavi kararı hekim tarafından verilmelidir."
)
YASAKLI_OZET_IFADELER = (
    "reçete", "reçetelen", "önerilir", "önerilmel", "kullanmalıdır",
    "kullanılmalıdır", "başlanmalı", "doz", "tedavi edil",
)


def compute_drug_statistics(conn, ziyaret_ids, guven_esigi=90):
    if not ziyaret_ids:
        return []

    placeholders = ",".join(["%s"] * len(ziyaret_ids))
    query = f"""
        SELECT ilac_adi_normalize, COUNT(*) as sayi
        FROM ilac_kullanimi
        WHERE ziyaret_id IN ({placeholders}) AND eslesme_guveni >= %s
        GROUP BY ilac_adi_normalize
        ORDER BY sayi DESC, ilac_adi_normalize ASC
    """
    cur = conn.cursor()
    cur.execute(query, list(ziyaret_ids) + [guven_esigi])
    rows = cur.fetchall()

    toplam = sum(sayi for _, sayi in rows)
    if toplam == 0:
        return []

    return [
        {"ilac": ilac, "sayi": sayi, "yuzde": round(100 * sayi / toplam, 1)}
        for ilac, sayi in rows
    ]


def generate_summary(query_text, statistics, client=None, demographic_context=None):
    if not statistics:
        return VERI_YOK_MESAJI

    stat_lines = "\n".join(f"- {s['ilac']}: %{s['yuzde']}" for s in statistics)
    profile_line = (
        f"Bu toplulaştırılmış özet, {demographic_context} profili için filtrelenmiştir.\n"
        if demographic_context else ""
    )
    prompt = (
        f"Bir hasta '{query_text}' şikayetiyle başvurdu. Geçmişte benzer semptomlu "
        f"ziyaretlerde yazılan reçete kayıtlarının ilaç bazında dağılımı:\n{stat_lines}\n\n"
        f"{profile_line}"
        "Bu istatistiği 2-3 cümlelik doğal bir Türkçe özet haline getir. "
        "Sadece verilen sayıları kullan, yeni bilgi uydurma; tedavi önerisi veya "
        "doz yazma."
    )

    if client is None:
        client = get_ollama_client()
    if client is None:
        return VERI_YOK_MESAJI

    response = client.chat(model=LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def build_evidence_summary(transparent_result):
    """Create the authoritative summary without using a language model.

    All counts, percentages and medication names are rendered directly from
    Python's aggregate result.  This is the primary output; an LLM may only
    add an optional explanatory note later.
    """
    combined = transparent_result["birlesik"]
    themes = [row["kategori"] for row in transparent_result["kategoriler"]]
    profile = f"{combined['yas']} yaş ({combined['yas_grubu']}), {combined['cinsiyet']}"
    if not themes:
        text = (
            f"{profile} profili için kullanıcı metnindeki ifadeler, tanımlı geniş "
            "semptom temalarıyla güvenle eşleşmedi. Bu nedenle ilaç örüntüsü hesaplanmadı."
        )
    elif not combined["uyumlu_ziyaret_sayisi"]:
        text = (
            f"{profile} profili için {', '.join(themes)} temaları analiz edildi; "
            "ancak yaş ve cinsiyet filtresinden geçen doğrulanmış geçmiş ziyaret bulunamadı."
        )
    else:
        base = (
            f"{profile} profili için {', '.join(themes)} temaları analiz edildi. "
            f"Yaş ve cinsiyet filtresinden {combined['uyumlu_hasta_sayisi']} kişi ve "
            f"{combined['uyumlu_ziyaret_sayisi']} ziyaret geçti."
        )
        drugs = combined["ilaclar"][:3]
        if drugs:
            drug_text = "; ".join(
                f"{row['ilac']} %{row['yuzde']}" for row in drugs
            )
            text = f"{base} Birleşik kayıtlarda en sık görülen ilaç kayıtları: {drug_text}."
        else:
            text = f"{base} Bu ziyaretlerde yüksek güvenli ilaç kaydı bulunamadı."
        if combined["kucuk_orneklem"]:
            text += " Örneklem küçüktür; sonuç yalnızca keşif amaçlı değerlendirilmelidir."
    return {
        "metin": text,
        "profil": profile,
        "temalar": themes,
        "uyumlu_hasta_sayisi": combined["uyumlu_hasta_sayisi"],
        "uyumlu_ziyaret_sayisi": combined["uyumlu_ziyaret_sayisi"],
        "kucuk_orneklem": combined["kucuk_orneklem"],
        "ilaclar": combined["ilaclar"],
        "uyari": TIBBI_UYARI,
    }


def _explanatory_prompt(evidence):
    controlled_note = build_contextual_explanatory_note(evidence)
    # The model does not receive patient text, medication names, counts or the
    # demographic profile. The evidence layer produces the factual wording;
    # Qwen is deliberately constrained to return that wording in a structured
    # response, rather than inventing a clinical interpretation.
    return (
        "Sadece JSON döndür. `note` değerine aşağıdaki metni hiçbir kelimesini "
        "değiştirmeden yaz. Başka alan, açıklama veya metin ekleme.\n\n"
        f"METİN:\n{controlled_note}"
    )


def build_contextual_explanatory_note(evidence):
    """Build a query-specific explanation from verified aggregate fields.

    This deliberately uses no LLM inference: it explains the method and the
    exact visible theme labels without turning their co-occurrence into a
    diagnosis or a causal claim.
    """
    themes = evidence["temalar"]
    if not themes:
        return (
            "Bu sorguda güvenle eşleşen geniş bir semptom teması bulunmadığı için "
            "yalnızca sınırlı bir örüntü incelemesi yapılabildi. Klinik değerlendirme "
            "ve tedavi kararı hekim tarafından verilmelidir."
        )
    theme_text = ", ".join(themes)
    return (
        f"Bu sorguda {theme_text} temaları birlikte değerlendirildi; her tema benzer "
        "geçmiş semptom ifadeleriyle anlamsal olarak eşleştirildi, ortak ziyaretler bir "
        "kez sayılarak yaş ve cinsiyet filtresi uygulandı. Bu gözlemsel örüntü klinik "
        "değerlendirme veya tedavi önerisi değildir; karar hekim tarafından verilmelidir."
    )


def _is_safe_explanatory_note(text, evidence, expected_note=None):
    if not isinstance(text, str) or not text.strip() or len(text) > 450:
        return False
    if "\n" in text.strip():
        return False
    lowered = text.casefold()
    if any(term in lowered for term in YASAKLI_OZET_IFADELER):
        return False
    if re.search(r"\d|%", text):
        return False
    if any(drug["ilac"].casefold() in lowered for drug in evidence["ilaclar"]):
        return False
    if expected_note is not None and text.strip() != expected_note:
        return False
    # Limit the free-form prose to the promised two-sentence explanatory note.
    sentences = re.findall(r"[^.!?]+[.!?]", text.strip())
    return len(sentences) == 2 and "".join(sentences).strip() == text.strip()


def generate_explanatory_note(evidence, client=None, return_source=False):
    """Ask the local LLM for prose only; return a fixed fallback if unsafe."""
    fallback = build_contextual_explanatory_note(evidence)
    def result(text, source):
        return (text, source) if return_source else text

    if not evidence["temalar"] or not evidence["uyumlu_ziyaret_sayisi"]:
        return result(fallback, "sabit")
    if client is None:
        client = get_ollama_client()
    if client is None:
        return result(fallback, "sabit")
    try:
        response = client.chat(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": _explanatory_prompt(evidence)}],
            format={
                "type": "object",
                "properties": {"note": {"type": "string"}},
                "required": ["note"],
                "additionalProperties": False,
            },
            options={"temperature": 0},
        )
        payload = json.loads(response["message"]["content"])
        note = payload["note"].strip()
    except Exception:
        # The deterministic evidence summary remains available when Ollama is
        # stopped, a model is missing, or the local request times out.
        return result(fallback, "sabit")
    return result(note, "qwen") if _is_safe_explanatory_note(note, evidence, fallback) else result(fallback, "sabit")

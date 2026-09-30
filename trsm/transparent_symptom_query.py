"""Explainable multi-symptom search for the local demographic query screen."""

import re

import numpy as np

from .profiled_recommendation import compute_profiled_recommendation, normalize_profile
from .symptom_categories import KATEGORILER
from .symptom_similarity import find_similar_phrases


CATEGORY_SIMILARITY_THRESHOLD = 0.60
MAX_CATEGORIES_PER_CLAUSE = 2
CATEGORY_SCORE_MARGIN = 0.12
SEARCH_SIMILARITY_THRESHOLD = 0.50
SEARCH_TOP_N = 1000
MAX_USER_PHRASES = 12

# These expressions require an immediate clinical safety response; an
# observational medication pattern is not an appropriate output for them.
HIGH_RISK_PATTERNS = (
    "intihar", "kendimi öldür", "ölmek istiyorum", "canıma kıy",
    "kendime zarar", "kendini öldür", "kendine zarar",
)
HIGH_RISK_MESSAGE = (
    "Metinde kendine zarar veya intihar riski çağrıştırabilecek bir ifade algılandı. "
    "Bu araç bu durumda ilaç örüntüsü üretmez; gecikmeden sorumlu hekim, acil "
    "servis veya yerel acil destek hattı ile iletişime geçilmelidir."
)

NEGATION_TERMS = (
    "yok", "değil", "olmadı", "olmuyor", "yaşamıyor", "görülmedi", "duymuyor",
)


# A comma in Turkish often separates adjectives inside one symptom statement
# ("kötü, istenmeyen düşünceler").  It is therefore a boundary only when both
# sides look like self-contained symptom clauses.
PREDICATE_WORDS = {
    "var", "yok", "değil", "hissediyorum", "hissediyor", "yaşıyorum",
    "yaşıyor", "düşünüyorum", "düşünüyor", "duyuyorum", "duyuyor",
    "görüyorum", "görüyor", "kusuyorum", "kusuyor",
}
PREDICATE_ENDINGS = (
    "yor", "ıyorum", "iyorum", "uyorum", "üyorum", "mış", "miş", "muş", "müş",
    "yım", "yim", "yum", "yüm",
)


def split_user_symptoms(text):
    """Split a long user narrative into readable symptom clauses.

    Full stops, semicolons and new lines are hard boundaries. Commas are soft
    boundaries: they split only two predicate-like fragments, so a phrase such
    as "kötü, istenmeyen düşünceler geliyor" remains intact. Clauses are
    retained verbatim for display; they are the user's own input, never
    historical patient text.
    """
    if not text or not text.strip():
        return []

    def has_predicate(fragment):
        words = re.findall(r"[a-zçğıöşü]+", fragment.casefold())
        if not words:
            return False
        last_word = words[-1]
        return last_word in PREDICATE_WORDS or last_word.endswith(PREDICATE_ENDINGS)

    clauses = []
    for hard_clause in re.split(r"[.;\n]+", text):
        comma_parts = [part.strip() for part in hard_clause.split(",")]
        comma_parts = [part for part in comma_parts if part]
        if not comma_parts:
            continue
        current = comma_parts[0]
        for next_part in comma_parts[1:]:
            if has_predicate(current) and has_predicate(next_part):
                clauses.append(current)
                current = next_part
            else:
                current = f"{current}, {next_part}"
        clauses.append(current)

    cleaned = []
    seen = set()
    for clause in clauses:
        clause = re.sub(r"\s+", " ", clause).strip(" -–—\t")
        key = clause.casefold()
        if len(clause) < 4 or key in seen:
            continue
        cleaned.append(clause)
        seen.add(key)
        if len(cleaned) == MAX_USER_PHRASES:
            break
    return cleaned


def contains_high_risk_expression(clauses):
    """Detect explicit self-harm language before running statistical matching."""
    return any(pattern in clause.casefold() for clause in clauses for pattern in HIGH_RISK_PATTERNS)


def _negated_categories(clause):
    """Find explicit seed mentions immediately followed by a negation cue.

    This is a conservative safety guard, not a full Turkish negation parser.
    A flagged category is withheld from automatic labelling rather than being
    treated as an absent clinical symptom.
    """
    lowered = clause.casefold()
    negated = set()
    for category, seeds in KATEGORILER.items():
        for seed in seeds:
            seed_lower = seed.casefold()
            start = lowered.find(seed_lower)
            while start != -1:
                suffix = lowered[start + len(seed_lower): start + len(seed_lower) + 32]
                if any(re.search(rf"\b{re.escape(term)}\b", suffix) for term in NEGATION_TERMS):
                    negated.add(category)
                    break
                start = lowered.find(seed_lower, start + len(seed_lower))
    return negated


def _normalize_rows(vectors):
    vectors = np.asarray(vectors, dtype=float)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms != 0)


def build_category_seed_embeddings(model):
    """Embed every visible category seed once for reuse during a session."""
    seed_texts = []
    seed_categories = []
    for category, seeds in KATEGORILER.items():
        seed_texts.extend(seeds)
        seed_categories.extend([category] * len(seeds))
    return {
        "vectors": _normalize_rows(model.encode(seed_texts)),
        "categories": seed_categories,
    }


def classify_symptom_phrases(phrases, model, seed_embeddings=None, threshold=CATEGORY_SIMILARITY_THRESHOLD):
    """Assign broad themes to already separated symptom phrases in one batch.

    This is shared by the live screen and the validation exporter so the
    reviewer evaluates exactly the category logic used in the product.
    """
    clauses = [str(clause).strip() for clause in phrases if str(clause).strip()]
    if not clauses:
        return []
    seed_embeddings = seed_embeddings or build_category_seed_embeddings(model)
    clause_vectors = _normalize_rows(model.encode(clauses))
    seed_vectors = seed_embeddings["vectors"]
    seed_categories = seed_embeddings["categories"]
    results = []
    for clause, vector in zip(clauses, clause_vectors):
        scores = seed_vectors @ vector
        best_by_category = {}
        for category, score in zip(seed_categories, scores):
            best_by_category[category] = max(best_by_category.get(category, -1), float(score))
        normalized_clause = clause.casefold()
        negated_categories = _negated_categories(clause)
        anchored_categories = {
            category for category, seeds in KATEGORILER.items()
            if any(seed.casefold() in normalized_clause for seed in seeds)
        } - negated_categories
        non_negated_scores = {
            category: score for category, score in best_by_category.items()
            if category not in negated_categories
        }
        best_score = max(non_negated_scores.values(), default=-1)
        eligible_categories = (
            anchored_categories if anchored_categories else (
                set() if negated_categories else {
                    category for category, score in non_negated_scores.items()
                    if score >= threshold and score >= best_score - CATEGORY_SCORE_MARGIN
                }
            )
        )
        matches = [
            {
                "kategori": category,
                "benzerlik": round(best_by_category[category], 3),
                "eslesme_turu": "ifade" if category in anchored_categories else "anlamsal",
            }
            for category in eligible_categories
        ]
        matches.sort(key=lambda row: (-row["benzerlik"], row["kategori"]))
        matches = matches[:MAX_CATEGORIES_PER_CLAUSE]
        ranked_scores = sorted(non_negated_scores.values(), reverse=True)
        score_margin = (
            round(ranked_scores[0] - ranked_scores[1], 3)
            if len(ranked_scores) > 1 else None
        )
        if negated_categories:
            quality_status = "olumsuzlama_kontrolu"
            quality_message = "Açık olumsuzlama işareti nedeniyle ilgili tema otomatik etiketlenmedi."
        elif not matches:
            quality_status = "belirsiz"
            quality_message = "Yeterli açıklıkta otomatik tema eşleşmesi bulunamadı."
        elif all(match["eslesme_turu"] == "ifade" for match in matches):
            quality_status = "acik_ifade"
            quality_message = "Tema, metindeki görünür tohum ifadeyle eşleşti."
        elif len(matches) > 1 or (score_margin is not None and score_margin < CATEGORY_SCORE_MARGIN):
            quality_status = "anlamsal_belirsizlik"
            quality_message = "Birden fazla yakın anlamsal tema bulundu; otomatik sonuç kesin kabul edilmemeli."
        else:
            quality_status = "anlamsal_eslesme"
            quality_message = "Tema anlamsal benzerlikle bulundu; klinik doğruluk puanı değildir."
        results.append({
            "ifade": clause,
            "kategoriler": matches,
            "durum": "eslesti" if matches else "belirsiz",
            "kalite_sinyali": {
                "durum": quality_status,
                "mesaj": quality_message,
                "olumsuzlanan_kategoriler": sorted(negated_categories),
                "en_iyi_ikinci_skor_farki": score_margin,
            },
        })
    return results


def classify_symptom_clauses(text, model, seed_embeddings=None, threshold=CATEGORY_SIMILARITY_THRESHOLD):
    """Split a long user narrative, then assign broad, explainable themes."""
    return classify_symptom_phrases(
        split_user_symptoms(text), model, seed_embeddings=seed_embeddings, threshold=threshold,
    )


def analyze_transparent_symptom_query(
    conn, text, age, gender, model, embeddings, ziyaret_ids, phrases,
    seed_embeddings=None, search_function=find_similar_phrases,
):
    """Return explainable, aggregate-only results for a long symptom narrative."""
    profile = normalize_profile(age, gender)
    classified = classify_symptom_clauses(text, model, seed_embeddings)
    if contains_high_risk_expression([row["ifade"] for row in classified]):
        empty = compute_profiled_recommendation(conn, [], age, gender)
        empty["ilaclar"] = []
        return {
            "sorgu": text,
            "analiz_edilen_ifadeler": classified,
            "kategoriler": [],
            "birlesik": empty,
            "guvenlik_uyarisi": HIGH_RISK_MESSAGE,
        }

    matches_by_category = {}
    phrases_by_category = {}
    all_matches = []
    unclassified_semantic_searches = []
    for clause in classified:
        query_embedding = model.encode(clause["ifade"])
        matches = search_function(
            query_embedding, embeddings, ziyaret_ids, phrases,
            top_n=SEARCH_TOP_N, min_similarity=SEARCH_SIMILARITY_THRESHOLD,
        )
        if clause["kategoriler"]:
            for category_match in clause["kategoriler"]:
                category = category_match["kategori"]
                matches_by_category.setdefault(category, []).extend(matches)
                phrases_by_category.setdefault(category, []).append(clause["ifade"])
        else:
            # A category label is an explanation aid, not a gate.  Preserve the
            # clause's semantic evidence in the combined aggregate while
            # explicitly reporting that its broad label remains uncertain.
            unclassified_semantic_searches.append({
                "ifade": clause["ifade"],
                "semantik_eslesen_ziyaret_sayisi": len({m["ziyaret_id"] for m in matches}),
                "en_yuksek_benzerlik": round(max((float(m["benzerlik"]) for m in matches), default=0), 3),
            })
        all_matches.extend(matches)

    categories = []
    for category in KATEGORILER:
        if category not in matches_by_category:
            continue
        result = compute_profiled_recommendation(conn, matches_by_category[category], age, gender)
        categories.append({
            "kategori": category,
            "kullanici_ifadeleri": list(dict.fromkeys(phrases_by_category[category])),
            **result,
            "ilaclar": result["ilaclar"][:8],
        })

    combined = compute_profiled_recommendation(conn, all_matches, age, gender)
    combined["ilaclar"] = combined["ilaclar"][:8]
    return {
        "sorgu": text,
        "analiz_edilen_ifadeler": classified,
        "kategoriler": categories,
        "birlesik": combined,
        "kategori_disinda_semantik_arama": unclassified_semantic_searches,
        "guvenlik_uyarisi": None,
    }

"""Descriptive before/after analysis around observed medication-list changes.

This module deliberately measures what is documented in later visits, rather
than claiming a medication caused improvement or deterioration.
"""

from collections import Counter, defaultdict
from datetime import date

from .treatment_timeline import build_patient_treatment_timeline


def _date_difference(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _first_follow_up_with_symptom_record(timeline_rows, change_index, max_follow_up_days):
    change_day = timeline_rows[change_index]["tarih"]
    for row in timeline_rows[change_index + 1:]:
        days = _date_difference(change_day, row["tarih"])
        if days > max_follow_up_days:
            break
        if row["semptom_ifade_sayisi"]:
            return row, days
    return None, None


def build_patient_transition_analysis(
    conn, patient_id, model, seed_embeddings=None, max_follow_up_days=90,
    precomputed_theme_details=None,
):
    """Compare recorded broad themes before a regimen change with later follow-up.

    A "disappeared" theme means it was not recorded at the selected follow-up;
    it does *not* establish symptom resolution or medication effectiveness.
    """
    timeline_data = build_patient_treatment_timeline(
        conn, patient_id, model=model, seed_embeddings=seed_embeddings,
        precomputed_theme_details=precomputed_theme_details,
    )
    timeline = timeline_data["zaman_noktalari"]
    index_by_date = {row["tarih"]: index for index, row in enumerate(timeline)}
    comparisons = []
    for change in timeline_data["gozlenen_ilac_degisimleri"]:
        change_index = index_by_date[change["tarih"]]
        before = timeline[index_by_date[change["onceki_tarih"]]]
        follow_up, days_to_follow_up = _first_follow_up_with_symptom_record(
            timeline, change_index, max_follow_up_days)
        before_themes = set(before["semptom_temalari"])
        change_day_themes = set(timeline[change_index]["semptom_temalari"])
        if follow_up is None:
            comparisons.append({
                **change,
                "onceki_kayit_temalari": sorted(before_themes),
                "degisim_gunu_temalari": sorted(change_day_themes),
                "onceki_semptom_ifade_sayisi": before["semptom_ifade_sayisi"],
                "onceki_belirsiz_ifade_sayisi": before["otomatik_belirsiz_ifade_sayisi"],
                "degisim_gunu_semptom_ifade_sayisi": timeline[change_index]["semptom_ifade_sayisi"],
                "degisim_gunu_belirsiz_ifade_sayisi": timeline[change_index]["otomatik_belirsiz_ifade_sayisi"],
                "takip_durumu": "takipte_semptom_kaydi_yok",
                "takip_tarihi": None,
                "takibe_kadar_gun": None,
                "takip_temalari": [],
                "takip_semptom_ifade_sayisi": 0,
                "takip_belirsiz_ifade_sayisi": 0,
                "kayitta_gorunmeyen_temalar": [],
                "takipte_yeni_gorunen_temalar": [],
                "devam_eden_temalar": [],
            })
            continue
        follow_up_themes = set(follow_up["semptom_temalari"])
        comparisons.append({
            **change,
            "onceki_kayit_temalari": sorted(before_themes),
            "degisim_gunu_temalari": sorted(change_day_themes),
            "onceki_semptom_ifade_sayisi": before["semptom_ifade_sayisi"],
            "onceki_belirsiz_ifade_sayisi": before["otomatik_belirsiz_ifade_sayisi"],
            "degisim_gunu_semptom_ifade_sayisi": timeline[change_index]["semptom_ifade_sayisi"],
            "degisim_gunu_belirsiz_ifade_sayisi": timeline[change_index]["otomatik_belirsiz_ifade_sayisi"],
            "takip_durumu": "takipte_semptom_kaydi_var",
            "takip_tarihi": follow_up["tarih"],
            "takibe_kadar_gun": days_to_follow_up,
            "takip_temalari": sorted(follow_up_themes),
            "takip_semptom_ifade_sayisi": follow_up["semptom_ifade_sayisi"],
            "takip_belirsiz_ifade_sayisi": follow_up["otomatik_belirsiz_ifade_sayisi"],
            "kayitta_gorunmeyen_temalar": sorted(before_themes - follow_up_themes),
            "takipte_yeni_gorunen_temalar": sorted(follow_up_themes - before_themes),
            "devam_eden_temalar": sorted(before_themes & follow_up_themes),
        })
    return {
        "hasta_id": patient_id,
        "takip_penceresi_gun": max_follow_up_days,
        "gecisler": comparisons,
        "sinirlilik_notu": (
            "Önceki ve sonraki temalar, ilgili ziyaret notlarında otomatik olarak bulunan "
            "geniş semptom temalarıdır. Bir temanın takipte görünmemesi iyileşme; yeni görünmesi "
            "ilaç yan etkisi veya kötüleşme kanıtı değildir."
        ),
    }


def transition_group_label(transition):
    """Stable, aggregate-safe label for one observed regimen transition."""
    removed = transition["sonraki_kayitta_listelenmeyen_ilaclar"]
    added = transition["eklenen_ilaclar"]
    if removed and added:
        return f"{' + '.join(removed)} → {' + '.join(added)}"
    if added:
        return f"Tedaviye ekleme → {' + '.join(added)}"
    if removed:
        return f"Kayıtta listelenmeme → {' + '.join(removed)}"
    return "Doz / sıklık değişimi"


def summarize_transition_analyses(patient_analyses):
    """Aggregate documented-theme changes by medication transition label."""
    groups = defaultdict(lambda: {
        "gecis_sayisi": 0,
        "takipli_gecis_sayisi": 0,
        "kayitta_gorunmeyen_tema_sayilari": Counter(),
        "takipte_yeni_gorunen_tema_sayilari": Counter(),
        "devam_eden_tema_sayilari": Counter(),
        "takibe_kadar_gunler": [],
    })
    for analysis in patient_analyses:
        for transition in analysis["gecisler"]:
            label = transition_group_label(transition)
            group = groups[label]
            group["gecis_sayisi"] += 1
            if transition["takip_durumu"] != "takipte_semptom_kaydi_var":
                continue
            group["takipli_gecis_sayisi"] += 1
            group["kayitta_gorunmeyen_tema_sayilari"].update(transition["kayitta_gorunmeyen_temalar"])
            group["takipte_yeni_gorunen_tema_sayilari"].update(transition["takipte_yeni_gorunen_temalar"])
            group["devam_eden_tema_sayilari"].update(transition["devam_eden_temalar"])
            group["takibe_kadar_gunler"].append(transition["takibe_kadar_gun"])
    summaries = []
    for label, group in groups.items():
        follow_up_count = group["takipli_gecis_sayisi"]
        summaries.append({
            "gecis": label,
            "gozlenen_gecis_sayisi": group["gecis_sayisi"],
            "semptom_kaydi_olan_takip_sayisi": follow_up_count,
            "ortalama_takip_gunu": round(
                sum(group["takibe_kadar_gunler"]) / follow_up_count, 1
            ) if follow_up_count else None,
            "takipte_kayitta_gorunmeyen_temalar": group["kayitta_gorunmeyen_tema_sayilari"].most_common(5),
            "takipte_yeni_gorunen_temalar": group["takipte_yeni_gorunen_tema_sayilari"].most_common(5),
            "devam_eden_temalar": group["devam_eden_tema_sayilari"].most_common(5),
        })
    return sorted(summaries, key=lambda row: (-row["semptom_kaydi_olan_takip_sayisi"], row["gecis"]))

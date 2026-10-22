"""Patient-level, observational medication-change timelines.

The output deliberately distinguishes an observed medication-list change from
an actual stop or a treatment effect.  A prescription may be absent from a
note for documentation reasons, and this database has no validated outcome
scale yet.
"""

from collections import defaultdict
from datetime import date

from .drug_matching import build_surface_form_index_from_db
from .symptom_extraction import classify_record_phrase
from .transparent_symptom_query import build_category_seed_embeddings, classify_symptom_phrases


def _valid_iso_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        return None


def _medication_days(conn, patient_id, confidence_threshold=90):
    rows = conn.execute(
        """SELECT z.id, z.tarih, ik.ilac_adi_normalize, ik.doz, ik.siklik
           FROM ziyaret z
           LEFT JOIN ilac_kullanimi ik
             ON ik.ziyaret_id = z.id AND ik.eslesme_guveni >= %s
           WHERE z.hasta_id = %s
           ORDER BY z.tarih, z.id""",
        (confidence_threshold, patient_id),
    ).fetchall()
    days = {}
    for visit_id, visit_date, medicine, dose, frequency in rows:
        day = _valid_iso_date(visit_date)
        if day is None:
            continue
        item = days.setdefault(day, {
            "tarih": day,
            "ziyaret_idleri": set(),
            "ilaclar": defaultdict(lambda: {"dozlar": set(), "sikliklar": set()}),
        })
        item["ziyaret_idleri"].add(visit_id)
        if medicine:
            item["ilaclar"][medicine]["dozlar"].add(dose or "")
            item["ilaclar"][medicine]["sikliklar"].add(frequency or "")
    return days


def _symptom_counts_by_day(conn, patient_id):
    rows = conn.execute(
        """SELECT z.tarih, sk.ifade_ham
           FROM ziyaret z JOIN semptom_kaydi sk ON sk.ziyaret_id = z.id
           WHERE z.hasta_id = %s AND trim(sk.ifade_ham) != ''
           ORDER BY sk.id""",
        (patient_id,),
    ).fetchall()
    surface_form_index = build_surface_form_index_from_db(conn)
    counts = defaultdict(int)
    for raw_date, phrase in rows:
        day = _valid_iso_date(raw_date)
        if day is not None and classify_record_phrase(phrase, surface_form_index) == "semptom":
            counts[day] += 1
    return dict(counts)


def _theme_details_by_day(conn, patient_id, model, seed_embeddings=None):
    """Return non-diagnostic broad-theme presence for each dated record day."""
    rows = conn.execute(
        """SELECT z.tarih, sk.ifade_ham
           FROM ziyaret z JOIN semptom_kaydi sk ON sk.ziyaret_id = z.id
           WHERE z.hasta_id = %s AND trim(sk.ifade_ham) != ''
           ORDER BY z.tarih, sk.id""",
        (patient_id,),
    ).fetchall()
    surface_form_index = build_surface_form_index_from_db(conn)
    dated_phrases = [
        (day, phrase) for raw_date, phrase in rows
        if (day := _valid_iso_date(raw_date)) is not None
        and classify_record_phrase(phrase, surface_form_index) == "semptom"
    ]
    if not dated_phrases:
        return {}
    classifications = classify_symptom_phrases(
        [phrase for _, phrase in dated_phrases], model,
        seed_embeddings or build_category_seed_embeddings(model),
    )
    details = defaultdict(lambda: {"temalar": set(), "belirsiz_ifade_sayisi": 0})
    for (day, _), classified in zip(dated_phrases, classifications):
        labels = [row["kategori"] for row in classified["kategoriler"]]
        details[day]["temalar"].update(labels)
        if classified["kalite_sinyali"]["durum"] in {
            "belirsiz", "anlamsal_belirsizlik", "olumsuzlama_kontrolu",
        }:
            details[day]["belirsiz_ifade_sayisi"] += 1
    return details


def build_theme_details_for_patients(conn, patient_ids, model, seed_embeddings=None):
    """Batch-build theme presence by pseudonymous patient/day for trend analysis."""
    if not patient_ids:
        return {}
    placeholders = ",".join(["%s"] * len(patient_ids))
    rows = conn.execute(
        f"""SELECT z.hasta_id, z.tarih, sk.ifade_ham
            FROM ziyaret z JOIN semptom_kaydi sk ON sk.ziyaret_id = z.id
            WHERE z.hasta_id IN ({placeholders}) AND trim(sk.ifade_ham) != ''
            ORDER BY z.hasta_id, z.tarih, sk.id""",
        list(patient_ids),
    ).fetchall()
    surface_form_index = build_surface_form_index_from_db(conn)
    dated_phrases = [
        (patient_id, day, phrase) for patient_id, raw_date, phrase in rows
        if (day := _valid_iso_date(raw_date)) is not None
        and classify_record_phrase(phrase, surface_form_index) == "semptom"
    ]
    if not dated_phrases:
        return {}
    classifications = classify_symptom_phrases(
        [phrase for _, _, phrase in dated_phrases], model,
        seed_embeddings or build_category_seed_embeddings(model),
    )
    details = defaultdict(lambda: defaultdict(
        lambda: {"temalar": set(), "belirsiz_ifade_sayisi": 0}
    ))
    for (patient_id, day, _), classified in zip(dated_phrases, classifications):
        labels = [row["kategori"] for row in classified["kategoriler"]]
        details[patient_id][day]["temalar"].update(labels)
        if classified["kalite_sinyali"]["durum"] in {
            "belirsiz", "anlamsal_belirsizlik", "olumsuzlama_kontrolu",
        }:
            details[patient_id][day]["belirsiz_ifade_sayisi"] += 1
    return details


def _render_day(day, symptom_counts, theme_details):
    medicines = []
    for name, details in sorted(day["ilaclar"].items()):
        medicines.append({
            "ilac": name,
            "dozlar": sorted(dose for dose in details["dozlar"] if dose),
            "sikliklar": sorted(freq for freq in details["sikliklar"] if freq),
        })
    return {
        "tarih": day["tarih"],
        "birlesmis_ziyaret_sayisi": len(day["ziyaret_idleri"]),
        "ilaclar": medicines,
        "semptom_ifade_sayisi": symptom_counts.get(day["tarih"], 0),
        "semptom_temalari": sorted(theme_details.get(day["tarih"], {}).get("temalar", set())),
        "otomatik_belirsiz_ifade_sayisi": theme_details.get(day["tarih"], {}).get("belirsiz_ifade_sayisi", 0),
        "ilac_kaydi_var": bool(medicines),
    }


def _observed_change(previous, current):
    previous_by_name = {item["ilac"]: item for item in previous["ilaclar"]}
    current_by_name = {item["ilac"]: item for item in current["ilaclar"]}
    added = sorted(set(current_by_name) - set(previous_by_name))
    no_longer_listed = sorted(set(previous_by_name) - set(current_by_name))
    dose_or_frequency_changed = []
    for medicine in sorted(set(previous_by_name) & set(current_by_name)):
        if (
            previous_by_name[medicine]["dozlar"] != current_by_name[medicine]["dozlar"]
            or previous_by_name[medicine]["sikliklar"] != current_by_name[medicine]["sikliklar"]
        ):
            dose_or_frequency_changed.append(medicine)
    if not (added or no_longer_listed or dose_or_frequency_changed):
        return None
    if added and no_longer_listed:
        # This is intentionally about documentation.  It does not establish
        # that one treatment was clinically stopped and another started.
        change_type = "ilac_kaydi_degisimi"
    elif added:
        change_type = "ilac_ekleme"
    elif no_longer_listed:
        change_type = "kayitta_listelenmeme"
    else:
        change_type = "doz_veya_siklik_degisimi"
    return {
        "onceki_tarih": previous["tarih"],
        "tarih": current["tarih"],
        "degisim_tipi": change_type,
        "onceki_rejim": sorted(previous_by_name),
        "yeni_rejim": sorted(current_by_name),
        "eklenen_ilaclar": added,
        # This is intentionally not called "stopped": absence in a note is not
        # proof that the patient stopped taking a medication.
        "sonraki_kayitta_listelenmeyen_ilaclar": no_longer_listed,
        "doz_veya_siklik_degisikligi_olan_ilaclar": dose_or_frequency_changed,
        "yorum": "Gözlenen kayıt değişimidir; kesilme veya klinik etki kanıtı değildir.",
    }


def build_patient_treatment_timeline(
    conn, patient_id, confidence_threshold=90, model=None, seed_embeddings=None,
    precomputed_theme_details=None,
):
    """Build same-day-merged medication observations and change candidates."""
    medication_days = _medication_days(conn, patient_id, confidence_threshold)
    symptom_counts = _symptom_counts_by_day(conn, patient_id)
    theme_details = precomputed_theme_details
    if theme_details is None:
        theme_details = (
            _theme_details_by_day(conn, patient_id, model, seed_embeddings) if model is not None else {}
        )
    timeline = [
        _render_day(medication_days[day], symptom_counts, theme_details)
        for day in sorted(medication_days)
    ]
    changes = []
    previous_with_medication = None
    for index, current in enumerate(timeline):
        if not current["ilac_kaydi_var"]:
            continue
        if previous_with_medication is not None:
            change = _observed_change(previous_with_medication, current)
            if change:
                change["onceki_kayit_temalari"] = previous_with_medication["semptom_temalari"]
                change["degisim_kaydi_temalari"] = current["semptom_temalari"]
                next_day = timeline[index + 1] if index + 1 < len(timeline) else None
                change["sonraki_takip_tarihi"] = next_day["tarih"] if next_day else None
                change["sonraki_takip_temalari"] = next_day["semptom_temalari"] if next_day else []
                changes.append(change)
        previous_with_medication = current
    return {
        "hasta_id": patient_id,
        "zaman_noktalari": timeline,
        "gozlenen_ilac_degisimleri": changes,
        "sinirlilik_notu": (
            "Semptom ifade sayısı, doğrulanmış klinik iyileşme ölçeği değildir. "
            "Geniş tema varlığı da yalnızca otomatik metin sinyalidir; ilaç etkisi için uzman "
            "tanımlı sonuç etiketi ve önceden belirlenmiş takip penceresi gerekir."
        ),
    }


def list_treatment_change_candidates(conn, confidence_threshold=90):
    """Return pseudonymous patient IDs with at least one observed list change."""
    patient_ids = [row[0] for row in conn.execute("SELECT id FROM hasta ORDER BY id")]
    candidates = []
    for patient_id in patient_ids:
        timeline = build_patient_treatment_timeline(conn, patient_id, confidence_threshold)
        changes = timeline["gozlenen_ilac_degisimleri"]
        medication_days = [row for row in timeline["zaman_noktalari"] if row["ilac_kaydi_var"]]
        if changes:
            candidates.append({
                "hasta_id": patient_id,
                "tarihli_ilac_kaydi_gun_sayisi": len(medication_days),
                "gozlenen_degisim_sayisi": len(changes),
                "ilk_tarih": medication_days[0]["tarih"],
                "son_tarih": medication_days[-1]["tarih"],
            })
    return candidates


def build_patient_drug_trend(conn, patient_id, years=range(2021, 2026), confidence_threshold=90):
    """Per-person medication records inside the trend window, for charting."""
    year_labels = [str(year) for year in years]
    timeline = build_patient_treatment_timeline(conn, patient_id, confidence_threshold)
    medication_days = [row for row in timeline["zaman_noktalari"] if row["ilac_kaydi_var"]]
    in_window = [row for row in medication_days if row["tarih"][:4] in year_labels]

    yearly = defaultdict(lambda: defaultdict(int))
    for row in in_window:
        for item in row["ilaclar"]:
            yearly[item["ilac"]][row["tarih"][:4]] += 1
    medicines = sorted(yearly, key=lambda name: (-sum(yearly[name].values()), name))

    return {
        "hasta_id": patient_id,
        "yillar": year_labels,
        "ilaclar": medicines,
        "zaman_noktalari": [
            {"tarih": row["tarih"], "ilaclar": row["ilaclar"]} for row in in_window
        ],
        "yillik_kayit_gunu": {name: dict(yearly[name]) for name in medicines},
        "degisimler": [
            {key: change[key] for key in (
                "onceki_tarih", "tarih", "degisim_tipi", "eklenen_ilaclar",
                "sonraki_kayitta_listelenmeyen_ilaclar",
                "doz_veya_siklik_degisikligi_olan_ilaclar",
            )}
            for change in timeline["gozlenen_ilac_degisimleri"]
            if change["tarih"][:4] in year_labels
        ],
        "pencere_disi_kayit_gunu": len(medication_days) - len(in_window),
        "sinirlilik_notu": (
            "Değerler, ilacın o yıl kaç farklı günün notunda kayıtlı olduğunu gösterir; "
            "bir notta görünmemesi ilacın kesildiği anlamına gelmez."
        ),
    }

from trsm.db import create_schema, get_connection
from trsm.treatment_timeline import build_patient_treatment_timeline, list_treatment_change_candidates


class ZeroModel:
    def encode(self, values):
        import numpy as np

        single = isinstance(values, str)
        values = [values] if single else values
        result = np.zeros((len(values), 2))
        return result[0] if single else result


def _visit_with_medications(conn, patient_id, day, medicines):
    cur = conn.cursor()
    cur.execute("INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, ?, 1)", (patient_id, day))
    visit_id = cur.lastrowid
    for medicine, dose, frequency in medicines:
        cur.execute(
            """INSERT INTO ilac_kullanimi
               (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
               VALUES (?, ?, ?, ?, ?, 100)""",
            (visit_id, medicine, medicine, dose, frequency),
        )
    cur.execute(
        "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (?, 'uyku sorunu', 'cluster_1')",
        (visit_id,),
    )
    conn.commit()


def test_timeline_merges_same_day_visits_and_describes_observed_changes_cautiously():
    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')").lastrowid
    _visit_with_medications(conn, patient_id, "2024-01-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2024-01-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2024-02-01", [("Akineton", "4 mg", "1x1"), ("Risperdal", "1 mg", "1x1")])

    timeline = build_patient_treatment_timeline(conn, patient_id)

    assert len(timeline["zaman_noktalari"]) == 2
    assert timeline["zaman_noktalari"][0]["birlesmis_ziyaret_sayisi"] == 2
    change = timeline["gozlenen_ilac_degisimleri"][0]
    assert change["eklenen_ilaclar"] == ["Risperdal"]
    assert change["doz_veya_siklik_degisikligi_olan_ilaclar"] == ["Akineton"]
    assert "etki kanıtı değildir" in change["yorum"]


def test_timeline_does_not_treat_missing_medication_visit_as_a_stop():
    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')").lastrowid
    _visit_with_medications(conn, patient_id, "2024-01-01", [("Akineton", "2 mg", "1x1")])
    conn.execute("INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, '2024-01-15', 1)", (patient_id,))
    conn.commit()
    _visit_with_medications(conn, patient_id, "2024-02-01", [("Akineton", "2 mg", "1x1")])

    timeline = build_patient_treatment_timeline(conn, patient_id)

    assert timeline["gozlenen_ilac_degisimleri"] == []


def test_change_candidate_list_contains_only_patients_with_observed_list_change():
    conn = get_connection(":memory:")
    create_schema(conn)
    changed = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('changed.pdf')").lastrowid
    stable = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('stable.pdf')").lastrowid
    _visit_with_medications(conn, changed, "2024-01-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, changed, "2024-02-01", [("Risperdal", "1 mg", "1x1")])
    _visit_with_medications(conn, stable, "2024-01-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, stable, "2024-02-01", [("Akineton", "2 mg", "1x1")])

    candidates = list_treatment_change_candidates(conn)

    assert [row["hasta_id"] for row in candidates] == [changed]


def test_timeline_can_include_automatic_theme_presence_without_claiming_outcome():
    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')").lastrowid
    _visit_with_medications(conn, patient_id, "2024-01-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2024-02-01", [("Risperdal", "1 mg", "1x1")])
    conn.execute("UPDATE semptom_kaydi SET ifade_ham = 'geceleri uyuyamıyor'")
    conn.commit()

    timeline = build_patient_treatment_timeline(conn, patient_id, model=ZeroModel())

    assert timeline["zaman_noktalari"][0]["semptom_temalari"] == ["Uyku bozukluğu"]
    assert timeline["gozlenen_ilac_degisimleri"][0]["onceki_kayit_temalari"] == ["Uyku bozukluğu"]
    assert "ilaç etkisi" in timeline["sinirlilik_notu"]


def test_patient_drug_trend_returns_window_points_yearly_counts_and_change_dates():
    from trsm.treatment_timeline import build_patient_drug_trend

    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')").lastrowid
    _visit_with_medications(conn, patient_id, "2019-05-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2021-03-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2021-03-01", [("Akineton", "2 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2022-06-01", [("Akineton", "2 mg", "1x1"), ("Risperdal", "1 mg", "1x1")])
    _visit_with_medications(conn, patient_id, "2023-01-10", [("Risperdal", "1 mg", "1x1")])

    trend = build_patient_drug_trend(conn, patient_id)

    assert trend["yillar"] == ["2021", "2022", "2023", "2024", "2025"]
    assert [row["tarih"] for row in trend["zaman_noktalari"]] == ["2021-03-01", "2022-06-01", "2023-01-10"]
    assert trend["zaman_noktalari"][1]["ilaclar"] == [
        {"ilac": "Akineton", "dozlar": ["2 mg"], "sikliklar": ["1x1"]},
        {"ilac": "Risperdal", "dozlar": ["1 mg"], "sikliklar": ["1x1"]},
    ]
    assert trend["ilaclar"] == ["Akineton", "Risperdal"]
    assert trend["yillik_kayit_gunu"]["Akineton"] == {"2021": 1, "2022": 1}
    assert trend["yillik_kayit_gunu"]["Risperdal"] == {"2022": 1, "2023": 1}
    assert [(c["tarih"], c["degisim_tipi"]) for c in trend["degisimler"]] == [
        ("2022-06-01", "ilac_ekleme"),
        ("2023-01-10", "kayitta_listelenmeme"),
    ]
    assert trend["pencere_disi_kayit_gunu"] == 1

import numpy as np

from trsm.db import create_schema, get_connection
from trsm.treatment_response_analysis import (
    build_patient_transition_analysis,
    summarize_transition_analyses,
)


class ZeroModel:
    def encode(self, values):
        single = isinstance(values, str)
        values = [values] if single else values
        result = np.zeros((len(values), 2))
        return result[0] if single else result


def _visit(conn, patient_id, visit_date, medicine, phrase):
    visit_id = conn.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, ?, 1)",
        (patient_id, visit_date),
    ).lastrowid
    conn.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, eslesme_guveni)
           VALUES (?, ?, ?, 100)""",
        (visit_id, medicine, medicine),
    )
    conn.execute(
        "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (?, ?, 'cluster_1')",
        (visit_id, phrase),
    )
    conn.commit()


def test_transition_analysis_compares_documented_themes_before_and_after_followup():
    conn = get_connection(":memory:")
    create_schema(conn)
    patient_id = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')").lastrowid
    _visit(conn, patient_id, "2024-01-01", "Risperdal", "geceleri uyuyamıyor")
    _visit(conn, patient_id, "2024-02-01", "Depakin", "gelecek kaygısı")
    _visit(conn, patient_id, "2024-03-01", "Depakin", "gelecek kaygısı")

    analysis = build_patient_transition_analysis(conn, patient_id, ZeroModel())

    transition = analysis["gecisler"][0]
    assert transition["degisim_tipi"] == "ilac_kaydi_degisimi"
    assert transition["onceki_rejim"] == ["Risperdal"]
    assert transition["yeni_rejim"] == ["Depakin"]
    assert transition["takip_durumu"] == "takipte_semptom_kaydi_var"
    assert transition["kayitta_gorunmeyen_temalar"] == ["Uyku bozukluğu"]
    assert transition["takipte_yeni_gorunen_temalar"] == ["Anksiyete / gerginlik"]
    assert transition["onceki_semptom_ifade_sayisi"] == 1
    assert transition["takip_semptom_ifade_sayisi"] == 1
    assert "iyileşme" in analysis["sinirlilik_notu"]


def test_transition_summary_groups_observed_switches_without_causal_claim():
    analyses = [{"gecisler": [{
        "sonraki_kayitta_listelenmeyen_ilaclar": ["Risperdal"],
        "eklenen_ilaclar": ["Depakin"],
        "takip_durumu": "takipte_semptom_kaydi_var",
        "takibe_kadar_gun": 28,
        "kayitta_gorunmeyen_temalar": ["Uyku bozukluğu"],
        "takipte_yeni_gorunen_temalar": ["Anksiyete / gerginlik"],
        "devam_eden_temalar": [],
    }]}]

    summary = summarize_transition_analyses(analyses)

    assert summary[0]["gecis"] == "Risperdal → Depakin"
    assert summary[0]["semptom_kaydi_olan_takip_sayisi"] == 1
    assert summary[0]["takipte_kayitta_gorunmeyen_temalar"] == [("Uyku bozukluğu", 1)]

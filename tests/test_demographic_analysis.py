from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.demographic_analysis import (
    age_group_for_age,
    demographic_coverage_summary,
    demographic_drug_distribution,
    demographic_patient_drug_distribution,
)


def _insert_patient_visit_medication(conn, dosya, birth_date, gender, visit_date, drug):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO hasta
           (dosya_adi, dogum_tarihi, dogum_tarihi_kaynagi, cinsiyet, cinsiyet_kaynagi)
           VALUES (%s, %s, 'manual_review', %s, 'manual_review') RETURNING id""",
        (dosya, birth_date, gender),
    )
    hasta_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (%s, %s, 1) RETURNING id",
        (hasta_id, visit_date),
    )
    ziyaret_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, eslesme_guveni)
           VALUES (%s, %s, %s, 100)""",
        (ziyaret_id, drug, drug),
    )
    conn.commit()


def test_age_group_for_age_handles_boundaries():
    assert age_group_for_age(15) == "15-17"
    assert age_group_for_age(17) == "15-17"
    assert age_group_for_age(18) == "18-29"
    assert age_group_for_age(29) == "18-29"
    assert age_group_for_age(30) == "30-44"
    assert age_group_for_age(60) == "60+"
    assert age_group_for_age(14) is None


def test_demographic_distribution_uses_verified_values_and_visit_age():
    conn = fresh_connection()
    create_schema(conn)
    _insert_patient_visit_medication(conn, "a.pdf", "15.07.1983", "Kadın", "2024-07-14", "IlacA")
    _insert_patient_visit_medication(conn, "b.pdf", "15.07.1983", "Kadın", "2024-07-15", "IlacB")
    _insert_patient_visit_medication(conn, "c.pdf", "01.01.1950", "Erkek", "2024-01-01", "IlacA")

    age_df = demographic_drug_distribution(conn, "yas_grubu", top_n=None)
    gender_df = demographic_drug_distribution(conn, "cinsiyet", top_n=None)

    assert set(age_df["demografik_grup"]) == {"30-44", "60+"}
    assert set(gender_df["demografik_grup"]) == {"Kadın", "Erkek"}
    women = gender_df[gender_df["demografik_grup"] == "Kadın"]
    assert set(women["yuzde"]) == {50.0}
    assert women["ziyaret_sayisi"].iloc[0] == 2


def test_demographic_coverage_reports_eligible_patients():
    conn = fresh_connection()
    create_schema(conn)
    _insert_patient_visit_medication(conn, "a.pdf", "15.07.1983", "Kadın", "2024-07-15", "IlacA")

    summary = demographic_coverage_summary(conn)

    assert summary == {
        "toplam_hasta": 1,
        "dogum_tarihi_dogrulanmis_hasta": 1,
        "yas_analizine_uygun_hasta": 1,
        "cinsiyet_dogrulanmis_hasta": 1,
    }


def test_patient_distribution_counts_repeated_visits_once_per_drug():
    conn = fresh_connection()
    create_schema(conn)
    _insert_patient_visit_medication(conn, "a.pdf", "15.07.1983", "Kadın", "2024-07-15", "IlacA")
    _insert_patient_visit_medication(conn, "b.pdf", "15.07.1983", "Kadın", "2024-07-15", "IlacA")
    patient_id = conn.execute("SELECT id FROM hasta WHERE dosya_adi='a.pdf'").fetchone()[0]
    visit_id = conn.execute("SELECT id FROM ziyaret WHERE hasta_id=%s", (patient_id,)).fetchone()[0]
    conn.execute(
        "INSERT INTO ilac_kullanimi (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, eslesme_guveni) VALUES (%s, 'IlacA', 'IlacA', 100)",
        (visit_id,),
    )
    conn.commit()

    result = demographic_patient_drug_distribution(conn, "cinsiyet", top_n=None)

    row = result.iloc[0]
    assert row["demografik_grup"] == "Kadın"
    assert row["ilaci_olan_hasta_sayisi"] == 2
    assert row["grupta_ilac_kaydi_olan_hasta_sayisi"] == 2
    assert row["hasta_yuzdesi"] == 100.0

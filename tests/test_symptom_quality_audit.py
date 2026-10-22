import numpy as np

from trsm.db import create_schema
from tests.pg import fresh_connection
from trsm.symptom_quality_audit import format_symptom_quality_audit, run_symptom_quality_audit


class ZeroModel:
    def encode(self, values):
        single = isinstance(values, str)
        values = [values] if single else values
        array = np.zeros((len(values), 2))
        return array[0] if single else array


def test_quality_audit_reports_automatic_signals_but_not_clinical_accuracy():
    conn = fresh_connection()
    create_schema(conn)
    patient_id = conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf') RETURNING id").fetchone()[0]
    visit_id = conn.execute("INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (%s, '2024-01-01', 1) RETURNING id", (patient_id,)).fetchone()[0]
    conn.cursor().executemany(
        "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (%s, %s, 'cluster_1')",
        [(visit_id, "geceleri uyuyamıyor"), (visit_id, "uykusuzluk yok")],
    )
    conn.commit()

    result = run_symptom_quality_audit(conn, sample_size=2, model=ZeroModel())
    report = format_symptom_quality_audit(result)

    assert result["incelenen_ifade_sayisi"] == 2
    assert result["kalite_sinyalleri"]["olumsuzlama_kontrolu"] == 1
    assert "klinik doğruluk" in report

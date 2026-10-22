from pathlib import Path

from .cleaning import fill_missing_dates
from .data_loading import load_raw_excel
from .db import create_schema, drop_schema, get_connection, table_exists
from .demographic_extraction import run_demographic_extraction
from .drug_dictionary import load_drug_dictionary, load_drug_dictionary_into_db
from .drug_matching import build_surface_form_index
from .medication_pipeline import run_medication_extraction
from .symptom_pipeline import run_symptom_extraction
from .visit_loading import load_visits

DEFAULT_DRUG_DICTIONARY_PATH = (
    Path(__file__).parent.parent / "data" / "ilac_sozluk_seed.csv"
)


class DatabaseNotEmptyError(RuntimeError):
    pass


def _has_patient_data(conn):
    return table_exists(conn, "hasta") and conn.execute(
        "SELECT EXISTS (SELECT 1 FROM hasta)"
    ).fetchone()[0]


def run_pipeline(
    excel_path,
    database_url=None,
    drug_dictionary_path=DEFAULT_DRUG_DICTIONARY_PATH,
    symptom_model=None,
    overwrite=False,
):
    conn = get_connection(database_url)
    try:
        if _has_patient_data(conn) and not overwrite:
            raise DatabaseNotEmptyError(
                "Veritabanında zaten hasta kaydı var. Tüm tabloları silip yeniden "
                "oluşturmak için overwrite=True (komut satırında --overwrite) kullanın."
            )

        df = load_raw_excel(excel_path)
        df = fill_missing_dates(df)

        drop_schema(conn)
        create_schema(conn)
        load_visits(conn, df)
        run_demographic_extraction(conn)

        drug_dictionary = load_drug_dictionary(drug_dictionary_path)
        load_drug_dictionary_into_db(conn, drug_dictionary)
        surface_form_index = build_surface_form_index(drug_dictionary)
        run_medication_extraction(conn, surface_form_index)

        run_symptom_extraction(conn, model=symptom_model, surface_form_index=surface_form_index)
    finally:
        conn.close()

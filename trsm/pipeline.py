from pathlib import Path

from .cleaning import fill_missing_dates
from .data_loading import load_raw_excel
from .db import create_schema, get_connection
from .drug_dictionary import load_drug_dictionary
from .drug_matching import build_surface_form_index
from .medication_pipeline import run_medication_extraction
from .symptom_pipeline import run_symptom_extraction
from .visit_loading import load_visits

DEFAULT_DRUG_DICTIONARY_PATH = (
    Path(__file__).parent.parent / "data" / "ilac_sozluk_seed.csv"
)


def run_pipeline(
    excel_path,
    db_path,
    drug_dictionary_path=DEFAULT_DRUG_DICTIONARY_PATH,
    symptom_model=None,
):
    df = load_raw_excel(excel_path)
    df = fill_missing_dates(df)

    conn = get_connection(db_path)
    create_schema(conn)
    load_visits(conn, df)

    drug_dictionary = load_drug_dictionary(drug_dictionary_path)
    surface_form_index = build_surface_form_index(drug_dictionary)
    run_medication_extraction(conn, surface_form_index)

    run_symptom_extraction(conn, model=symptom_model)

    conn.close()

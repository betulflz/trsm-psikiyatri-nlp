import streamlit as st
from sentence_transformers import SentenceTransformer

from trsm.db import get_connection
from trsm.recommendation import compute_drug_statistics, generate_summary
from trsm.symptom_similarity import find_similar_phrases, load_symptom_index

DB_PATH = "trsm.db"
INDEX_PATH = "data/symptom_index.npz"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TIBBI_UYARI = (
    "Bu bir istatistiksel özet olup tıbbi tavsiye değildir, "
    "tedavi kararı hekim tarafından verilmelidir."
)


@st.cache_resource
def load_resources():
    model = SentenceTransformer(MODEL_NAME)
    embeddings, ziyaret_ids, phrases = load_symptom_index(INDEX_PATH)
    conn = get_connection(DB_PATH)
    return model, embeddings, ziyaret_ids, phrases, conn


st.title("TRSM İlaç Öneri Asistanı")
st.warning(TIBBI_UYARI)

model, embeddings, ziyaret_ids, phrases, conn = load_resources()

query = st.text_input("Semptomunuzu yazın (örn. 'halsizim')")

if query:
    query_embedding = model.encode([query])[0]
    similar = find_similar_phrases(query_embedding, embeddings, ziyaret_ids, phrases)
    similar_ziyaret_ids = list({s["ziyaret_id"] for s in similar})

    stats = compute_drug_statistics(conn, similar_ziyaret_ids)
    summary = generate_summary(query, stats)

    st.subheader("İlaç İstatistiği")
    if stats:
        st.table(stats)
    else:
        st.info("Bu semptoma yeterince benzer geçmiş veri bulunamadı.")

    st.subheader("Özet")
    st.write(summary)

    st.warning(TIBBI_UYARI)

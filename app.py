from pathlib import Path

import streamlit as st
from sentence_transformers import SentenceTransformer

from trsm.db import get_connection
from trsm.recommendation import (
    TIBBI_UYARI,
    build_evidence_summary,
    generate_explanatory_note,
)
from trsm.symptom_similarity import load_symptom_index
from trsm.transparent_symptom_query import (
    analyze_transparent_symptom_query,
    build_category_seed_embeddings,
)

INDEX_PATH = "data/symptom_index.npz"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@st.cache_resource
def load_resources():
    model = SentenceTransformer(MODEL_NAME)
    embeddings, ziyaret_ids, phrases = load_symptom_index(INDEX_PATH)
    seed_embeddings = build_category_seed_embeddings(model)
    conn = get_connection(autocommit=True)
    return model, embeddings, ziyaret_ids, phrases, seed_embeddings, conn


st.title("TRSM İlaç Öneri Asistanı")
st.warning(TIBBI_UYARI)

try:
    get_connection().close()
except Exception as exc:
    st.error(
        f"PostgreSQL veritabanına bağlanılamadı: {exc}. `docker compose up -d` ile "
        "veritabanını başlatın ve .env dosyasındaki DATABASE_URL değerini kontrol edin."
    )
    st.stop()

if not Path(INDEX_PATH).exists():
    st.error(
        f"Semptom indeks dosyası bulunamadı: '{INDEX_PATH}'. Önce indeks dosyasını "
        f"oluşturun: `python3 scripts/build_symptom_index.py {INDEX_PATH}`."
    )
    st.stop()

model, embeddings, ziyaret_ids, phrases, seed_embeddings, conn = load_resources()

col_age, col_gender = st.columns(2)
with col_age:
    age = st.number_input("Yaş", min_value=15, max_value=120, value=25, step=1)
with col_gender:
    gender = st.selectbox("Cinsiyet", options=["Kadın", "Erkek"], index=None, placeholder="Seçiniz")
query = st.text_area(
    "Yakınmaları ayrıntılı yazın",
    placeholder="Örn. hasta bunalmış, geceleri uyuyamıyor, gelecek kaygıları yaşıyor...",
    max_chars=2000,
)

if query and gender:
    result = analyze_transparent_symptom_query(
        conn, query, age, gender, model, embeddings, ziyaret_ids, phrases,
        seed_embeddings=seed_embeddings,
    )
    evidence = build_evidence_summary(result)

    st.subheader("Kanıt özeti")
    st.success(evidence["metin"])
    st.warning(evidence["uyari"])
    st.subheader("Metnin şeffaf çözümlemesi")
    st.table([
        {
            "ifade": row["ifade"],
            "temalar": ", ".join(item["kategori"] for item in row["kategoriler"]) or "Belirsiz",
        }
        for row in result["analiz_edilen_ifadeler"]
    ])
    st.subheader("Tema bazlı kanıtlar")
    for theme in result["kategoriler"]:
        st.markdown(f"#### {theme['kategori']}")
        st.caption(f"{theme['uyumlu_hasta_sayisi']} kişi / {theme['uyumlu_ziyaret_sayisi']} ziyaret")
        st.table(theme["ilaclar"])

    if st.button("Qwen ile açıklayıcı not üret"):
        try:
            st.info(generate_explanatory_note(evidence))
        except Exception:
            st.info("Açıklayıcı not üretilemedi; kanıt özeti yukarıda görüntüleniyor.")

elif query:
    st.info("İstatistiksel özeti görmek için cinsiyet seçin.")

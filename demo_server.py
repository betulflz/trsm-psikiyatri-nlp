"""TRSM demo sunucusu — gerçek trsm.db ve data/symptom_index.npz üzerinde
çalışan hafif bir API. Statik/dondurulmuş veri yok; her istek gerçek
veritabanı sorgusu veya gerçek embedding araması çalıştırır.

Çalıştırma: /opt/anaconda3/bin/python3 demo_server.py
Sonra: http://localhost:5000
"""
import sys
import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent))

from trsm.db import get_connection
from trsm.recommendation import (
    build_evidence_summary,
    compute_drug_statistics,
    generate_explanatory_note,
)
from trsm.qwen_symptom_labeling import compare_qwen_with_baseline
from trsm.symptom_similarity import find_similar_phrases, load_symptom_index
from trsm.symptom_categories import KATEGORILER
from trsm.transparent_symptom_query import (
    analyze_transparent_symptom_query,
    build_category_seed_embeddings,
    classify_symptom_clauses,
    contains_high_risk_expression,
)
from trsm.treatment_response_analysis import build_patient_transition_analysis
from trsm.treatment_timeline import list_treatment_change_candidates

DB_PATH = "trsm.db"
INDEX_PATH = "data/symptom_index.npz"
TRANSITION_STATS_PATH = Path("data/tedavi_gecis_istatistikleri.json")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
GUVEN_ESIGI = 90
MIN_SIMILARITY = 0.75

app = Flask(__name__, static_folder=None)

print("Model yükleniyor...")
model = SentenceTransformer(MODEL_NAME)
print("Semptom indeksi yükleniyor...")
embeddings, ziyaret_ids, phrases = load_symptom_index(INDEX_PATH)
category_seed_embeddings = build_category_seed_embeddings(model)
print(f"Hazır: {embeddings.shape[0]} semptom kaydı.")

_kategori_cache = None
_treatment_candidate_cache = None


def get_connection_():
    return get_connection(DB_PATH)


def treatment_change_candidates():
    global _treatment_candidate_cache
    if _treatment_candidate_cache is None:
        conn = get_connection_()
        try:
            _treatment_candidate_cache = list_treatment_change_candidates(conn)
        finally:
            conn.close()
    return _treatment_candidate_cache

def kategori_esleyen_ziyaretler(tohumlar):
    eslenen = set()
    for tohum in tohumlar:
        qemb = model.encode(tohum)
        matches = find_similar_phrases(
            qemb, embeddings, ziyaret_ids, phrases,
            top_n=embeddings.shape[0], min_similarity=MIN_SIMILARITY,
        )
        eslenen.update(m["ziyaret_id"] for m in matches)
    return eslenen


def compute_kategoriler():
    global _kategori_cache
    if _kategori_cache is not None:
        return _kategori_cache
    print("Kategoriler hesaplanıyor (bir kez, önbelleğe alınacak)...")
    conn = get_connection_()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM ziyaret")
        all_ids = [r[0] for r in cur.fetchall()]
        baseline = compute_drug_statistics(conn, all_ids, guven_esigi=GUVEN_ESIGI)

        kategoriler = {}
        for kategori, tohumlar in KATEGORILER.items():
            ziyaret_id_seti = kategori_esleyen_ziyaretler(tohumlar)
            stats = compute_drug_statistics(conn, list(ziyaret_id_seti), guven_esigi=GUVEN_ESIGI)
            kategoriler[kategori] = {
                "tohumlar": tohumlar,
                "ziyaret_sayisi": len(ziyaret_id_seti),
                "ilaclar": stats[:8],
            }
        _kategori_cache = {"kategoriler": kategoriler, "baseline": baseline[:10]}
        print("Kategoriler hazır.")
        return _kategori_cache
    finally:
        conn.close()


@app.route("/")
def index():
    return send_from_directory(Path(__file__).parent, "demo.html")


@app.route("/api/genel")
def api_genel():
    conn = get_connection_()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM hasta")
        hasta = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ziyaret")
        ziyaret = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ilac_kullanimi")
        ilac_kayit = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT ilac_adi_normalize) FROM ilac_kullanimi")
        farkli_ilac = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ilac_varyasyon")
        varyasyon = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM semptom_kaydi")
        semptom = cur.fetchone()[0]
        return jsonify({
            "hasta_sayisi": hasta,
            "ziyaret_sayisi": ziyaret,
            "ilac_kayit_sayisi": ilac_kayit,
            "farkli_ilac_sayisi": farkli_ilac,
            "varyasyon_sayisi": varyasyon,
            "semptom_kayit_sayisi": semptom,
        })
    finally:
        conn.close()


@app.route("/api/trend")
def api_trend():
    conn = get_connection_()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT ik.ilac_adi_normalize, COUNT(*) c FROM ilac_kullanimi ik
            JOIN ziyaret z ON z.id=ik.ziyaret_id
            WHERE substr(z.tarih,1,4) BETWEEN '2021' AND '2025' AND ik.eslesme_guveni>=?
            GROUP BY ik.ilac_adi_normalize ORDER BY c DESC LIMIT 6""", (GUVEN_ESIGI,))
        top6 = [r[0] for r in cur.fetchall()]
        if not top6:
            return jsonify({"ilaclar": [], "veri": {}, "yillar": []})

        placeholders = ",".join("?" * len(top6))
        cur.execute(f"""SELECT substr(z.tarih,1,4) yil, ik.ilac_adi_normalize, COUNT(*) c FROM ilac_kullanimi ik
            JOIN ziyaret z ON z.id=ik.ziyaret_id
            WHERE substr(z.tarih,1,4) BETWEEN '2021' AND '2025' AND ik.eslesme_guveni>=?
            AND ik.ilac_adi_normalize IN ({placeholders})
            GROUP BY yil, ik.ilac_adi_normalize""", [GUVEN_ESIGI] + top6)
        veri = {}
        for yil, ilac, c in cur.fetchall():
            veri.setdefault(ilac, {})[yil] = c
        return jsonify({"ilaclar": top6, "veri": veri, "yillar": ["2021", "2022", "2023", "2024", "2025"]})
    finally:
        conn.close()


@app.route("/api/kategoriler")
def api_kategoriler():
    return jsonify(compute_kategoriler())


@app.route("/api/tedavi-gecis-istatistikleri")
def api_tedavi_gecis_istatistikleri():
    if not TRANSITION_STATS_PATH.exists():
        return jsonify({"hata": "Geçiş istatistiği henüz hazırlanmadı."}), 404
    return jsonify(json.loads(TRANSITION_STATS_PATH.read_text(encoding="utf-8")))


@app.route("/api/tedavi-gecis-hastalar")
def api_tedavi_gecis_hastalar():
    rows = treatment_change_candidates()
    return jsonify({
        "hastalar": [
            {
                "kod": f"X-{index:03d}",
                "hasta_id": row["hasta_id"],
                "gozlenen_degisim_sayisi": row["gozlenen_degisim_sayisi"],
            }
            for index, row in enumerate(rows, start=1)
        ],
    })


@app.route("/api/hasta-tedavi-gecis")
def api_hasta_tedavi_gecis():
    try:
        patient_id = int(request.args.get("hasta_id", ""))
    except ValueError:
        return jsonify({"hata": "Geçerli bir kişi kodu seçilmeli."}), 400
    if patient_id not in {row["hasta_id"] for row in treatment_change_candidates()}:
        return jsonify({"hata": "Bu kişi için gözlenen ilaç değişimi bulunamadı."}), 404
    conn = get_connection_()
    try:
        result = build_patient_transition_analysis(
            conn, patient_id, model, seed_embeddings=category_seed_embeddings,
        )
        return jsonify(result)
    finally:
        conn.close()


@app.route("/api/sorgu", methods=["POST"])
def api_sorgu():
    body = request.get_json(force=True) or {}
    query = (body.get("sorgu") or "").strip()
    if not query:
        return jsonify({"hata": "Sorgu boş olamaz."}), 400
    age = body.get("yas")
    gender = body.get("cinsiyet")

    conn = get_connection_()
    try:
        try:
            result = analyze_transparent_symptom_query(
                conn, query, age, gender, model, embeddings, ziyaret_ids, phrases,
                seed_embeddings=category_seed_embeddings,
            )
        except ValueError as exc:
            return jsonify({"hata": str(exc)}), 400
        evidence = build_evidence_summary(result)
        ozet = None
        ozet_kaynagi = None
        if body.get("ozet_iste"):
            ozet, ozet_kaynagi = generate_explanatory_note(evidence, return_source=True)
        return jsonify({
            **result,
            "kanit_ozeti": evidence,
            "ozet": ozet,
            "ozet_kaynagi": ozet_kaynagi,
        })
    finally:
        conn.close()


@app.route("/api/ikinci-gorus", methods=["POST"])
def api_ikinci_gorus():
    """Optional, local-Qwen method-agreement check for the visible clauses."""
    body = request.get_json(force=True) or {}
    query = (body.get("sorgu") or "").strip()
    if not query:
        return jsonify({"hata": "Sorgu boş olamaz."}), 400
    classified = classify_symptom_clauses(query, model, category_seed_embeddings)
    if contains_high_risk_expression([row["ifade"] for row in classified]):
        return jsonify({
            "hata": "Yüksek risk çağrıştıran ifadelerde otomatik ikinci görüş çalıştırılmaz.",
        }), 400
    return jsonify(compare_qwen_with_baseline(classified))


if __name__ == "__main__":
    compute_kategoriler()  # başlangıçta bir kez hesapla, ilk istekte gecikme olmasın
    app.run(host="127.0.0.1", port=8765, debug=False)

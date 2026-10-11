# Öneri/Chat Sistemi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Yeni bir hastanın semptom ifadesine göre, geçmişte benzer semptomlu
hastalara verilen ilaçları istatistiksel olarak gösteren ve yerel bir LLM ile
doğal dile çeviren bir Streamlit sohbet uygulaması oluşturmak.

**Architecture:** İki testable Python modülü (`trsm/symptom_similarity.py`:
embedding indeksi + en-yakın-komşu arama; `trsm/recommendation.py`: ilaç
istatistiği + LLM özeti), bir CLI hazırlık script'i (indeksi bir kere inşa
eder), ve bunları birleştiren tek bir Streamlit uygulaması (`app.py`).

**Tech Stack:** Python 3.10+, `numpy` (kosinüs benzerliği), `sentence-transformers`
(alt proje 1 ile aynı model), `ollama` (Python client, yerel Gemma2-2B),
`streamlit`, `sqlite3`.

**Spec:** [docs/superpowers/specs/2026-08-25-oneri-chat-sistemi-design.md](../specs/2026-08-25-oneri-chat-sistemi-design.md)

## Global Constraints

- LLM'e asla ham hasta verisi gönderilmez — sadece önceden hesaplanmış agregat
  istatistik (ilaç adı + yüzde) prompt olarak verilir.
- İlaç istatistiği hesaplanırken `eslesme_guveni >= 90` filtresi uygulanır
  (varsayılan `GUVEN_ESIGI = 90`, alt proje 2 ile tutarlı).
- Benzerlik skoru `min_similarity` (varsayılan 0.5) altındaki eşleşmeler
  hariç tutulur; yeterli benzer veri yoksa sistem "veri bulunamadı" der,
  uydurma cevap üretmez.
- Arayüzde sabit, kaldırılamaz tıbbi uyarı metni gösterilir: "Bu bir
  istatistiksel özet olup tıbbi tavsiye değildir, tedavi kararı hekim
  tarafından verilmelidir."
- Embedding indeksi ayrı bir dosyada tutulur (`.npz`), `trsm.db`'ye
  yazılmaz ve git'e commit edilmez (büyük ikili, yeniden üretilebilir).
- Ollama zaten kurulu ve çalışıyor (`gemma2:2b` modeli indirilmiş,
  `ollama list` ile doğrulanabilir); bu plan bunu varsayar.
- LLM çağıran testler gerçek Ollama sunucusuna bağlanmaz — enjekte edilebilir
  bir `client` parametresiyle sahte (fake) client kullanılır (alt proje
  1'deki `FakeModel` deseniyle tutarlı).

---

### Task 1: Semptom Benzerlik İndeksi ve Arama

**Files:**
- Create: `trsm/symptom_similarity.py`
- Test: `tests/test_symptom_similarity.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` (dolu `semptom_kaydi` tablosu), `embed_phrases`
  (Task 11'den, `trsm/symptom_clustering.py` — zaten mevcut ve mergelenmiş)
- Produces: `build_symptom_index(conn, index_path, model=None) -> None` (npz
  dosyasına yazar), `load_symptom_index(index_path) -> tuple[np.ndarray,
  list[int], list[str]]` (embeddings, ziyaret_ids, phrases),
  `find_similar_phrases(query_embedding, embeddings, ziyaret_ids, phrases,
  top_n=50, min_similarity=0.5) -> list[dict]` (anahtarlar: `ziyaret_id`,
  `ifade`, `benzerlik`)

- [ ] **Step 1: Testi yaz**

`tests/test_symptom_similarity.py`:

```python
import numpy as np

from trsm.db import get_connection, create_schema
from trsm.symptom_similarity import (
    build_symptom_index,
    find_similar_phrases,
    load_symptom_index,
)


class FakeModel:
    def encode(self, phrases):
        # "Aaaaa" ile başlayanlar bir vektör bölgesinde, "Bbbbb" ile
        # başlayanlar başka bir bölgede kümelenir.
        return [[1.0, 0.0] if p.startswith("Aaaaa") else [0.0, 1.0] for p in phrases]


def _insert_semptom(conn, dosya, ifade):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (dosya,))
    hasta_id = cur.lastrowid
    cur.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, '2024-01-01', 1)",
        (hasta_id,),
    )
    ziyaret_id = cur.lastrowid
    cur.execute(
        "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (?, ?, 'kategorisiz')",
        (ziyaret_id, ifade),
    )
    conn.commit()
    return ziyaret_id


def test_build_and_load_symptom_index_round_trips(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    zid_a = _insert_semptom(conn, "a.pdf", "Aaaaa bir durum")
    zid_b = _insert_semptom(conn, "b.pdf", "Bbbbb iki durum")

    index_path = tmp_path / "index.npz"
    build_symptom_index(conn, str(index_path), model=FakeModel())

    embeddings, ziyaret_ids, phrases = load_symptom_index(str(index_path))
    assert embeddings.shape == (2, 2)
    assert ziyaret_ids == [zid_a, zid_b]
    assert phrases == ["Aaaaa bir durum", "Bbbbb iki durum"]


def test_find_similar_phrases_returns_closest_above_threshold():
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]])
    ziyaret_ids = [10, 20, 30]
    phrases = ["Aaaaa", "Bbbbb", "Aaaaa yakın"]

    query_embedding = np.array([1.0, 0.0])
    results = find_similar_phrases(
        query_embedding, embeddings, ziyaret_ids, phrases, top_n=50, min_similarity=0.5
    )

    result_ziyaret_ids = [r["ziyaret_id"] for r in results]
    assert 10 in result_ziyaret_ids
    assert 30 in result_ziyaret_ids
    assert 20 not in result_ziyaret_ids


def test_find_similar_phrases_respects_top_n():
    embeddings = np.array([[1.0, 0.0], [0.99, 0.01], [0.98, 0.02]])
    ziyaret_ids = [1, 2, 3]
    phrases = ["a", "b", "c"]

    query_embedding = np.array([1.0, 0.0])
    results = find_similar_phrases(
        query_embedding, embeddings, ziyaret_ids, phrases, top_n=2, min_similarity=0.0
    )

    assert len(results) == 2


def test_find_similar_phrases_empty_embeddings_returns_empty_list():
    embeddings = np.zeros((0, 2))
    results = find_similar_phrases(np.array([1.0, 0.0]), embeddings, [], [])
    assert results == []
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_symptom_similarity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trsm.symptom_similarity'`

- [ ] **Step 3: Implementasyon**

`trsm/symptom_similarity.py`:

```python
import numpy as np

from .symptom_clustering import embed_phrases


def build_symptom_index(conn, index_path, model=None):
    cur = conn.cursor()
    cur.execute("SELECT ziyaret_id, ifade_ham FROM semptom_kaydi")
    rows = cur.fetchall()

    ziyaret_ids = [row[0] for row in rows]
    phrases = [row[1] for row in rows]

    embeddings = np.asarray(embed_phrases(phrases, model=model))

    np.savez(
        index_path,
        embeddings=embeddings,
        ziyaret_ids=np.array(ziyaret_ids),
        phrases=np.array(phrases, dtype=object),
    )


def load_symptom_index(index_path):
    # allow_pickle=True is required because `phrases` is saved as a dtype=object
    # array (variable-length strings). Safe here: index_path is always a file
    # this same codebase wrote via build_symptom_index from local trsm.db data —
    # never an externally supplied or untrusted file.
    data = np.load(index_path, allow_pickle=True)
    return data["embeddings"], data["ziyaret_ids"].tolist(), data["phrases"].tolist()


def find_similar_phrases(query_embedding, embeddings, ziyaret_ids, phrases, top_n=50, min_similarity=0.5):
    if embeddings.shape[0] == 0:
        return []

    query_norm = query_embedding / np.linalg.norm(query_embedding)
    embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    similarities = embeddings_norm @ query_norm

    order = np.argsort(-similarities)[:top_n]

    results = []
    for i in order:
        score = float(similarities[i])
        if score < min_similarity:
            continue
        results.append({
            "ziyaret_id": ziyaret_ids[i],
            "ifade": phrases[i],
            "benzerlik": score,
        })
    return results
```

Not: `np.savez` çağrısı `.npz` uzantısını otomatik ekler eğer `index_path`
zaten `.npz` ile bitmiyorsa. Test dosya yolu zaten `.npz` ile bittiği için bu
bir sorun yaratmaz, ama implementasyonda bunu bilerek bırakıyoruz (numpy'ın
standart davranışı).

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_symptom_similarity.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/symptom_similarity.py tests/test_symptom_similarity.py
git commit -m "feat: semptom benzerlik indeksi ve en-yakın-komşu arama"
```

---

### Task 2: İlaç İstatistiği ve LLM Özeti

**Files:**
- Create: `trsm/recommendation.py`
- Test: `tests/test_recommendation.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` (dolu `ilac_kullanimi` tablosu)
- Produces: `compute_drug_statistics(conn, ziyaret_ids, guven_esigi=90) ->
  list[dict]` (anahtarlar: `ilac`, `sayi`, `yuzde`, yüzdeye göre azalan sıralı),
  `generate_summary(query_text, statistics, client=None) -> str`

- [ ] **Step 1: Testi yaz**

`tests/test_recommendation.py`:

```python
from trsm.db import get_connection, create_schema
from trsm.recommendation import compute_drug_statistics, generate_summary


def _insert_medication(conn, ziyaret_id_seed, ilac_adi, eslesme_guveni):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (f"hasta{ziyaret_id_seed}.pdf",))
    hasta_id = cur.lastrowid
    cur.execute(
        "INSERT INTO ziyaret (hasta_id, tarih, sayfa_no) VALUES (?, '2024-01-01', 1)",
        (hasta_id,),
    )
    ziyaret_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ilac_kullanimi
           (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
           VALUES (?, ?, ?, NULL, NULL, ?)""",
        (ziyaret_id, ilac_adi, ilac_adi, eslesme_guveni),
    )
    conn.commit()
    return ziyaret_id


def test_compute_drug_statistics_computes_percentages_and_orders_by_count():
    conn = get_connection(":memory:")
    create_schema(conn)
    z1 = _insert_medication(conn, 1, "Stilizan", 100)
    z2 = _insert_medication(conn, 2, "Stilizan", 95)
    z3 = _insert_medication(conn, 3, "Akineton", 90)

    stats = compute_drug_statistics(conn, [z1, z2, z3])

    assert stats[0]["ilac"] == "Stilizan"
    assert stats[0]["sayi"] == 2
    assert stats[0]["yuzde"] == round(100 * 2 / 3, 1)
    assert stats[1]["ilac"] == "Akineton"
    assert stats[1]["sayi"] == 1


def test_compute_drug_statistics_respects_guven_esigi():
    conn = get_connection(":memory:")
    create_schema(conn)
    z1 = _insert_medication(conn, 1, "Stilizan", 60)

    stats = compute_drug_statistics(conn, [z1], guven_esigi=90)

    assert stats == []


def test_compute_drug_statistics_empty_ziyaret_ids_returns_empty_list():
    conn = get_connection(":memory:")
    create_schema(conn)
    assert compute_drug_statistics(conn, []) == []


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat(self, model, messages):
        self.calls.append((model, messages))
        return {"message": {"content": "Sahte özet metni."}}


def test_generate_summary_calls_client_with_statistics_in_prompt():
    client = FakeClient()
    statistics = [{"ilac": "Stilizan", "sayi": 2, "yuzde": 66.7}]

    result = generate_summary("halsizim", statistics, client=client)

    assert result == "Sahte özet metni."
    assert len(client.calls) == 1
    model, messages = client.calls[0]
    prompt = messages[0]["content"]
    assert "Stilizan" in prompt
    assert "66.7" in prompt
    assert "halsizim" in prompt


def test_generate_summary_returns_fixed_message_without_calling_client_when_no_data():
    client = FakeClient()

    result = generate_summary("nadir bir semptom", [], client=client)

    assert "bulunamadı" in result
    assert len(client.calls) == 0
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_recommendation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trsm.recommendation'`

- [ ] **Step 3: Implementasyon**

`trsm/recommendation.py`:

```python
LLM_MODEL_NAME = "gemma2:2b"

VERI_YOK_MESAJI = "Bu semptoma yeterince benzer geçmiş veri bulunamadı."


def compute_drug_statistics(conn, ziyaret_ids, guven_esigi=90):
    if not ziyaret_ids:
        return []

    placeholders = ",".join("?" * len(ziyaret_ids))
    query = f"""
        SELECT ilac_adi_normalize, COUNT(*) as sayi
        FROM ilac_kullanimi
        WHERE ziyaret_id IN ({placeholders}) AND eslesme_guveni >= ?
        GROUP BY ilac_adi_normalize
        ORDER BY sayi DESC
    """
    cur = conn.cursor()
    cur.execute(query, list(ziyaret_ids) + [guven_esigi])
    rows = cur.fetchall()

    toplam = sum(sayi for _, sayi in rows)
    if toplam == 0:
        return []

    return [
        {"ilac": ilac, "sayi": sayi, "yuzde": round(100 * sayi / toplam, 1)}
        for ilac, sayi in rows
    ]


def generate_summary(query_text, statistics, client=None):
    if not statistics:
        return VERI_YOK_MESAJI

    stat_lines = "\n".join(f"- {s['ilac']}: %{s['yuzde']}" for s in statistics)
    prompt = (
        f"Bir hasta '{query_text}' şikayetiyle başvurdu. Geçmişte benzer semptomlu "
        f"hastalara verilen ilaçların dağılımı:\n{stat_lines}\n\n"
        "Bu istatistiği 2-3 cümlelik doğal bir Türkçe özet haline getir. "
        "Sadece verilen sayıları kullan, yeni bilgi uydurma."
    )

    if client is None:
        import ollama
        client = ollama

    response = client.chat(model=LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_recommendation.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/recommendation.py tests/test_recommendation.py
git commit -m "feat: ilaç istatistiği hesaplama ve LLM özeti"
```

---

### Task 3: İndeks İnşa CLI'ı ve Bağımlılıklar

**Files:**
- Create: `scripts/build_symptom_index.py`
- Modify: `requirements.txt`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `get_connection`, `create_schema` yok gerekmiyor burada — sadece
  `get_connection` (Task 2, `trsm/db.py`, zaten mevcut), `build_symptom_index`
  (Task 1)
- Produces: Çalıştırılabilir bir CLI script; başka bir task tarafından
  tüketilmiyor (Task 4'ün manuel doğrulama adımında elle çalıştırılacak).

Bu task'ın kendi otomatik testi yok — `scripts/run_pipeline.py` ve
`scripts/export_validation_sample.py`'nin daha önce kurulan presedansıyla
tutarlı (bu script'ler de gerçek veritabanı/model gerektirdiği için doğrudan
test edilmedi, sadece doğru yazıldığından ve entegrasyon noktasında elle
çalıştırıldığından emin olunuyor — bu doğrulama Task 4'te yapılacak).

- [ ] **Step 1: Bağımlılıkları `requirements.txt`'e ekle**

Mevcut `requirements.txt`'in sonuna ekle:

```
streamlit>=1.28
ollama>=0.3
```

Run: `pip install -r requirements.txt`
Expected: kurulum hatasız tamamlanır.

- [ ] **Step 2: CLI script'i yaz**

`scripts/build_symptom_index.py`:

```python
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.symptom_similarity import build_symptom_index


def main():
    parser = argparse.ArgumentParser(
        description="Semptom benzerlik indeksini (embedding) trsm.db'den inşa eder"
    )
    parser.add_argument("db_path", help="Dolu trsm.db dosyasının yolu")
    parser.add_argument("index_path", help="Oluşturulacak .npz indeks dosyasının yolu")
    args = parser.parse_args()

    conn = get_connection(args.db_path)
    try:
        build_symptom_index(conn, args.index_path)
    finally:
        conn.close()

    print(f"Semptom indeksi oluşturuldu: {args.index_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: `.gitignore`'a indeks dosyasını ekle**

`.gitignore`'a şu satırı ekle: `*.npz`

- [ ] **Step 4: Script'in syntax olarak doğru olduğunu doğrula**

Run: `python3 -c "import ast; ast.parse(open('scripts/build_symptom_index.py').read())"`
Expected: hatasız tamamlanır (syntax hatası yok).

Run: `python3 -m pytest -v` (tüm mevcut test paketi — regresyon yok mu kontrol et)
Expected: Tüm testler PASS (bu task'ta yeni test eklenmedi, ama mevcutların
bozulmadığından emin ol).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_symptom_index.py requirements.txt .gitignore
git commit -m "feat: semptom indeksi CLI'ı ve bağımlılıklar"
```

---

### Task 4: Streamlit Sohbet Uygulaması

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `get_connection` (Task 2), `load_symptom_index`,
  `find_similar_phrases` (Task 1), `compute_drug_statistics`,
  `generate_summary` (Task 2), `SentenceTransformer` (sentence-transformers,
  doğrudan)

Bu task'ın otomatik testi yok — Streamlit uygulamaları gerçek model +
gerçek Ollama sunucusu + gerçek veritabanı gerektirdiğinden, doğrulama
Step 3'teki manuel çalıştırma ile yapılır (alt proje 2'nin notebook
task'ındaki "gerçek veriye karşı çalıştır ve çıktıyı incele" desenine
tutarlı).

- [ ] **Step 1: `app.py`'ı yaz**

`app.py` (repo kökü):

```python
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
```

- [ ] **Step 2: Semptom indeksini gerçek veriye karşı inşa et**

Run: `python3 scripts/build_symptom_index.py trsm.db data/symptom_index.npz`
Expected: `Semptom indeksi oluşturuldu: data/symptom_index.npz` çıktısı; bu
adım `trsm.db`'nin `semptom_kaydi` tablosunun dolu olmasını gerektirir (alt
proje 1'in pipeline'ının tamamlanmış olması gerekir — eğer tablo boşsa,
BLOCKED bildir ve pipeline'ın tamamlanmasını bekle).

- [ ] **Step 3: Uygulamayı gerçek veriyle manuel çalıştır ve doğrula**

Run: `streamlit run app.py --server.headless true &` (arka planda başlat,
birkaç saniye bekle, sonra `curl -s http://localhost:8501` ile sayfanın
döndüğünü doğrula, sonra süreci durdur — tam bir tarayıcı testi değil ama
uygulamanın çökmeden ayağa kalktığını doğrular).

Ayrıca, `trsm.recommendation` ve `trsm.symptom_similarity` fonksiyonlarını
doğrudan bir Python betiğinde (geçici, silinecek) gerçek `trsm.db` ve gerçek
`SentenceTransformer` + gerçek `ollama` client'ıyla uçtan uca çağırarak,
örnek bir sorgu ("halsizim" gibi) için:
- En az 1 benzer ifade bulunduğunu,
- İlaç istatistiği tablosunun boş olmadığını (gerçek veri varsa),
- `generate_summary`'nin gerçek Ollama'dan bir yanıt döndürdüğünü (boş
  string değil)

doğrula ve bu çıktıyı rapora ekle.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: streamlit sohbet uygulaması"
```

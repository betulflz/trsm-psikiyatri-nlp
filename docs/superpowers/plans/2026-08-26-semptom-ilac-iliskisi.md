# Semptom-İlaç İlişkisi Bulgusu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `notebooks/semptom_ilac_iliskisi.ipynb`, a notebook that cross-tabulates known psychiatric symptom categories against drug usage statistics across the full `trsm.db` dataset, using the already-validated `find_similar_phrases` similarity search per category seed phrase.

**Architecture:** For each of 10 literature-derived symptom categories, run every seed phrase through `find_similar_phrases` separately against `data/symptom_index.npz` (never average seed embeddings — that dilutes matches, confirmed empirically) and union the matched `ziyaret_id`s. Feed each category's visit-id set into the existing `compute_drug_statistics` to get a drug distribution table, then visualize as a category × drug heatmap.

**Tech Stack:** `sqlite3`, `pandas`, `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`), `matplotlib`/`seaborn`, Jupyter notebook.

**Spec:** `docs/superpowers/specs/2026-08-26-semptom-ilac-iliskisi-design.md`

## Global Constraints

- Similarity threshold: `min_similarity=0.75` (per seed-phrase query)
- `find_similar_phrases` top_n per seed query: `500`
- Drug confidence threshold: `guven_esigi=90` (matches existing trend notebook convention)
- Small-sample warning threshold: category matched-visit count `< 20`
- A visit may match multiple categories (no forced single-category assignment)
- No new `trsm/` module — this is analysis code local to the notebook, per spec's "Dosya Yapısı" section
- Model: `paraphrase-multilingual-MiniLM-L12-v2` (must match the model `data/symptom_index.npz` was built with, or similarity scores are meaningless)

---

### Task 1: Notebook setup — data loading and category definitions

**Files:**
- Create: `notebooks/semptom_ilac_iliskisi.ipynb`

**Interfaces:**
- Produces: `conn` (sqlite3 connection to `trsm.db`), `model` (loaded `SentenceTransformer`), `embeddings, ziyaret_ids, phrases` (from `load_symptom_index`), `KATEGORILER` (dict: category name -> list of seed phrase strings)

- [ ] **Step 1: Create the notebook with a title cell and imports cell**

Markdown cell:
```markdown
# Semptom-İlaç İlişkisi Bulgusu

Bilinen psikiyatrik semptom kategorileri ile bu kategorilere karşılık gelen
ziyaretlerde en sık kullanılan ilaçlar arasındaki ilişkiyi, veri setinin
tamamı üzerinden sistematik olarak analiz eder.

**Yöntem:** Her kategori, örnek Türkçe ifadelerle (tohum) temsil edilir. Her
tohum ayrı ayrı `find_similar_phrases` ile tüm semptom kayıtlarına karşı
taranır (ortalama vektör KULLANILMAZ — bkz. tasarım dokümanı, ortalama
almanın gerçek verilerde eşleşmeleri sulandırdığı doğrulandı). Bir kayıt
herhangi bir tohuma eşik üstü benzerse, o kaydın ziyareti kategoriye dahil
edilir.

**Sınırlama:** Bu tanımlayıcı/istatistiksel bir bulgudur — "bu semptom
grubunda bu ilaçlar sık kullanılmış" der, nedensellik ("bu ilaç bu semptomu
tedavi eder") iddia etmez.
```

Code cell:
```python
import sqlite3
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer

sys.path.insert(0, "..")  # trsm/ paketini bulabilmek için (repo kökü)
from trsm.recommendation import compute_drug_statistics
from trsm.symptom_similarity import find_similar_phrases, load_symptom_index

DB_PATH = "../trsm.db"
INDEX_PATH = "../data/symptom_index.npz"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_SIMILARITY = 0.75
TOP_N_PER_SEED = 500
GUVEN_ESIGI = 90
KUCUK_ORNEKLEM_ESIGI = 20

conn = sqlite3.connect(DB_PATH)
model = SentenceTransformer(MODEL_NAME)
embeddings, ziyaret_ids, phrases = load_symptom_index(INDEX_PATH)

print(f"Semptom indeksi: {embeddings.shape[0]} kayıt, {embeddings.shape[1]} boyut")
```

- [ ] **Step 2: Add the category definitions cell**

Code cell:
```python
KATEGORILER = {
    "Uyku bozukluğu": ["uykusuzluk", "uyku düzensizliği", "aşırı uyku hali"],
    "Öfke / ajitasyon": ["öfke nöbeti", "ajitasyon", "saldırganlık", "huzursuzluk"],
    "Anksiyete / gerginlik": ["anksiyete", "gerginlik", "kaygı", "endişe hali"],
    "Depresif belirtiler": ["çökkünlük", "isteksizlik", "mutsuzluk", "enerji azlığı", "ağlama", "üzüntü"],
    "Manik / taşkın belirtiler": ["taşkınlık", "aşırı enerji", "hızlı konuşma", "elevasyon"],
    "Halüsinasyon / hezeyan": ["halüsinasyon", "sesler duyma", "hezeyan", "şüphecilik"],
    "İştah / kilo değişimi": ["iştahsızlık", "aşırı iştah", "kilo alımı", "kilo kaybı"],
    "Sosyal içe kapanma": ["içe kapanma", "sosyal izolasyon", "işlevsellik kaybı"],
    "Madde kullanımı": ["madde kullanımı", "alkol kullanımı", "bağımlılık"],
    "Tedaviye uyumsuzluk": ["ilaç bırakma", "düzensiz ilaç kullanımı", "tedaviyi reddetme"],
}

for kategori, tohumlar in KATEGORILER.items():
    print(f"{kategori}: {len(tohumlar)} tohum ifade")
```

- [ ] **Step 3: Run both cells and verify no errors**

In Jupyter (or via `jupyter nbconvert --to notebook --execute`), run the notebook up to this point. Expected: prints the index shape (should be `96693` rows if run after the latest pipeline run) and 10 lines listing each category's seed count, no exceptions.

- [ ] **Step 4: Commit**

```bash
git add notebooks/semptom_ilac_iliskisi.ipynb
git commit -m "feat: add symptom-drug relationship notebook - setup and categories"
```

---

### Task 2: Per-category visit matching (seed-union, not averaged vector)

**Files:**
- Modify: `notebooks/semptom_ilac_iliskisi.ipynb` (append cells)

**Interfaces:**
- Consumes: `KATEGORILER: dict[str, list[str]]`, `model: SentenceTransformer`, `embeddings: np.ndarray`, `ziyaret_ids: list`, `phrases: list`, `MIN_SIMILARITY: float`, `TOP_N_PER_SEED: int` (all from Task 1)
- Produces: `kategori_ziyaretleri: dict[str, set[int]]` (category name -> set of matched `ziyaret_id`), `kategori_ozet_df: pd.DataFrame` (columns: `kategori`, `eslesen_ziyaret_sayisi`, `kucuk_ornemklem`)

- [ ] **Step 1: Add the matching function and summary table cell**

Code cell:
```python
def kategori_esleyen_ziyaretler(tohumlar, embeddings, ziyaret_ids, phrases, model, min_similarity, top_n):
    """Her tohumu ayrı sorgu olarak çalıştırır, eşleşen ziyaret_id'lerin
    birleşimini döner. Tohum embedding'lerini ortalamak yerine ayrı ayrı
    sorgulamak bilinçli bir tercih: ortalama, konuşma diline yakın
    ifadelerin (örn. "mutsuzum ağlayasım geliyor") gerçek eşleşmesini
    sulandırıyor (bkz. tasarım dokümanı)."""
    eslenen = set()
    for tohum in tohumlar:
        qemb = model.encode(tohum)
        matches = find_similar_phrases(
            qemb, embeddings, ziyaret_ids, phrases,
            top_n=top_n, min_similarity=min_similarity,
        )
        eslenen.update(m["ziyaret_id"] for m in matches)
    return eslenen


kategori_ziyaretleri = {}
for kategori, tohumlar in KATEGORILER.items():
    kategori_ziyaretleri[kategori] = kategori_esleyen_ziyaretler(
        tohumlar, embeddings, ziyaret_ids, phrases, model,
        MIN_SIMILARITY, TOP_N_PER_SEED,
    )

kategori_ozet_df = pd.DataFrame([
    {
        "kategori": kategori,
        "eslesen_ziyaret_sayisi": len(ziyaret_id_seti),
        "kucuk_ornemklem": len(ziyaret_id_seti) < KUCUK_ORNEKLEM_ESIGI,
    }
    for kategori, ziyaret_id_seti in kategori_ziyaretleri.items()
]).sort_values("eslesen_ziyaret_sayisi", ascending=False)

kategori_ozet_df
```

- [ ] **Step 2: Run the cell and inspect output**

Run in Jupyter. Expected: a DataFrame with 10 rows, one per category, `eslesen_ziyaret_sayisi` column with positive integers (sanity check: none should be 0 — if a category shows 0 matches, its seed phrases likely need revision; note this in the notebook rather than silently proceeding if it happens).

- [ ] **Step 3: Commit**

```bash
git add notebooks/semptom_ilac_iliskisi.ipynb
git commit -m "feat: add per-category visit matching via seed-union queries"
```

---

### Task 3: Drug statistics per category

**Files:**
- Modify: `notebooks/semptom_ilac_iliskisi.ipynb` (append cells)

**Interfaces:**
- Consumes: `kategori_ziyaretleri: dict[str, set[int]]` (Task 2), `conn: sqlite3.Connection`, `GUVEN_ESIGI: int` (Task 1), `compute_drug_statistics(conn, ziyaret_ids, guven_esigi=90) -> list[{"ilac": str, "sayi": int, "yuzde": float}]` (existing, `trsm/recommendation.py`)
- Produces: `kategori_ilac_df: pd.DataFrame` (columns: `kategori`, `ilac`, `sayi`, `yuzde`) — long format, one row per (category, drug) pair, top 10 drugs per category

- [ ] **Step 1: Add the drug statistics cell**

Code cell:
```python
kategori_ilac_satirlari = []
for kategori, ziyaret_id_seti in kategori_ziyaretleri.items():
    istatistikler = compute_drug_statistics(conn, list(ziyaret_id_seti), guven_esigi=GUVEN_ESIGI)
    for satir in istatistikler[:10]:
        kategori_ilac_satirlari.append({
            "kategori": kategori,
            "ilac": satir["ilac"],
            "sayi": satir["sayi"],
            "yuzde": satir["yuzde"],
        })

kategori_ilac_df = pd.DataFrame(kategori_ilac_satirlari)
kategori_ilac_df
```

- [ ] **Step 2: Add a per-category readable table cell**

Code cell:
```python
for kategori in KATEGORILER:
    alt_df = kategori_ilac_df[kategori_ilac_df["kategori"] == kategori]
    ziyaret_sayisi = len(kategori_ziyaretleri[kategori])
    uyari = " (KÜÇÜK ÖRNEKLEM)" if ziyaret_sayisi < KUCUK_ORNEKLEM_ESIGI else ""
    print(f"\n{kategori} — {ziyaret_sayisi} ziyaret{uyari}")
    if alt_df.empty:
        print("  (güven eşiğini geçen ilaç kaydı yok)")
    else:
        for _, satir in alt_df.iterrows():
            print(f"  {satir['ilac']}: %{satir['yuzde']} ({satir['sayi']} kayıt)")
```

- [ ] **Step 3: Run both cells and inspect output**

Run in Jupyter. Expected: `kategori_ilac_df` has up to 100 rows (10 categories × up to 10 drugs), no exceptions. The printed per-category breakdown should show plausible drug names (cross-check a couple of categories against clinical intuition is NOT required here — that's out of scope per the spec — but the printout should be non-empty for categories with reasonable visit counts).

- [ ] **Step 4: Commit**

```bash
git add notebooks/semptom_ilac_iliskisi.ipynb
git commit -m "feat: add drug statistics per symptom category"
```

---

### Task 4: Visualization — category × drug heatmap

**Files:**
- Modify: `notebooks/semptom_ilac_iliskisi.ipynb` (append cells)

**Interfaces:**
- Consumes: `kategori_ilac_df: pd.DataFrame` (Task 3)
- Produces: a rendered heatmap figure (notebook output, not saved to disk — consistent with the existing trend notebook, which also renders inline rather than exporting PNGs)

- [ ] **Step 1: Add the heatmap cell**

Code cell:
```python
pivot_df = kategori_ilac_df.pivot_table(
    index="kategori", columns="ilac", values="yuzde", fill_value=0,
)

# En sık geçen ilk 15 ilaca göre sütunları sınırla (okunabilirlik için)
en_sik_ilaclar = (
    kategori_ilac_df.groupby("ilac")["sayi"].sum().sort_values(ascending=False).head(15).index
)
pivot_df = pivot_df[[ilac for ilac in en_sik_ilaclar if ilac in pivot_df.columns]]

plt.figure(figsize=(14, 6))
sns.heatmap(pivot_df, annot=True, fmt=".0f", cmap="YlOrRd", cbar_kws={"label": "% (kategori içi)"})
plt.title("Semptom Kategorisi × İlaç Kullanım Yüzdesi")
plt.xlabel("İlaç")
plt.ylabel("Semptom Kategorisi")
plt.tight_layout()
plt.show()
```

- [ ] **Step 2: Run the cell and verify the heatmap renders**

Run in Jupyter. Expected: a heatmap figure with up to 10 rows (categories) and up to 15 columns (drugs), no exceptions.

- [ ] **Step 3: Commit**

```bash
git add notebooks/semptom_ilac_iliskisi.ipynb
git commit -m "feat: add category-drug heatmap visualization"
```

---

### Task 5: Summary cell and full end-to-end verification

**Files:**
- Modify: `notebooks/semptom_ilac_iliskisi.ipynb` (append cells)

**Interfaces:**
- Consumes: `kategori_ziyaretleri: dict[str, set[int]]` (Task 2), `kategori_ozet_df: pd.DataFrame` (Task 2)

- [ ] **Step 1: Add the summary cell**

Code cell:
```python
toplam_eslesen_ziyaret = len(set().union(*kategori_ziyaretleri.values()))
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM ziyaret")
toplam_ziyaret = cur.fetchone()[0]

en_buyuk = kategori_ozet_df.iloc[0]
en_kucuk = kategori_ozet_df.iloc[-1]

print("=== Genel Özet ===")
print(f"Toplam ziyaret: {toplam_ziyaret}")
print(f"En az bir kategoriye giren ziyaret: {toplam_eslesen_ziyaret} (%{100*toplam_eslesen_ziyaret/toplam_ziyaret:.1f})")
print(f"En büyük örneklem: {en_buyuk['kategori']} ({en_buyuk['eslesen_ziyaret_sayisi']} ziyaret)")
print(f"En küçük örneklem: {en_kucuk['kategori']} ({en_kucuk['eslesen_ziyaret_sayisi']} ziyaret)")
```

Markdown cell:
```markdown
## Metodolojik Sınırlama

Bu analiz **tanımlayıcı/istatistikseldir**: "bu semptom kategorisiyle
ilişkili ziyaretlerde şu ilaçlar sık kullanılmış" der. Bir ilacın bir
semptomu **tedavi ettiği** yönünde nedensel bir iddia içermez — ilaç
kullanımı ile semptom birlikte gözlenmiştir, ama hangisinin önce geldiği,
aralarındaki nedensellik yönü bu analizden çıkarılamaz. Ayrıca semptom
kategorileri literatürden alınan geniş tema başlıklarıdır, klinik tanı
kategorileri değildir ve tam/eksiksiz olduğu iddia edilmez.
```

- [ ] **Step 2: Run the full notebook end-to-end from a clean kernel**

Run: `jupyter nbconvert --to notebook --execute --inplace notebooks/semptom_ilac_iliskisi.ipynb`

Expected: exits with code 0, no exceptions in any cell. Open the notebook and confirm the summary numbers look sane (e.g., `toplam_eslesen_ziyaret` should be well under `toplam_ziyaret` — not every visit will match a symptom category, and it should not be 0 either).

- [ ] **Step 3: Commit**

```bash
git add notebooks/semptom_ilac_iliskisi.ipynb
git commit -m "feat: add summary and methodological limitations to symptom-drug notebook"
```

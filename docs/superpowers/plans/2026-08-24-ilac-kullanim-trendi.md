# İlaç Kullanım Trendi Analizi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `trsm.db` içindeki ilaç kullanım verisinden, en sık kullanılan 10 ilacın
yıllara göre kullanım trendini gösteren bir Jupyter notebook üretmek.

**Architecture:** Tek bir Jupyter notebook (`notebooks/ilac_kullanim_trendi.ipynb`),
altı sıralı hücrede: veri yükleme+güven filtresi → tarih/yıl işleme → gruplama+en
sık 10 ilaç → trend grafiği+pivot tablo → özet istatistik. Yeni `trsm/` kodu yok —
notebook veritabanını salt-okunur kullanıyor. Bu tek dosyalık, sıralı-hücreli bir
teslimat olduğu için, önceki alt projedeki gibi pytest-tabanlı TDD yerine, notebook'u
gerçek `trsm.db` verisine karşı çalıştırıp çıktı değerlerini bilinen veri
gerçekleriyle doğrulamak "test" rolünü görüyor (spec'te bu şekilde onaylandı).

**Tech Stack:** Python 3.10+, `sqlite3`, `pandas`, `matplotlib`, `seaborn`,
`nbformat` (notebook'u programatik olarak inşa etmek için), `jupyter`/`nbconvert`
(notebook'u başsız çalıştırıp doğrulamak için).

**Spec:** [docs/superpowers/specs/2026-08-24-ilac-kullanim-trendi-design.md](../specs/2026-08-24-ilac-kullanim-trendi-design.md)

## Global Constraints

- Güven eşiği parametrize: notebook'un ilk kod hücresinde `GUVEN_ESIGI = 90`
  şeklinde tek bir değişken; `ilac_kullanimi.eslesme_guveni >= GUVEN_ESIGI`
  filtresi uygulanır.
- Zaman granularitesi: yıllık. `ziyaret.tarih` (ISO `YYYY-MM-DD`) alanından
  `tarih[:4]` ile yıl çıkarılır.
- Kapsam sadece yıllık ilaç kullanım trendi — ilaç geçiş örüntüleri, semptom-ilaç
  çapraz analizi, hasta bazlı özet istatistikler bu planın dışında.
- `trsm/` paketine yeni kod eklenmez; notebook veritabanını sadece okur.
- Notebook dosya yolu: `notebooks/ilac_kullanim_trendi.ipynb`.
- Veri kaybı şeffaf raporlanır: düşük güvenli filtrelenen kayıt sayısı ve tarihsiz
  kayıt sayısı notebook çıktısında ayrı ayrı gösterilir.
- Bu plan `trsm.db`'nin alt proje 1 tarafından zaten doldurulmuş olmasını varsayar
  (gerçek 41.676 satırlık veri seti üzerinde, `data/ilac_sozluk_seed.csv`'deki
  42 ilaçlık sözlükle).

---

### Task 1: İlaç Kullanım Trendi Notebook'u

**Files:**
- Create: `notebooks/ilac_kullanim_trendi.ipynb`
- Modify: `requirements.txt` (matplotlib, seaborn, nbformat, jupyter eklenir)

**Interfaces:**
- Consumes: `trsm.db` şeması (Task 2'de tanımlanan `ilac_kullanimi`, `ziyaret`
  tabloları — alt proje 1'in spec'i, bu repo'da zaten mevcut ve dolu)
- Produces: Çalıştırılabilir bir `.ipynb` dosyası; bu plan başka bir task
  tarafından tüketilmiyor (alt proje bu tek notebook ile tamamlanıyor).

- [ ] **Step 1: Bağımlılıkları `requirements.txt`'e ekle**

Mevcut `requirements.txt`'in sonuna ekle:

```
matplotlib>=3.7
seaborn>=0.12
nbformat>=5.9
jupyter>=1.0
```

Run: `pip install -r requirements.txt`
Expected: kurulum hatasız tamamlanır.

- [ ] **Step 2: `notebooks/` dizinini oluştur**

Run: `mkdir -p notebooks`

- [ ] **Step 3: Notebook'u programatik olarak inşa eden script'i çalıştır**

Bu script `nbformat` kullanarak notebook'u hücre hücre inşa eder ve
`notebooks/ilac_kullanim_trendi.ipynb` olarak yazar. Aşağıdaki Python kodunu
`build_notebook.py` adında geçici bir dosyaya yaz (repo köküne), çalıştır, sonra
bu geçici dosyayı sil (notebook'un kendisi kalıcı, script sadece inşa aracı):

```python
import nbformat as nbf

nb = nbf.v4.new_notebook()

cells = []

cells.append(nbf.v4.new_markdown_cell(
    "# İlaç Kullanım Trendi Analizi\n\n"
    "TRSM veri setindeki (`trsm.db`) ilaç kullanım kayıtlarının yıllara göre "
    "dağılımını gösterir. Kaynak: alt proje 1'in ürettiği yapılandırılmış "
    "veritabanı (`ilac_kullanimi`, `ziyaret` tabloları)."
))

cells.append(nbf.v4.new_markdown_cell(
    "## 1. Veri Yükleme ve Güven Filtresi\n\n"
    "Bulanık eşleştirme güven skoru (`eslesme_guveni`) düşük olan kayıtlar "
    "trend grafiklerini çarpıtabileceğinden bir eşik altında filtrelenir. "
    "`GUVEN_ESIGI` değeri değiştirilerek farklı eşiklerin sonucu nasıl "
    "etkilediği gösterilebilir."
))

cells.append(nbf.v4.new_code_cell(
"""import sqlite3
import pandas as pd

DB_PATH = "../trsm.db"
GUVEN_ESIGI = 90

conn = sqlite3.connect(DB_PATH)
toplam_kayit = conn.execute("SELECT COUNT(*) FROM ilac_kullanimi").fetchone()[0]

query = \"\"\"
    SELECT ik.ilac_adi_normalize, ik.eslesme_guveni, z.tarih
    FROM ilac_kullanimi ik
    JOIN ziyaret z ON z.id = ik.ziyaret_id
    WHERE ik.eslesme_guveni >= ?
\"\"\"
df = pd.read_sql(query, conn, params=(GUVEN_ESIGI,))
conn.close()

dusuk_guvenli_sayisi = toplam_kayit - len(df)
print(f"Veritabanındaki toplam ilaç kaydı: {toplam_kayit}")
print(f"Güven eşiği (>= {GUVEN_ESIGI}) altında filtrelenen kayıt: {dusuk_guvenli_sayisi}")
print(f"Analize dahil edilebilecek kayıt (güven filtresi sonrası): {len(df)}")
df.head()"""
))

cells.append(nbf.v4.new_markdown_cell(
    "## 2. Tarih / Yıl İşleme\n\n"
    "`ziyaret.tarih` alanı zaten ISO formatında (`YYYY-MM-DD`) normalize "
    "edilmiş (alt proje 1). Tarihi olmayan kayıtlar yıllık trendden hariç "
    "tutulur ve sayısı raporlanır."
))

cells.append(nbf.v4.new_code_cell(
"""tarihsiz_sayisi = df["tarih"].isna().sum()
print(f"Tarihi olmayan ilaç kaydı sayısı: {tarihsiz_sayisi} ({tarihsiz_sayisi/len(df):.1%})")

df = df.dropna(subset=["tarih"]).copy()
df["yil"] = df["tarih"].str[:4].astype(int)
print(f"Analize dahil edilen kayıt: {len(df)}")
print(f"Kapsanan yıl aralığı: {df['yil'].min()} - {df['yil'].max()}")"""
))

cells.append(nbf.v4.new_markdown_cell(
    "## 3. Yıl × İlaç Gruplaması ve En Sık 10 İlaç\n\n"
    "42 ilacın tamamını tek grafikte göstermek okunabilirliği bozacağından, "
    "tüm zaman aralığında en sık geçen ilk 10 ilaç seçilir."
))

cells.append(nbf.v4.new_code_cell(
"""yillik_sayim = df.groupby(["yil", "ilac_adi_normalize"]).size().reset_index(name="sayi")

en_sik_10 = df["ilac_adi_normalize"].value_counts().head(10).index.tolist()
print("En sık kullanılan 10 ilaç:")
for i, ilac in enumerate(en_sik_10, 1):
    print(f"{i}. {ilac}")"""
))

cells.append(nbf.v4.new_markdown_cell(
    "## 4. Trend Grafiği ve Pivot Tablo"
))

cells.append(nbf.v4.new_code_cell(
"""import matplotlib.pyplot as plt
import seaborn as sns

pivot = (
    yillik_sayim[yillik_sayim["ilac_adi_normalize"].isin(en_sik_10)]
    .pivot(index="yil", columns="ilac_adi_normalize", values="sayi")
    .fillna(0)
)

fig, ax = plt.subplots(figsize=(12, 6))
pivot.plot(ax=ax, marker="o")
ax.set_xlabel("Yıl")
ax.set_ylabel("Kayıt Sayısı")
ax.set_title("En Sık Kullanılan 10 İlacın Yıllara Göre Kullanım Trendi")
ax.legend(title="İlaç", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()
plt.savefig("ilac_kullanim_trendi.png", dpi=150)
plt.show()

pivot"""
))

cells.append(nbf.v4.new_markdown_cell(
    "## 5. Özet"
))

cells.append(nbf.v4.new_code_cell(
"""print("=== Özet ===")
print(f"Veritabanındaki toplam ilaç kaydı: {toplam_kayit}")
print(f"Güven eşiği (>= {GUVEN_ESIGI}) altında filtrelenen kayıt: {dusuk_guvenli_sayisi}")
print(f"Tarihsiz kayıt (analiz dışı bırakıldı): {tarihsiz_sayisi}")
print(f"Analize dahil edilen kayıt: {len(df)}")
print(f"Kapsanan yıl aralığı: {df['yil'].min()} - {df['yil'].max()}")"""
))

nb["cells"] = cells

with open("notebooks/ilac_kullanim_trendi.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("Notebook yazıldı: notebooks/ilac_kullanim_trendi.ipynb")
```

Run: `python3 build_notebook.py && rm build_notebook.py`
Expected: `Notebook yazıldı: notebooks/ilac_kullanim_trendi.ipynb` çıktısı, ve
`build_notebook.py` script'i silinmiş olmalı (sadece `.ipynb` kalır).

- [ ] **Step 4: Notebook'u gerçek veritabanına karşı başsız çalıştır**

Run: `jupyter nbconvert --to notebook --execute --inplace notebooks/ilac_kullanim_trendi.ipynb`

Expected: Hatasız tamamlanır (exit code 0). Eğer `trsm.db` dosyası repo kökünde
yoksa (alt proje 1'in pipeline'ı henüz çalıştırılmamışsa), bu adım
`sqlite3.OperationalError: unable to open database file` ile başarısız olur —
bu durumda BLOCKED bildir, `trsm.db`'nin önce üretilmesi gerektiğini belirt.

- [ ] **Step 5: Çalıştırılan notebook'un çıktılarını gerçek veriyle doğrula**

`notebooks/ilac_kullanim_trendi.ipynb` dosyasını oku (JSON olarak) ve kod
hücrelerinin `outputs` alanlarındaki `stdout` metnini kontrol et. Aşağıdakileri
doğrula:

- Hücre 1 çıktısı: "Veritabanındaki toplam ilaç kaydı: " satırındaki sayı 0'dan
  büyük olmalı (alt proje 1'in gerçek çalıştırması ~28.000 civarı bir sayı
  üretmişti — tam sayı değişebilir, sadece makul aralıkta (>1000, <100000) olduğunu
  doğrula, tam eşleşme bekleme).
- Hücre 3 çıktısı: "En sık kullanılan 10 ilaç:" listesi tam olarak 10 madde
  içermeli, ve `data/ilac_sozluk_seed.csv`'deki resmi ilaç adlarından biri
  olmalı (örn. Xeplion, Depakin, Akineton gibi — seed dosyasını oku ve
  karşılaştır).
- Hücre 4 çıktısı: bir pivot tablo DataFrame'i (satır: yıl, kolon: ilaç adı)
  üretilmiş olmalı, ve `ilac_kullanim_trendi.png` dosyası repo kökünde
  oluşmuş olmalı.
- Hücre 5 çıktısı: "Kapsanan yıl aralığı" satırındaki yıllar 2015-2026 arasında
  makul bir aralıkta olmalı (veri setinin gerçek tarih aralığına göre; kesin
  sınırları bilmiyorsan, sadece 4 haneli, mantıklı yıl değerleri olduğunu
  doğrula — örn. 1900 veya 3000 gibi anormal değerler olmamalı).

Eğer bu kontrollerden biri başarısız olursa (örn. bir hücre hata fırlattı, ya da
çıktı mantıksız), notebook'un ilgili hücresini düzelt ve Step 4'ü tekrarla.

- [ ] **Step 6: `.gitignore`'a oluşturulan PNG dosyasını ekle (opsiyonel çıktı, versiyon kontrolüne girmesin)**

`.gitignore`'a şu satırı ekle: `ilac_kullanim_trendi.png`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt notebooks/ilac_kullanim_trendi.ipynb .gitignore
git commit -m "feat: ilaç kullanım trendi analizi notebook'u"
```

Not: Bu commit'te `trsm.db` dosyası YER ALMAMALI (veritabanı repo'ya commit
edilmez — büyük, ikili, ve yeniden üretilebilir bir dosya). Eğer `.gitignore`'da
`trsm.db` veya `*.db` yoksa, bunu da bu adımda `.gitignore`'a ekle ve commit'e dahil et.

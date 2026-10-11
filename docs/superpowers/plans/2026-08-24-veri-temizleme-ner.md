# Veri Temizleme & Varlık Çıkarımı — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ham OCR Excel çıktısını (41.676 satır, 547 hasta) temizlenmiş, ilaç/semptom
varlıkları çıkarılmış, ilişkisel bir SQLite veritabanına dönüştüren bir pipeline oluşturmak.

**Architecture:** Dört bağımsız aşama (temizleme → ilaç çıkarımı → semptom çıkarımı →
SQLite yükleme), her biri kendi modülünde, kendi testleriyle. `pipeline.py` bu aşamaları
sırayla çağıran tek bir orkestrasyon fonksiyonu sağlar; `scripts/run_pipeline.py` bunu CLI
olarak açığa çıkarır.

**Tech Stack:** Python 3.10+, pandas, openpyxl, rapidfuzz, sentence-transformers (yerel
model), scikit-learn (HDBSCAN), stdlib `sqlite3`, pytest.

**Spec:** [docs/superpowers/specs/2026-08-24-veri-temizleme-ner-design.md](../specs/2026-08-24-veri-temizleme-ner-design.md)

## Global Constraints

- Tüm işleme yerelde çalışır — hiçbir hasta verisi internete/dış API'ye gönderilmez.
- Donanım: Apple M1, 8GB RAM — modeller CPU'da makul sürede çalışacak kadar hafif olmalı.
- Ham metin (`ham_mudahale_metni`, `ham_sonuc_metni`, `ilac_adi_ham`, `ifade_ham`) hiçbir
  aşamada silinmez veya üzerine yazılmaz — her çıkarım orijinal kaynağa referans verir.
- Veritabanı: SQLite, şema `docs/superpowers/specs/2026-08-24-veri-temizleme-ner-design.md`
  içindeki veri modeliyle birebir uyumlu.
- Kaynak veri: `~/Excel_Toplu/TRSM_Tum_Raporlar_Birlesik.xlsx` (kolonlar: `Dosya`, `Sayfa`,
  `Tarih`, `Müdahale`, `Sonuç`).

---

### Task 1: Proje İskeleti

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `trsm/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `trsm` importable paket kökü; `pytest` çalıştırılabilir test altyapısı.

- [ ] **Step 1: `requirements.txt` oluştur**

```
pandas>=2.0
openpyxl>=3.1
rapidfuzz>=3.5
sentence-transformers>=2.2
scikit-learn>=1.3
pytest>=7.4
```

- [ ] **Step 2: `pytest.ini` oluştur**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: Paket iskeletini oluştur**

`trsm/__init__.py` (boş dosya) ve `tests/__init__.py` (boş dosya) oluştur.

- [ ] **Step 4: Bağımlılıkları kur**

Run: `pip install -r requirements.txt`
Expected: kurulum hatasız tamamlanır.

- [ ] **Step 5: Boş test koşumunu doğrula**

Run: `pytest`
Expected: "no tests ran" veya benzeri, hata yok.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini trsm/__init__.py tests/__init__.py
git commit -m "chore: proje iskeletini oluştur"
```

---

### Task 2: SQLite Şeması ve Bağlantı Yardımcıları

**Files:**
- Create: `trsm/schema.sql`
- Create: `trsm/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `get_connection(db_path: str) -> sqlite3.Connection`,
  `create_schema(conn: sqlite3.Connection) -> None`

- [ ] **Step 1: Şema dosyasını yaz**

`trsm/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS hasta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dosya_adi TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ziyaret (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hasta_id INTEGER NOT NULL REFERENCES hasta(id),
    tarih TEXT,
    sayfa_no INTEGER,
    ham_mudahale_metni TEXT,
    ham_sonuc_metni TEXT
);

CREATE TABLE IF NOT EXISTS ilac_sozluk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resmi_ad TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ilac_varyasyon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ilac_sozluk_id INTEGER NOT NULL REFERENCES ilac_sozluk(id),
    varyasyon TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ilac_kullanimi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ziyaret_id INTEGER NOT NULL REFERENCES ziyaret(id),
    ilac_adi_normalize TEXT,
    ilac_adi_ham TEXT NOT NULL,
    doz TEXT,
    siklik TEXT,
    eslesme_guveni REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS semptom_kaydi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ziyaret_id INTEGER NOT NULL REFERENCES ziyaret(id),
    ifade_ham TEXT NOT NULL,
    kategori TEXT
);
```

- [ ] **Step 2: Testi yaz**

`tests/test_db.py`:

```python
import sqlite3
from trsm.db import get_connection, create_schema


def test_create_schema_creates_all_tables():
    conn = get_connection(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    expected = {
        "hasta", "ziyaret", "ilac_sozluk", "ilac_varyasyon",
        "ilac_kullanimi", "semptom_kaydi",
    }
    assert expected.issubset(tables)


def test_get_connection_enables_foreign_keys():
    conn = get_connection(":memory:")
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys")
    assert cur.fetchone()[0] == 1
```

- [ ] **Step 3: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trsm.db'`

- [ ] **Step 4: `trsm/db.py` implementasyonu**

```python
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn):
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()
```

- [ ] **Step 5: Testin geçtiğini doğrula**

Run: `pytest tests/test_db.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add trsm/schema.sql trsm/db.py tests/test_db.py
git commit -m "feat: SQLite şeması ve bağlantı yardımcıları"
```

---

### Task 3: Excel Yükleme Modülü

**Files:**
- Create: `trsm/data_loading.py`
- Test: `tests/test_data_loading.py`

**Interfaces:**
- Produces: `load_raw_excel(path: str) -> pandas.DataFrame` (kolonlar:
  `Dosya`, `Sayfa`, `Tarih`, `Müdahale`, `Sonuç`)

- [ ] **Step 1: Testi yaz**

`tests/test_data_loading.py`:

```python
import pandas as pd
import pytest
from trsm.data_loading import load_raw_excel


def test_load_raw_excel_returns_expected_columns(tmp_path):
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "Dosya": ["a.pdf"],
        "Sayfa": [1],
        "Tarih": ["09.08.2024"],
        "Müdahale": ["not"],
        "Sonuç": ["ilaç"],
    })
    df.to_excel(excel_path, index=False)

    result = load_raw_excel(str(excel_path))

    assert list(result.columns) == ["Dosya", "Sayfa", "Tarih", "Müdahale", "Sonuç"]
    assert len(result) == 1


def test_load_raw_excel_raises_on_missing_columns(tmp_path):
    excel_path = tmp_path / "bad.xlsx"
    pd.DataFrame({"Dosya": ["a.pdf"]}).to_excel(excel_path, index=False)

    with pytest.raises(ValueError, match="eksik"):
        load_raw_excel(str(excel_path))
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_data_loading.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/data_loading.py`:

```python
import pandas as pd

REQUIRED_COLUMNS = ["Dosya", "Sayfa", "Tarih", "Müdahale", "Sonuç"]


def load_raw_excel(path):
    df = pd.read_excel(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Excel dosyasında beklenen kolonlar eksik: {missing}")
    return df
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_data_loading.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/data_loading.py tests/test_data_loading.py
git commit -m "feat: Excel yükleme modülü"
```

---

### Task 4: Tarih Normalizasyonu ve Forward-Fill

**Files:**
- Create: `trsm/cleaning.py`
- Test: `tests/test_cleaning.py`

**Interfaces:**
- Consumes: `pandas.DataFrame` (Task 3'ten, `Dosya`, `Tarih` kolonları)
- Produces: `parse_tarih(value) -> str | None` (ISO format `YYYY-MM-DD`),
  `fill_missing_dates(df: pandas.DataFrame) -> pandas.DataFrame` (yeni kolon:
  `tarih_normalize`)

- [ ] **Step 1: Testi yaz**

`tests/test_cleaning.py`:

```python
import pandas as pd
from trsm.cleaning import parse_tarih, fill_missing_dates


def test_parse_tarih_dot_format():
    assert parse_tarih("09.08.2024") == "2024-08-09"


def test_parse_tarih_slash_format():
    assert parse_tarih("15/06/2021") == "2021-06-15"


def test_parse_tarih_missing_returns_none():
    assert parse_tarih(None) is None
    assert parse_tarih(float("nan")) is None


def test_parse_tarih_unparseable_returns_none():
    assert parse_tarih("bilinmeyen") is None


def test_fill_missing_dates_forward_fills_per_patient():
    df = pd.DataFrame({
        "Dosya": ["a.pdf", "a.pdf", "a.pdf", "b.pdf"],
        "Tarih": ["01.01.2024", None, None, "02.02.2024"],
    })

    result = fill_missing_dates(df)

    assert result["tarih_normalize"].tolist() == [
        "2024-01-01", "2024-01-01", "2024-01-01", "2024-02-02",
    ]
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_cleaning.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/cleaning.py`:

```python
from datetime import datetime

import pandas as pd

DATE_PATTERNS = ["%d.%m.%Y", "%d/%m/%Y"]


def parse_tarih(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def fill_missing_dates(df):
    df = df.copy()
    df["tarih_normalize"] = df["Tarih"].apply(parse_tarih)
    df["tarih_normalize"] = df.groupby("Dosya")["tarih_normalize"].transform(
        lambda s: s.ffill()
    )
    return df
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_cleaning.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/cleaning.py tests/test_cleaning.py
git commit -m "feat: tarih normalizasyonu ve hasta bazlı forward-fill"
```

---

### Task 5: Hasta & Ziyaret Tablolarını Yükleme

**Files:**
- Create: `trsm/visit_loading.py`
- Test: `tests/test_visit_loading.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` (şema kurulu, Task 2), `pandas.DataFrame` (`Dosya`,
  `Sayfa`, `Müdahale`, `Sonuç`, `tarih_normalize` kolonları, Task 4 çıktısı)
- Produces: `load_visits(conn: sqlite3.Connection, df: pandas.DataFrame) -> None`
  (satırları `hasta` ve `ziyaret` tablolarına yazar)

- [ ] **Step 1: Testi yaz**

`tests/test_visit_loading.py`:

```python
import pandas as pd
from trsm.db import get_connection, create_schema
from trsm.visit_loading import load_visits


def test_load_visits_creates_one_hasta_per_unique_dosya():
    conn = get_connection(":memory:")
    create_schema(conn)
    df = pd.DataFrame({
        "Dosya": ["a.pdf", "a.pdf", "b.pdf"],
        "Sayfa": [1, 2, 1],
        "Müdahale": ["not1", None, "not3"],
        "Sonuç": ["sonuc1", "sonuc2", None],
        "tarih_normalize": ["2024-01-01", "2024-01-02", "2024-02-01"],
    })

    load_visits(conn, df)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hasta")
    assert cur.fetchone()[0] == 2
    cur.execute("SELECT COUNT(*) FROM ziyaret")
    assert cur.fetchone()[0] == 3


def test_load_visits_preserves_null_text_as_null():
    conn = get_connection(":memory:")
    create_schema(conn)
    df = pd.DataFrame({
        "Dosya": ["a.pdf"],
        "Sayfa": [1],
        "Müdahale": [None],
        "Sonuç": ["sonuc1"],
        "tarih_normalize": ["2024-01-01"],
    })

    load_visits(conn, df)

    cur = conn.cursor()
    cur.execute("SELECT ham_mudahale_metni, ham_sonuc_metni FROM ziyaret")
    row = cur.fetchone()
    assert row[0] is None
    assert row[1] == "sonuc1"
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_visit_loading.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/visit_loading.py`:

```python
import pandas as pd


def load_visits(conn, df):
    cur = conn.cursor()
    hasta_id_cache = {}

    for record in df.to_dict("records"):
        dosya = record["Dosya"]
        if dosya not in hasta_id_cache:
            cur.execute("INSERT OR IGNORE INTO hasta (dosya_adi) VALUES (?)", (dosya,))
            cur.execute("SELECT id FROM hasta WHERE dosya_adi = ?", (dosya,))
            hasta_id_cache[dosya] = cur.fetchone()[0]
        hasta_id = hasta_id_cache[dosya]

        mudahale = record.get("Müdahale")
        sonuc = record.get("Sonuç")
        cur.execute(
            """INSERT INTO ziyaret
               (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
               VALUES (?, ?, ?, ?, ?)""",
            (
                hasta_id,
                record.get("tarih_normalize"),
                record.get("Sayfa"),
                None if pd.isna(mudahale) else mudahale,
                None if pd.isna(sonuc) else sonuc,
            ),
        )
    conn.commit()
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_visit_loading.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/visit_loading.py tests/test_visit_loading.py
git commit -m "feat: hasta ve ziyaret tablolarını yükleme"
```

---

### Task 6: İlaç Sözlüğü (Seed Veri + Yükleyici)

**Files:**
- Create: `data/ilac_sozluk_seed.csv`
- Create: `trsm/drug_dictionary.py`
- Test: `tests/test_drug_dictionary.py`

**Interfaces:**
- Produces: `load_drug_dictionary(csv_path: str) -> dict[str, list[str]]`
  (resmi_ad -> [resmi_ad, *varyasyonlar])

- [ ] **Step 1: Seed CSV'yi oluştur**

`data/ilac_sozluk_seed.csv` (örnek veride görülen ilaçlarla başlangıç seti — proje
ilerledikçe manuel doğrulama sırasında genişletilecek):

```csv
resmi_ad,varyasyonlar
Stilizan,
Akineton,
Venerys,Venegres
Lithium,Lityum
Cedrina,
Abilify Maintena,Abilify Maintina
Abilider,
Anipe,
```

- [ ] **Step 2: Testi yaz**

`tests/test_drug_dictionary.py`:

```python
from trsm.drug_dictionary import load_drug_dictionary


def test_load_drug_dictionary_includes_official_name_as_variation(tmp_path):
    csv_path = tmp_path / "sozluk.csv"
    csv_path.write_text("resmi_ad,varyasyonlar\nStilizan,\n", encoding="utf-8")

    result = load_drug_dictionary(str(csv_path))

    assert result["Stilizan"] == ["Stilizan"]


def test_load_drug_dictionary_splits_pipe_separated_variations(tmp_path):
    csv_path = tmp_path / "sozluk.csv"
    csv_path.write_text(
        "resmi_ad,varyasyonlar\nVenerys,Venegres|Venerus\n", encoding="utf-8"
    )

    result = load_drug_dictionary(str(csv_path))

    assert result["Venerys"] == ["Venerys", "Venegres", "Venerus"]
```

- [ ] **Step 3: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_drug_dictionary.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implementasyon**

`trsm/drug_dictionary.py`:

```python
import csv


def load_drug_dictionary(csv_path):
    entries = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resmi_ad = row["resmi_ad"].strip()
            variations = [resmi_ad]
            raw_variations = (row.get("varyasyonlar") or "").strip()
            if raw_variations:
                variations.extend(
                    v.strip() for v in raw_variations.split("|") if v.strip()
                )
            entries[resmi_ad] = variations
    return entries
```

- [ ] **Step 5: Testin geçtiğini doğrula**

Run: `pytest tests/test_drug_dictionary.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add data/ilac_sozluk_seed.csv trsm/drug_dictionary.py tests/test_drug_dictionary.py
git commit -m "feat: ilaç sözlüğü seed verisi ve yükleyici"
```

---

### Task 7: Aday Çıkarımı ve Bulanık Eşleştirme

**Files:**
- Create: `trsm/drug_matching.py`
- Test: `tests/test_drug_matching.py`

**Interfaces:**
- Consumes: `dict[str, list[str]]` (Task 6 çıktısı, `load_drug_dictionary` formatı)
- Produces: `extract_candidates(text: str) -> list[tuple[str, int, int]]`
  (aday, başlangıç, bitiş), `build_surface_form_index(drug_dictionary) -> dict[str, str]`
  (yüzey_formu -> resmi_ad), `match_drug(candidate, surface_form_index, threshold=85) ->
  tuple[str, float] | None`

- [ ] **Step 1: Testi yaz**

`tests/test_drug_matching.py`:

```python
from trsm.drug_matching import extract_candidates, build_surface_form_index, match_drug


def test_extract_candidates_finds_single_word():
    candidates = extract_candidates("Stilizan 5mg tb")
    tokens = [c[0] for c in candidates]
    assert "Stilizan" in tokens


def test_extract_candidates_finds_multi_word_drug_name():
    candidates = extract_candidates("Abilify Maintena 400mg Enj")
    tokens = [c[0] for c in candidates]
    assert "Abilify Maintena" in tokens


def test_extract_candidates_returns_correct_span():
    candidates = extract_candidates("xx Stilizan yy")
    match = next(c for c in candidates if c[0] == "Stilizan")
    assert match[1] == 3
    assert match[2] == 11


def test_build_surface_form_index_maps_variations_to_official_name():
    dictionary = {"Venerys": ["Venerys", "Venegres"]}
    index = build_surface_form_index(dictionary)
    assert index["Venegres"] == "Venerys"
    assert index["Venerys"] == "Venerys"


def test_match_drug_exact_match_scores_100():
    index = {"Stilizan": "Stilizan"}
    result = match_drug("Stilizan", index)
    assert result == ("Stilizan", 100.0)


def test_match_drug_typo_still_matches_above_threshold():
    index = {"Venerys": "Venerys", "Venegres": "Venerys"}
    result = match_drug("Venegre", index, threshold=70)
    assert result is not None
    resmi_ad, score = result
    assert resmi_ad == "Venerys"
    assert score >= 70


def test_match_drug_below_threshold_returns_none():
    index = {"Stilizan": "Stilizan"}
    result = match_drug("tamamen alakasız kelime", index, threshold=90)
    assert result is None
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_drug_matching.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/drug_matching.py`:

```python
import re

from rapidfuzz import fuzz, process

TOKEN_PATTERN = re.compile(
    r"[A-Za-zÇĞİÖŞÜçğıöşü]+(?:\s[A-Za-zÇĞİÖŞÜçğıöşü]+){0,2}"
)


def extract_candidates(text):
    if not text:
        return []
    return [
        (m.group(0), m.start(), m.end())
        for m in TOKEN_PATTERN.finditer(text)
        if len(m.group(0)) >= 3
    ]


def build_surface_form_index(drug_dictionary):
    index = {}
    for resmi_ad, variations in drug_dictionary.items():
        for form in variations:
            index[form] = resmi_ad
    return index


def match_drug(candidate, surface_form_index, threshold=85):
    choices = list(surface_form_index.keys())
    if not choices:
        return None
    best = process.extractOne(candidate, choices, scorer=fuzz.WRatio)
    if best is None:
        return None
    matched_form, score, _ = best
    if score < threshold:
        return None
    return surface_form_index[matched_form], score
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_drug_matching.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/drug_matching.py tests/test_drug_matching.py
git commit -m "feat: ilaç adayı çıkarımı ve bulanık eşleştirme"
```

---

### Task 8: Doz / Sıklık Çıkarımı

**Files:**
- Create: `trsm/dose_extraction.py`
- Test: `tests/test_dose_extraction.py`

**Interfaces:**
- Produces: `extract_dose_frequency(window_text: str) -> tuple[str | None, str | None]`
  (doz, siklik)

- [ ] **Step 1: Testi yaz**

`tests/test_dose_extraction.py`:

```python
from trsm.dose_extraction import extract_dose_frequency


def test_extract_dose_frequency_finds_both():
    doz, siklik = extract_dose_frequency("5mg tb -> 3x1 sabah")
    assert doz == "5mg"
    assert siklik == "3x1"


def test_extract_dose_frequency_only_dose_present():
    doz, siklik = extract_dose_frequency("400mg (08.08.24)")
    assert doz == "400mg"
    assert siklik is None


def test_extract_dose_frequency_none_present():
    doz, siklik = extract_dose_frequency("Bireysel görüşme yapıldı")
    assert doz is None
    assert siklik is None
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_dose_extraction.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/dose_extraction.py`:

```python
import re

DOSE_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s?(?:mg|mcg|ml)\b", re.IGNORECASE)
FREQUENCY_PATTERN = re.compile(r"\d+\s?x\s?\d+(?:/\d+)?", re.IGNORECASE)


def extract_dose_frequency(window_text):
    dose_match = DOSE_PATTERN.search(window_text)
    freq_match = FREQUENCY_PATTERN.search(window_text)
    doz = dose_match.group(0) if dose_match else None
    siklik = freq_match.group(0) if freq_match else None
    return doz, siklik
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_dose_extraction.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/dose_extraction.py tests/test_dose_extraction.py
git commit -m "feat: doz ve sıklık regex çıkarımı"
```

---

### Task 9: İlaç Çıkarımı Pipeline'ı (DB'ye Yazma)

**Files:**
- Create: `trsm/medication_pipeline.py`
- Test: `tests/test_medication_pipeline.py`

**Interfaces:**
- Consumes: `extract_candidates`, `match_drug` (Task 7), `extract_dose_frequency`
  (Task 8), `sqlite3.Connection` (şema kurulu ve `ziyaret` satırları dolu)
- Produces: `extract_medications_from_text(text, surface_form_index, threshold=85) ->
  list[dict]` (anahtarlar: `ilac_adi_normalize`, `ilac_adi_ham`, `doz`, `siklik`,
  `eslesme_guveni`), `run_medication_extraction(conn, surface_form_index, threshold=85)
  -> None`

- [ ] **Step 1: Testi yaz**

`tests/test_medication_pipeline.py`:

```python
from trsm.db import get_connection, create_schema
from trsm.medication_pipeline import (
    extract_medications_from_text,
    run_medication_extraction,
)


def test_extract_medications_from_text_finds_drug_dose_and_frequency():
    index = {"Stilizan": "Stilizan"}
    text = "Stilizan 5mg tb -> 3x1"

    results = extract_medications_from_text(text, index)

    assert len(results) == 1
    assert results[0]["ilac_adi_normalize"] == "Stilizan"
    assert results[0]["ilac_adi_ham"] == "Stilizan"
    assert results[0]["doz"] == "5mg"
    assert results[0]["siklik"] == "3x1"


def test_extract_medications_from_text_empty_text_returns_empty_list():
    assert extract_medications_from_text(None, {}) == []
    assert extract_medications_from_text("", {}) == []


def test_run_medication_extraction_writes_rows_to_db():
    conn = get_connection(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES ('a.pdf')")
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, 'Stilizan 5mg tb -> 3x1', NULL)""",
        (hasta_id,),
    )
    conn.commit()

    index = {"Stilizan": "Stilizan"}
    run_medication_extraction(conn, index)

    cur.execute("SELECT ilac_adi_normalize, doz, siklik FROM ilac_kullanimi")
    rows = cur.fetchall()
    assert rows == [("Stilizan", "5mg", "3x1")]
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_medication_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/medication_pipeline.py`:

```python
from .dose_extraction import extract_dose_frequency
from .drug_matching import extract_candidates, match_drug

WINDOW_SIZE = 40


def extract_medications_from_text(text, surface_form_index, threshold=85):
    results = []
    if not text:
        return results

    for candidate, start, end in extract_candidates(text):
        match = match_drug(candidate, surface_form_index, threshold=threshold)
        if match is None:
            continue
        resmi_ad, score = match
        window = text[end : end + WINDOW_SIZE]
        doz, siklik = extract_dose_frequency(window)
        results.append({
            "ilac_adi_normalize": resmi_ad,
            "ilac_adi_ham": candidate,
            "doz": doz,
            "siklik": siklik,
            "eslesme_guveni": score,
        })
    return results


def run_medication_extraction(conn, surface_form_index, threshold=85):
    cur = conn.cursor()
    cur.execute("SELECT id, ham_mudahale_metni, ham_sonuc_metni FROM ziyaret")
    rows = cur.fetchall()

    for ziyaret_id, mudahale, sonuc in rows:
        combined_text = " ".join(t for t in [mudahale, sonuc] if t)
        medications = extract_medications_from_text(
            combined_text, surface_form_index, threshold=threshold
        )
        for med in medications:
            cur.execute(
                """INSERT INTO ilac_kullanimi
                   (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ziyaret_id,
                    med["ilac_adi_normalize"],
                    med["ilac_adi_ham"],
                    med["doz"],
                    med["siklik"],
                    med["eslesme_guveni"],
                ),
            )
    conn.commit()
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_medication_pipeline.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/medication_pipeline.py tests/test_medication_pipeline.py
git commit -m "feat: ilaç çıkarımı pipeline'ı"
```

---

### Task 10: Semptom İfadesi Bölme (Phrase Splitting)

**Files:**
- Create: `trsm/symptom_extraction.py`
- Test: `tests/test_symptom_extraction.py`

**Interfaces:**
- Produces: `split_into_phrases(text: str, min_length: int = 6) -> list[str]`

- [ ] **Step 1: Testi yaz**

`tests/test_symptom_extraction.py`:

```python
from trsm.symptom_extraction import split_into_phrases


def test_split_into_phrases_splits_on_punctuation():
    text = "Uyku iyi. Anksiyete belirgin, huzursuzluk var."
    phrases = split_into_phrases(text)
    assert "Uyku iyi" in phrases
    assert "Anksiyete belirgin" in phrases
    assert "huzursuzluk var" in phrases


def test_split_into_phrases_filters_short_fragments():
    phrases = split_into_phrases("iyi. Anksiyete belirgin.")
    assert "iyi" not in phrases
    assert "Anksiyete belirgin" in phrases


def test_split_into_phrases_empty_text_returns_empty_list():
    assert split_into_phrases(None) == []
    assert split_into_phrases("") == []
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_symptom_extraction.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/symptom_extraction.py`:

```python
import re

SPLIT_PATTERN = re.compile(r"[.,;\n]|->|\s-\s")


def split_into_phrases(text, min_length=6):
    if not text:
        return []
    parts = SPLIT_PATTERN.split(text)
    phrases = [p.strip() for p in parts]
    return [p for p in phrases if len(p) >= min_length]
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_symptom_extraction.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/symptom_extraction.py tests/test_symptom_extraction.py
git commit -m "feat: semptom ifadesi bölme"
```

---

### Task 11: Gömme (Embedding) ve Kümeleme

**Files:**
- Create: `trsm/symptom_clustering.py`
- Test: `tests/test_symptom_clustering.py`

**Interfaces:**
- Produces: `embed_phrases(phrases: list[str], model=None) -> array-like`,
  `cluster_phrases(embeddings, min_cluster_size: int = 5) -> array-like` (küme
  etiketleri; gürültü için `-1`)

**Not:** `embed_phrases` varsayılan olarak `sentence-transformers` ile
`paraphrase-multilingual-MiniLM-L12-v2` modelini yükler (~470MB, Türkçe dahil çok dilli,
CPU'da 8GB RAM'e sığar). Model ağırlıkları ilk çalıştırmada bir kere internetten indirilip
yerel önbelleğe alınır — sonraki tüm çalıştırmalarda tamamen yerel çalışır, hasta verisi
hiçbir zaman dışarı gönderilmez. Testler gerçek modeli indirmemek için sahte bir model
enjekte eder.

- [ ] **Step 1: Testi yaz**

`tests/test_symptom_clustering.py`:

```python
import numpy as np

from trsm.symptom_clustering import cluster_phrases, embed_phrases


class FakeModel:
    def encode(self, phrases):
        return [[float(len(p)), 0.0] for p in phrases]


def test_embed_phrases_uses_provided_model():
    result = embed_phrases(["abc", "abcdef"], model=FakeModel())
    assert list(result[0]) == [3.0, 0.0]
    assert list(result[1]) == [6.0, 0.0]


def test_cluster_phrases_groups_similar_vectors():
    embeddings = np.array([
        [1.0, 0.0],
        [1.0, 0.1],
        [0.0, 1.0],
        [0.0, 1.1],
    ])

    labels = cluster_phrases(embeddings, min_cluster_size=2)

    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_symptom_clustering.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/symptom_clustering.py`:

```python
from sklearn.cluster import HDBSCAN

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def embed_phrases(phrases, model=None):
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    return model.encode(phrases)


def cluster_phrases(embeddings, min_cluster_size=5):
    clusterer = HDBSCAN(min_cluster_size=min_cluster_size)
    return clusterer.fit_predict(embeddings)
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_symptom_clustering.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/symptom_clustering.py tests/test_symptom_clustering.py
git commit -m "feat: semptom gömme ve kümeleme"
```

---

### Task 12: Semptom Çıkarımı Pipeline'ı (DB'ye Yazma)

**Files:**
- Create: `trsm/symptom_pipeline.py`
- Test: `tests/test_symptom_pipeline.py`

**Interfaces:**
- Consumes: `split_into_phrases` (Task 10), `embed_phrases`, `cluster_phrases`
  (Task 11), `sqlite3.Connection` (şema kurulu ve `ziyaret` satırları dolu)
- Produces: `run_symptom_extraction(conn, min_cluster_size=5, model=None) -> None`

- [ ] **Step 1: Testi yaz**

`tests/test_symptom_pipeline.py`:

```python
from trsm.db import get_connection, create_schema
from trsm.symptom_pipeline import run_symptom_extraction


class FakeModel:
    def encode(self, phrases):
        return [[0.0, 0.0] if p.startswith("Aaaaa") else [10.0, 10.0] for p in phrases]


def _insert_ziyaret(conn, dosya, mudahale):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (dosya,))
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, ?, NULL)""",
        (hasta_id, mudahale),
    )
    conn.commit()


def test_run_symptom_extraction_writes_rows_with_consistent_categories():
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_ziyaret(conn, "a.pdf", "Aaaaa bir durum, Bbbbb iki durum.")
    _insert_ziyaret(conn, "b.pdf", "Aaaaa bir durum, Bbbbb iki durum.")

    run_symptom_extraction(conn, min_cluster_size=2, model=FakeModel())

    cur = conn.cursor()
    cur.execute("SELECT ifade_ham, kategori FROM semptom_kaydi")
    rows = cur.fetchall()

    assert len(rows) == 4
    categories_by_phrase = {}
    for ifade, kategori in rows:
        categories_by_phrase.setdefault(ifade, set()).add(kategori)

    for kategoriler in categories_by_phrase.values():
        assert len(kategoriler) == 1

    aaaaa_kategori = next(k for i, k in rows if i.startswith("Aaaaa"))
    bbbbb_kategori = next(k for i, k in rows if i.startswith("Bbbbb"))
    assert aaaaa_kategori != bbbbb_kategori
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_symptom_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/symptom_pipeline.py`:

```python
from .symptom_clustering import cluster_phrases, embed_phrases
from .symptom_extraction import split_into_phrases


def run_symptom_extraction(conn, min_cluster_size=5, model=None):
    cur = conn.cursor()
    cur.execute("SELECT id, ham_mudahale_metni, ham_sonuc_metni FROM ziyaret")
    rows = cur.fetchall()

    ziyaret_ids = []
    phrases = []
    for ziyaret_id, mudahale, sonuc in rows:
        combined = " ".join(t for t in [mudahale, sonuc] if t)
        for phrase in split_into_phrases(combined):
            ziyaret_ids.append(ziyaret_id)
            phrases.append(phrase)

    if not phrases:
        return

    embeddings = embed_phrases(phrases, model=model)
    labels = cluster_phrases(embeddings, min_cluster_size=min_cluster_size)

    for ziyaret_id, phrase, label in zip(ziyaret_ids, phrases, labels):
        kategori = "kategorisiz" if label == -1 else f"cluster_{label}"
        cur.execute(
            "INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham, kategori) VALUES (?, ?, ?)",
            (ziyaret_id, phrase, kategori),
        )
    conn.commit()
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_symptom_pipeline.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add trsm/symptom_pipeline.py tests/test_symptom_pipeline.py
git commit -m "feat: semptom çıkarımı pipeline'ı"
```

---

### Task 13: Uçtan Uca Pipeline Orkestrasyonu ve CLI

**Files:**
- Create: `trsm/pipeline.py`
- Create: `scripts/run_pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: Tüm önceki task'ların tüm public fonksiyonları
- Produces: `run_pipeline(excel_path, db_path, drug_dictionary_path=DEFAULT_..., symptom_model=None) -> None`

- [ ] **Step 1: Testi yaz**

`tests/test_pipeline.py`:

```python
import sqlite3

import pandas as pd

from trsm.pipeline import run_pipeline


class FakeModel:
    def encode(self, phrases):
        return [[float(len(p)), 0.0] for p in phrases]


def test_run_pipeline_end_to_end(tmp_path):
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "Dosya": ["test.pdf", "test.pdf"],
        "Sayfa": [1, 1],
        "Tarih": ["09.08.2024", None],
        "Müdahale": [
            "Stilizan 5mg tb -> 3x1. Uyku iyi.",
            "Devam eden görüşme notu burada.",
        ],
        "Sonuç": ["Devam", None],
    })
    df.to_excel(excel_path, index=False)

    db_path = tmp_path / "trsm.db"
    run_pipeline(str(excel_path), str(db_path), symptom_model=FakeModel())

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM hasta")
    assert cur.fetchone()[0] == 1

    cur.execute("SELECT COUNT(*) FROM ziyaret")
    assert cur.fetchone()[0] == 2

    cur.execute("SELECT ilac_adi_normalize, doz, siklik FROM ilac_kullanimi")
    assert ("Stilizan", "5mg", "3x1") in cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM semptom_kaydi")
    assert cur.fetchone()[0] > 0

    conn.close()
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/pipeline.py`:

```python
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
```

`scripts/run_pipeline.py`:

```python
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="TRSM veri temizleme ve varlık çıkarımı pipeline'ı"
    )
    parser.add_argument("excel_path", help="Ham OCR Excel dosyasının yolu")
    parser.add_argument("db_path", help="Oluşturulacak SQLite veritabanı dosyasının yolu")
    args = parser.parse_args()

    run_pipeline(args.excel_path, args.db_path)
    print(f"Pipeline tamamlandı: {args.db_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Tüm test paketini çalıştır**

Run: `pytest -v`
Expected: Tüm testler PASS (Task 1-13 toplamı).

- [ ] **Step 6: Commit**

```bash
git add trsm/pipeline.py scripts/run_pipeline.py tests/test_pipeline.py
git commit -m "feat: uçtan uca pipeline orkestrasyonu ve CLI"
```

---

### Task 14: Manuel Doğrulama Örneklemi Aracı

**Files:**
- Create: `trsm/validation_export.py`
- Test: `tests/test_validation_export.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` (dolu `hasta`/`ziyaret` tabloları)
- Produces: `export_validation_sample(conn, output_csv, sample_size=30, seed=42) -> None`

- [ ] **Step 1: Testi yaz**

`tests/test_validation_export.py`:

```python
import csv

from trsm.db import get_connection, create_schema
from trsm.validation_export import export_validation_sample


def _insert_hasta_with_ziyaret(conn, dosya):
    cur = conn.cursor()
    cur.execute("INSERT INTO hasta (dosya_adi) VALUES (?)", (dosya,))
    hasta_id = cur.lastrowid
    cur.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, '2024-01-01', 1, 'not', 'sonuc')""",
        (hasta_id,),
    )
    conn.commit()


def test_export_validation_sample_writes_csv_with_header_and_rows(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    _insert_hasta_with_ziyaret(conn, "a.pdf")
    _insert_hasta_with_ziyaret(conn, "b.pdf")

    output_csv = tmp_path / "sample.csv"
    export_validation_sample(conn, str(output_csv), sample_size=10)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == [
        "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
        "manuel_ilac_notu", "manuel_semptom_notu",
    ]
    assert len(rows) == 3


def test_export_validation_sample_respects_sample_size(tmp_path):
    conn = get_connection(":memory:")
    create_schema(conn)
    for i in range(5):
        _insert_hasta_with_ziyaret(conn, f"hasta{i}.pdf")

    output_csv = tmp_path / "sample.csv"
    export_validation_sample(conn, str(output_csv), sample_size=2)

    with open(output_csv, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert len(rows) == 3
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest tests/test_validation_export.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`trsm/validation_export.py`:

```python
import csv
import random


def export_validation_sample(conn, output_csv, sample_size=30, seed=42):
    cur = conn.cursor()
    cur.execute("SELECT id FROM hasta")
    hasta_ids = [row[0] for row in cur.fetchall()]
    random.Random(seed).shuffle(hasta_ids)
    sample_ids = hasta_ids[:sample_size]

    rows = []
    if sample_ids:
        placeholders = ",".join("?" * len(sample_ids))
        cur.execute(
            f"""SELECT h.dosya_adi, z.tarih, z.ham_mudahale_metni, z.ham_sonuc_metni
                FROM ziyaret z JOIN hasta h ON h.id = z.hasta_id
                WHERE z.hasta_id IN ({placeholders})
                ORDER BY h.dosya_adi, z.tarih""",
            sample_ids,
        )
        rows = cur.fetchall()

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "dosya_adi", "tarih", "ham_mudahale_metni", "ham_sonuc_metni",
            "manuel_ilac_notu", "manuel_semptom_notu",
        ])
        for row in rows:
            writer.writerow(list(row) + ["", ""])
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/test_validation_export.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Tüm test paketini çalıştır**

Run: `pytest -v`
Expected: Tüm testler PASS.

- [ ] **Step 6: Commit**

```bash
git add trsm/validation_export.py tests/test_validation_export.py
git commit -m "feat: manuel doğrulama örneklemi export aracı"
```

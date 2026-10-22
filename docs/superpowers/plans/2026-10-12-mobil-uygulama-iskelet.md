# Kartela Mobil Uygulaması (Aşama 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed hesaplarla giriş yapılan, `trsm.db`'deki gerçek hasta dosyalarını ve OCR notlarını rol bazlı gösteren, "Mürekkep + Zümrüt" temalı Expo (React Native) uygulamasını ve onu besleyen Flask `mobile_api` blueprint'ini kurmak.

**Architecture:** Sunucu tarafında `trsm/mobile_api/` paketi, `create_mobile_blueprint(db_path, secret_key, ...)` fabrikasıyla `/api/m` altında token korumalı JSON uç noktaları sunar; `demo_server.py` yalnızca bu blueprint'i kaydeder (model yükleyen `demo_server.py` testlerde içe aktarılmaz). Mobil tarafta `mobile/` altında Expo Router uygulaması; tek bir `(tabs)` grubu role göre sekmeleri filtreler, sunucu verisi TanStack Query ile çekilir, tasarım sistemi `src/theme` + `src/ui` içindedir.

**Tech Stack:** Python 3.11, Flask 3, werkzeug.security, itsdangerous, SQLite, pytest · Expo SDK (güncel, `npx expo install` ile uyumlu sürümler), Expo Router, TypeScript, react-native-reanimated, react-native-svg, @tanstack/react-query, expo-secure-store, @react-native-async-storage/async-storage, expo-image-picker, expo-file-system, @react-native-community/datetimepicker, @shopify/flash-list, lucide-react-native, @expo-google-fonts/geist, @expo-google-fonts/geist-mono, jest-expo.

**Spec:** `docs/superpowers/specs/2026-10-12-mobil-uygulama-iskelet-design.md`

## Global Constraints

- Yeni Python bağımlılığı eklenmez; yalnızca Flask ile gelen `werkzeug` ve `itsdangerous` kullanılır.
- Mevcut uç noktalar ve `demo.html` davranışı değişmez; yeni uç noktalar yalnızca `/api/m` öneki altındadır.
- Hata gövdesi her zaman `{"hata": "<Türkçe mesaj>", "kod": "<makine kodu>"}`.
- Token geçerliliği 12 saat; imza anahtarı `TRSM_SECRET_KEY`, yoksa `data/mobile_secret.key` (Git dışı).
- Sunucu varsayılan `127.0.0.1`'de dinler; `TRSM_HOST=0.0.0.0` ile yerel ağa açılır.
- İlaç sayımlarında ve vurgularda `eslesme_guveni >= 90` (mevcut `GUVEN_ESIGI`).
- Admin klinik uç noktalara (`/ozet`, `/hastalar*`) erişirse 403; doktor/hemşire `/sistem`, `/kullanicilar` için 403.
- Testler gerçek `trsm.db` yerine geçici SQLite dosyalarıyla çalışır; gerçek hasta satırları test çıktısına, commit'e veya dış servislere taşınmaz.
- Arayüz metinleri Türkçe. Yazı: Geist (400/500/600/700/800) ve yalnızca OCR/ham metin/dosya no için Geist Mono.
- Renk token'ları spec §4.2 tablosundaki değerlerin birebir aynısıdır.
- Animasyonlar Reanimated ile; giriş animasyonları ≤ 600 ms, kademeli gecikme ≤ 60 ms/öğe; "hareketi azalt" açıkken atlanır.
- Mobil paketler `npx expo install` ile kurulur (SDK uyumlu sürüm seçimi için); `npm install` yalnızca Expo dışı saf JS paketlerde.

## Verinin bilinen özellikleri (plan yazılırken ölçüldü)

- `hasta.dosya_adi` hastanın "Ad Soyad" bilgisidir (uzantısız); bazı kayıtlar NFD.
- `hasta.dogum_tarihi` biçimi `GG.AA.YYYY` (397 kayıt); ISO biçimi de desteklenmeli.
- `ziyaret.tarih` 41.676 kaydın 22.374'ünde **NULL**; 187 hastanın hiç tarihli notu yok. Tarihsiz notlar listelenir ve en sona sıralanır.

## Review Focus

- Tarihsiz notlar (`tarih IS NULL`): notlar sayfalamasında kaybolmamalı, en sonda görünmeli; mobilde "Tarihsiz" başlığıyla gösterilmeli → Task 4 testi `test_notes_paginate_with_undated_last`.
- Hiç tarihli notu olmayan dosya: `son_ziyaret` null, `yogunluk` sıfırlar; mobil kart "Tarihli not yok" yazmalı → Task 4 `test_list_patients_density_and_order`, Task 13 kart metni.
- Büyük harfli/NFD OCR metni (`DEPAKİN`, ayrışık `ğ`): vurgu yine bulunmalı ve konumlar UTF-16 olmalı → Task 3 testleri.
- Bozuk/başka dosyaya ait `once` imleci: 400 dönmeli, 500 değil → Task 5 `test_notes_invalid_cursor_is_400`.
- Sunucu adresi değişince/ulaşılamazken: uygulama kilitlenmemeli, "Tekrar dene / Adresi değiştir" sunmalı → Task 8 `client.test.ts` ağ hatası testi, Task 11 bağlantı hatası ekranı.

---

## Dosya Haritası

**Sunucu (yeni):**
- `trsm/mobile_api/__init__.py` — `create_mobile_blueprint` dışa aktarımı
- `trsm/mobile_api/users.py` — kullanıcı oluşturma, doğrulama, okuma
- `trsm/mobile_api/seed.py` — üç demo hesabını idempotent ekleme
- `trsm/mobile_api/auth.py` — token üretme/okuma, gizli anahtar yükleme
- `trsm/mobile_api/highlights.py` — Türkçe katlama ve vurgu aralıkları
- `trsm/mobile_api/queries.py` — özet, hasta listesi, detay, notlar, sistem
- `trsm/mobile_api/blueprint.py` — Flask uç noktaları ve rol kontrolü
- `scripts/seed_mobile_users.py` — seed CLI
- `tests/mobile_fixtures.py`, `tests/test_mobile_users.py`, `tests/test_mobile_highlights.py`, `tests/test_mobile_queries.py`, `tests/test_mobile_endpoints.py`

**Sunucu (değişen):** `trsm/schema.sql` (kullanici tablosu), `demo_server.py` (blueprint kaydı, `TRSM_HOST`), `README.md` (mobil bölümü).

**Mobil (yeni, `mobile/`):**
- `app/_layout.tsx`, `app/index.tsx`, `app/giris.tsx`, `app/(tabs)/_layout.tsx`, `app/(tabs)/{ozet,dosyalar,yeni,sistem,kullanicilar,ayarlar}.tsx`, `app/dosya/[id].tsx`
- `src/theme/{tokens.ts,ThemeProvider.tsx}`
- `src/lib/{tcKimlik.ts,turkishSearch.ts,roleTabs.ts,ocrSegments.ts,format.ts}` + `__tests__`
- `src/api/{types.ts,client.ts,errors.ts,ServerUrlProvider.tsx,hooks.ts}` + `__tests__`
- `src/auth/{tokenStore.ts,AuthProvider.tsx,demoAccounts.ts}`
- `src/storage/prefs.ts`
- `src/ui/*` (bileşen kataloğu)
- `src/features/{ozet,dosyalar,dosya-detay,yeni-hasta,ayarlar,admin}/*`

> **Not (spec'ten bilinçli sapma):** Spec §5 rol başına ayrı route grubu (`(doktor)`, `(hemsire)`, `(admin)`) öneriyor. Expo Router'da aynı yol adı (`/ozet`) birden fazla grupta çakıştığı için tek `(tabs)` grubu kullanılır ve sekmeler `tabsForRole(rol)` ile filtrelenir; rol dışı sekmeler `href: null` ile gizlenir ve ekran içinde de rol kontrolü yapılır. Davranış spec'le aynıdır. Spec §4.2'deki ≈250 ms tema renk geçişi uygulanmaz (tüm ağacı yeniden bağlamadan güvenli yapılamıyor); tema anında değişir.

---

## Ön Koşul (yürütücü, başlamadan)

- [ ] Ana çalışma ağacında kullanıcının commit edilmemiş değişiklikleri var (`demo.html`, `demo_server.py`, `trsm/treatment_timeline.py` ve takip edilmeyen dosyalar). **Bunlara dokunma, commit'e ekleme.** İşi `superpowers:using-git-worktrees` ile `mobil-uygulama` dalında, `tek-tik-kurulum`'un mevcut HEAD'inden açılan ayrı bir worktree'de yap.
- [ ] Worktree'de gerçek veriyle uçtan uca deneme için (Task 17) şu Git dışı dosyalara symlink gerekir: `trsm.db`, `data/symptom_index.npz`, `data/tedavi_gecis_istatistikleri.json`, `models/`. Komutlar Task 17'de.

---

### Task 1: Kullanıcı tablosu, kullanıcı işlemleri ve seed

**Files:**
- Modify: `trsm/schema.sql` (sona ekle)
- Create: `trsm/mobile_api/__init__.py` (geçici olarak boş docstring; Task 5'te dışa aktarım eklenir)
- Create: `trsm/mobile_api/users.py`, `trsm/mobile_api/seed.py`, `scripts/seed_mobile_users.py`
- Test: `tests/test_mobile_users.py`

**Interfaces:**
- Produces:
  - `ROLLER: tuple[str, ...] = ("admin", "doktor", "hemsire")`
  - `ensure_user(conn, kullanici_adi: str, ad_soyad: str, rol: str, sifre: str) -> bool` (True = oluşturuldu)
  - `authenticate(conn, kullanici_adi: str, sifre: str) -> dict | None`
  - `get_user(conn, user_id: int) -> dict | None`
  - `list_users(conn) -> list[dict]`
  - kullanıcı dict anahtarları: `id, kullanici_adi, ad_soyad, rol, sifre_hash, google_sub, google_eposta`
  - `seed_demo_users(conn, env: Mapping[str, str]) -> dict[str, bool]`
  - `DEMO_ACCOUNTS`, `DEFAULT_PASSWORDS = {"doktor": "kartela-doktor", "hemsire": "kartela-hemsire", "admin": "kartela-admin"}`

- [ ] **Step 1: Write the failing test** — `tests/test_mobile_users.py`

```python
import pytest

from trsm.db import create_schema, get_connection
from trsm.mobile_api.seed import DEFAULT_PASSWORDS, seed_demo_users
from trsm.mobile_api.users import authenticate, ensure_user, get_user, list_users


def _conn():
    conn = get_connection(":memory:")
    create_schema(conn)
    return conn


def test_ensure_user_creates_once_and_never_overwrites_password():
    conn = _conn()
    assert ensure_user(conn, "doktor", "Demo Doktor", "doktor", "ilk") is True
    assert ensure_user(conn, "doktor", "Başka Ad", "doktor", "ikinci") is False
    assert authenticate(conn, "doktor", "ilk")["ad_soyad"] == "Demo Doktor"
    assert authenticate(conn, "doktor", "ikinci") is None
    assert len(list_users(conn)) == 1


def test_password_is_stored_hashed():
    conn = _conn()
    ensure_user(conn, "hemsire", "Demo Hemşire", "hemsire", "gizli")
    stored = conn.execute("SELECT sifre_hash FROM kullanici").fetchone()[0]
    assert stored != "gizli" and len(stored) > 20


def test_authenticate_rejects_unknown_user_and_wrong_password():
    conn = _conn()
    ensure_user(conn, "admin", "Demo Admin", "admin", "dogru")
    assert authenticate(conn, "yok", "dogru") is None
    assert authenticate(conn, "admin", "yanlis") is None
    user = authenticate(conn, "admin", "dogru")
    assert user["rol"] == "admin"
    assert get_user(conn, user["id"])["kullanici_adi"] == "admin"
    assert get_user(conn, 999) is None


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        ensure_user(_conn(), "x", "X", "sekreter", "s")


def test_seed_is_idempotent_and_uses_env_passwords():
    conn = _conn()
    first = seed_demo_users(conn, {"TRSM_SEED_PASSWORD_DOKTOR": "ozel"})
    second = seed_demo_users(conn, {})
    assert first == {"doktor": True, "hemsire": True, "admin": True}
    assert second == {"doktor": False, "hemsire": False, "admin": False}
    assert authenticate(conn, "doktor", "ozel") is not None
    assert authenticate(conn, "hemsire", DEFAULT_PASSWORDS["hemsire"]) is not None
    assert sorted(u["rol"] for u in list_users(conn)) == ["admin", "doktor", "hemsire"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mobile_users.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trsm.mobile_api'`

- [ ] **Step 3: Write minimal implementation**

`trsm/schema.sql` dosyasının sonuna ekle:

```sql

CREATE TABLE IF NOT EXISTS kullanici (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT NOT NULL UNIQUE,
    ad_soyad TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('admin', 'doktor', 'hemsire')),
    sifre_hash TEXT NOT NULL,
    google_sub TEXT UNIQUE,
    google_eposta TEXT,
    olusturma_zamani TEXT NOT NULL
);
```

`trsm/mobile_api/__init__.py`:

```python
"""Kartela mobil uygulaması için JSON API."""
```

`trsm/mobile_api/users.py`:

```python
"""Mobil uygulama kullanıcıları: oluşturma, şifre doğrulama, okuma."""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

ROLLER = ("admin", "doktor", "hemsire")
_KEYS = ("id", "kullanici_adi", "ad_soyad", "rol", "sifre_hash", "google_sub", "google_eposta")
_SELECT = "SELECT " + ", ".join(_KEYS) + " FROM kullanici"


def _to_user(row):
    return dict(zip(_KEYS, row)) if row is not None else None


def ensure_user(conn, kullanici_adi, ad_soyad, rol, sifre):
    """Kullanıcı yoksa oluşturur; varsa hiçbir alanına (şifre dahil) dokunmaz."""
    if rol not in ROLLER:
        raise ValueError(f"Bilinmeyen rol: {rol}")
    if conn.execute("SELECT 1 FROM kullanici WHERE kullanici_adi = ?", (kullanici_adi,)).fetchone():
        return False
    conn.execute(
        """INSERT INTO kullanici (kullanici_adi, ad_soyad, rol, sifre_hash, olusturma_zamani)
           VALUES (?, ?, ?, ?, ?)""",
        (
            kullanici_adi,
            ad_soyad,
            rol,
            generate_password_hash(sifre),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return True


def authenticate(conn, kullanici_adi, sifre):
    user = _to_user(conn.execute(_SELECT + " WHERE kullanici_adi = ?", (kullanici_adi,)).fetchone())
    if user is None or not check_password_hash(user["sifre_hash"], sifre):
        return None
    return user


def get_user(conn, user_id):
    return _to_user(conn.execute(_SELECT + " WHERE id = ?", (user_id,)).fetchone())


def list_users(conn):
    return [_to_user(row) for row in conn.execute(_SELECT + " ORDER BY id")]
```

`trsm/mobile_api/seed.py`:

```python
"""Üç demo hesabını (doktor, hemşire, admin) idempotent olarak ekler."""
from trsm.mobile_api.users import ensure_user

DEMO_ACCOUNTS = (
    ("doktor", "Demo Doktor", "doktor"),
    ("hemsire", "Demo Hemşire", "hemsire"),
    ("admin", "Demo Admin", "admin"),
)
DEFAULT_PASSWORDS = {
    "doktor": "kartela-doktor",
    "hemsire": "kartela-hemsire",
    "admin": "kartela-admin",
}


def seed_demo_users(conn, env):
    results = {}
    for username, full_name, role in DEMO_ACCOUNTS:
        password = env.get(f"TRSM_SEED_PASSWORD_{role.upper()}") or DEFAULT_PASSWORDS[role]
        results[username] = ensure_user(conn, username, full_name, role, password)
    return results
```

`scripts/seed_mobile_users.py`:

```python
"""Mobil uygulamanın üç demo hesabını oluşturur (varsa dokunmaz).

Çalıştırma: uv run python scripts/seed_mobile_users.py [--db trsm.db]
Şifreler TRSM_SEED_PASSWORD_DOKTOR / _HEMSIRE / _ADMIN ortam
değişkenlerinden okunur; verilmezse trsm/mobile_api/seed.py'deki demo
şifreleri kullanılır.
"""
import argparse
import os
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trsm.db import create_schema, get_connection
from trsm.mobile_api.seed import seed_demo_users
from trsm.runtime_paths import runtime_data_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(runtime_data_paths()["db"]))
    args = parser.parse_args()
    with closing(get_connection(args.db)) as conn:
        create_schema(conn)
        results = seed_demo_users(conn, os.environ)
    for username, created in results.items():
        print(f"{username}: {'oluşturuldu' if created else 'zaten var, dokunulmadı'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mobile_users.py -v`
Expected: 5 passed

- [ ] **Step 5: Run full suite (şema değişikliği mevcut testleri bozmasın)**

Run: `uv run pytest -q`
Expected: tüm testler geçer (önceki 139 + 5)

- [ ] **Step 6: Commit**

```bash
git add trsm/schema.sql trsm/mobile_api/__init__.py trsm/mobile_api/users.py trsm/mobile_api/seed.py scripts/seed_mobile_users.py tests/test_mobile_users.py
git commit -m "feat(mobil-api): kullanıcı tablosu, şifre doğrulama ve demo hesap seed'i"
```

---

### Task 2: Token ve gizli anahtar

**Files:**
- Create: `trsm/mobile_api/auth.py`
- Test: `tests/test_mobile_users.py` (aynı dosyaya ekle)

**Interfaces:**
- Produces:
  - `TOKEN_MAX_AGE_SECONDS = 43200`
  - `make_serializer(secret_key: str) -> URLSafeTimedSerializer`
  - `issue_token(serializer, user_id: int) -> str`
  - `read_token(serializer, token: str, max_age: int = TOKEN_MAX_AGE_SECONDS) -> int | None`
  - `load_or_create_secret(path: Path, env: Mapping[str, str]) -> str`

- [ ] **Step 1: Write the failing test** — `tests/test_mobile_users.py` sonuna ekle

```python
from trsm.mobile_api.auth import issue_token, load_or_create_secret, make_serializer, read_token


def test_token_roundtrip_and_rejections():
    serializer = make_serializer("anahtar")
    token = issue_token(serializer, 7)
    assert read_token(serializer, token) == 7
    assert read_token(make_serializer("baska"), token) is None
    assert read_token(serializer, "bozuk.token") is None
    assert read_token(serializer, token, max_age=-1) is None  # süresi dolmuş


def test_secret_prefers_env_then_file_then_creates(tmp_path):
    path = tmp_path / "data" / "mobile_secret.key"
    assert load_or_create_secret(path, {"TRSM_SECRET_KEY": "env"}) == "env"
    assert not path.exists()
    created = load_or_create_secret(path, {})
    assert path.exists() and len(created) == 64
    assert load_or_create_secret(path, {}) == created
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mobile_users.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trsm.mobile_api.auth'`

- [ ] **Step 3: Write minimal implementation** — `trsm/mobile_api/auth.py`

```python
"""İmzalı, süreli oturum token'ları ve imza anahtarının yüklenmesi."""
import secrets
from pathlib import Path

from itsdangerous import BadSignature, URLSafeTimedSerializer

TOKEN_MAX_AGE_SECONDS = 12 * 60 * 60


def make_serializer(secret_key):
    return URLSafeTimedSerializer(secret_key, salt="kartela-mobil-oturum")


def issue_token(serializer, user_id):
    return serializer.dumps({"uid": int(user_id)})


def read_token(serializer, token, max_age=TOKEN_MAX_AGE_SECONDS):
    """Geçerli token için kullanıcı id'si; bozuk/süresi dolmuşsa None."""
    try:
        payload = serializer.loads(token, max_age=max_age)
    except BadSignature:  # SignatureExpired da BadSignature alt sınıfıdır
        return None
    user_id = payload.get("uid") if isinstance(payload, dict) else None
    return user_id if isinstance(user_id, int) else None


def load_or_create_secret(path, env):
    if env.get("TRSM_SECRET_KEY"):
        return env["TRSM_SECRET_KEY"]
    path = Path(path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32)
    path.write_text(secret, encoding="utf-8")
    return secret
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mobile_users.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add trsm/mobile_api/auth.py tests/test_mobile_users.py
git commit -m "feat(mobil-api): imzalı oturum token'ı ve gizli anahtar yükleme"
```

---

### Task 3: OCR metninde vurgu aralıkları

**Files:**
- Create: `trsm/mobile_api/highlights.py`
- Test: `tests/test_mobile_highlights.py`

**Interfaces:**
- Produces:
  - `turkish_fold(text: str) -> str` — uzunluğu koruyan Türkçe küçük harfe çevirme (İ→i, I→ı)
  - `find_highlights(text: str, drug_terms: Iterable[str], symptom_terms: Iterable[str]) -> list[dict]` — `[{"bas": int, "son": int, "tur": "ilac" | "belirti"}]`, konumlar **UTF-16 kod birimi** (JS string indeksleriyle aynı), sıralı, çakışmasız. `text` NFC olmalı (çağıran normalize eder); terimler fonksiyon içinde NFC'ye çevrilir.

- [ ] **Step 1: Write the failing test** — `tests/test_mobile_highlights.py`

```python
import unicodedata

from trsm.mobile_api.highlights import find_highlights, turkish_fold


def test_turkish_fold_keeps_length_and_handles_dotted_i():
    assert turkish_fold("İLAÇ Işık") == "ilaç ışık"
    assert len(turkish_fold("İİII")) == 4


def test_finds_drug_and_symptom_case_insensitively():
    text = "İLAÇ: DEPAKİN devam. Huzursuzluk"
    assert find_highlights(text, ["Depakin"], ["huzursuzluk"]) == [
        {"bas": 6, "son": 13, "tur": "ilac"},
        {"bas": 21, "son": 32, "tur": "belirti"},
    ]


def test_marks_every_occurrence_and_skips_missing_or_empty_terms():
    text = "Depakin 500, sonra yine depakin"
    result = find_highlights(text, ["Depakin", "Abilify", "  "], [])
    assert [(r["bas"], r["son"]) for r in result] == [(0, 7), (24, 31)]


def test_drug_wins_over_overlapping_symptom():
    text = "lityum zehirlenmesi"
    result = find_highlights(text, ["lityum"], ["lityum zehirlenmesi"])
    assert result == [{"bas": 0, "son": 6, "tur": "ilac"}]


def test_nfd_term_matches_nfc_text():
    text = "Baş ağrısı var"
    term = unicodedata.normalize("NFD", "baş ağrısı")
    assert find_highlights(text, [], [term]) == [{"bas": 0, "son": 10, "tur": "belirti"}]


def test_offsets_are_utf16_units():
    text = "😀 Depakin"
    assert find_highlights(text, ["Depakin"], []) == [{"bas": 3, "son": 10, "tur": "ilac"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mobile_highlights.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation** — `trsm/mobile_api/highlights.py`

```python
"""OCR notu içinde ilaç ve belirti ifadelerinin konumları.

DB konum saklamadığı için ifadeler metin içinde aranır. Türkçe katlama
karakter başına yapılır ve uzunluğu korur; böylece katlanmış metindeki
indeks orijinal metindeki indekse eşittir.
"""
import unicodedata


def _fold_char(ch):
    if ch == "İ":
        return "i"
    if ch == "I":
        return "ı"
    lowered = ch.lower()
    return lowered if len(lowered) == 1 else ch


def turkish_fold(text):
    return "".join(_fold_char(ch) for ch in text)


def _utf16_offsets(text):
    offsets = [0]
    for ch in text:
        offsets.append(offsets[-1] + (2 if ord(ch) > 0xFFFF else 1))
    return offsets


def find_highlights(text, drug_terms, symptom_terms):
    folded = turkish_fold(text)
    candidates = []
    for priority, kind, terms in ((0, "ilac", drug_terms), (1, "belirti", symptom_terms)):
        for term in terms:
            needle = turkish_fold(unicodedata.normalize("NFC", term or "").strip())
            if not needle:
                continue
            start = folded.find(needle)
            while start != -1:
                candidates.append((priority, start, start + len(needle), kind))
                start = folded.find(needle, start + len(needle))
    candidates.sort(key=lambda c: (c[0], c[1], c[1] - c[2]))
    taken = []
    for _, start, end, kind in candidates:
        if all(end <= s or start >= e for s, e, _ in taken):
            taken.append((start, end, kind))
    taken.sort()
    offsets = _utf16_offsets(text)
    return [{"bas": offsets[s], "son": offsets[e], "tur": kind} for s, e, kind in taken]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mobile_highlights.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add trsm/mobile_api/highlights.py tests/test_mobile_highlights.py
git commit -m "feat(mobil-api): OCR metninde Türkçe duyarlı ilaç/belirti vurgu aralıkları"
```

---

### Task 4: Sorgular (özet, hasta listesi, detay, notlar, sistem)

**Files:**
- Create: `trsm/mobile_api/queries.py`, `tests/mobile_fixtures.py`
- Test: `tests/test_mobile_queries.py`

**Interfaces:**
- Consumes: `find_highlights`, `turkish_fold` (Task 3)
- Produces:
  - `summary(conn, threshold: int) -> dict` — anahtarlar: `toplam_dosya, toplam_not, ilacli_not, yillik_not[{yil, sayi}], cinsiyet{erkek, kadin, bilinmiyor}, en_sik_ilaclar[{ilac, sayi}], okunmamis_rapor`
  - `list_patients(conn, today: date) -> list[dict]` — her öğe: `id, ad, cinsiyet, yas, not_sayisi, son_ziyaret, yogunluk(list[int] 12), okunmamis`
  - `patient_detail(conn, patient_id: int, today: date, threshold: int) -> dict | None` — `id, ad, cinsiyet, yas, dosya_no, tc_maskeli, not_sayisi, ilac_sayisi, ilk_kayit, son_kayit`
  - `patient_notes(conn, patient_id: int, threshold: int, before_id: int | None = None, limit: int = 20) -> dict` — `{"notlar": [...], "sonraki": int | None}`; imleç dosyaya ait değilse `ValueError`
  - not öğesi: `id, tarih, sayfa_no, metin, vurgular, ilaclar[{ad, doz, siklik}], belirti_sayisi, gorsel_var`
  - `system_status(conn, db_path: Path) -> dict` — `tablolar{...}, db_boyutu_mb`
  - `tests/mobile_fixtures.py`: `build_fixture_db(path) -> dict[str, int]` (ziyaret id'leri: `v1..v5`)

- [ ] **Step 1: Write the fixture** — `tests/mobile_fixtures.py`

```python
"""Mobil API testleri için küçük, tamamen uydurma veritabanı."""
import unicodedata
from contextlib import closing

from trsm.db import create_schema, get_connection


def _visit(conn, patient_id, tarih, mudahale, sonuc=None, drugs=(), symptoms=()):
    visit_id = conn.execute(
        """INSERT INTO ziyaret (hasta_id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni)
           VALUES (?, ?, 1, ?, ?)""",
        (patient_id, tarih, mudahale, sonuc),
    ).lastrowid
    for ham, normalize, doz, siklik, guven in drugs:
        conn.execute(
            """INSERT INTO ilac_kullanimi
               (ziyaret_id, ilac_adi_normalize, ilac_adi_ham, doz, siklik, eslesme_guveni)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (visit_id, normalize, ham, doz, siklik, guven),
        )
    for ifade in symptoms:
        conn.execute("INSERT INTO semptom_kaydi (ziyaret_id, ifade_ham) VALUES (?, ?)", (visit_id, ifade))
    return visit_id


def build_fixture_db(path):
    with closing(get_connection(path)) as conn:
        create_schema(conn)
        ayse = conn.execute(
            "INSERT INTO hasta (dosya_adi, cinsiyet, dogum_tarihi) VALUES ('Ayşe Kaya', 'Kadın', '07.01.1989')"
        ).lastrowid
        ismail = conn.execute(
            "INSERT INTO hasta (dosya_adi, cinsiyet, dogum_tarihi) VALUES ('İsmail Işık', 'Erkek', '1990-05-20')"
        ).lastrowid
        conn.execute("INSERT INTO hasta (dosya_adi) VALUES ('Boş Dosya')")
        ids = {
            "v1": _visit(conn, ayse, "2021-03-01", "Depakin 500 2x1 başlandı", "Uykusuzluk var",
                         drugs=[("Depakin", "Depakin", "500", "2x1", 95)], symptoms=["uykusuzluk"]),
            "v2": _visit(conn, ayse, "2023-06-10", "Abilify 10mg eklendi",
                         drugs=[("Abilify", "Abilify", "10mg", None, 100), ("Lityum", "Lithium", None, None, 80)]),
            "v3": _visit(conn, ayse, "2023-06-10", "Kontrol"),
            "v4": _visit(conn, ayse, None, unicodedata.normalize("NFD", "Baş ağrısı var"),
                         symptoms=["baş ağrısı"]),
            "v5": _visit(conn, ismail, "2025-01-15", "İLAÇ: DEPAKİN devam. Huzursuzluk",
                         drugs=[("Depakin", "Depakin", None, None, 92)], symptoms=["huzursuzluk"]),
        }
        conn.commit()
    return {"ayse": ayse, "ismail": ismail, "bos": 3, **ids}
```

- [ ] **Step 2: Write the failing test** — `tests/test_mobile_queries.py`

```python
from contextlib import closing
from datetime import date

import pytest

from tests.mobile_fixtures import build_fixture_db
from trsm.db import get_connection
from trsm.mobile_api.queries import (
    list_patients,
    patient_detail,
    patient_notes,
    summary,
    system_status,
)

TODAY = date(2026, 10, 12)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "mobil.db"
    ids = build_fixture_db(path)
    with closing(get_connection(path)) as conn:
        yield conn, ids, path


def test_summary_counts(db):
    conn, _, _ = db
    result = summary(conn, 90)
    assert result["toplam_dosya"] == 3
    assert result["toplam_not"] == 5
    assert result["ilacli_not"] == 3
    assert result["yillik_not"] == [
        {"yil": 2021, "sayi": 1}, {"yil": 2022, "sayi": 0}, {"yil": 2023, "sayi": 2},
        {"yil": 2024, "sayi": 0}, {"yil": 2025, "sayi": 1},
    ]
    assert result["cinsiyet"] == {"erkek": 1, "kadin": 1, "bilinmiyor": 1}
    assert result["en_sik_ilaclar"] == [{"ilac": "Depakin", "sayi": 2}, {"ilac": "Abilify", "sayi": 1}]
    assert result["okunmamis_rapor"] == 0


def test_list_patients_density_and_order(db):
    conn, ids, _ = db
    patients = list_patients(conn, TODAY)
    assert [p["ad"] for p in patients] == ["Ayşe Kaya", "Boş Dosya", "İsmail Işık"]
    ayse, bos, ismail = patients
    assert ayse["yas"] == 37 and ismail["yas"] == 36 and bos["yas"] is None
    assert ayse["not_sayisi"] == 4 and ayse["son_ziyaret"] == "2023-06-10"
    assert ayse["yogunluk"] == [2] + [0] * 10 + [3]
    assert ismail["yogunluk"] == [0] * 11 + [3]
    assert bos["yogunluk"] == [0] * 12 and bos["son_ziyaret"] is None and bos["not_sayisi"] == 0
    assert ayse["okunmamis"] is False


def test_patient_detail(db):
    conn, ids, _ = db
    detail = patient_detail(conn, ids["ayse"], TODAY, 90)
    assert detail == {
        "id": ids["ayse"], "ad": "Ayşe Kaya", "cinsiyet": "Kadın", "yas": 37,
        "dosya_no": "#0001", "tc_maskeli": None, "not_sayisi": 4, "ilac_sayisi": 2,
        "ilk_kayit": "2021-03-01", "son_kayit": "2023-06-10",
    }
    assert patient_detail(conn, 999, TODAY, 90) is None


def test_note_content_and_highlights(db):
    conn, ids, _ = db
    notes = patient_notes(conn, ids["ayse"], 90, limit=10)["notlar"]
    v1 = next(n for n in notes if n["id"] == ids["v1"])
    assert v1["metin"] == "Depakin 500 2x1 başlandı\n\nUykusuzluk var"
    assert v1["vurgular"] == [{"bas": 0, "son": 7, "tur": "ilac"}, {"bas": 26, "son": 36, "tur": "belirti"}]
    assert v1["ilaclar"] == [{"ad": "Depakin", "doz": "500", "siklik": "2x1"}]
    assert v1["belirti_sayisi"] == 1 and v1["gorsel_var"] is False and v1["sayfa_no"] == 1
    v2 = next(n for n in notes if n["id"] == ids["v2"])
    assert [i["ad"] for i in v2["ilaclar"]] == ["Abilify"]  # güveni 80 olan Lityum dışarıda
    v4 = next(n for n in notes if n["id"] == ids["v4"])
    assert v4["metin"] == "Baş ağrısı var"  # NFD → NFC
    assert v4["vurgular"] == [{"bas": 0, "son": 10, "tur": "belirti"}]


def test_notes_paginate_with_undated_last(db):
    conn, ids, _ = db
    first = patient_notes(conn, ids["ayse"], 90, limit=2)
    assert [n["id"] for n in first["notlar"]] == [ids["v3"], ids["v2"]]
    assert first["sonraki"] == ids["v2"]
    second = patient_notes(conn, ids["ayse"], 90, before_id=first["sonraki"], limit=2)
    assert [n["id"] for n in second["notlar"]] == [ids["v1"], ids["v4"]]
    assert second["notlar"][1]["tarih"] is None
    assert second["sonraki"] is None


def test_notes_cursor_from_other_patient_raises(db):
    conn, ids, _ = db
    with pytest.raises(ValueError):
        patient_notes(conn, ids["ayse"], 90, before_id=ids["v5"])


def test_system_status(db):
    conn, _, path = db
    status = system_status(conn, path)
    assert status["tablolar"]["hasta"] == 3
    assert status["tablolar"]["ziyaret"] == 5
    assert status["tablolar"]["kullanici"] == 0
    assert status["db_boyutu_mb"] >= 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_mobile_queries.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trsm.mobile_api.queries'`

- [ ] **Step 4: Write minimal implementation** — `trsm/mobile_api/queries.py`

```python
"""Mobil uygulamanın okuduğu salt-okunur sorgular."""
import unicodedata
from datetime import date, datetime
from pathlib import Path

from trsm.mobile_api.highlights import find_highlights, turkish_fold

TREND_YEARS = tuple(range(2021, 2026))
DENSITY_BUCKETS = 12
STATUS_TABLES = ("hasta", "ziyaret", "ilac_kullanimi", "semptom_kaydi", "ilac_sozluk", "kullanici")
_GENDER_KEYS = {"Erkek": "erkek", "Kadın": "kadin"}
_ORDER_KEY = "COALESCE(tarih, '')"  # tarihsiz notlar en sona düşer


def _nfc(value):
    return unicodedata.normalize("NFC", value) if value else value


def parse_birth_date(value):
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def compute_age(birth, today):
    if birth is None:
        return None
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _parse_iso(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def density(dates):
    """İlk ve son tarihli not arasını 12 kovaya böler, her kovayı 0-3'e ölçekler."""
    days = sorted(d for d in dates if d is not None)
    buckets = [0] * DENSITY_BUCKETS
    if not days:
        return buckets
    first, span = days[0], (days[-1] - days[0]).days
    for day in days:
        if span == 0:
            index = DENSITY_BUCKETS - 1
        else:
            index = min(DENSITY_BUCKETS - 1, int((day - first).days / span * DENSITY_BUCKETS))
        buckets[index] += 1
    peak = max(buckets)

    def level(count):
        if count == 0:
            return 0
        if count * 3 >= peak * 2:
            return 3
        if count * 3 >= peak:
            return 2
        return 1

    return [level(count) for count in buckets]


def summary(conn, threshold):
    yearly = dict(conn.execute(
        "SELECT substr(tarih, 1, 4), COUNT(*) FROM ziyaret WHERE tarih IS NOT NULL GROUP BY 1"
    ).fetchall())
    genders = {"erkek": 0, "kadin": 0, "bilinmiyor": 0}
    for value, count in conn.execute("SELECT cinsiyet, COUNT(*) FROM hasta GROUP BY cinsiyet"):
        genders[_GENDER_KEYS.get(_nfc(value), "bilinmiyor")] += count
    top = conn.execute(
        """SELECT ilac_adi_normalize, COUNT(*) AS sayi FROM ilac_kullanimi
           WHERE eslesme_guveni >= ? AND ilac_adi_normalize IS NOT NULL
           GROUP BY ilac_adi_normalize ORDER BY sayi DESC, ilac_adi_normalize ASC LIMIT 5""",
        (threshold,),
    ).fetchall()
    return {
        "toplam_dosya": conn.execute("SELECT COUNT(*) FROM hasta").fetchone()[0],
        "toplam_not": conn.execute("SELECT COUNT(*) FROM ziyaret").fetchone()[0],
        "ilacli_not": conn.execute(
            "SELECT COUNT(DISTINCT ziyaret_id) FROM ilac_kullanimi WHERE eslesme_guveni >= ?", (threshold,)
        ).fetchone()[0],
        "yillik_not": [{"yil": year, "sayi": yearly.get(str(year), 0)} for year in TREND_YEARS],
        "cinsiyet": genders,
        "en_sik_ilaclar": [{"ilac": name, "sayi": count} for name, count in top],
        "okunmamis_rapor": 0,
    }


def list_patients(conn, today):
    dates_by_patient = {}
    for patient_id, tarih in conn.execute("SELECT hasta_id, tarih FROM ziyaret"):
        dates_by_patient.setdefault(patient_id, []).append(_parse_iso(tarih))
    patients = []
    for patient_id, name, gender, birth in conn.execute("SELECT id, dosya_adi, cinsiyet, dogum_tarihi FROM hasta"):
        dates = dates_by_patient.get(patient_id, [])
        dated = [d for d in dates if d is not None]
        patients.append({
            "id": patient_id,
            "ad": _nfc(name),
            "cinsiyet": _nfc(gender),
            "yas": compute_age(parse_birth_date(birth), today),
            "not_sayisi": len(dates),
            "son_ziyaret": max(dated).isoformat() if dated else None,
            "yogunluk": density(dates),
            "okunmamis": False,
        })
    patients.sort(key=lambda p: (turkish_fold(p["ad"] or ""), p["id"]))
    return patients


def patient_detail(conn, patient_id, today, threshold):
    row = conn.execute(
        "SELECT id, dosya_adi, cinsiyet, dogum_tarihi FROM hasta WHERE id = ?", (patient_id,)
    ).fetchone()
    if row is None:
        return None
    note_count, first, last = conn.execute(
        "SELECT COUNT(*), MIN(tarih), MAX(tarih) FROM ziyaret WHERE hasta_id = ?", (patient_id,)
    ).fetchone()
    drug_count = conn.execute(
        """SELECT COUNT(DISTINCT COALESCE(ik.ilac_adi_normalize, ik.ilac_adi_ham))
           FROM ilac_kullanimi ik JOIN ziyaret z ON z.id = ik.ziyaret_id
           WHERE z.hasta_id = ? AND ik.eslesme_guveni >= ?""",
        (patient_id, threshold),
    ).fetchone()[0]
    pid, name, gender, birth = row
    return {
        "id": pid,
        "ad": _nfc(name),
        "cinsiyet": _nfc(gender),
        "yas": compute_age(parse_birth_date(birth), today),
        "dosya_no": f"#{pid:04d}",
        "tc_maskeli": None,
        "not_sayisi": note_count,
        "ilac_sayisi": drug_count,
        "ilk_kayit": first,
        "son_kayit": last,
    }


def _build_note(conn, row, threshold):
    visit_id, tarih, page, intervention, result = row
    parts = (_nfc(intervention), _nfc(result))
    text = "\n\n".join(part.strip() for part in parts if part and part.strip())
    drugs = conn.execute(
        """SELECT ilac_adi_ham, ilac_adi_normalize, doz, siklik FROM ilac_kullanimi
           WHERE ziyaret_id = ? AND eslesme_guveni >= ? ORDER BY id""",
        (visit_id, threshold),
    ).fetchall()
    symptoms = [r[0] for r in conn.execute(
        "SELECT ifade_ham FROM semptom_kaydi WHERE ziyaret_id = ? ORDER BY id", (visit_id,)
    )]
    medicines, seen = [], set()
    for raw, normalized, dose, frequency in drugs:
        name = normalized or raw
        if name in seen:
            continue
        seen.add(name)
        medicines.append({"ad": name, "doz": dose, "siklik": frequency})
    return {
        "id": visit_id,
        "tarih": tarih,
        "sayfa_no": page,
        "metin": text,
        "vurgular": find_highlights(text, [d[0] for d in drugs], symptoms),
        "ilaclar": medicines,
        "belirti_sayisi": len(symptoms),
        "gorsel_var": False,
    }


def patient_notes(conn, patient_id, threshold, before_id=None, limit=20):
    where, params = "hasta_id = ?", [patient_id]
    if before_id is not None:
        cursor = conn.execute(
            f"SELECT {_ORDER_KEY} FROM ziyaret WHERE id = ? AND hasta_id = ?", (before_id, patient_id)
        ).fetchone()
        if cursor is None:
            raise ValueError("İmleç bu dosyaya ait değil.")
        where += f" AND ({_ORDER_KEY} < ? OR ({_ORDER_KEY} = ? AND id < ?))"
        params += [cursor[0], cursor[0], before_id]
    rows = conn.execute(
        f"""SELECT id, tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni FROM ziyaret
            WHERE {where} ORDER BY {_ORDER_KEY} DESC, id DESC LIMIT ?""",
        (*params, limit + 1),
    ).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "notlar": [_build_note(conn, row, threshold) for row in rows],
        "sonraki": rows[-1][0] if has_more else None,
    }


def system_status(conn, db_path):
    path = Path(db_path)
    size = path.stat().st_size if path.exists() else 0
    return {
        "tablolar": {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in STATUS_TABLES},
        "db_boyutu_mb": round(size / 1_048_576, 1),
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_mobile_queries.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add trsm/mobile_api/queries.py tests/mobile_fixtures.py tests/test_mobile_queries.py
git commit -m "feat(mobil-api): özet, hasta listesi, dosya detayı ve sayfalı not sorguları"
```

---

### Task 5: Blueprint, rol kontrolü ve uç noktalar

**Files:**
- Create: `trsm/mobile_api/blueprint.py`
- Modify: `trsm/mobile_api/__init__.py`
- Test: `tests/test_mobile_endpoints.py`

**Interfaces:**
- Consumes: Task 1–4 fonksiyonları.
- Produces: `create_mobile_blueprint(db_path, secret_key: str, *, confidence_threshold: int = 90, today: Callable[[], date] = date.today, status_extra: Callable[[], dict] = lambda: {}) -> Blueprint` (url_prefix `/api/m`). Uç noktalar spec §6.3 + `GET /api/m/saglik` (kimlik doğrulamasız, `{"durum": "ok"}`; mobil "Bağlantıyı sına" için). Genel kullanıcı JSON'u: `{id, kullanici_adi, ad_soyad, rol, google_bagli}`. Liste uç noktaları sarmalanmış döner: `{"hastalar": [...]}`, `{"kullanicilar": [...]}`.

- [ ] **Step 1: Write the failing test** — `tests/test_mobile_endpoints.py`

```python
from contextlib import closing
from datetime import date

import pytest
from flask import Flask

from tests.mobile_fixtures import build_fixture_db
from trsm.db import get_connection
from trsm.mobile_api import create_mobile_blueprint
from trsm.mobile_api.auth import issue_token, make_serializer
from trsm.mobile_api.users import ensure_user

SECRET = "test-anahtari"


@pytest.fixture
def ctx(tmp_path):
    path = tmp_path / "mobil.db"
    ids = build_fixture_db(path)
    app = Flask(__name__)
    app.register_blueprint(create_mobile_blueprint(
        path, SECRET, today=lambda: date(2026, 10, 12),
        status_extra=lambda: {"semptom_indeksi": True, "ollama": False},
    ))
    with closing(get_connection(path)) as conn:
        for role in ("doktor", "hemsire", "admin"):
            ensure_user(conn, role, f"Demo {role}", role, f"{role}-sifre")
    return app.test_client(), ids


def _login(client, role):
    response = client.post("/api/m/giris", json={"kullanici_adi": role, "sifre": f"{role}-sifre"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_health_needs_no_token(ctx):
    client, _ = ctx
    assert client.get("/api/m/saglik").get_json() == {"durum": "ok"}


def test_login_success_and_me(ctx):
    client, _ = ctx
    response = client.post("/api/m/giris", json={"kullanici_adi": "doktor", "sifre": "doktor-sifre"})
    body = response.get_json()
    assert body["kullanici"] == {
        "id": 1, "kullanici_adi": "doktor", "ad_soyad": "Demo doktor", "rol": "doktor", "google_bagli": False,
    }
    me = client.get("/api/m/ben", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.get_json()["rol"] == "doktor"


@pytest.mark.parametrize("payload, status, kod", [
    ({"kullanici_adi": "doktor", "sifre": "yanlis"}, 401, "hatali_giris"),
    ({"kullanici_adi": "yok", "sifre": "x"}, 401, "hatali_giris"),
    ({"kullanici_adi": "doktor"}, 400, "eksik_bilgi"),
    (None, 400, "eksik_bilgi"),
])
def test_login_failures(ctx, payload, status, kod):
    client, _ = ctx
    response = client.post("/api/m/giris", json=payload) if payload is not None else client.post("/api/m/giris")
    assert response.status_code == status
    assert response.get_json()["kod"] == kod


@pytest.mark.parametrize("header", [None, "Bearer bozuk", "Token x"])
def test_missing_or_bad_token_is_401(ctx, header):
    client, _ = ctx
    headers = {"Authorization": header} if header else {}
    response = client.get("/api/m/ben", headers=headers)
    assert response.status_code == 401
    assert response.get_json() == {"hata": "Oturum geçersiz ya da süresi doldu.", "kod": "oturum_gecersiz"}


def test_token_for_deleted_user_is_401(ctx):
    client, _ = ctx
    token = issue_token(make_serializer(SECRET), 999)
    assert client.get("/api/m/ben", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("role, path, status", [
    ("admin", "/api/m/ozet", 403),
    ("admin", "/api/m/hastalar", 403),
    ("admin", "/api/m/hastalar/1", 403),
    ("admin", "/api/m/hastalar/1/notlar", 403),
    ("doktor", "/api/m/sistem", 403),
    ("hemsire", "/api/m/kullanicilar", 403),
    ("doktor", "/api/m/ozet", 200),
    ("hemsire", "/api/m/hastalar", 200),
    ("admin", "/api/m/sistem", 200),
    ("admin", "/api/m/kullanicilar", 200),
])
def test_role_matrix(ctx, role, path, status):
    client, _ = ctx
    response = client.get(path, headers=_login(client, role))
    assert response.status_code == status
    if status == 403:
        assert response.get_json()["kod"] == "yetki_yok"


def test_clinical_payloads(ctx):
    client, ids = ctx
    headers = _login(client, "doktor")
    assert client.get("/api/m/ozet", headers=headers).get_json()["toplam_dosya"] == 3
    patients = client.get("/api/m/hastalar", headers=headers).get_json()["hastalar"]
    assert [p["ad"] for p in patients] == ["Ayşe Kaya", "Boş Dosya", "İsmail Işık"]
    detail = client.get(f"/api/m/hastalar/{ids['ayse']}", headers=headers).get_json()
    assert detail["dosya_no"] == "#0001"
    notes = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?limit=2", headers=headers).get_json()
    assert notes["sonraki"] == ids["v2"]
    rest = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?limit=2&once={notes['sonraki']}", headers=headers)
    assert rest.get_json()["sonraki"] is None


def test_unknown_patient_is_404(ctx):
    client, _ = ctx
    headers = _login(client, "doktor")
    assert client.get("/api/m/hastalar/999", headers=headers).get_json()["kod"] == "dosya_yok"
    assert client.get("/api/m/hastalar/999/notlar", headers=headers).status_code == 404


@pytest.mark.parametrize("query", ["once=abc", "limit=xyz"])
def test_notes_bad_params_are_400(ctx, query):
    client, ids = ctx
    response = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?{query}", headers=_login(client, "doktor"))
    assert response.status_code == 400


def test_notes_invalid_cursor_is_400(ctx):
    client, ids = ctx
    response = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?once={ids['v5']}", headers=_login(client, "doktor"))
    assert response.status_code == 400
    assert response.get_json()["kod"] == "gecersiz_imlec"


def test_limit_is_clamped(ctx):
    client, ids = ctx
    response = client.get(f"/api/m/hastalar/{ids['ayse']}/notlar?limit=0", headers=_login(client, "doktor"))
    assert len(response.get_json()["notlar"]) == 1


def test_admin_payloads(ctx):
    client, _ = ctx
    headers = _login(client, "admin")
    system = client.get("/api/m/sistem", headers=headers).get_json()
    assert system["tablolar"]["kullanici"] == 3
    assert system["semptom_indeksi"] is True and system["ollama"] is False
    users = client.get("/api/m/kullanicilar", headers=headers).get_json()["kullanicilar"]
    assert [u["rol"] for u in users] == ["doktor", "hemsire", "admin"]
    assert all("sifre_hash" not in u for u in users)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mobile_endpoints.py -v`
Expected: FAIL with `ImportError: cannot import name 'create_mobile_blueprint'`

- [ ] **Step 3: Write minimal implementation**

`trsm/mobile_api/blueprint.py`:

```python
"""Kartela mobil uygulamasının /api/m uç noktaları."""
from contextlib import closing
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Blueprint, g, jsonify, request

from trsm.db import create_schema, get_connection
from trsm.mobile_api import queries
from trsm.mobile_api.auth import issue_token, make_serializer, read_token
from trsm.mobile_api.users import authenticate, get_user, list_users

CLINICAL_ROLES = ("doktor", "hemsire")
DEFAULT_NOTE_LIMIT = 20
MAX_NOTE_LIMIT = 50


def _error(status, code, message):
    return jsonify({"hata": message, "kod": code}), status


def _public(user):
    return {
        "id": user["id"],
        "kullanici_adi": user["kullanici_adi"],
        "ad_soyad": user["ad_soyad"],
        "rol": user["rol"],
        "google_bagli": user["google_sub"] is not None,
    }


def _int_arg(name, default):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)  # ValueError çağıranda 400'e çevrilir


def create_mobile_blueprint(db_path, secret_key, *, confidence_threshold=90, today=date.today,
                            status_extra=lambda: {}):
    db_path = Path(db_path)
    serializer = make_serializer(secret_key)
    with closing(get_connection(db_path)) as conn:
        create_schema(conn)
    bp = Blueprint("mobile_api", __name__, url_prefix="/api/m")

    def connect():
        return closing(get_connection(db_path))

    def requires(*roles):
        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                header = request.headers.get("Authorization", "")
                token = header[len("Bearer "):] if header.startswith("Bearer ") else ""
                user_id = read_token(serializer, token) if token else None
                user = None
                if user_id is not None:
                    with connect() as conn:
                        user = get_user(conn, user_id)
                if user is None:
                    return _error(401, "oturum_gecersiz", "Oturum geçersiz ya da süresi doldu.")
                if roles and user["rol"] not in roles:
                    return _error(403, "yetki_yok", "Bu alan rolünüze kapalı.")
                g.mobil_kullanici = user
                return view(*args, **kwargs)
            return wrapper
        return decorator

    @bp.get("/saglik")
    def health():
        return jsonify({"durum": "ok"})

    @bp.post("/giris")
    def login():
        body = request.get_json(silent=True) or {}
        username = str(body.get("kullanici_adi") or "").strip()
        password = str(body.get("sifre") or "")
        if not username or not password:
            return _error(400, "eksik_bilgi", "Kullanıcı adı ve şifre gerekli.")
        with connect() as conn:
            user = authenticate(conn, username, password)
        if user is None:
            return _error(401, "hatali_giris", "Kullanıcı adı ya da şifre hatalı.")
        return jsonify({"token": issue_token(serializer, user["id"]), "kullanici": _public(user)})

    @bp.get("/ben")
    @requires()
    def me():
        return jsonify(_public(g.mobil_kullanici))

    @bp.get("/ozet")
    @requires(*CLINICAL_ROLES)
    def overview():
        with connect() as conn:
            return jsonify(queries.summary(conn, confidence_threshold))

    @bp.get("/hastalar")
    @requires(*CLINICAL_ROLES)
    def patients():
        with connect() as conn:
            return jsonify({"hastalar": queries.list_patients(conn, today())})

    @bp.get("/hastalar/<int:patient_id>")
    @requires(*CLINICAL_ROLES)
    def patient(patient_id):
        with connect() as conn:
            detail = queries.patient_detail(conn, patient_id, today(), confidence_threshold)
        if detail is None:
            return _error(404, "dosya_yok", "Dosya bulunamadı.")
        return jsonify(detail)

    @bp.get("/hastalar/<int:patient_id>/notlar")
    @requires(*CLINICAL_ROLES)
    def notes(patient_id):
        try:
            before_id = _int_arg("once", None)
            limit = min(MAX_NOTE_LIMIT, max(1, _int_arg("limit", DEFAULT_NOTE_LIMIT)))
        except ValueError:
            return _error(400, "gecersiz_parametre", "Sayfalama parametreleri sayı olmalı.")
        with connect() as conn:
            if conn.execute("SELECT 1 FROM hasta WHERE id = ?", (patient_id,)).fetchone() is None:
                return _error(404, "dosya_yok", "Dosya bulunamadı.")
            try:
                page = queries.patient_notes(conn, patient_id, confidence_threshold, before_id, limit)
            except ValueError:
                return _error(400, "gecersiz_imlec", "Sayfalama imleci bu dosyaya ait değil.")
        return jsonify(page)

    @bp.get("/sistem")
    @requires("admin")
    def system():
        with connect() as conn:
            status = queries.system_status(conn, db_path)
        return jsonify({**status, **status_extra()})

    @bp.get("/kullanicilar")
    @requires("admin")
    def users():
        with connect() as conn:
            return jsonify({"kullanicilar": [_public(u) for u in list_users(conn)]})

    return bp
```

`trsm/mobile_api/__init__.py` içeriğini değiştir:

```python
"""Kartela mobil uygulaması için JSON API."""
from trsm.mobile_api.blueprint import create_mobile_blueprint

__all__ = ["create_mobile_blueprint"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mobile_endpoints.py tests/test_mobile_queries.py tests/test_mobile_users.py tests/test_mobile_highlights.py -v`
Expected: tümü geçer

- [ ] **Step 5: Commit**

```bash
git add trsm/mobile_api/__init__.py trsm/mobile_api/blueprint.py tests/test_mobile_endpoints.py
git commit -m "feat(mobil-api): rol korumalı /api/m uç noktaları"
```

---

### Task 6: Demo sunucusuna bağlama, ağ erişimi ve dokümantasyon

**Files:**
- Modify: `demo_server.py` (import bloğu, `app = Flask(...)` sonrası, `__main__` bloğu)
- Modify: `README.md` (yeni bölüm)
- Modify: `.gitignore` zaten `data/mobile_secret.key` içeriyor (spec commit'inde eklendi) — kontrol et.

**Interfaces:**
- Consumes: `create_mobile_blueprint`, `load_or_create_secret`.

- [ ] **Step 1: `demo_server.py` import bloğuna ekle** (`from trsm.runtime_paths import runtime_data_paths` satırının altına)

```python
from trsm.mobile_api import create_mobile_blueprint
from trsm.mobile_api.auth import load_or_create_secret
```

- [ ] **Step 2: `app = Flask(__name__, static_folder=None)` satırının hemen altına ekle**

```python
app.register_blueprint(create_mobile_blueprint(
    DB_PATH,
    load_or_create_secret(PATHS["data_dir"] / "mobile_secret.key", os.environ),
    confidence_threshold=GUVEN_ESIGI,
    status_extra=lambda: {
        "semptom_indeksi": INDEX_PATH.exists(),
        "ollama": qwen_status("qwen2.5:3b")["kullanilabilir"],
    },
))
```

- [ ] **Step 3: `__main__` bloğundaki `app.run(...)` satırını değiştir**

```python
    app.run(host=os.getenv("TRSM_HOST", "127.0.0.1"), port=SERVER_PORT, debug=False)
```

- [ ] **Step 4: `README.md` sonuna ekle**

````markdown
## Mobil uygulama (Kartela)

Sunucu tarafı `demo_server.py` içinde `/api/m` önekiyle çalışır. İlk kurulumda
demo hesaplarını oluşturun (varsa dokunmaz):

```bash
uv run python scripts/seed_mobile_users.py
```

Demo hesapları: `doktor` / `kartela-doktor`, `hemsire` / `kartela-hemsire`,
`admin` / `kartela-admin` (şifreler `TRSM_SEED_PASSWORD_<ROL>` ile değiştirilebilir).

Telefonun erişebilmesi için sunucuyu yerel ağa açın (yalnızca güvenilir Wi-Fi):

```bash
TRSM_HOST=0.0.0.0 uv run python demo_server.py
```

Mobil uygulama `mobile/` klasöründedir; ayrıntılar `mobile/README.md`.
````

- [ ] **Step 5: Duman testi — sunucu gerçek DB ile açılıyor mu**

Run (ana çalışma ağacındaki veriler symlink'lenmişse; değilse Task 17'ye bırak ve bunu not et):
```bash
uv run python scripts/seed_mobile_users.py
TRSM_HOST=127.0.0.1 uv run python demo_server.py &
sleep 25
curl -s http://127.0.0.1:8765/api/m/saglik
TOKEN=$(curl -s -X POST http://127.0.0.1:8765/api/m/giris -H 'Content-Type: application/json' -d '{"kullanici_adi":"doktor","sifre":"kartela-doktor"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8765/api/m/ozet | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["toplam_dosya"], d["toplam_not"])'
kill %1
```
Expected: `{"durum":"ok"}` ve `434 41676`. Hasta satırlarını terminale dökme; yalnızca sayıları yazdır.

- [ ] **Step 6: Full suite**

Run: `uv run pytest -q`
Expected: tümü geçer

- [ ] **Step 7: Commit**

```bash
git add demo_server.py README.md
git commit -m "feat(mobil-api): blueprint'i demo sunucusuna bağla, TRSM_HOST ile ağ erişimi"
```

---

### Task 7: Expo projesi, bağımlılıklar, test altyapısı ve tema token'ları

**Files:**
- Create: `mobile/` (create-expo-app), `mobile/app.json` (düzenle), `mobile/package.json` (düzenle), `mobile/tsconfig.json` (düzenle), `mobile/.env.example`, `mobile/README.md`
- Create: `mobile/src/theme/tokens.ts`, `mobile/src/theme/ThemeProvider.tsx`, `mobile/src/storage/prefs.ts`
- Test: `mobile/src/theme/__tests__/tokens.test.ts`

**Interfaces:**
- Produces:
  - `type ThemeName = 'light' | 'dark'`, `type ThemePreference = 'sistem' | 'acik' | 'koyu'`
  - `palettes: Record<ThemeName, Colors>`; `Colors` anahtarları: `bg, surface, surfaceRaised, ink, inkMuted, line, deep, onDeep, primary, primarySoft, accent, onAccent, accentSoft, highlight, highlightInk, danger, dangerSoft`
  - `space`, `radius`, `fontFamily`, `typeScale`, `TypeVariant`
  - `resolveTheme(pref: ThemePreference, system: 'light' | 'dark' | null | undefined): ThemeName`
  - `useTheme(): { colors: Colors; name: ThemeName; preference: ThemePreference; setPreference(p): void }`
  - `prefs`: `getThemePreference()`, `setThemePreference(p)`, `getServerUrl()`, `setServerUrl(u)`, `getDrafts()`, `setDrafts(d)` (AsyncStorage)

- [ ] **Step 1: Projeyi oluştur ve bağımlılıkları kur**

```bash
cd <worktree-kökü>
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
npx expo install expo-router react-native-safe-area-context react-native-screens expo-linking expo-constants expo-status-bar expo-system-ui \
  react-native-reanimated react-native-worklets react-native-svg expo-secure-store @react-native-async-storage/async-storage \
  expo-image-picker expo-file-system @react-native-community/datetimepicker @shopify/flash-list expo-font expo-haptics \
  @expo-google-fonts/geist @expo-google-fonts/geist-mono
npm install @tanstack/react-query lucide-react-native
npx expo install jest-expo jest @types/jest -- --save-dev
npm install --save-dev @testing-library/react-native
rm -f App.tsx index.ts
npx expo-doctor
```
Expected: `expo-doctor` uyumsuz paket raporlamaz (rapor ederse önerdiği `npx expo install --fix` komutunu çalıştır).

- [ ] **Step 2: `mobile/package.json` düzenle** — `"main"` alanını ve test betiğini/jest yapılandırmasını ayarla (diğer alanlara dokunma)

```json
{
  "main": "expo-router/entry",
  "scripts": {
    "start": "expo start",
    "test": "jest"
  },
  "jest": {
    "preset": "jest-expo",
    "moduleNameMapper": { "^@/(.*)$": "<rootDir>/src/$1" }
  }
}
```

- [ ] **Step 3: `mobile/tsconfig.json`** — `compilerOptions` içine ekle

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

- [ ] **Step 4: `mobile/app.json`** — `expo` nesnesinde şu alanları ayarla

```json
{
  "expo": {
    "name": "Kartela",
    "slug": "kartela",
    "scheme": "kartela",
    "userInterfaceStyle": "automatic",
    "plugins": [
      "expo-router",
      "expo-secure-store",
      [
        "expo-image-picker",
        {
          "photosPermission": "Rapor sayfalarını eklemek için galeriye erişim gerekir.",
          "cameraPermission": "Rapor fotoğrafı çekmek için kamera gerekir."
        }
      ]
    ]
  }
}
```

- [ ] **Step 5: `mobile/.env.example`**

```
# Sunucunun bilgisayardaki yerel ağ adresi (aynı Wi-Fi). Kopyalayın: cp .env.example .env
EXPO_PUBLIC_API_URL=http://192.168.1.20:8765
```

`mobile/.gitignore` dosyasında `.env` satırı yoksa ekle (`.env*.local` create-expo-app ile gelir; `.env` ayrıca eklenmeli).

- [ ] **Step 6: Write the failing test** — `mobile/src/theme/__tests__/tokens.test.ts`

```ts
import { palettes, resolveTheme } from '../tokens';

describe('resolveTheme', () => {
  it('sistem tercihinde cihaz moduna uyar, bilinmiyorsa açık', () => {
    expect(resolveTheme('sistem', 'dark')).toBe('dark');
    expect(resolveTheme('sistem', 'light')).toBe('light');
    expect(resolveTheme('sistem', null)).toBe('light');
    expect(resolveTheme('sistem', undefined)).toBe('light');
  });

  it('açık ve koyu tercih cihazı geçersiz kılar', () => {
    expect(resolveTheme('acik', 'dark')).toBe('light');
    expect(resolveTheme('koyu', 'light')).toBe('dark');
  });
});

describe('palettes', () => {
  it('iki temada da aynı token anahtarları var', () => {
    expect(Object.keys(palettes.dark).sort()).toEqual(Object.keys(palettes.light).sort());
  });

  it('spec §4.2 değerleri', () => {
    expect(palettes.light.primary).toBe('#1E8C6E');
    expect(palettes.dark.primary).toBe('#34B48F');
    expect(palettes.light.deep).toBe('#15181D');
    expect(palettes.light.accent).toBe('#9ED9C3');
    expect(palettes.light.highlight).toBe('#F3E08A');
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd mobile && npx jest src/theme`
Expected: FAIL — `Cannot find module '../tokens'`

- [ ] **Step 8: Write implementation** — `mobile/src/theme/tokens.ts`

```ts
export type ThemeName = 'light' | 'dark';
export type ThemePreference = 'sistem' | 'acik' | 'koyu';

const light = {
  bg: '#F3F4F4',
  surface: '#FFFFFF',
  surfaceRaised: '#FFFFFF',
  ink: '#111418',
  inkMuted: '#5F656D',
  line: '#E4E6E9',
  deep: '#15181D',
  onDeep: '#FFFFFF',
  primary: '#1E8C6E',
  primarySoft: '#DCEFE7',
  accent: '#9ED9C3',
  onAccent: '#15181D',
  accentSoft: '#E2F4EC',
  highlight: '#F3E08A',
  highlightInk: '#111418',
  danger: '#E5484D',
  dangerSoft: '#FDECEC',
};

export type Colors = Record<keyof typeof light, string>;

const dark: Colors = {
  bg: '#0E1013',
  surface: '#171A1F',
  surfaceRaised: '#1E2228',
  ink: '#ECEFF1',
  inkMuted: '#9AA1A9',
  line: '#262A31',
  deep: '#1B1F25',
  onDeep: '#ECEFF1',
  primary: '#34B48F',
  primarySoft: '#12302A',
  accent: '#9ED9C3',
  onAccent: '#0E1013',
  accentSoft: '#1A3A30',
  highlight: '#E6CF6A',
  highlightInk: '#111418',
  danger: '#FF6369',
  dangerSoft: '#3A1A1C',
};

export const palettes: Record<ThemeName, Colors> = { light, dark };

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32 } as const;
export const radius = { chip: 8, input: 12, card: 18, hero: 22, tab: 22 } as const;

export const fontFamily = {
  400: 'Geist_400Regular',
  500: 'Geist_500Medium',
  600: 'Geist_600SemiBold',
  700: 'Geist_700Bold',
  800: 'Geist_800ExtraBold',
  mono: 'GeistMono_400Regular',
  monoMedium: 'GeistMono_500Medium',
} as const;

export type FontWeight = 400 | 500 | 600 | 700 | 800;

export const typeScale = {
  display: { fontSize: 44, lineHeight: 48, weight: 800 as FontWeight, letterSpacing: -1.5 },
  title: { fontSize: 24, lineHeight: 30, weight: 800 as FontWeight, letterSpacing: -0.5 },
  heading: { fontSize: 18, lineHeight: 24, weight: 700 as FontWeight, letterSpacing: -0.3 },
  body: { fontSize: 15, lineHeight: 21, weight: 500 as FontWeight, letterSpacing: 0 },
  bodySmall: { fontSize: 13, lineHeight: 18, weight: 500 as FontWeight, letterSpacing: 0 },
  label: { fontSize: 11, lineHeight: 14, weight: 600 as FontWeight, letterSpacing: 0.2 },
  mono: { fontSize: 12, lineHeight: 19, weight: 400 as FontWeight, letterSpacing: 0 },
} as const;

export type TypeVariant = keyof typeof typeScale;

export function resolveTheme(
  preference: ThemePreference,
  system: 'light' | 'dark' | null | undefined,
): ThemeName {
  if (preference === 'acik') return 'light';
  if (preference === 'koyu') return 'dark';
  return system === 'dark' ? 'dark' : 'light';
}
```

`mobile/src/storage/prefs.ts`:

```ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { ThemePreference } from '@/theme/tokens';

const KEYS = {
  theme: 'kartela.tema',
  serverUrl: 'kartela.sunucu',
  drafts: 'kartela.taslaklar',
} as const;

export type DraftPatient = {
  id: string;
  adSoyad: string;
  cinsiyet: 'Kadın' | 'Erkek' | null;
  dogumTarihi: string | null; // YYYY-MM-DD
  tcKimlik: string | null;
  sayfalar: string[]; // uygulama dizinindeki dosya URI'leri, sıralı
  olusturma: string; // ISO
};

async function readJson<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export const prefs = {
  async getThemePreference(): Promise<ThemePreference> {
    const value = await AsyncStorage.getItem(KEYS.theme);
    return value === 'acik' || value === 'koyu' ? value : 'sistem';
  },
  setThemePreference: (value: ThemePreference) => AsyncStorage.setItem(KEYS.theme, value),
  getServerUrl: () => AsyncStorage.getItem(KEYS.serverUrl),
  setServerUrl: (value: string) => AsyncStorage.setItem(KEYS.serverUrl, value),
  getDrafts: () => readJson<DraftPatient[]>(KEYS.drafts, []),
  setDrafts: (drafts: DraftPatient[]) => AsyncStorage.setItem(KEYS.drafts, JSON.stringify(drafts)),
};
```

`mobile/src/theme/ThemeProvider.tsx`:

```tsx
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { prefs } from '@/storage/prefs';
import { palettes, resolveTheme, type Colors, type ThemeName, type ThemePreference } from './tokens';

type ThemeContextValue = {
  colors: Colors;
  name: ThemeName;
  preference: ThemePreference;
  setPreference: (value: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('sistem');

  useEffect(() => {
    prefs.getThemePreference().then(setPreferenceState);
  }, []);

  const value = useMemo<ThemeContextValue>(() => {
    const name = resolveTheme(preference, system);
    return {
      colors: palettes[name],
      name,
      preference,
      setPreference: (next) => {
        setPreferenceState(next);
        prefs.setThemePreference(next);
      },
    };
  }, [preference, system]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme ThemeProvider içinde kullanılmalı');
  return value;
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd mobile && npx jest src/theme`
Expected: 4 passed

- [ ] **Step 10: `mobile/README.md`**

````markdown
# Kartela (mobil)

TRSM arşivindeki hasta dosyalarını doktor ve hemşire için gösteren Expo uygulaması.

## Çalıştırma

1. Bilgisayarda sunucuyu yerel ağa açın (repo kökünde):
   `uv run python scripts/seed_mobile_users.py` ve `TRSM_HOST=0.0.0.0 uv run python demo_server.py`
2. Bilgisayarın yerel IP'sini bulun (macOS: `ipconfig getifaddr en0`).
3. `cp .env.example .env` ve `EXPO_PUBLIC_API_URL`'i `http://<IP>:8765` yapın.
4. `npm install` ve `npx expo start`; telefonda Expo Go ile QR kodu okutun.
   Telefon ve bilgisayar aynı Wi-Fi'da olmalı.

Adres değişirse uygulamada Ayarlar → Sunucu satırından güncelleyebilirsiniz.

Demo hesapları: `doktor` / `kartela-doktor`, `hemsire` / `kartela-hemsire`, `admin` / `kartela-admin`.

## Test

`npm test`
````

- [ ] **Step 11: Commit**

```bash
git add mobile
git commit -m "feat(mobil): Expo iskeleti, tema token'ları ve tercih depolama"
```

---

### Task 8: Saf yardımcılar — TC Kimlik, Türkçe arama, rol sekmeleri, OCR parçalama, biçimlendirme

**Files:**
- Create: `mobile/src/lib/{tcKimlik.ts,turkishSearch.ts,roleTabs.ts,ocrSegments.ts,format.ts}`
- Test: `mobile/src/lib/__tests__/{tcKimlik,turkishSearch,roleTabs,ocrSegments,format}.test.ts`

**Interfaces:**
- Produces:
  - `isValidTcKimlik(value: string): boolean`, `maskTcKimlik(value: string): string`
  - `foldTr(s: string): string`, `matchesQuery(text: string, query: string): boolean`
  - `type Rol = 'admin' | 'doktor' | 'hemsire'`, `type TabName = 'ozet' | 'dosyalar' | 'yeni' | 'sistem' | 'kullanicilar' | 'ayarlar'`, `ALL_TABS: TabName[]`, `tabsForRole(rol): TabName[]`, `homeTab(rol): TabName`, `canViewPatients(rol): boolean`
  - `type Highlight = { bas: number; son: number; tur: 'ilac' | 'belirti' }`, `type Segment = { text: string; tur: 'ilac' | 'belirti' | null }`, `splitHighlights(text: string, highlights: Highlight[]): Segment[]`
  - `formatDate(iso: string | null): string` (`'3 Eyl 2025'` / `'Tarihsiz'`), `formatNumber(n: number): string` (`'41.676'`), `initials(name: string): string` (`'AK'`)

- [ ] **Step 1: Write the failing tests**

`mobile/src/lib/__tests__/tcKimlik.test.ts`:

```ts
import { isValidTcKimlik, maskTcKimlik } from '../tcKimlik';

describe('isValidTcKimlik', () => {
  it('geçerli numarayı kabul eder', () => {
    expect(isValidTcKimlik('10000000146')).toBe(true);
  });
  it.each(['10000000147', '10000000136', '01234567890', '1234', '1000000014a', ''])(
    '%s geçersiz',
    (value) => expect(isValidTcKimlik(value)).toBe(false),
  );
});

describe('maskTcKimlik', () => {
  it('ilk 3 ve son 2 hane görünür', () => {
    expect(maskTcKimlik('10000000146')).toBe('100******46');
  });
  it('11 hane değilse olduğu gibi döner', () => {
    expect(maskTcKimlik('123')).toBe('123');
  });
});
```

`mobile/src/lib/__tests__/turkishSearch.test.ts`:

```ts
import { foldTr, matchesQuery } from '../turkishSearch';

describe('foldTr', () => {
  it('İ → i ve I → ı', () => {
    expect(foldTr('İSMAİL IŞIK')).toBe('ismail ışık');
  });
  it('NFD girdiyi NFC yapar', () => {
    expect(foldTr('Ağrı')).toBe('ağrı');
  });
});

describe('matchesQuery', () => {
  it('Türkçe büyük/küçük harf', () => {
    expect(matchesQuery('İsmail Işık', 'ışı')).toBe(true);
    expect(matchesQuery('İsmail Işık', 'ISMA')).toBe(false); // I → ı, "ısma" yok
    expect(matchesQuery('İsmail Işık', 'İSMA')).toBe(true);
  });
  it('aksansız yazımı da bulur', () => {
    expect(matchesQuery('Ayşe Kaya', 'ayse')).toBe(true);
    expect(matchesQuery('Gül Ağrı', 'gul agri')).toBe(true);
  });
  it('boş sorgu her şeyi eşler', () => {
    expect(matchesQuery('Ayşe', '   ')).toBe(true);
  });
});
```

`mobile/src/lib/__tests__/roleTabs.test.ts`:

```ts
import { canViewPatients, homeTab, tabsForRole } from '../roleTabs';

it('rol → sekmeler (spec §3)', () => {
  expect(tabsForRole('doktor')).toEqual(['ozet', 'dosyalar', 'yeni', 'ayarlar']);
  expect(tabsForRole('hemsire')).toEqual(['ozet', 'dosyalar', 'ayarlar']);
  expect(tabsForRole('admin')).toEqual(['sistem', 'kullanicilar', 'ayarlar']);
});

it('ana sekme ve hasta erişimi', () => {
  expect(homeTab('doktor')).toBe('ozet');
  expect(homeTab('admin')).toBe('sistem');
  expect(canViewPatients('hemsire')).toBe(true);
  expect(canViewPatients('admin')).toBe(false);
});
```

`mobile/src/lib/__tests__/ocrSegments.test.ts`:

```ts
import { splitHighlights } from '../ocrSegments';

it('aralıkları sıralı parçalara böler', () => {
  expect(
    splitHighlights('Depakin devam, uykusuzluk', [
      { bas: 15, son: 25, tur: 'belirti' },
      { bas: 0, son: 7, tur: 'ilac' },
    ]),
  ).toEqual([
    { text: 'Depakin', tur: 'ilac' },
    { text: ' devam, ', tur: null },
    { text: 'uykusuzluk', tur: 'belirti' },
  ]);
});

it('vurgu yoksa tek parça', () => {
  expect(splitHighlights('Kontrol', [])).toEqual([{ text: 'Kontrol', tur: null }]);
});

it('çakışan, sınır dışı ve boş aralıkları atlar', () => {
  expect(
    splitHighlights('abcdef', [
      { bas: 0, son: 3, tur: 'ilac' },
      { bas: 2, son: 4, tur: 'belirti' },
      { bas: 5, son: 99, tur: 'belirti' },
      { bas: 4, son: 4, tur: 'ilac' },
    ]),
  ).toEqual([
    { text: 'abc', tur: 'ilac' },
    { text: 'def', tur: null },
  ]);
});

it('boş metin boş liste', () => {
  expect(splitHighlights('', [])).toEqual([]);
});
```

`mobile/src/lib/__tests__/format.test.ts`:

```ts
import { formatDate, formatNumber, initials } from '../format';

it('tarih', () => {
  expect(formatDate('2025-09-03')).toBe('3 Eyl 2025');
  expect(formatDate(null)).toBe('Tarihsiz');
  expect(formatDate('bozuk')).toBe('Tarihsiz');
});

it('sayı binlik ayracı', () => {
  expect(formatNumber(41676)).toBe('41.676');
  expect(formatNumber(434)).toBe('434');
});

it('baş harfler', () => {
  expect(initials('Ayşe Kaya')).toBe('AK');
  expect(initials('ismail ışık')).toBe('İI');
  expect(initials('Demo')).toBe('D');
  expect(initials('')).toBe('?');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mobile && npx jest src/lib`
Expected: FAIL — modüller bulunamıyor

- [ ] **Step 3: Write implementations**

`mobile/src/lib/tcKimlik.ts`:

```ts
/** T.C. Kimlik No resmi kontrol hanesi algoritması. */
export function isValidTcKimlik(value: string): boolean {
  if (!/^[1-9][0-9]{10}$/.test(value)) return false;
  const d = value.split('').map(Number);
  const odd = d[0] + d[2] + d[4] + d[6] + d[8];
  const even = d[1] + d[3] + d[5] + d[7];
  const tenth = (((odd * 7 - even) % 10) + 10) % 10;
  if (tenth !== d[9]) return false;
  const eleventh = d.slice(0, 10).reduce((sum, n) => sum + n, 0) % 10;
  return eleventh === d[10];
}

export function maskTcKimlik(value: string): string {
  return value.length === 11 ? `${value.slice(0, 3)}******${value.slice(9)}` : value;
}
```

`mobile/src/lib/turkishSearch.ts`:

```ts
const ASCII_MAP: Record<string, string> = { ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u' };

/** Türkçe kurallarıyla küçük harf (İ→i, I→ı) ve NFC. */
export function foldTr(value: string): string {
  return value.normalize('NFC').replace(/İ/g, 'i').replace(/I/g, 'ı').toLowerCase();
}

function asciiFold(value: string): string {
  return value.replace(/[çğıöşü]/g, (ch) => ASCII_MAP[ch]);
}

export function matchesQuery(text: string, query: string): boolean {
  const q = foldTr(query.trim());
  if (!q) return true;
  const t = foldTr(text);
  // Aksansız arama yalnızca sorgu aksansızsa devreye girer; "ISMA" gibi
  // Türkçe büyük I yazımı ı olarak yorumlanmaya devam eder.
  const queryHasTurkish = /[çğıöşü]/.test(q);
  return t.includes(q) || (!queryHasTurkish && asciiFold(t).includes(q));
}
```

> Not: `matchesQuery('İsmail Işık', 'ISMA')` → `q = 'ısma'` (Türkçe karakter içerir) → aksansız dal kapalı → `false`. Testle uyumlu.

`mobile/src/lib/roleTabs.ts`:

```ts
export type Rol = 'admin' | 'doktor' | 'hemsire';
export type TabName = 'ozet' | 'dosyalar' | 'yeni' | 'sistem' | 'kullanicilar' | 'ayarlar';

export const ALL_TABS: TabName[] = ['ozet', 'dosyalar', 'yeni', 'sistem', 'kullanicilar', 'ayarlar'];

const TABS: Record<Rol, TabName[]> = {
  doktor: ['ozet', 'dosyalar', 'yeni', 'ayarlar'],
  hemsire: ['ozet', 'dosyalar', 'ayarlar'],
  admin: ['sistem', 'kullanicilar', 'ayarlar'],
};

export const TAB_LABELS: Record<TabName, string> = {
  ozet: 'Özet',
  dosyalar: 'Dosyalar',
  yeni: 'Yeni',
  sistem: 'Sistem',
  kullanicilar: 'Kullanıcılar',
  ayarlar: 'Ayarlar',
};

export function tabsForRole(rol: Rol): TabName[] {
  return TABS[rol];
}

export function homeTab(rol: Rol): TabName {
  return TABS[rol][0];
}

export function canViewPatients(rol: Rol): boolean {
  return rol === 'doktor' || rol === 'hemsire';
}
```

`mobile/src/lib/ocrSegments.ts`:

```ts
export type Highlight = { bas: number; son: number; tur: 'ilac' | 'belirti' };
export type Segment = { text: string; tur: 'ilac' | 'belirti' | null };

/** Sunucunun UTF-16 aralıklarını (JS string indeksleri) metin parçalarına çevirir. */
export function splitHighlights(text: string, highlights: Highlight[]): Segment[] {
  const valid = [...highlights]
    .filter((h) => h.bas >= 0 && h.son <= text.length && h.son > h.bas)
    .sort((a, b) => a.bas - b.bas);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const h of valid) {
    if (h.bas < cursor) continue; // çakışan aralık
    if (h.bas > cursor) segments.push({ text: text.slice(cursor, h.bas), tur: null });
    segments.push({ text: text.slice(h.bas, h.son), tur: h.tur });
    cursor = h.son;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), tur: null });
  return segments;
}
```

`mobile/src/lib/format.ts`:

```ts
const MONTHS = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];

export function formatDate(iso: string | null): string {
  const match = iso ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso) : null;
  if (!match) return 'Tarihsiz';
  const [, year, month, day] = match;
  const monthIndex = Number(month) - 1;
  if (monthIndex < 0 || monthIndex > 11) return 'Tarihsiz';
  return `${Number(day)} ${MONTHS[monthIndex]} ${year}`;
}

export function formatNumber(value: number): string {
  return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

function upperTr(ch: string): string {
  if (ch === 'i') return 'İ';
  if (ch === 'ı') return 'I';
  return ch.toUpperCase();
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return upperTr(first) + (last ? upperTr(last) : '');
}
```

> `formatNumber` `toLocaleString('tr-TR')` yerine düzenli ifade kullanır; Hermes'te `Intl` yerel verisinin varlığına güvenmemek için.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mobile && npx jest src/lib`
Expected: tümü geçer

- [ ] **Step 5: Commit**

```bash
git add mobile/src/lib
git commit -m "feat(mobil): TC doğrulama, Türkçe arama, rol sekmeleri, OCR parçalama ve biçimlendirme"
```

---

### Task 9: API istemcisi, hata eşleme, sunucu adresi ve oturum

**Files:**
- Create: `mobile/src/api/{types.ts,errors.ts,client.ts,ServerUrlProvider.tsx,hooks.ts}`, `mobile/src/auth/{tokenStore.ts,AuthProvider.tsx,demoAccounts.ts}`
- Test: `mobile/src/api/__tests__/client.test.ts`

**Interfaces:**
- Consumes: `Rol` (Task 8), `prefs` (Task 7)
- Produces:
  - Tipler (`types.ts`): `Kullanici`, `GirisYaniti`, `Ozet`, `HastaOzeti`, `HastaDetayi`, `Not`, `NotSayfasi`, `SistemDurumu` (alanlar Task 4–5 ile birebir)
  - `class ApiError extends Error { kind: ApiErrorKind; status: number | null; kod?: string }`, `type ApiErrorKind = 'yetkisiz' | 'yasak' | 'bulunamadi' | 'istek' | 'sunucu' | 'ag'`
  - `describeError(error: unknown): { title: string; message: string }`
  - `createApiClient(options: { getBaseUrl: () => string; getToken: () => string | null; onUnauthorized: () => void; fetchImpl?: typeof fetch; timeoutMs?: number }): ApiClient` — `ApiClient = { get<T>(path: string): Promise<T>; post<T>(path: string, body: unknown): Promise<T> }`
  - `useServerUrl(): { url: string; setUrl(u: string): Promise<void>; ready: boolean }`
  - `useAuth(): { status: 'yukleniyor' | 'girissiz' | 'girisli' | 'baglanti_hatasi'; user: Kullanici | null; client: ApiClient; login(k: string, s: string): Promise<void>; logout(): Promise<void>; retry(): void }`
  - Hook'lar (`hooks.ts`): `useOzet()`, `useHastalar()`, `useHasta(id)`, `useNotlar(id)` (infinite), `useSistem()`, `useKullanicilar()`
  - `DEMO_ACCOUNTS: { rol: Rol; kullaniciAdi: string; sifre: string; etiket: string }[]`

- [ ] **Step 1: Write the failing test** — `mobile/src/api/__tests__/client.test.ts`

```ts
import { createApiClient } from '../client';
import { ApiError, describeError } from '../errors';

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

type AnyMock = jest.Mock<any, any>;

function makeClient(fetchImpl: AnyMock, token: string | null = 'tok') {
  const onUnauthorized = jest.fn();
  const client = createApiClient({
    getBaseUrl: () => 'http://sunucu:8765/',
    getToken: () => token,
    onUnauthorized,
    fetchImpl: fetchImpl as unknown as typeof fetch,
    timeoutMs: 50,
  });
  return { client, onUnauthorized };
}

it('başarılı GET token ekler ve JSON döner', async () => {
  const fetchImpl: AnyMock = jest.fn(() => jsonResponse(200, { a: 1 }));
  const { client } = makeClient(fetchImpl);
  await expect(client.get('/api/m/ozet')).resolves.toEqual({ a: 1 });
  const [url, init] = fetchImpl.mock.calls[0];
  expect(url).toBe('http://sunucu:8765/api/m/ozet');
  expect(init.headers.Authorization).toBe('Bearer tok');
});

it('token yoksa Authorization başlığı yok', async () => {
  const fetchImpl: AnyMock = jest.fn(() => jsonResponse(200, {}));
  const { client } = makeClient(fetchImpl, null);
  await client.post('/api/m/giris', { kullanici_adi: 'x' });
  expect(fetchImpl.mock.calls[0][1].headers.Authorization).toBeUndefined();
  expect(fetchImpl.mock.calls[0][1].body).toBe('{"kullanici_adi":"x"}');
});

it('401 oturumu kapatır ve yetkisiz hatası verir', async () => {
  const fetchImpl = jest.fn(() => jsonResponse(401, { hata: 'Oturum geçersiz', kod: 'oturum_gecersiz' }));
  const { client, onUnauthorized } = makeClient(fetchImpl);
  await expect(client.get('/api/m/ben')).rejects.toMatchObject({ kind: 'yetkisiz', status: 401 });
  expect(onUnauthorized).toHaveBeenCalledTimes(1);
});

it('giriş uç noktasındaki 401 oturumu kapatmaz', async () => {
  const fetchImpl = jest.fn(() => jsonResponse(401, { hata: 'Hatalı', kod: 'hatali_giris' }));
  const { client, onUnauthorized } = makeClient(fetchImpl);
  await expect(client.post('/api/m/giris', {})).rejects.toMatchObject({ kind: 'yetkisiz', kod: 'hatali_giris' });
  expect(onUnauthorized).not.toHaveBeenCalled();
});

it.each([
  [403, 'yasak'],
  [404, 'bulunamadi'],
  [400, 'istek'],
  [500, 'sunucu'],
])('%i → %s', async (status, kind) => {
  const fetchImpl = jest.fn(() => jsonResponse(status, { hata: 'Mesaj', kod: 'k' }));
  const { client } = makeClient(fetchImpl);
  const error = (await client.get('/x').catch((e) => e)) as ApiError;
  expect(error.kind).toBe(kind);
  expect(error.message).toBe('Mesaj');
});

it('ağ hatası ve zaman aşımı → ag', async () => {
  const failing = jest.fn(() => Promise.reject(new TypeError('Network request failed')));
  await expect(makeClient(failing).client.get('/x')).rejects.toMatchObject({ kind: 'ag', status: null });

  const hanging = jest.fn(
    (_url: string, init: RequestInit) =>
      new Promise((_resolve, reject) => {
        init.signal?.addEventListener('abort', () => reject(new Error('aborted')));
      }),
  );
  await expect(makeClient(hanging).client.get('/x')).rejects.toMatchObject({ kind: 'ag' });
});

it('JSON olmayan hata gövdesi', async () => {
  const fetchImpl = jest.fn(() =>
    Promise.resolve({ ok: false, status: 502, json: () => Promise.reject(new Error('html')) } as Response),
  );
  await expect(makeClient(fetchImpl).client.get('/x')).rejects.toMatchObject({ kind: 'sunucu' });
});

it('describeError kullanıcı dostu başlık verir', () => {
  expect(describeError(new ApiError('ag', null, 'x')).title).toBe('Sunucuya ulaşılamıyor');
  expect(describeError(new ApiError('yasak', 403, 'Bu alan rolünüze kapalı.')).message).toBe('Bu alan rolünüze kapalı.');
  expect(describeError(new Error('?')).title).toBe('Beklenmeyen hata');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && npx jest src/api`
Expected: FAIL — modül bulunamıyor

- [ ] **Step 3: Write implementations**

`mobile/src/api/types.ts`:

```ts
import type { Rol } from '@/lib/roleTabs';
import type { Highlight } from '@/lib/ocrSegments';

export type Kullanici = { id: number; kullanici_adi: string; ad_soyad: string; rol: Rol; google_bagli: boolean };
export type GirisYaniti = { token: string; kullanici: Kullanici };

export type Ozet = {
  toplam_dosya: number;
  toplam_not: number;
  ilacli_not: number;
  yillik_not: { yil: number; sayi: number }[];
  cinsiyet: { erkek: number; kadin: number; bilinmiyor: number };
  en_sik_ilaclar: { ilac: string; sayi: number }[];
  okunmamis_rapor: number;
};

export type HastaOzeti = {
  id: number;
  ad: string;
  cinsiyet: string | null;
  yas: number | null;
  not_sayisi: number;
  son_ziyaret: string | null;
  yogunluk: number[];
  okunmamis: boolean;
};

export type HastaDetayi = {
  id: number;
  ad: string;
  cinsiyet: string | null;
  yas: number | null;
  dosya_no: string;
  tc_maskeli: string | null;
  not_sayisi: number;
  ilac_sayisi: number;
  ilk_kayit: string | null;
  son_kayit: string | null;
};

export type Not = {
  id: number;
  tarih: string | null;
  sayfa_no: number | null;
  metin: string;
  vurgular: Highlight[];
  ilaclar: { ad: string; doz: string | null; siklik: string | null }[];
  belirti_sayisi: number;
  gorsel_var: boolean;
};

export type NotSayfasi = { notlar: Not[]; sonraki: number | null };

export type SistemDurumu = {
  tablolar: Record<string, number>;
  db_boyutu_mb: number;
  semptom_indeksi: boolean;
  ollama: boolean;
};
```

`mobile/src/api/errors.ts`:

```ts
export type ApiErrorKind = 'yetkisiz' | 'yasak' | 'bulunamadi' | 'istek' | 'sunucu' | 'ag';

export class ApiError extends Error {
  constructor(
    public kind: ApiErrorKind,
    public status: number | null,
    message: string,
    public kod?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function kindForStatus(status: number): ApiErrorKind {
  if (status === 401) return 'yetkisiz';
  if (status === 403) return 'yasak';
  if (status === 404) return 'bulunamadi';
  if (status >= 400 && status < 500) return 'istek';
  return 'sunucu';
}

const TITLES: Record<ApiErrorKind, string> = {
  ag: 'Sunucuya ulaşılamıyor',
  yetkisiz: 'Oturum sona erdi',
  yasak: 'Erişim yok',
  bulunamadi: 'Bulunamadı',
  istek: 'İstek hatalı',
  sunucu: 'Sunucu hatası',
};

export function describeError(error: unknown): { title: string; message: string } {
  if (error instanceof ApiError) {
    const fallback =
      error.kind === 'ag'
        ? 'Telefon ve bilgisayarın aynı Wi-Fi ağında olduğundan ve sunucunun açık olduğundan emin olun.'
        : 'Lütfen tekrar deneyin.';
    return { title: TITLES[error.kind], message: error.kind === 'ag' ? fallback : error.message || fallback };
  }
  return { title: 'Beklenmeyen hata', message: 'Lütfen tekrar deneyin.' };
}
```

`mobile/src/api/client.ts`:

```ts
import { ApiError, kindForStatus } from './errors';

export type ApiClient = {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body: unknown): Promise<T>;
};

type Options = {
  getBaseUrl: () => string;
  getToken: () => string | null;
  onUnauthorized: () => void;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
};

const LOGIN_PATH = '/api/m/giris';

export function createApiClient({
  getBaseUrl,
  getToken,
  onUnauthorized,
  fetchImpl = fetch,
  timeoutMs = 10_000,
}: Options): ApiClient {
  async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const token = getToken();
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let response: Response;
    try {
      response = await fetchImpl(getBaseUrl().replace(/\/+$/, '') + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
    } catch {
      throw new ApiError('ag', null, 'Sunucuya ulaşılamıyor.');
    } finally {
      clearTimeout(timer);
    }
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (response.ok) return payload as T;
    const data = (payload ?? {}) as { hata?: string; kod?: string };
    const error = new ApiError(kindForStatus(response.status), response.status, data.hata ?? '', data.kod);
    if (error.kind === 'yetkisiz' && path !== LOGIN_PATH) onUnauthorized();
    throw error;
  }

  return {
    get: (path) => request('GET', path),
    post: (path, body) => request('POST', path, body),
  };
}
```

`mobile/src/auth/tokenStore.ts`:

```ts
import * as SecureStore from 'expo-secure-store';

const KEY = 'kartela.oturum';

export const tokenStore = {
  get: () => SecureStore.getItemAsync(KEY),
  set: (token: string) => SecureStore.setItemAsync(KEY, token),
  clear: () => SecureStore.deleteItemAsync(KEY),
};
```

`mobile/src/auth/demoAccounts.ts`:

```ts
import type { Rol } from '@/lib/roleTabs';

/** scripts/seed_mobile_users.py varsayılanlarıyla aynı; yalnızca __DEV__'de gösterilir. */
export const DEMO_ACCOUNTS: { rol: Rol; kullaniciAdi: string; sifre: string; etiket: string }[] = [
  { rol: 'doktor', kullaniciAdi: 'doktor', sifre: 'kartela-doktor', etiket: 'Doktor' },
  { rol: 'hemsire', kullaniciAdi: 'hemsire', sifre: 'kartela-hemsire', etiket: 'Hemşire' },
  { rol: 'admin', kullaniciAdi: 'admin', sifre: 'kartela-admin', etiket: 'Admin' },
];
```

`mobile/src/api/ServerUrlProvider.tsx`:

```tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { prefs } from '@/storage/prefs';

const DEFAULT_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8765';

type Value = { url: string; ready: boolean; setUrl: (url: string) => Promise<void> };
const ServerUrlContext = createContext<Value | null>(null);

export function ServerUrlProvider({ children }: { children: ReactNode }) {
  const [url, setUrlState] = useState(DEFAULT_URL);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    prefs.getServerUrl().then((saved) => {
      if (saved) setUrlState(saved);
      setReady(true);
    });
  }, []);

  const setUrl = async (next: string) => {
    const cleaned = next.trim().replace(/\/+$/, '');
    setUrlState(cleaned);
    await prefs.setServerUrl(cleaned);
  };

  return <ServerUrlContext.Provider value={{ url, ready, setUrl }}>{children}</ServerUrlContext.Provider>;
}

export function useServerUrl(): Value {
  const value = useContext(ServerUrlContext);
  if (!value) throw new Error('useServerUrl ServerUrlProvider içinde kullanılmalı');
  return value;
}
```

`mobile/src/auth/AuthProvider.tsx`:

```tsx
import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createApiClient, type ApiClient } from '@/api/client';
import { ApiError } from '@/api/errors';
import { useServerUrl } from '@/api/ServerUrlProvider';
import type { GirisYaniti, Kullanici } from '@/api/types';
import { tokenStore } from './tokenStore';

type Status = 'yukleniyor' | 'girissiz' | 'girisli' | 'baglanti_hatasi';
type Value = {
  status: Status;
  user: Kullanici | null;
  client: ApiClient;
  login: (kullaniciAdi: string, sifre: string) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => void;
};

const AuthContext = createContext<Value | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { url, ready } = useServerUrl();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>('yukleniyor');
  const [user, setUser] = useState<Kullanici | null>(null);
  const [attempt, setAttempt] = useState(0);
  const tokenRef = useRef<string | null>(null);
  const urlRef = useRef(url);
  urlRef.current = url;

  const logout = useCallback(async () => {
    tokenRef.current = null;
    await tokenStore.clear();
    queryClient.clear();
    setUser(null);
    setStatus('girissiz');
  }, [queryClient]);

  const client = useMemo(
    () =>
      createApiClient({
        getBaseUrl: () => urlRef.current,
        getToken: () => tokenRef.current,
        onUnauthorized: () => {
          void logout();
        },
      }),
    [logout],
  );

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    (async () => {
      setStatus('yukleniyor');
      const token = await tokenStore.get();
      if (!token) {
        if (!cancelled) setStatus('girissiz');
        return;
      }
      tokenRef.current = token;
      try {
        const me = await client.get<Kullanici>('/api/m/ben');
        if (!cancelled) {
          setUser(me);
          setStatus('girisli');
        }
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.kind === 'yetkisiz') return; // logout zaten çağrıldı
        setStatus('baglanti_hatasi');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, client, attempt]);

  const login = useCallback(
    async (kullaniciAdi: string, sifre: string) => {
      const result = await client.post<GirisYaniti>('/api/m/giris', { kullanici_adi: kullaniciAdi, sifre });
      tokenRef.current = result.token;
      await tokenStore.set(result.token);
      setUser(result.kullanici);
      setStatus('girisli');
    },
    [client],
  );

  const value = useMemo<Value>(
    () => ({ status, user, client, login, logout, retry: () => setAttempt((n) => n + 1) }),
    [status, user, client, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Value {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth AuthProvider içinde kullanılmalı');
  return value;
}
```

`mobile/src/api/hooks.ts`:

```ts
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useAuth } from '@/auth/AuthProvider';
import type { HastaDetayi, HastaOzeti, Kullanici, NotSayfasi, Ozet, SistemDurumu } from './types';

function useUserKey() {
  const { user } = useAuth();
  return user?.id ?? 0;
}

export function useOzet() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({ queryKey: ['ozet', uid], queryFn: () => client.get<Ozet>('/api/m/ozet') });
}

export function useHastalar() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({
    queryKey: ['hastalar', uid],
    queryFn: async () => (await client.get<{ hastalar: HastaOzeti[] }>('/api/m/hastalar')).hastalar,
  });
}

export function useHasta(id: number) {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({
    queryKey: ['hasta', uid, id],
    queryFn: () => client.get<HastaDetayi>(`/api/m/hastalar/${id}`),
    enabled: Number.isFinite(id),
  });
}

export function useNotlar(id: number) {
  const { client } = useAuth();
  const uid = useUserKey();
  return useInfiniteQuery({
    queryKey: ['notlar', uid, id],
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) =>
      client.get<NotSayfasi>(`/api/m/hastalar/${id}/notlar?limit=20${pageParam ? `&once=${pageParam}` : ''}`),
    getNextPageParam: (last) => last.sonraki,
    enabled: Number.isFinite(id),
  });
}

export function useSistem() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({ queryKey: ['sistem', uid], queryFn: () => client.get<SistemDurumu>('/api/m/sistem') });
}

export function useKullanicilar() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({
    queryKey: ['kullanicilar', uid],
    queryFn: async () => (await client.get<{ kullanicilar: Kullanici[] }>('/api/m/kullanicilar')).kullanicilar,
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && npx jest src/api`
Expected: tümü geçer

- [ ] **Step 5: Tip kontrolü**

Run: `cd mobile && npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 6: Commit**

```bash
git add mobile/src/api mobile/src/auth
git commit -m "feat(mobil): API istemcisi, hata eşleme, sunucu adresi ve oturum yönetimi"
```

---

### Task 10: Temel UI bileşenleri

**Files:**
- Create: `mobile/src/ui/{Text.tsx,Card.tsx,HeroCard.tsx,Button.tsx,Chip.tsx,FilterChips.tsx,SegmentedControl.tsx,SearchField.tsx,FormField.tsx,Skeleton.tsx,EmptyState.tsx,ErrorState.tsx,Stamp.tsx,PressableScale.tsx,Screen.tsx,index.ts}`
- Test: `mobile/src/ui/__tests__/Text.test.tsx`

**Interfaces:**
- Consumes: `useTheme`, token'lar (Task 7), `describeError` (Task 9)
- Produces (hepsi `@/ui` üzerinden dışa aktarılır):
  - `Text({ variant?: TypeVariant; color?: keyof Colors; weight?: FontWeight; style?; ...TextProps })`
  - `Card({ style?, children })`, `HeroCard({ style?, children })`
  - `PressableScale({ onPress, disabled?, style?, children })` — basınca 0.97 ölçek
  - `Button({ title, onPress, variant?: 'primary' | 'deep' | 'ghost'; disabled?; loading?; icon? })`
  - `Chip({ label, tone?: 'neutral' | 'primary' | 'highlight' | 'danger' | 'accent' })`
  - `FilterChips<T extends string>({ options: { value: T; label: string }[]; value: T; onChange(v: T) })`
  - `SegmentedControl<T extends string>({ options, value, onChange })`
  - `SearchField({ value, onChangeText, placeholder })`
  - `FormField({ label, error?, ...TextInputProps })`
  - `Skeleton({ width?, height, radius? })`
  - `EmptyState({ title, message, icon? })`, `ErrorState({ error: unknown; onRetry?; extra? })`
  - `Stamp({ title, subtitle })`
  - `Screen({ children, scroll?: boolean; refreshing?; onRefresh?; padded? })` — güvenli alan + `bg` zemin + alt tab bar boşluğu

- [ ] **Step 0: Jest kurulum dosyası** — `mobile/jest.setup.js`

```js
require('react-native-reanimated').setUpTests();
require('@testing-library/react-native/extend-expect');
```

`mobile/package.json` → `jest` nesnesine ekle: `"setupFilesAfterEnv": ["./jest.setup.js"]`.

- [ ] **Step 1: Write the failing test** — `mobile/src/ui/__tests__/Text.test.tsx`

```tsx
import { render } from '@testing-library/react-native';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { palettes } from '@/theme/tokens';
import { Text } from '../Text';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

it('varyant yazı ailesini ve tema rengini uygular', () => {
  const { getByText } = render(
    <ThemeProvider>
      <Text variant="mono" color="inkMuted">
        Depakin
      </Text>
      <Text variant="title">Başlık</Text>
    </ThemeProvider>,
  );
  const mono = getByText('Depakin');
  expect(mono).toHaveStyle({ fontFamily: 'GeistMono_400Regular', color: palettes.light.inkMuted });
  expect(getByText('Başlık')).toHaveStyle({ fontFamily: 'Geist_800ExtraBold', fontSize: 24 });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && npx jest src/ui`
Expected: FAIL — `Cannot find module '../Text'`

- [ ] **Step 3: Write implementations**

`mobile/src/ui/Text.tsx`:

```tsx
import { Text as RNText, type TextProps } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, typeScale, type Colors, type FontWeight, type TypeVariant } from '@/theme/tokens';

type Props = TextProps & { variant?: TypeVariant; color?: keyof Colors; weight?: FontWeight };

export function Text({ variant = 'body', color = 'ink', weight, style, ...rest }: Props) {
  const { colors } = useTheme();
  const scale = typeScale[variant];
  const family = variant === 'mono' ? fontFamily.mono : fontFamily[weight ?? scale.weight];
  return (
    <RNText
      maxFontSizeMultiplier={1.3}
      {...rest}
      style={[
        {
          fontFamily: family,
          fontSize: scale.fontSize,
          lineHeight: scale.lineHeight,
          letterSpacing: scale.letterSpacing,
          color: colors[color],
        },
        style,
      ]}
    />
  );
}
```

`mobile/src/ui/PressableScale.tsx`:

```tsx
import type { ReactNode } from 'react';
import { Pressable, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = { onPress?: () => void; disabled?: boolean; style?: StyleProp<ViewStyle>; children: ReactNode; accessibilityLabel?: string };

export function PressableScale({ onPress, disabled, style, children, accessibilityLabel }: Props) {
  const scale = useSharedValue(1);
  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <AnimatedPressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      disabled={disabled}
      onPress={onPress}
      onPressIn={() => (scale.value = withSpring(0.97, { damping: 18, stiffness: 400 }))}
      onPressOut={() => (scale.value = withSpring(1, { damping: 14, stiffness: 300 }))}
      style={[style, animated]}
    >
      {children}
    </AnimatedPressable>
  );
}
```

`mobile/src/ui/Card.tsx`:

```tsx
import type { ReactNode } from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';

export function Card({ style, children }: { style?: StyleProp<ViewStyle>; children: ReactNode }) {
  const { colors, name } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: colors.surface,
          borderRadius: radius.card,
          padding: 14,
          borderWidth: name === 'dark' ? 1 : 0,
          borderColor: colors.line,
          shadowColor: '#0D1B24',
          shadowOpacity: name === 'light' ? 0.06 : 0,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: 4 },
          elevation: name === 'light' ? 2 : 0,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}
```

`mobile/src/ui/HeroCard.tsx`:

```tsx
import type { ReactNode } from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';

/** `deep` zeminli vurgu kartı; sağ üstte yarı saydam ana renk halkası. */
export function HeroCard({ style, children }: { style?: StyleProp<ViewStyle>; children: ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={[{ backgroundColor: colors.deep, borderRadius: radius.hero, padding: 16, overflow: 'hidden' }, style]}>
      <View
        pointerEvents="none"
        style={{
          position: 'absolute',
          right: -36,
          top: -36,
          width: 130,
          height: 130,
          borderRadius: 65,
          backgroundColor: colors.primary,
          opacity: 0.4,
        }}
      />
      {children}
    </View>
  );
}
```

`mobile/src/ui/Button.tsx`:

```tsx
import type { ReactNode } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { PressableScale } from './PressableScale';
import { Text } from './Text';

type Props = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'deep' | 'ghost';
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
};

export function Button({ title, onPress, variant = 'primary', disabled, loading, icon }: Props) {
  const { colors } = useTheme();
  const background = variant === 'primary' ? colors.primary : variant === 'deep' ? colors.deep : 'transparent';
  const foreground = variant === 'ghost' ? 'primary' : 'onDeep';
  return (
    <PressableScale
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityLabel={title}
      style={{
        backgroundColor: background,
        borderRadius: 14,
        paddingVertical: 14,
        paddingHorizontal: 18,
        opacity: disabled ? 0.5 : 1,
        borderWidth: variant === 'ghost' ? 1 : 0,
        borderColor: colors.line,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        {loading ? <ActivityIndicator color={colors.onDeep} /> : icon}
        <Text variant="body" weight={700} color={foreground}>
          {title}
        </Text>
      </View>
    </PressableScale>
  );
}
```

`mobile/src/ui/Chip.tsx`:

```tsx
import { View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { radius, type Colors } from '@/theme/tokens';
import { Text } from './Text';

type Tone = 'neutral' | 'primary' | 'highlight' | 'danger' | 'accent';

const TONES: Record<Tone, { bg: keyof Colors; fg: keyof Colors }> = {
  neutral: { bg: 'line', fg: 'ink' },
  primary: { bg: 'primarySoft', fg: 'primary' },
  highlight: { bg: 'highlight', fg: 'highlightInk' },
  danger: { bg: 'dangerSoft', fg: 'danger' },
  accent: { bg: 'accent', fg: 'onAccent' },
};

export function Chip({ label, tone = 'neutral' }: { label: string; tone?: Tone }) {
  const { colors } = useTheme();
  const t = TONES[tone];
  return (
    <View style={{ backgroundColor: colors[t.bg], borderRadius: radius.chip, paddingHorizontal: 8, paddingVertical: 3, alignSelf: 'flex-start' }}>
      <Text variant="label" weight={700} color={t.fg}>
        {label}
      </Text>
    </View>
  );
}
```

`mobile/src/ui/FilterChips.tsx`:

```tsx
import { ScrollView } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { PressableScale } from './PressableScale';
import { Text } from './Text';

type Props<T extends string> = { options: { value: T; label: string }[]; value: T; onChange: (value: T) => void };

export function FilterChips<T extends string>({ options, value, onChange }: Props<T>) {
  const { colors } = useTheme();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <PressableScale
            key={option.value}
            onPress={() => onChange(option.value)}
            accessibilityLabel={option.label}
            style={{
              backgroundColor: active ? colors.deep : colors.surface,
              borderColor: colors.line,
              borderWidth: active ? 0 : 1,
              borderRadius: 10,
              paddingHorizontal: 12,
              paddingVertical: 6,
            }}
          >
            <Text variant="bodySmall" weight={600} color={active ? 'onDeep' : 'ink'}>
              {option.label}
            </Text>
          </PressableScale>
        );
      })}
    </ScrollView>
  );
}
```

`mobile/src/ui/SegmentedControl.tsx`:

```tsx
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import Animated, { useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Props<T extends string> = { options: { value: T; label: string }[]; value: T; onChange: (value: T) => void };

export function SegmentedControl<T extends string>({ options, value, onChange }: Props<T>) {
  const { colors } = useTheme();
  const [width, setWidth] = useState(0);
  const index = Math.max(0, options.findIndex((o) => o.value === value));
  const segment = options.length ? (width - 6) / options.length : 0;
  const thumb = useAnimatedStyle(() => ({
    transform: [{ translateX: withSpring(index * segment, { damping: 18, stiffness: 220 }) }],
  }));
  return (
    <View
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      style={{ flexDirection: 'row', backgroundColor: colors.line, borderRadius: 12, padding: 3 }}
    >
      {width > 0 && (
        <Animated.View
          style={[
            { position: 'absolute', top: 3, left: 3, bottom: 3, width: segment, borderRadius: 9, backgroundColor: colors.surface },
            thumb,
          ]}
        />
      )}
      {options.map((option) => (
        <Pressable
          key={option.value}
          accessibilityRole="button"
          accessibilityState={{ selected: option.value === value }}
          onPress={() => onChange(option.value)}
          style={{ flex: 1, paddingVertical: 8, alignItems: 'center' }}
        >
          <Text variant="bodySmall" weight={option.value === value ? 700 : 500}>
            {option.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}
```

`mobile/src/ui/SearchField.tsx`:

```tsx
import { Search, X } from 'lucide-react-native';
import { Pressable, TextInput, View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';

type Props = { value: string; onChangeText: (value: string) => void; placeholder: string };

export function SearchField({ value, onChangeText, placeholder }: Props) {
  const { colors } = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: colors.surface,
        borderRadius: radius.input,
        borderWidth: 1,
        borderColor: colors.line,
        paddingHorizontal: 12,
      }}
    >
      <Search size={18} color={colors.inkMuted} strokeWidth={2} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.inkMuted}
        autoCorrect={false}
        style={{ flex: 1, paddingVertical: 11, fontFamily: fontFamily[500], fontSize: 15, color: colors.ink }}
      />
      {value.length > 0 && (
        <Pressable accessibilityLabel="Aramayı temizle" onPress={() => onChangeText('')} hitSlop={10}>
          <X size={18} color={colors.inkMuted} strokeWidth={2} />
        </Pressable>
      )}
    </View>
  );
}
```

`mobile/src/ui/FormField.tsx`:

```tsx
import { TextInput, View, type TextInputProps } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';
import { Text } from './Text';

type Props = TextInputProps & { label: string; error?: string | null; mono?: boolean };

export function FormField({ label, error, mono, style, ...rest }: Props) {
  const { colors } = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <Text variant="label" color="inkMuted">
        {label}
      </Text>
      <TextInput
        placeholderTextColor={colors.inkMuted}
        {...rest}
        style={[
          {
            backgroundColor: colors.surface,
            borderRadius: radius.input,
            borderWidth: 1,
            borderColor: error ? colors.danger : colors.line,
            paddingHorizontal: 12,
            paddingVertical: 12,
            fontFamily: mono ? fontFamily.mono : fontFamily[500],
            fontSize: 15,
            color: colors.ink,
          },
          style,
        ]}
      />
      {error ? (
        <Text variant="label" color="danger">
          {error}
        </Text>
      ) : null}
    </View>
  );
}
```

`mobile/src/ui/Skeleton.tsx`:

```tsx
import { useEffect } from 'react';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import type { DimensionValue } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';

export function Skeleton({ width = '100%', height, radius = 12 }: { width?: DimensionValue; height: number; radius?: number }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const opacity = useSharedValue(0.5);
  useEffect(() => {
    if (!reduced) opacity.value = withRepeat(withTiming(1, { duration: 700 }), -1, true);
  }, [reduced, opacity]);
  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));
  return <Animated.View style={[{ width, height, borderRadius: radius, backgroundColor: colors.line }, style]} />;
}
```

`mobile/src/ui/EmptyState.tsx`:

```tsx
import type { ReactNode } from 'react';
import { View } from 'react-native';
import { Text } from './Text';

export function EmptyState({ title, message, icon }: { title: string; message: string; icon?: ReactNode }) {
  return (
    <View style={{ alignItems: 'center', paddingVertical: 40, paddingHorizontal: 24, gap: 8 }}>
      {icon}
      <Text variant="heading" style={{ textAlign: 'center' }}>
        {title}
      </Text>
      <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
        {message}
      </Text>
    </View>
  );
}
```

`mobile/src/ui/ErrorState.tsx`:

```tsx
import { CloudOff } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { View } from 'react-native';
import { describeError } from '@/api/errors';
import { useTheme } from '@/theme/ThemeProvider';
import { Button } from './Button';
import { Text } from './Text';

export function ErrorState({ error, onRetry, extra }: { error: unknown; onRetry?: () => void; extra?: ReactNode }) {
  const { colors } = useTheme();
  const { title, message } = describeError(error);
  return (
    <View style={{ alignItems: 'center', padding: 24, gap: 10 }}>
      <CloudOff size={36} color={colors.danger} strokeWidth={2} />
      <Text variant="heading" style={{ textAlign: 'center' }}>
        {title}
      </Text>
      <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
        {message}
      </Text>
      {extra}
      {onRetry ? <Button title="Tekrar dene" onPress={onRetry} variant="deep" /> : null}
    </View>
  );
}
```

`mobile/src/ui/Stamp.tsx`:

```tsx
import { useEffect } from 'react';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withSpring, withTiming } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

/** Eğik "kaşe"; yukarıdan büyükçe gelip yaylanarak basılır. */
export function Stamp({ title, subtitle }: { title: string; subtitle: string }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const scale = useSharedValue(reduced ? 1 : 2.2);
  const opacity = useSharedValue(reduced ? 1 : 0);
  useEffect(() => {
    if (reduced) return;
    scale.value = withDelay(250, withSpring(1, { damping: 9, stiffness: 180 }));
    opacity.value = withDelay(250, withTiming(1, { duration: 180 }));
  }, [reduced, scale, opacity]);
  const style = useAnimatedStyle(() => ({ opacity: opacity.value, transform: [{ rotate: '-6deg' }, { scale: scale.value }] }));
  return (
    <Animated.View
      style={[
        { alignSelf: 'center', borderWidth: 3, borderColor: colors.danger, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 7, alignItems: 'center' },
        style,
      ]}
    >
      <Text variant="heading" weight={800} color="danger" style={{ letterSpacing: 0.6 }}>
        {title}
      </Text>
      <Text variant="label" weight={700} color="danger" style={{ letterSpacing: 1.6 }}>
        {subtitle}
      </Text>
    </Animated.View>
  );
}
```

`mobile/src/ui/Screen.tsx`:

```tsx
import type { ReactNode } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '@/theme/ThemeProvider';

export const TAB_BAR_SPACE = 96;

type Props = { children: ReactNode; scroll?: boolean; refreshing?: boolean; onRefresh?: () => void; padded?: boolean; edges?: ('top' | 'bottom')[] };

export function Screen({ children, scroll = true, refreshing = false, onRefresh, padded = true, edges = ['top'] }: Props) {
  const { colors } = useTheme();
  const padding = padded ? 16 : 0;
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: colors.bg }}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={{ padding, paddingBottom: TAB_BAR_SPACE, gap: 12 }}
          refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} /> : undefined}
        >
          {children}
        </ScrollView>
      ) : (
        <View style={{ flex: 1, padding }}>{children}</View>
      )}
    </SafeAreaView>
  );
}
```

`mobile/src/ui/index.ts`:

```ts
export { Button } from './Button';
export { Card } from './Card';
export { Chip } from './Chip';
export { EmptyState } from './EmptyState';
export { ErrorState } from './ErrorState';
export { FilterChips } from './FilterChips';
export { FormField } from './FormField';
export { HeroCard } from './HeroCard';
export { PressableScale } from './PressableScale';
export { Screen, TAB_BAR_SPACE } from './Screen';
export { SearchField } from './SearchField';
export { SegmentedControl } from './SegmentedControl';
export { Skeleton } from './Skeleton';
export { Stamp } from './Stamp';
export { Text } from './Text';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && npx jest src/ui && npx tsc --noEmit`
Expected: test geçer, tip hatası yok.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/ui mobile/package.json mobile/jest.setup.js
git commit -m "feat(mobil): tasarım sistemi temel bileşenleri"
```

---

### Task 11: Veri bileşenleri — grafikler, sayaç, OCR metni, zaman çizgisi, hap tab bar

**Files:**
- Create: `mobile/src/ui/{useCountUp.ts,StatTile.tsx,BarChart.tsx,Donut.tsx,HBarList.tsx,OcrText.tsx,Timeline.tsx,DensityDots.tsx,PillTabBar.tsx}`
- Modify: `mobile/src/ui/index.ts` (dışa aktarımlar)
- Test: `mobile/src/ui/__tests__/OcrText.test.tsx`

**Interfaces:**
- Consumes: `splitHighlights`, `Highlight` (Task 8), `TabName`, `TAB_LABELS` (Task 8)
- Produces:
  - `useCountUp(target: number, durationMs?: number): number`
  - `StatTile({ label, value: number, footnote?, progress?: number /*0-1*/ })`
  - `BarChart({ data: { label: string; value: number }[]; highlightIndex?: number; height?: number; onDeep?: boolean })`
  - `Donut({ segments: { value: number; color: string }[]; size?: number; stroke?: number })`
  - `HBarList({ items: { label: string; value: number }[] })`
  - `OcrText({ text: string; highlights: Highlight[]; numberOfLines?: number; animate?: boolean })`
  - `TimelineItem({ title: string; subtitle?: string; latest?: boolean; index: number; children })`
  - `DensityDots({ levels: number[] })`
  - `PillTabBar(props: BottomTabBarProps & { visible: TabName[] })`

- [ ] **Step 1: Write the failing test** — `mobile/src/ui/__tests__/OcrText.test.tsx`

```tsx
import { render } from '@testing-library/react-native';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { palettes } from '@/theme/tokens';
import { OcrText } from '../OcrText';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

it('animasyonsuz modda ilaçları fosforlu, belirtileri altı çizili verir', () => {
  const { getByText } = render(
    <ThemeProvider>
      <OcrText
        text="Depakin devam, uykusuzluk"
        highlights={[
          { bas: 0, son: 7, tur: 'ilac' },
          { bas: 15, son: 25, tur: 'belirti' },
        ]}
        animate={false}
      />
    </ThemeProvider>,
  );
  expect(getByText('Depakin')).toHaveStyle({ backgroundColor: palettes.light.highlight });
  expect(getByText('uykusuzluk')).toHaveStyle({ textDecorationLine: 'underline' });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && npx jest src/ui/__tests__/OcrText.test.tsx`
Expected: FAIL — modül yok

- [ ] **Step 3: Write implementations**

`mobile/src/ui/useCountUp.ts`:

```ts
import { useEffect, useState } from 'react';
import { useReducedMotion } from 'react-native-reanimated';

/** Sayıyı 0'dan hedefe ease-out ile sayar; "hareketi azalt" açıksa doğrudan hedef. */
export function useCountUp(target: number, durationMs = 1100): number {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(reduced ? target : 0);
  useEffect(() => {
    if (reduced) {
      setValue(target);
      return;
    }
    let frame = 0;
    const start = Date.now();
    const tick = () => {
      const k = Math.min(1, (Date.now() - start) / durationMs);
      setValue(Math.round(target * (1 - Math.pow(1 - k, 3))));
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs, reduced]);
  return value;
}
```

`mobile/src/ui/StatTile.tsx`:

```tsx
import { View } from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';
import { useEffect } from 'react';
import { formatNumber } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { Card } from './Card';
import { Text } from './Text';
import { useCountUp } from './useCountUp';

type Props = { label: string; value: number; footnote?: string; progress?: number };

export function StatTile({ label, value, footnote, progress }: Props) {
  const { colors } = useTheme();
  const shown = useCountUp(value);
  const reduced = useReducedMotion();
  const fill = useSharedValue(reduced ? progress ?? 0 : 0);
  useEffect(() => {
    if (progress !== undefined && !reduced) fill.value = withDelay(400, withTiming(progress, { duration: 700 }));
  }, [progress, reduced, fill]);
  const bar = useAnimatedStyle(() => ({ width: `${fill.value * 100}%` }));
  return (
    <Card style={{ flex: 1, gap: 2 }}>
      <Text variant="label" color="inkMuted">
        {label}
      </Text>
      <Text variant="title">{formatNumber(shown)}</Text>
      {progress !== undefined && (
        <View style={{ height: 5, borderRadius: 3, backgroundColor: colors.primarySoft, overflow: 'hidden', marginTop: 6 }}>
          <Animated.View style={[{ height: '100%', backgroundColor: colors.primary }, bar]} />
        </View>
      )}
      {footnote ? (
        <Text variant="label" color="inkMuted" weight={500} style={{ marginTop: 4 }}>
          {footnote}
        </Text>
      ) : null}
    </Card>
  );
}
```

`mobile/src/ui/BarChart.tsx`:

```tsx
import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withSpring } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Datum = { label: string; value: number };
type Props = { data: Datum[]; highlightIndex?: number; height?: number; onDeep?: boolean };

function Bar({ ratio, index, color, height }: { ratio: number; index: number; color: string; height: number }) {
  const reduced = useReducedMotion();
  const h = useSharedValue(reduced ? ratio * height : 0);
  useEffect(() => {
    if (!reduced) h.value = withDelay(150 + index * 60, withSpring(ratio * height, { damping: 13, stiffness: 140 }));
    else h.value = ratio * height;
  }, [ratio, height, index, reduced, h]);
  const style = useAnimatedStyle(() => ({ height: Math.max(4, h.value) }));
  return <Animated.View style={[{ flex: 1, borderRadius: 6, backgroundColor: color }, style]} />;
}

export function BarChart({ data, highlightIndex, height = 56, onDeep = false }: Props) {
  const { colors } = useTheme();
  const max = Math.max(1, ...data.map((d) => d.value));
  const muted = onDeep ? 'rgba(255,255,255,0.28)' : colors.primarySoft;
  const strong = onDeep ? colors.accent : colors.primary;
  return (
    <View>
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, height }}>
        {data.map((d, i) => (
          <Bar key={d.label} ratio={d.value / max} index={i} height={height} color={i === highlightIndex ? strong : muted} />
        ))}
      </View>
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 5 }}>
        {data.map((d) => (
          <Text key={d.label} variant="label" color={onDeep ? 'onDeep' : 'inkMuted'} style={{ flex: 1, textAlign: 'center', opacity: onDeep ? 0.65 : 1 }}>
            {d.label}
          </Text>
        ))}
      </View>
    </View>
  );
}
```

`mobile/src/ui/Donut.tsx`:

```tsx
import { useEffect } from 'react';
import Animated, { useAnimatedProps, useReducedMotion, useSharedValue, withDelay, withTiming, Easing } from 'react-native-reanimated';
import Svg, { Circle } from 'react-native-svg';
import { useTheme } from '@/theme/ThemeProvider';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);
type Segment = { value: number; color: string };

function Arc({ c, r, stroke, circumference, fraction, startFraction, color, delay }: {
  c: number; r: number; stroke: number; circumference: number; fraction: number; startFraction: number; color: string; delay: number;
}) {
  const reduced = useReducedMotion();
  const progress = useSharedValue(reduced ? 1 : 0);
  useEffect(() => {
    if (!reduced) progress.value = withDelay(delay, withTiming(1, { duration: 900, easing: Easing.out(Easing.cubic) }));
  }, [reduced, delay, progress]);
  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: circumference - circumference * fraction * progress.value,
  }));
  return (
    <AnimatedCircle
      cx={c}
      cy={c}
      r={r}
      fill="none"
      stroke={color}
      strokeWidth={stroke}
      strokeDasharray={`${circumference} ${circumference}`}
      rotation={-90 + 360 * startFraction}
      origin={`${c}, ${c}`}
      animatedProps={animatedProps}
    />
  );
}

export function Donut({ segments, size = 64, stroke = 9 }: { segments: Segment[]; size?: number; stroke?: number }) {
  const { colors } = useTheme();
  const c = size / 2;
  const r = c - stroke / 2;
  const circumference = 2 * Math.PI * r;
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1;
  let start = 0;
  return (
    <Svg width={size} height={size}>
      <Circle cx={c} cy={c} r={r} fill="none" stroke={colors.primarySoft} strokeWidth={stroke} />
      {segments.map((segment, i) => {
        const fraction = segment.value / total;
        const arc = (
          <Arc key={i} c={c} r={r} stroke={stroke} circumference={circumference} fraction={fraction}
            startFraction={start} color={segment.color} delay={300 + i * 200} />
        );
        start += fraction;
        return arc;
      })}
    </Svg>
  );
}
```

`mobile/src/ui/HBarList.tsx`:

```tsx
import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, { useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withTiming, Easing } from 'react-native-reanimated';
import { formatNumber } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

function Row({ label, value, ratio, index }: { label: string; value: number; ratio: number; index: number }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const width = useSharedValue(reduced ? ratio : 0);
  useEffect(() => {
    if (!reduced) width.value = withDelay(450 + index * 60, withTiming(ratio, { duration: 700, easing: Easing.out(Easing.cubic) }));
  }, [ratio, index, reduced, width]);
  const fill = useAnimatedStyle(() => ({ width: `${width.value * 100}%` }));
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Text variant="bodySmall" weight={600} numberOfLines={1} style={{ width: 78 }}>
        {label}
      </Text>
      <View style={{ flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.primarySoft, overflow: 'hidden' }}>
        <Animated.View style={[{ height: '100%', borderRadius: 4, backgroundColor: colors.primary }, fill]} />
      </View>
      <Text variant="mono" color="inkMuted" style={{ width: 44, textAlign: 'right' }}>
        {formatNumber(value)}
      </Text>
    </View>
  );
}

export function HBarList({ items }: { items: { label: string; value: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <View style={{ gap: 9 }}>
      {items.map((item, index) => (
        <Row key={item.label} label={item.label} value={item.value} ratio={item.value / max} index={index} />
      ))}
    </View>
  );
}
```

`mobile/src/ui/OcrText.tsx`:

```tsx
import { useEffect, useMemo, useState } from 'react';
import { useReducedMotion } from 'react-native-reanimated';
import { splitHighlights, type Highlight } from '@/lib/ocrSegments';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Props = { text: string; highlights: Highlight[]; numberOfLines?: number; animate?: boolean };

/**
 * OCR metni (mono). İlaçlar fosforlu zeminle, belirtiler ana renkli altçizgiyle.
 * animate=true iken vurgular sırayla (140 ms arayla) belirir; RN satır içi metinde
 * genişlik animasyonu desteklemediği için "sweep" sıralı görünür olmayla verilir.
 * Not: Android'de altçizgi rengi metin rengini kullanır (textDecorationColor yalnızca iOS).
 */
export function OcrText({ text, highlights, numberOfLines, animate = true }: Props) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const segments = useMemo(() => splitHighlights(text, highlights), [text, highlights]);
  const marked = segments.filter((s) => s.tur !== null).length;
  const instant = !animate || reduced;
  const [revealed, setRevealed] = useState(instant ? marked : 0);

  useEffect(() => {
    if (instant) {
      setRevealed(marked);
      return;
    }
    setRevealed(0);
    const timers = Array.from({ length: marked }, (_, i) => setTimeout(() => setRevealed(i + 1), 250 + i * 140));
    return () => timers.forEach(clearTimeout);
  }, [instant, marked, text]);

  let order = 0;
  return (
    <Text variant="mono" numberOfLines={numberOfLines}>
      {segments.map((segment, i) => {
        if (segment.tur === null) return segment.text;
        const visible = order++ < revealed;
        if (segment.tur === 'ilac') {
          return (
            <Text key={i} variant="mono" style={{ backgroundColor: visible ? colors.highlight : 'transparent', color: visible ? colors.highlightInk : colors.ink }}>
              {segment.text}
            </Text>
          );
        }
        return (
          <Text key={i} variant="mono" style={visible ? { textDecorationLine: 'underline', textDecorationColor: colors.primary } : undefined}>
            {segment.text}
          </Text>
        );
      })}
    </Text>
  );
}
```

`mobile/src/ui/Timeline.tsx`:

```tsx
import type { ReactNode } from 'react';
import { View } from 'react-native';
import Animated, { FadeInDown, useReducedMotion } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Props = { title: string; subtitle?: string; latest?: boolean; index: number; isLast?: boolean; children?: ReactNode };

export function TimelineItem({ title, subtitle, latest = false, index, isLast = false, children }: Props) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const entering = reduced ? undefined : FadeInDown.delay(Math.min(index, 8) * 60).duration(450);
  return (
    <Animated.View entering={entering} style={{ flexDirection: 'row', gap: 12 }}>
      <View style={{ width: 14, alignItems: 'center' }}>
        <View
          style={{
            marginTop: 3,
            width: 12,
            height: 12,
            borderRadius: 6,
            backgroundColor: latest ? colors.accent : colors.surface,
            borderWidth: latest ? 0 : 2.5,
            borderColor: colors.primary,
            shadowColor: colors.accent,
            shadowOpacity: latest ? 0.9 : 0,
            shadowRadius: 6,
          }}
        />
        {!isLast && <View style={{ flex: 1, width: 2, backgroundColor: colors.line, marginTop: 4 }} />}
      </View>
      <View style={{ flex: 1, paddingBottom: 18, gap: 7 }}>
        <Text variant="bodySmall" weight={700}>
          {title}
          {subtitle ? (
            <Text variant="bodySmall" color="inkMuted">
              {`  ·  ${subtitle}`}
            </Text>
          ) : null}
        </Text>
        {children}
      </View>
    </Animated.View>
  );
}
```

`mobile/src/ui/DensityDots.tsx`:

```tsx
import { View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';

/** Sunucunun 0–3 ölçekli 12 kovalık yoğunluğu; 0 = boş halka. */
export function DensityDots({ levels }: { levels: number[] }) {
  const { colors } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2 }}>
      {levels.map((level, i) => (
        <View
          key={i}
          style={{
            width: 4,
            height: level === 0 ? 4 : 4 + level * 3,
            borderRadius: 2,
            backgroundColor: level === 0 ? colors.line : colors.primary,
            opacity: level === 0 ? 1 : 0.45 + level * 0.18,
          }}
        />
      ))}
    </View>
  );
}
```

`mobile/src/ui/PillTabBar.tsx`:

```tsx
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { Folder, LayoutGrid, Plus, Server, Settings, Users, type LucideIcon } from 'lucide-react-native';
import { Pressable, View } from 'react-native';
import Animated, { FadeIn, LinearTransition } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { TAB_LABELS, type TabName } from '@/lib/roleTabs';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';

const ICONS: Record<TabName, LucideIcon> = {
  ozet: LayoutGrid,
  dosyalar: Folder,
  yeni: Plus,
  sistem: Server,
  kullanicilar: Users,
  ayarlar: Settings,
};

export function PillTabBar({ state, navigation, visible }: BottomTabBarProps & { visible: TabName[] }) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const routes = state.routes.filter((route) => visible.includes(route.name as TabName));
  const focusedName = state.routes[state.index]?.name;
  return (
    <View
      style={{
        position: 'absolute',
        left: 12,
        right: 12,
        bottom: Math.max(insets.bottom, 12),
        height: 64,
        borderRadius: radius.tab,
        backgroundColor: colors.deep,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 6,
      }}
    >
      {routes.map((route) => {
        const name = route.name as TabName;
        const focused = route.name === focusedName;
        const Icon = ICONS[name];
        return (
          <Animated.View key={route.key} layout={LinearTransition.springify().damping(16)} style={{ flex: focused ? 2.2 : 1 }}>
            <Pressable
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={TAB_LABELS[name]}
              onPress={() => {
                const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
                if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
              }}
              style={{
                height: 44,
                borderRadius: 15,
                backgroundColor: focused ? colors.accent : 'transparent',
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <Icon size={19} strokeWidth={2.2} color={focused ? colors.onAccent : 'rgba(255,255,255,0.55)'} />
              {focused && (
                <Animated.Text
                  entering={FadeIn.duration(200)}
                  numberOfLines={1}
                  style={{ fontFamily: fontFamily[700], fontSize: 12, color: colors.onAccent }}
                >
                  {TAB_LABELS[name]}
                </Animated.Text>
              )}
            </Pressable>
          </Animated.View>
        );
      })}
    </View>
  );
}
```

> `@react-navigation/bottom-tabs` Expo Router ile birlikte gelir; tip içe aktarımı ek kurulum gerektirmez. `npx tsc` bulamazsa `npx expo install @react-navigation/bottom-tabs` çalıştır.

`mobile/src/ui/index.ts` dosyasına ekle:

```ts
export { BarChart } from './BarChart';
export { DensityDots } from './DensityDots';
export { Donut } from './Donut';
export { HBarList } from './HBarList';
export { OcrText } from './OcrText';
export { PillTabBar } from './PillTabBar';
export { StatTile } from './StatTile';
export { TimelineItem } from './Timeline';
export { useCountUp } from './useCountUp';
```

- [ ] **Step 4: Run tests and type check**

Run: `cd mobile && npx jest && npx tsc --noEmit`
Expected: tümü geçer, tip hatası yok

- [ ] **Step 5: Commit**

```bash
git add mobile/src/ui
git commit -m "feat(mobil): grafikler, sayaç, OCR metni, zaman çizgisi ve hap tab bar"
```

---

### Task 12: Navigasyon, kök sağlayıcılar ve giriş ekranı

**Files:**
- Create: `mobile/app/_layout.tsx`, `mobile/app/index.tsx`, `mobile/app/giris.tsx`, `mobile/app/(tabs)/_layout.tsx`, `mobile/src/features/baglanti/BaglantiHatasi.tsx`, `mobile/src/ui/Logo.tsx`
- Create (geçici yer tutucu ekranlar; Task 13–16'da gerçek içerik gelir): `mobile/app/(tabs)/{ozet,dosyalar,yeni,sistem,kullanicilar,ayarlar}.tsx`, `mobile/app/dosya/[id].tsx`

**Interfaces:**
- Consumes: `ThemeProvider`, `ServerUrlProvider`, `AuthProvider`, `useAuth`, `tabsForRole`, `homeTab`, `ALL_TABS`, `PillTabBar`, `DEMO_ACCOUNTS`, UI bileşenleri
- Produces: rotalar `/giris`, `/(tabs)/<sekme>`, `/dosya/<id>`; `RoleGuard({ allow: Rol[]; children })` (`mobile/src/auth/RoleGuard.tsx`)

- [ ] **Step 1: `mobile/src/ui/Logo.tsx`** (dosya sekmesi işareti)

```tsx
import Svg, { Path, Rect } from 'react-native-svg';
import { useTheme } from '@/theme/ThemeProvider';

export function Logo({ size = 56 }: { size?: number }) {
  const { colors } = useTheme();
  return (
    <Svg width={size} height={size} viewBox="0 0 54 54">
      <Rect x={9} y={14} width={38} height={32} rx={4} fill={colors.accent} />
      <Path d="M5 12a4 4 0 0 1 4-4h12l4 5h20a4 4 0 0 1 4 4v25a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z" fill={colors.primary} />
      <Rect x={13} y={24} width={22} height={5} rx={1} fill={colors.highlight} />
      <Rect x={13} y={33} width={28} height={2.5} rx={1} fill="#FFFFFF" opacity={0.7} />
    </Svg>
  );
}
```

`index.ts`'e ekle: `export { Logo } from './Logo';`

- [ ] **Step 2: `mobile/src/auth/RoleGuard.tsx`**

```tsx
import type { ReactNode } from 'react';
import { ApiError } from '@/api/errors';
import type { Rol } from '@/lib/roleTabs';
import { ErrorState, Screen } from '@/ui';
import { useAuth } from './AuthProvider';

export function RoleGuard({ allow, children }: { allow: Rol[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user || !allow.includes(user.rol)) {
    return (
      <Screen scroll={false}>
        <ErrorState error={new ApiError('yasak', 403, 'Bu alan rolünüze kapalı.')} />
      </Screen>
    );
  }
  return <>{children}</>;
}
```

- [ ] **Step 3: `mobile/src/features/baglanti/BaglantiHatasi.tsx`**

```tsx
import { useState } from 'react';
import { View } from 'react-native';
import { ApiError } from '@/api/errors';
import { useServerUrl } from '@/api/ServerUrlProvider';
import { useAuth } from '@/auth/AuthProvider';
import { Button, ErrorState, FormField, Screen } from '@/ui';

export function BaglantiHatasi() {
  const { url, setUrl } = useServerUrl();
  const { retry, logout } = useAuth();
  const [draft, setDraft] = useState(url);
  const [editing, setEditing] = useState(false);
  return (
    <Screen>
      <View style={{ flex: 1, justifyContent: 'center', gap: 16, paddingTop: 80 }}>
        <ErrorState error={new ApiError('ag', null, '')} onRetry={retry} />
        {editing ? (
          <View style={{ gap: 10 }}>
            <FormField label="Sunucu adresi" value={draft} onChangeText={setDraft} autoCapitalize="none" keyboardType="url" mono />
            <Button title="Kaydet ve dene" onPress={async () => { await setUrl(draft); setEditing(false); retry(); }} />
          </View>
        ) : (
          <Button title={`Adresi değiştir (${url})`} variant="ghost" onPress={() => setEditing(true)} />
        )}
        <Button title="Çıkış yap" variant="ghost" onPress={logout} />
      </View>
    </Screen>
  );
}
```

- [ ] **Step 4: `mobile/app/_layout.tsx`**

```tsx
import { Geist_400Regular, Geist_500Medium, Geist_600SemiBold, Geist_700Bold, Geist_800ExtraBold, useFonts } from '@expo-google-fonts/geist';
import { GeistMono_400Regular, GeistMono_500Medium } from '@expo-google-fonts/geist-mono';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ServerUrlProvider } from '@/api/ServerUrlProvider';
import { ApiError } from '@/api/errors';
import { AuthProvider, useAuth } from '@/auth/AuthProvider';
import { BaglantiHatasi } from '@/features/baglanti/BaglantiHatasi';
import { canViewPatients } from '@/lib/roleTabs';
import { ThemeProvider, useTheme } from '@/theme/ThemeProvider';

SplashScreen.preventAutoHideAsync();

function RootNavigator() {
  const { status, user } = useAuth();
  const { colors, name } = useTheme();

  useEffect(() => {
    if (status !== 'yukleniyor') SplashScreen.hideAsync();
  }, [status]);

  if (status === 'yukleniyor') return null;
  if (status === 'baglanti_hatasi') return <BaglantiHatasi />;

  const signedIn = status === 'girisli' && user !== null;
  return (
    <>
      <StatusBar style={name === 'dark' ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="giris" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn}>
          <Stack.Screen name="(tabs)" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn && canViewPatients(user!.rol)}>
          <Stack.Screen name="dosya/[id]" options={{ animation: 'slide_from_right' }} />
        </Stack.Protected>
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Geist_400Regular,
    Geist_500Medium,
    Geist_600SemiBold,
    Geist_700Bold,
    Geist_800ExtraBold,
    GeistMono_400Regular,
    GeistMono_500Medium,
  });
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: (count, error) => !(error instanceof ApiError && ['yetkisiz', 'yasak', 'bulunamadi', 'istek'].includes(error.kind)) && count < 2,
          },
        },
      }),
  );
  if (!fontsLoaded) return null;
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <QueryClientProvider client={queryClient}>
            <ServerUrlProvider>
              <AuthProvider>
                <RootNavigator />
              </AuthProvider>
            </ServerUrlProvider>
          </QueryClientProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
```

> `Stack.Protected` Expo Router v5+ ile gelir. Kurulu sürümde yoksa aynı mantığı `app/index.tsx` yönlendirmesi + `useSegments`/`router.replace` ile kur (giriş yoksa `/giris`, varsa rolün ana sekmesi; hemşire/doktor dışı `dosya/*` → ana sekme).
> `@expo-google-fonts/geist` dışa aktarım adlarını kurulu paketten doğrula (`grep -o "Geist_[0-9]*[A-Za-z]*" node_modules/@expo-google-fonts/geist/index.js | sort -u`); farklıysa hem burada hem `tokens.ts → fontFamily`'de güncelle. `expo-splash-screen` ve `react-native-gesture-handler` eksikse `npx expo install expo-splash-screen react-native-gesture-handler`.

- [ ] **Step 5: `mobile/app/index.tsx`**

```tsx
import { Redirect } from 'expo-router';
import { useAuth } from '@/auth/AuthProvider';
import { homeTab } from '@/lib/roleTabs';

export default function Index() {
  const { user } = useAuth();
  if (!user) return <Redirect href="/giris" />;
  return <Redirect href={`/(tabs)/${homeTab(user.rol)}`} />;
}
```

- [ ] **Step 6: `mobile/app/(tabs)/_layout.tsx`**

```tsx
import { Tabs } from 'expo-router';
import { useAuth } from '@/auth/AuthProvider';
import { ALL_TABS, homeTab, tabsForRole } from '@/lib/roleTabs';
import { PillTabBar } from '@/ui';

export default function TabsLayout() {
  const { user } = useAuth();
  if (!user) return null;
  const visible = tabsForRole(user.rol);
  return (
    <Tabs
      initialRouteName={homeTab(user.rol)}
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <PillTabBar {...props} visible={visible} />}
    >
      {ALL_TABS.map((name) => (
        <Tabs.Screen key={name} name={name} options={{ href: visible.includes(name) ? undefined : null }} />
      ))}
    </Tabs>
  );
}
```

- [ ] **Step 7: Geçici sekme ekranları** — her biri için (`ozet`, `dosyalar`, `yeni`, `sistem`, `kullanicilar`, `ayarlar`) `mobile/app/(tabs)/<ad>.tsx`:

```tsx
import { Screen, Text } from '@/ui';

export default function Placeholder() {
  return (
    <Screen>
      <Text variant="title">Hazırlanıyor</Text>
    </Screen>
  );
}
```

ve `mobile/app/dosya/[id].tsx` aynı içerikle.

- [ ] **Step 8: `mobile/app/giris.tsx`**

```tsx
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, View } from 'react-native';
import Animated, { FadeInDown, useAnimatedStyle, useSharedValue, withSequence, withTiming } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';
import { describeError } from '@/api/errors';
import { useAuth } from '@/auth/AuthProvider';
import { DEMO_ACCOUNTS } from '@/auth/demoAccounts';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, FormField, Logo, PressableScale, Text } from '@/ui';

export default function Giris() {
  const { colors } = useTheme();
  const { login } = useAuth();
  const [kullaniciAdi, setKullaniciAdi] = useState('');
  const [sifre, setSifre] = useState('');
  const [hata, setHata] = useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const shake = useSharedValue(0);
  const shakeStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }] }));

  async function submit(k = kullaniciAdi, s = sifre) {
    setHata(null);
    setYukleniyor(true);
    try {
      await login(k.trim(), s);
    } catch (error) {
      setHata(describeError(error).message);
      shake.value = withSequence(
        withTiming(-10, { duration: 50 }),
        withTiming(10, { duration: 50 }),
        withTiming(-6, { duration: 50 }),
        withTiming(0, { duration: 50 }),
      );
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.deep }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
        <Animated.View entering={FadeInDown.duration(500)} style={{ gap: 10, marginBottom: 32 }}>
          <Logo size={60} />
          <Text variant="display" color="onDeep">
            kartela
          </Text>
          <Text variant="body" color="onDeep" style={{ opacity: 0.7 }}>
            TRSM hasta arşivi
          </Text>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(120).duration(500)} style={[{ backgroundColor: colors.surface, borderRadius: 22, padding: 18, gap: 14 }, shakeStyle]}>
          <FormField label="Kullanıcı adı" value={kullaniciAdi} onChangeText={setKullaniciAdi} autoCapitalize="none" autoCorrect={false} textContentType="username" />
          <FormField label="Şifre" value={sifre} onChangeText={setSifre} secureTextEntry textContentType="password" error={hata} onSubmitEditing={() => submit()} />
          <Button title="Giriş yap" onPress={() => submit()} loading={yukleniyor} disabled={!kullaniciAdi || !sifre} />
          <Button title="Google ile giriş (yakında)" variant="ghost" onPress={() => {}} disabled />
        </Animated.View>

        {__DEV__ && (
          <Animated.View entering={FadeInDown.delay(240).duration(500)} style={{ flexDirection: 'row', gap: 8, marginTop: 20, justifyContent: 'center' }}>
            {DEMO_ACCOUNTS.map((account) => (
              <PressableScale
                key={account.rol}
                accessibilityLabel={`${account.etiket} olarak gir`}
                onPress={() => {
                  setKullaniciAdi(account.kullaniciAdi);
                  setSifre(account.sifre);
                  submit(account.kullaniciAdi, account.sifre);
                }}
                style={{ backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 7 }}
              >
                <Text variant="label" color="onDeep">
                  {account.etiket}
                </Text>
              </PressableScale>
            ))}
          </Animated.View>
        )}
        <View style={{ height: 24 }} />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
```

- [ ] **Step 9: Tip kontrolü ve testler**

Run: `cd mobile && npx tsc --noEmit && npx jest`
Expected: hata yok, testler geçer

- [ ] **Step 10: Cihazda doğrulama**

Sunucuyu açık tutarak (`TRSM_HOST=0.0.0.0 uv run python demo_server.py`, Task 17'deki symlink'lerle) `cd mobile && npx expo start` → Expo Go. Kontrol: giriş ekranı Geist fontuyla görünür; yanlış şifrede kart sarsılır ve "Kullanıcı adı ya da şifre hatalı." yazar; "Doktor" hızlı girişi 4 sekmeli, "Hemşire" 3 sekmeli, "Admin" Sistem/Kullanıcılar/Ayarlar sekmeli hap tab bar açar; aktif sekme genişleyip etiketini gösterir.

- [ ] **Step 11: Commit**

```bash
git add mobile/app mobile/src/auth/RoleGuard.tsx mobile/src/features/baglanti mobile/src/ui/Logo.tsx mobile/src/ui/index.ts mobile/package.json
git commit -m "feat(mobil): kök sağlayıcılar, rol bazlı sekmeler ve giriş ekranı"
```

---

### Task 13: Özet ekranı

**Files:**
- Create: `mobile/src/features/ozet/OzetEkrani.tsx`
- Modify: `mobile/app/(tabs)/ozet.tsx`

**Interfaces:**
- Consumes: `useOzet`, `useAuth`, `HeroCard`, `BarChart`, `StatTile`, `Donut`, `HBarList`, `Card`, `Skeleton`, `ErrorState`, `RoleGuard`, `formatNumber`, `initials`, `useCountUp`

- [ ] **Step 1: `mobile/src/features/ozet/OzetEkrani.tsx`**

```tsx
import { View } from 'react-native';
import Animated, { FadeInDown, useReducedMotion } from 'react-native-reanimated';
import { useOzet } from '@/api/hooks';
import { useAuth } from '@/auth/AuthProvider';
import { formatNumber, initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { BarChart, Card, Chip, Donut, ErrorState, HBarList, HeroCard, Screen, Skeleton, StatTile, Text, useCountUp } from '@/ui';

const TODAY = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', weekday: 'long' });

function todayLabel() {
  try {
    return TODAY.format(new Date());
  } catch {
    return '';
  }
}

export function OzetEkrani() {
  const { colors } = useTheme();
  const { user } = useAuth();
  const reduced = useReducedMotion();
  const query = useOzet();
  const data = query.data;
  const total = useCountUp(data?.toplam_dosya ?? 0);
  const enter = (i: number) => (reduced ? undefined : FadeInDown.delay(i * 60).duration(500));

  return (
    <Screen refreshing={query.isRefetching} onRefresh={() => query.refetch()}>
      <Animated.View entering={enter(0)} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Text variant="label" color="inkMuted">
            {todayLabel()}
          </Text>
          <Text variant="title">Arşiv özeti</Text>
        </View>
        <View style={{ width: 40, height: 40, borderRadius: 13, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' }}>
          <Text variant="bodySmall" weight={800} color="onAccent">
            {initials(user?.ad_soyad ?? '')}
          </Text>
        </View>
      </Animated.View>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !data ? (
        <View style={{ gap: 12 }}>
          <Skeleton height={190} radius={22} />
          <View style={{ flexDirection: 'row', gap: 12 }}>
            <View style={{ flex: 1 }}><Skeleton height={110} radius={18} /></View>
            <View style={{ flex: 1 }}><Skeleton height={110} radius={18} /></View>
          </View>
          <Skeleton height={150} radius={18} />
        </View>
      ) : (
        <>
          <Animated.View entering={enter(1)}>
            <HeroCard>
              <Text variant="label" color="onDeep" style={{ opacity: 0.7 }}>
                Toplam dosya
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8 }}>
                <Text variant="display" color="onDeep">
                  {formatNumber(total)}
                </Text>
                {data.okunmamis_rapor > 0 && <Chip label={`+${data.okunmamis_rapor} okunmadı`} tone="accent" />}
              </View>
              <View style={{ marginTop: 12 }}>
                <BarChart
                  onDeep
                  height={52}
                  highlightIndex={data.yillik_not.length - 1}
                  data={data.yillik_not.map((y, i) => ({ label: i === 0 ? String(y.yil) : `'${String(y.yil).slice(2)}`, value: y.sayi }))}
                />
              </View>
            </HeroCard>
          </Animated.View>

          <Animated.View entering={enter(2)} style={{ flexDirection: 'row', gap: 12 }}>
            <StatTile
              label="Ziyaret notu"
              value={data.toplam_not}
              progress={data.toplam_not ? data.ilacli_not / data.toplam_not : 0}
              footnote={`%${data.toplam_not ? Math.round((data.ilacli_not / data.toplam_not) * 100) : 0}'inde ilaç okundu`}
            />
            <Card style={{ flex: 1, alignItems: 'center', gap: 6 }}>
              <Donut
                size={68}
                segments={[
                  { value: data.cinsiyet.erkek, color: colors.primary },
                  { value: data.cinsiyet.kadin, color: colors.accent },
                ]}
              />
              <Text variant="label">
                <Text variant="label" style={{ color: colors.primary }}>● </Text>
                {data.cinsiyet.erkek} E   <Text variant="label" style={{ color: colors.accent }}>● </Text>
                {data.cinsiyet.kadin} K
              </Text>
            </Card>
          </Animated.View>

          <Animated.View entering={enter(3)}>
            <Card style={{ gap: 10 }}>
              <Text variant="label" color="inkMuted">
                En sık okunan ilaçlar
              </Text>
              <HBarList items={data.en_sik_ilaclar.map((d) => ({ label: d.ilac, value: d.sayi }))} />
            </Card>
          </Animated.View>
        </>
      )}
    </Screen>
  );
}
```

- [ ] **Step 2: `mobile/app/(tabs)/ozet.tsx`**

```tsx
import { RoleGuard } from '@/auth/RoleGuard';
import { OzetEkrani } from '@/features/ozet/OzetEkrani';

export default function Ozet() {
  return (
    <RoleGuard allow={['doktor', 'hemsire']}>
      <OzetEkrani />
    </RoleGuard>
  );
}
```

- [ ] **Step 3: Tip kontrolü**

Run: `cd mobile && npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 4: Cihazda doğrulama**

Doktorla giriş → Özet: hero kartta `434` sayarak gelir, yıl çubukları yaylanarak büyür (son yıl nane rengi), "Ziyaret notu" `41.676` ve ilerleme çubuğu, halka grafik çizilir (`242 E · 191 K`), en sık ilaçlar listesinde Depakin ilk sırada. Aşağı çekince yenilenir. Ayarlar'da koyu tema seçilince (Task 16 sonrası tekrar kontrol) renkler değişir.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/features/ozet "mobile/app/(tabs)/ozet.tsx"
git commit -m "feat(mobil): gerçek veriyle Özet ekranı"
```

---

### Task 14: Dosyalar listesi ve dosya detayı

**Files:**
- Create: `mobile/src/features/dosyalar/{DosyalarEkrani.tsx,DosyaKarti.tsx,filtre.ts}`, `mobile/src/features/dosya-detay/{DosyaDetayEkrani.tsx,NotKarti.tsx}`
- Modify: `mobile/app/(tabs)/dosyalar.tsx`, `mobile/app/dosya/[id].tsx`
- Test: `mobile/src/features/dosyalar/__tests__/filtre.test.ts`

**Interfaces:**
- Consumes: `useHastalar`, `useHasta`, `useNotlar`, `matchesQuery`, `formatDate`, `initials`, `OcrText`, `TimelineItem`, `DensityDots`, `Stamp`, UI bileşenleri
- Produces: `type Filtre = 'tumu' | 'son' | 'okunmadi'`, `filterPatients(list: HastaOzeti[], query: string, filtre: Filtre): HastaOzeti[]`

- [ ] **Step 1: Write the failing test** — `mobile/src/features/dosyalar/__tests__/filtre.test.ts`

```ts
import type { HastaOzeti } from '@/api/types';
import { filterPatients } from '../filtre';

const base = { cinsiyet: null, yas: null, yogunluk: [], okunmamis: false };
const list: HastaOzeti[] = [
  { ...base, id: 1, ad: 'Ayşe Kaya', not_sayisi: 4, son_ziyaret: '2023-06-10' },
  { ...base, id: 2, ad: 'Boş Dosya', not_sayisi: 0, son_ziyaret: null },
  { ...base, id: 3, ad: 'İsmail Işık', not_sayisi: 1, son_ziyaret: '2025-01-15', okunmamis: true },
];

it('tümü: sunucu sırası korunur, arama Türkçe duyarlı', () => {
  expect(filterPatients(list, '', 'tumu').map((p) => p.id)).toEqual([1, 2, 3]);
  expect(filterPatients(list, 'ayse', 'tumu').map((p) => p.id)).toEqual([1]);
  expect(filterPatients(list, 'IŞI', 'tumu').map((p) => p.id)).toEqual([3]);
});

it('son ziyaret: tarihliler yeniden eskiye, tarihsizler en sonda', () => {
  expect(filterPatients(list, '', 'son').map((p) => p.id)).toEqual([3, 1, 2]);
});

it('okunmadı: yalnızca okunmamış dosyalar', () => {
  expect(filterPatients(list, '', 'okunmadi').map((p) => p.id)).toEqual([3]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && npx jest src/features/dosyalar`
Expected: FAIL — modül yok

- [ ] **Step 3: Write implementations**

`mobile/src/features/dosyalar/filtre.ts`:

```ts
import type { HastaOzeti } from '@/api/types';
import { matchesQuery } from '@/lib/turkishSearch';

export type Filtre = 'tumu' | 'son' | 'okunmadi';

export function filterPatients(list: HastaOzeti[], query: string, filtre: Filtre): HastaOzeti[] {
  let result = list.filter((p) => matchesQuery(p.ad, query));
  if (filtre === 'okunmadi') result = result.filter((p) => p.okunmamis);
  if (filtre === 'son') {
    result = [...result].sort((a, b) => {
      if (a.son_ziyaret === b.son_ziyaret) return a.id - b.id;
      if (a.son_ziyaret === null) return 1;
      if (b.son_ziyaret === null) return -1;
      return a.son_ziyaret < b.son_ziyaret ? 1 : -1;
    });
  }
  return result;
}
```

`mobile/src/features/dosyalar/DosyaKarti.tsx`:

```tsx
import { router } from 'expo-router';
import { View } from 'react-native';
import Animated, { FadeInDown, useReducedMotion } from 'react-native-reanimated';
import type { HastaOzeti } from '@/api/types';
import { formatDate } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';
import { Chip, DensityDots, PressableScale, Text } from '@/ui';

function subtitle(p: HastaOzeti) {
  if (p.okunmamis) return 'Ham rapor · okunmadı';
  if (p.not_sayisi === 0) return 'Not yok';
  if (!p.son_ziyaret) return `${p.not_sayisi} not · tarihli not yok`;
  return `${p.not_sayisi} not · son ${formatDate(p.son_ziyaret)}`;
}

export function DosyaKarti({ hasta, index }: { hasta: HastaOzeti; index: number }) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  return (
    <Animated.View entering={reduced || index > 10 ? undefined : FadeInDown.delay(index * 50).duration(400)}>
      <PressableScale
        accessibilityLabel={`${hasta.ad} dosyasını aç`}
        onPress={() => router.push(`/dosya/${hasta.id}`)}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          backgroundColor: colors.surface,
          borderRadius: radius.card,
          padding: 12,
          marginBottom: 8,
        }}
      >
        <View style={{ width: 5, alignSelf: 'stretch', borderRadius: 3, backgroundColor: hasta.okunmamis ? colors.danger : colors.primary }} />
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="body" weight={700} numberOfLines={1}>
            {hasta.ad}
          </Text>
          <Text variant="label" weight={500} color={hasta.okunmamis ? 'danger' : 'inkMuted'}>
            {subtitle(hasta)}
          </Text>
        </View>
        {hasta.okunmamis ? <Chip label="YENİ" tone="danger" /> : <DensityDots levels={hasta.yogunluk} />}
      </PressableScale>
    </Animated.View>
  );
}
```

`mobile/src/features/dosyalar/DosyalarEkrani.tsx`:

```tsx
import { FlashList } from '@shopify/flash-list';
import { FolderSearch } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useHastalar } from '@/api/hooks';
import { useTheme } from '@/theme/ThemeProvider';
import { EmptyState, ErrorState, FilterChips, SearchField, Skeleton, TAB_BAR_SPACE, Text } from '@/ui';
import { DosyaKarti } from './DosyaKarti';
import { filterPatients, type Filtre } from './filtre';

export function DosyalarEkrani() {
  const { colors } = useTheme();
  const query = useHastalar();
  const [arama, setArama] = useState('');
  const [filtre, setFiltre] = useState<Filtre>('tumu');
  const all = query.data ?? [];
  const list = useMemo(() => filterPatients(all, arama, filtre), [all, arama, filtre]);
  const okunmamis = all.filter((p) => p.okunmamis).length;

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{ paddingHorizontal: 16, paddingTop: 8, gap: 10 }}>
        <Text variant="title">Dosyalar</Text>
        <SearchField value={arama} onChangeText={setArama} placeholder="İsimle ara" />
        <FilterChips<Filtre>
          value={filtre}
          onChange={setFiltre}
          options={[
            { value: 'tumu', label: `Tümü ${all.length || ''}`.trim() },
            { value: 'son', label: 'Son ziyaret' },
            { value: 'okunmadi', label: `Okunmadı ${okunmamis}` },
          ]}
        />
      </View>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : query.isPending ? (
        <View style={{ padding: 16, gap: 8 }}>
          {Array.from({ length: 7 }, (_, i) => (
            <Skeleton key={i} height={62} radius={18} />
          ))}
        </View>
      ) : (
        <FlashList
          data={list}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item, index }) => <DosyaKarti hasta={item} index={index} />}
          contentContainerStyle={{ padding: 16, paddingBottom: TAB_BAR_SPACE }}
          onRefresh={() => query.refetch()}
          refreshing={query.isRefetching}
          keyboardDismissMode="on-drag"
          ListEmptyComponent={
            <EmptyState
              icon={<FolderSearch size={36} color={colors.inkMuted} />}
              title="Sonuç yok"
              message={arama ? `"${arama}" ile eşleşen dosya bulunamadı.` : 'Bu filtrede dosya yok.'}
            />
          }
        />
      )}
    </SafeAreaView>
  );
}
```

> FlashList sürümün `estimatedItemSize` istiyorsa (v1) `estimatedItemSize={70}` ekle; v2'de gerekmez.

`mobile/src/features/dosya-detay/NotKarti.tsx`:

```tsx
import { useState } from 'react';
import { View } from 'react-native';
import type { Not } from '@/api/types';
import { Card, Chip, OcrText, PressableScale } from '@/ui';

export function NotKarti({ not }: { not: Not }) {
  const [acik, setAcik] = useState(false);
  return (
    <PressableScale accessibilityLabel="Notu aç/kapat" onPress={() => setAcik((v) => !v)}>
      <Card style={{ gap: 10 }}>
        {not.metin ? (
          <OcrText key={acik ? 'acik' : 'kapali'} text={not.metin} highlights={not.vurgular} numberOfLines={acik ? undefined : 4} animate={acik} />
        ) : (
          <OcrText text="(Bu notta okunabilir metin yok)" highlights={[]} animate={false} />
        )}
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
          {not.ilaclar.length > 0 && <Chip label={`${not.ilaclar.length} ilaç`} tone="highlight" />}
          {not.belirti_sayisi > 0 && <Chip label={`${not.belirti_sayisi} belirti`} tone="primary" />}
          {acik &&
            not.ilaclar.map((ilac) => (
              <Chip key={ilac.ad} label={[ilac.ad, ilac.doz, ilac.siklik].filter(Boolean).join(' · ')} tone="neutral" />
            ))}
        </View>
      </Card>
    </PressableScale>
  );
}
```

> `gorsel_var` arşiv notlarında her zaman `false`; "Ham sayfa" düğmesi Aşama 2'ye kadar hiç çizilmez (spec §6.3).

`mobile/src/features/dosya-detay/DosyaDetayEkrani.tsx`:

```tsx
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { ChevronLeft } from 'lucide-react-native';
import { ActivityIndicator, Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useHasta, useNotlar } from '@/api/hooks';
import type { HastaDetayi } from '@/api/types';
import { formatDate, initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { ErrorState, Skeleton, Stamp, Text, TimelineItem } from '@/ui';
import { NotKarti } from './NotKarti';

function Baslik({ hasta }: { hasta: HastaDetayi | undefined }) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const meta = hasta ? [hasta.cinsiyet, hasta.yas !== null ? `${hasta.yas}` : null].filter(Boolean).join(' · ') : '';
  return (
    <View style={{ backgroundColor: colors.deep, paddingTop: insets.top + 6, paddingHorizontal: 18, paddingBottom: 18, borderBottomLeftRadius: 26, borderBottomRightRadius: 26 }}>
      <Pressable accessibilityLabel="Geri" onPress={() => router.back()} hitSlop={12} style={{ flexDirection: 'row', alignItems: 'center' }}>
        <ChevronLeft size={20} color={colors.onDeep} />
        <Text variant="bodySmall" color="onDeep" style={{ opacity: 0.75 }}>
          Dosyalar
        </Text>
      </Pressable>
      {!hasta ? (
        <View style={{ marginTop: 14, gap: 8 }}>
          <Skeleton height={50} width="70%" />
          <Skeleton height={54} />
        </View>
      ) : (
        <>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 12 }}>
            <View style={{ width: 50, height: 50, borderRadius: 16, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' }}>
              <Text variant="heading" weight={800} color="onAccent">
                {initials(hasta.ad)}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text variant="title" color="onDeep" numberOfLines={1}>
                {hasta.ad}
              </Text>
              <Text variant="bodySmall" color="onDeep" style={{ opacity: 0.7 }}>
                {meta ? `${meta} · ` : ''}
                <Text variant="mono" color="onDeep">{hasta.dosya_no}</Text>
              </Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 14 }}>
            {[
              [String(hasta.not_sayisi), 'not'],
              [String(hasta.ilac_sayisi), 'ilaç'],
              [hasta.ilk_kayit ? hasta.ilk_kayit.slice(0, 4) : '—', 'ilk kayıt'],
            ].map(([value, label]) => (
              <View key={label} style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 12, padding: 10 }}>
                <Text variant="heading" weight={800} color="onDeep">
                  {value}
                </Text>
                <Text variant="label" weight={500} color="onDeep" style={{ opacity: 0.7 }}>
                  {label}
                </Text>
              </View>
            ))}
          </View>
        </>
      )}
    </View>
  );
}

export function DosyaDetayEkrani({ id }: { id: number }) {
  const { colors } = useTheme();
  const hasta = useHasta(id);
  const notlar = useNotlar(id);
  const items = notlar.data?.pages.flatMap((p) => p.notlar) ?? [];

  if (hasta.isError) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <Baslik hasta={undefined} />
        <ErrorState error={hasta.error} onRetry={() => hasta.refetch()} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <FlashList
        data={items}
        keyExtractor={(n) => String(n.id)}
        ListHeaderComponent={
          <View style={{ marginBottom: 16 }}>
            <Baslik hasta={hasta.data} />
          </View>
        }
        renderItem={({ item, index }) => (
          <View style={{ paddingHorizontal: 16 }}>
            <TimelineItem
              index={index}
              latest={index === 0}
              isLast={index === items.length - 1 && !notlar.hasNextPage}
              title={formatDate(item.tarih)}
              subtitle={item.sayfa_no ? `sayfa ${item.sayfa_no}` : undefined}
            >
              <NotKarti not={item} />
            </TimelineItem>
          </View>
        )}
        onEndReachedThreshold={0.6}
        onEndReached={() => {
          if (notlar.hasNextPage && !notlar.isFetchingNextPage) notlar.fetchNextPage();
        }}
        ListEmptyComponent={
          notlar.isPending ? (
            <View style={{ padding: 16, gap: 10 }}>
              <Skeleton height={120} radius={18} />
              <Skeleton height={120} radius={18} />
            </View>
          ) : notlar.isError ? (
            <ErrorState error={notlar.error} onRetry={() => notlar.refetch()} />
          ) : (
            <View style={{ paddingTop: 30, gap: 16, paddingHorizontal: 24 }}>
              <Stamp title="HENÜZ OKUNMADI" subtitle="ANALİZ EDİLMİŞ RAPOR YOK" />
              <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
                Bu dosyada OCR'dan geçmiş not bulunmuyor.
              </Text>
            </View>
          )
        }
        ListFooterComponent={
          notlar.isFetchingNextPage ? <ActivityIndicator style={{ marginVertical: 20 }} color={colors.primary} /> : <View style={{ height: 40 }} />
        }
      />
    </View>
  );
}
```

`mobile/app/(tabs)/dosyalar.tsx`:

```tsx
import { RoleGuard } from '@/auth/RoleGuard';
import { DosyalarEkrani } from '@/features/dosyalar/DosyalarEkrani';

export default function Dosyalar() {
  return (
    <RoleGuard allow={['doktor', 'hemsire']}>
      <DosyalarEkrani />
    </RoleGuard>
  );
}
```

`mobile/app/dosya/[id].tsx`:

```tsx
import { useLocalSearchParams } from 'expo-router';
import { RoleGuard } from '@/auth/RoleGuard';
import { DosyaDetayEkrani } from '@/features/dosya-detay/DosyaDetayEkrani';

export default function Dosya() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <RoleGuard allow={['doktor', 'hemsire']}>
      <DosyaDetayEkrani id={Number(id)} />
    </RoleGuard>
  );
}
```

- [ ] **Step 4: Run tests and type check**

Run: `cd mobile && npx jest && npx tsc --noEmit`
Expected: tümü geçer

- [ ] **Step 5: Cihazda doğrulama**

Dosyalar: 434 dosya listelenir, kartlar kayarak girer, "ayse" araması aksanlı ismi bulur, "Son ziyaret" filtresi tarihsiz dosyaları sona atar, tarihli notu olmayan dosyada "tarihli not yok" yazar. Bir dosyaya basınca detay açılır: koyu başlık, sayaçlar, zaman çizgisinde ilk not nane rengi nokta; not kartına dokununca metin açılır ve ilaçlar sırayla fosforlanır; aşağı kaydırınca yeni notlar yüklenir ve en sonda "Tarihsiz" başlıklı notlar görünür. Notu olmayan bir dosyada kaşe basılır.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/features/dosyalar mobile/src/features/dosya-detay "mobile/app/(tabs)/dosyalar.tsx" "mobile/app/dosya/[id].tsx"
git commit -m "feat(mobil): dosya listesi, arama/filtre ve zaman çizgili dosya detayı"
```

---

### Task 15: Yeni hasta formu (yerel taslak)

**Files:**
- Create: `mobile/src/features/yeni-hasta/{YeniHastaEkrani.tsx,KimlikAdimi.tsx,RaporAdimi.tsx,taslak.ts,dogrulama.ts,DateField.tsx}`
- Modify: `mobile/app/(tabs)/yeni.tsx`
- Test: `mobile/src/features/yeni-hasta/__tests__/dogrulama.test.ts`

**Interfaces:**
- Consumes: `isValidTcKimlik`, `prefs` (`DraftPatient`, `getDrafts`, `setDrafts`), UI bileşenleri
- Produces:
  - `type KimlikForm = { adSoyad: string; cinsiyet: 'Kadın' | 'Erkek' | null; dogumTarihi: string | null; tcKimlik: string }`
  - `validateKimlik(form: KimlikForm, today: Date): Partial<Record<keyof KimlikForm, string>>`
  - `saveDraft(form: KimlikForm, pageUris: string[]): Promise<DraftPatient>`, `deleteDraft(id: string): Promise<void>`, `movePage(pages: string[], index: number, delta: -1 | 1): string[]`

- [ ] **Step 1: Write the failing test** — `mobile/src/features/yeni-hasta/__tests__/dogrulama.test.ts`

```ts
import { validateKimlik } from '../dogrulama';
import { movePage } from '../taslak';

jest.mock('expo-file-system', () => ({}));
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

const today = new Date('2026-10-12T12:00:00Z');
const valid = { adSoyad: 'Ali Rıza', cinsiyet: 'Erkek' as const, dogumTarihi: '1985-04-02', tcKimlik: '10000000146' };

it('geçerli form hatasız', () => {
  expect(validateKimlik(valid, today)).toEqual({});
});

it('ad soyad zorunlu, en az iki kelime', () => {
  expect(validateKimlik({ ...valid, adSoyad: '  ' }, today).adSoyad).toBe('Ad soyad gerekli.');
  expect(validateKimlik({ ...valid, adSoyad: 'Ali' }, today).adSoyad).toBe('Ad ve soyadı birlikte girin.');
});

it('TC boşsa sorun yok, doluysa algoritma kontrolü', () => {
  expect(validateKimlik({ ...valid, tcKimlik: '' }, today).tcKimlik).toBeUndefined();
  expect(validateKimlik({ ...valid, tcKimlik: '10000000147' }, today).tcKimlik).toBe('Geçerli bir T.C. Kimlik No girin.');
});

it('gelecekteki doğum tarihi reddedilir', () => {
  expect(validateKimlik({ ...valid, dogumTarihi: '2027-01-01' }, today).dogumTarihi).toBe('Doğum tarihi gelecekte olamaz.');
});

it('sayfa sırası', () => {
  expect(movePage(['a', 'b', 'c'], 0, 1)).toEqual(['b', 'a', 'c']);
  expect(movePage(['a', 'b', 'c'], 0, -1)).toEqual(['a', 'b', 'c']);
  expect(movePage(['a', 'b', 'c'], 2, 1)).toEqual(['a', 'b', 'c']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && npx jest src/features/yeni-hasta`
Expected: FAIL — modül yok

- [ ] **Step 3: Write implementations**

`mobile/src/features/yeni-hasta/dogrulama.ts`:

```ts
import { isValidTcKimlik } from '@/lib/tcKimlik';

export type KimlikForm = {
  adSoyad: string;
  cinsiyet: 'Kadın' | 'Erkek' | null;
  dogumTarihi: string | null; // YYYY-MM-DD
  tcKimlik: string;
};

export function validateKimlik(form: KimlikForm, today: Date): Partial<Record<keyof KimlikForm, string>> {
  const errors: Partial<Record<keyof KimlikForm, string>> = {};
  const name = form.adSoyad.trim();
  if (!name) errors.adSoyad = 'Ad soyad gerekli.';
  else if (name.split(/\s+/).length < 2) errors.adSoyad = 'Ad ve soyadı birlikte girin.';
  if (form.tcKimlik && !isValidTcKimlik(form.tcKimlik)) errors.tcKimlik = 'Geçerli bir T.C. Kimlik No girin.';
  if (form.dogumTarihi && form.dogumTarihi > today.toISOString().slice(0, 10)) {
    errors.dogumTarihi = 'Doğum tarihi gelecekte olamaz.';
  }
  return errors;
}
```

`mobile/src/features/yeni-hasta/taslak.ts`:

```ts
import { Directory, File, Paths } from 'expo-file-system';
import { prefs, type DraftPatient } from '@/storage/prefs';
import type { KimlikForm } from './dogrulama';

export function movePage(pages: string[], index: number, delta: -1 | 1): string[] {
  const target = index + delta;
  if (target < 0 || target >= pages.length) return pages;
  const next = [...pages];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

/** Görselleri uygulama belgeler dizinine kopyalar (önbellek temizlense de kalsın) ve taslağı kaydeder. */
export async function saveDraft(form: KimlikForm, pageUris: string[]): Promise<DraftPatient> {
  const id = `taslak-${Date.now()}`;
  const dir = new Directory(Paths.document, 'taslaklar', id);
  dir.create({ intermediates: true });
  const sayfalar = pageUris.map((uri, i) => {
    const dest = new File(dir, `sayfa-${i + 1}.jpg`);
    new File(uri).copy(dest);
    return dest.uri;
  });
  const draft: DraftPatient = {
    id,
    adSoyad: form.adSoyad.trim(),
    cinsiyet: form.cinsiyet,
    dogumTarihi: form.dogumTarihi,
    tcKimlik: form.tcKimlik || null,
    sayfalar,
    olusturma: new Date().toISOString(),
  };
  await prefs.setDrafts([draft, ...(await prefs.getDrafts())]);
  return draft;
}

export async function deleteDraft(id: string): Promise<void> {
  const dir = new Directory(Paths.document, 'taslaklar', id);
  if (dir.exists) dir.delete();
  await prefs.setDrafts((await prefs.getDrafts()).filter((d) => d.id !== id));
}
```

> `expo-file-system`'in `File`/`Directory`/`Paths` API'sini kurulu sürümün belgesiyle doğrula (context7: `expo-file-system`). Yalnızca eski API varsa aynı davranışı `expo-file-system/legacy` → `makeDirectoryAsync`, `copyAsync`, `deleteAsync`, `documentDirectory` ile yaz.

`mobile/src/features/yeni-hasta/DateField.tsx`:

```tsx
import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, View } from 'react-native';
import { formatDate } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { radius } from '@/theme/tokens';
import { PressableScale, Text } from '@/ui';

type Props = { label: string; value: string | null; onChange: (iso: string) => void; error?: string };

function toIso(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function DateField({ label, value, onChange, error }: Props) {
  const { colors, name } = useTheme();
  const [open, setOpen] = useState(false);
  const current = value ? new Date(`${value}T12:00:00`) : new Date(1990, 0, 1);
  return (
    <View style={{ gap: 6 }}>
      <Text variant="label" color="inkMuted">
        {label}
      </Text>
      {Platform.OS === 'ios' ? (
        <View style={{ alignItems: 'flex-start' }}>
          <DateTimePicker
            value={current}
            mode="date"
            display="compact"
            maximumDate={new Date()}
            locale="tr-TR"
            themeVariant={name}
            accentColor={colors.primary}
            onChange={(_, date) => date && onChange(toIso(date))}
          />
        </View>
      ) : (
        <>
          <PressableScale
            accessibilityLabel={label}
            onPress={() => setOpen(true)}
            style={{ backgroundColor: colors.surface, borderRadius: radius.input, borderWidth: 1, borderColor: error ? colors.danger : colors.line, padding: 12 }}
          >
            <Text variant="body" color={value ? 'ink' : 'inkMuted'}>
              {value ? formatDate(value) : 'Tarih seçin'}
            </Text>
          </PressableScale>
          {open && (
            <DateTimePicker
              value={current}
              mode="date"
              maximumDate={new Date()}
              onChange={(event, date) => {
                setOpen(false);
                if (event.type === 'set' && date) onChange(toIso(date));
              }}
            />
          )}
        </>
      )}
      {error ? (
        <Text variant="label" color="danger">
          {error}
        </Text>
      ) : null}
    </View>
  );
}
```

`mobile/src/features/yeni-hasta/KimlikAdimi.tsx`:

```tsx
import { View } from 'react-native';
import { Button, FormField, SegmentedControl, Text } from '@/ui';
import { DateField } from './DateField';
import type { KimlikForm } from './dogrulama';

type Props = {
  form: KimlikForm;
  errors: Partial<Record<keyof KimlikForm, string>>;
  onChange: (patch: Partial<KimlikForm>) => void;
  onNext: () => void;
};

export function KimlikAdimi({ form, errors, onChange, onNext }: Props) {
  return (
    <View style={{ gap: 14 }}>
      <FormField label="Ad soyad *" value={form.adSoyad} onChangeText={(adSoyad) => onChange({ adSoyad })} autoCapitalize="words" error={errors.adSoyad} />
      <View style={{ gap: 6 }}>
        <Text variant="label" color="inkMuted">
          Cinsiyet
        </Text>
        <SegmentedControl<'Kadın' | 'Erkek' | 'belirsiz'>
          value={form.cinsiyet ?? 'belirsiz'}
          onChange={(v) => onChange({ cinsiyet: v === 'belirsiz' ? null : v })}
          options={[
            { value: 'Kadın', label: 'Kadın' },
            { value: 'Erkek', label: 'Erkek' },
            { value: 'belirsiz', label: 'Belirtilmedi' },
          ]}
        />
      </View>
      <DateField label="Doğum tarihi" value={form.dogumTarihi} onChange={(dogumTarihi) => onChange({ dogumTarihi })} error={errors.dogumTarihi} />
      <FormField
        label="T.C. Kimlik No"
        value={form.tcKimlik}
        onChangeText={(t) => onChange({ tcKimlik: t.replace(/\D/g, '').slice(0, 11) })}
        keyboardType="number-pad"
        maxLength={11}
        mono
        error={errors.tcKimlik}
        placeholder="11 hane"
      />
      <Button title="Devam: rapor sayfaları" onPress={onNext} />
    </View>
  );
}
```

`mobile/src/features/yeni-hasta/RaporAdimi.tsx`:

```tsx
import * as ImagePicker from 'expo-image-picker';
import { ArrowLeft, ArrowRight, Camera, ImagePlus, Trash2 } from 'lucide-react-native';
import { Alert, Image, Pressable, ScrollView, View } from 'react-native';
import Animated, { FadeIn, LinearTransition } from 'react-native-reanimated';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Text } from '@/ui';
import { movePage } from './taslak';

type Props = { pages: string[]; onChange: (pages: string[]) => void; onBack: () => void; onSave: () => void; saving: boolean };

export function RaporAdimi({ pages, onChange, onBack, onSave, saving }: Props) {
  const { colors } = useTheme();

  async function pick(source: 'kamera' | 'galeri') {
    const permission =
      source === 'kamera' ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('İzin gerekli', source === 'kamera' ? 'Kamera izni verilmedi.' : 'Galeri izni verilmedi.');
      return;
    }
    const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.7, allowsMultipleSelection: source === 'galeri' };
    const result = source === 'kamera' ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    if (!result.canceled) onChange([...pages, ...result.assets.map((a) => a.uri)]);
  }

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Button title="Fotoğraf çek" variant="deep" icon={<Camera size={18} color={colors.onDeep} />} onPress={() => pick('kamera')} />
        </View>
        <View style={{ flex: 1 }}>
          <Button title="Galeriden" variant="deep" icon={<ImagePlus size={18} color={colors.onDeep} />} onPress={() => pick('galeri')} />
        </View>
      </View>

      {pages.length === 0 ? (
        <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center', paddingVertical: 24 }}>
          Henüz sayfa eklenmedi. Raporun her sayfası ayrı bir fotoğraf olarak eklenir.
        </Text>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 12, paddingVertical: 6 }}>
          {pages.map((uri, index) => (
            <Animated.View key={uri} entering={FadeIn} layout={LinearTransition.springify()} style={{ width: 120, gap: 6 }}>
              <Image source={{ uri }} style={{ width: 120, height: 160, borderRadius: 10, backgroundColor: colors.line }} />
              <Text variant="mono" color="inkMuted">{`sayfa ${index + 1}`}</Text>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <Pressable accessibilityLabel="Sola taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, -1))}>
                  <ArrowLeft size={18} color={colors.ink} />
                </Pressable>
                <Pressable accessibilityLabel="Sayfayı sil" hitSlop={8} onPress={() => onChange(pages.filter((_, i) => i !== index))}>
                  <Trash2 size={18} color={colors.danger} />
                </Pressable>
                <Pressable accessibilityLabel="Sağa taşı" hitSlop={8} onPress={() => onChange(movePage(pages, index, 1))}>
                  <ArrowRight size={18} color={colors.ink} />
                </Pressable>
              </View>
            </Animated.View>
          ))}
        </ScrollView>
      )}

      <Button title="Taslağı kaydet" onPress={onSave} loading={saving} disabled={pages.length === 0} />
      <Button title="Geri: kimlik bilgileri" variant="ghost" onPress={onBack} />
    </View>
  );
}
```

`mobile/src/features/yeni-hasta/YeniHastaEkrani.tsx`:

```tsx
import { useFocusEffect } from 'expo-router';
import { Trash2 } from 'lucide-react-native';
import { useCallback, useState } from 'react';
import { Alert, Pressable, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { maskTcKimlik } from '@/lib/tcKimlik';
import { prefs, type DraftPatient } from '@/storage/prefs';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Card, Chip, Screen, Stamp, Text } from '@/ui';
import { validateKimlik, type KimlikForm } from './dogrulama';
import { KimlikAdimi } from './KimlikAdimi';
import { RaporAdimi } from './RaporAdimi';
import { deleteDraft, saveDraft } from './taslak';

const EMPTY: KimlikForm = { adSoyad: '', cinsiyet: null, dogumTarihi: null, tcKimlik: '' };

export function YeniHastaEkrani() {
  const { colors } = useTheme();
  const [adim, setAdim] = useState<1 | 2 | 'bitti'>(1);
  const [form, setForm] = useState<KimlikForm>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof KimlikForm, string>>>({});
  const [pages, setPages] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [drafts, setDrafts] = useState<DraftPatient[]>([]);

  useFocusEffect(
    useCallback(() => {
      prefs.getDrafts().then(setDrafts);
    }, []),
  );

  function next() {
    const found = validateKimlik(form, new Date());
    setErrors(found);
    if (Object.keys(found).length === 0) setAdim(2);
  }

  async function save() {
    setSaving(true);
    try {
      await saveDraft(form, pages);
      setDrafts(await prefs.getDrafts());
      setAdim('bitti');
    } catch {
      Alert.alert('Kaydedilemedi', 'Taslak cihaza yazılamadı. Lütfen tekrar deneyin.');
    } finally {
      setSaving(false);
    }
  }

  function reset() {
    setForm(EMPTY);
    setPages([]);
    setErrors({});
    setAdim(1);
  }

  return (
    <Screen>
      <View style={{ gap: 4 }}>
        <Text variant="title">Yeni dosya</Text>
        <Text variant="bodySmall" color="inkMuted">
          {adim === 1 ? 'Adım 1/2 · Kimlik bilgileri' : adim === 2 ? 'Adım 2/2 · Rapor sayfaları' : 'Taslak kaydedildi'}
        </Text>
      </View>

      {adim !== 'bitti' && (
        <View style={{ flexDirection: 'row', gap: 6 }}>
          <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: colors.primary }} />
          <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: adim === 2 ? colors.primary : colors.line }} />
        </View>
      )}

      {adim === 1 && (
        <Animated.View entering={FadeInDown.duration(350)}>
          <KimlikAdimi form={form} errors={errors} onChange={(patch) => setForm((f) => ({ ...f, ...patch }))} onNext={next} />
        </Animated.View>
      )}
      {adim === 2 && (
        <Animated.View entering={FadeInDown.duration(350)}>
          <RaporAdimi pages={pages} onChange={setPages} onBack={() => setAdim(1)} onSave={save} saving={saving} />
        </Animated.View>
      )}
      {adim === 'bitti' && (
        <View style={{ gap: 18, paddingVertical: 20 }}>
          <Stamp title="HENÜZ OKUNMADI" subtitle="ANALİZ EDİLMİŞ RAPOR YOK" />
          <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
            Taslak bu cihazda saklandı. Sunucuya kayıt ve OCR bir sonraki aşamada eklenecek.
          </Text>
          <Button title="Yeni dosya başlat" onPress={reset} />
        </View>
      )}

      {drafts.length > 0 && (
        <View style={{ gap: 8, marginTop: 10 }}>
          <Text variant="label" color="inkMuted">
            Cihazdaki taslaklar · {drafts.length}
          </Text>
          {drafts.map((draft) => (
            <Card key={draft.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text variant="body" weight={700}>
                  {draft.adSoyad}
                </Text>
                <Text variant="label" weight={500} color="inkMuted">
                  {[draft.cinsiyet, draft.tcKimlik ? maskTcKimlik(draft.tcKimlik) : null, `${draft.sayfalar.length} sayfa`].filter(Boolean).join(' · ')}
                </Text>
              </View>
              <Chip label="Taslak" tone="danger" />
              <Pressable
                accessibilityLabel="Taslağı sil"
                hitSlop={8}
                onPress={async () => {
                  await deleteDraft(draft.id);
                  setDrafts(await prefs.getDrafts());
                }}
              >
                <Trash2 size={18} color={colors.inkMuted} />
              </Pressable>
            </Card>
          ))}
        </View>
      )}
    </Screen>
  );
}
```

`mobile/app/(tabs)/yeni.tsx`:

```tsx
import { RoleGuard } from '@/auth/RoleGuard';
import { YeniHastaEkrani } from '@/features/yeni-hasta/YeniHastaEkrani';

export default function Yeni() {
  return (
    <RoleGuard allow={['doktor']}>
      <YeniHastaEkrani />
    </RoleGuard>
  );
}
```

- [ ] **Step 4: Run tests and type check**

Run: `cd mobile && npx jest && npx tsc --noEmit`
Expected: tümü geçer

- [ ] **Step 5: Cihazda doğrulama**

Doktor → Yeni: tek kelimelik ad ve `10000000147` TC ile "Devam" hata gösterir; düzeltince 2. adıma geçer; kamera ve galeri izin ister, sayfalar küçük resim olarak gelir, sola/sağa taşınır ve silinir; "Taslağı kaydet" sonrası kaşe basılır ve taslak listede maskeli TC ile görünür; uygulama kapatılıp açılınca taslak duruyor; silince kaybolur. Hemşire hesabında bu sekme görünmez.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/features/yeni-hasta "mobile/app/(tabs)/yeni.tsx"
git commit -m "feat(mobil): iki adımlı yeni hasta formu ve cihaz taslağı"
```

---

### Task 16: Ayarlar ve admin ekranları

**Files:**
- Create: `mobile/src/features/ayarlar/AyarlarEkrani.tsx`, `mobile/src/features/admin/{SistemEkrani.tsx,KullanicilarEkrani.tsx}`
- Modify: `mobile/app/(tabs)/{ayarlar,sistem,kullanicilar}.tsx`

**Interfaces:**
- Consumes: `useAuth`, `useTheme`, `useServerUrl`, `useSistem`, `useKullanicilar`, `formatNumber`, `initials`, UI bileşenleri

- [ ] **Step 1: `mobile/src/features/ayarlar/AyarlarEkrani.tsx`**

```tsx
import { useState } from 'react';
import { View } from 'react-native';
import { useServerUrl } from '@/api/ServerUrlProvider';
import { useAuth } from '@/auth/AuthProvider';
import { initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import type { ThemePreference } from '@/theme/tokens';
import { Button, Card, Chip, FormField, Screen, SegmentedControl, Text } from '@/ui';

const ROL_ADI = { doktor: 'Doktor', hemsire: 'Hemşire', admin: 'Admin' } as const;

export function AyarlarEkrani() {
  const { colors, preference, setPreference } = useTheme();
  const { user, logout } = useAuth();
  const { url, setUrl } = useServerUrl();
  const [draftUrl, setDraftUrl] = useState(url);
  const [testResult, setTestResult] = useState<'ok' | 'hata' | null>(null);
  const [testing, setTesting] = useState(false);

  async function testConnection() {
    setTesting(true);
    setTestResult(null);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(`${draftUrl.trim().replace(/\/+$/, '')}/api/m/saglik`, { signal: controller.signal });
      setTestResult(response.ok ? 'ok' : 'hata');
      if (response.ok) await setUrl(draftUrl);
    } catch {
      setTestResult('hata');
    } finally {
      clearTimeout(timer);
      setTesting(false);
    }
  }

  return (
    <Screen>
      <Text variant="title">Ayarlar</Text>

      <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View style={{ width: 48, height: 48, borderRadius: 15, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' }}>
          <Text variant="heading" weight={800} color="onAccent">
            {initials(user?.ad_soyad ?? '')}
          </Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text variant="heading">{user?.ad_soyad}</Text>
          <Text variant="bodySmall" color="inkMuted">
            {user ? ROL_ADI[user.rol] : ''} · <Text variant="mono" color="inkMuted">{user?.kullanici_adi}</Text>
          </Text>
        </View>
      </Card>

      <Card style={{ gap: 10 }}>
        <Text variant="label" color="inkMuted">
          Tema
        </Text>
        <SegmentedControl<ThemePreference>
          value={preference}
          onChange={setPreference}
          options={[
            { value: 'sistem', label: 'Sistem' },
            { value: 'acik', label: 'Açık' },
            { value: 'koyu', label: 'Koyu' },
          ]}
        />
      </Card>

      <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 10, opacity: 0.7 }}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="body" weight={700}>
            Google hesabı
          </Text>
          <Text variant="label" weight={500} color="inkMuted">
            Farklı e-postalı bir Google hesabını bu hesaba bağlayın.
          </Text>
        </View>
        <Chip label="Yakında" tone="primary" />
      </Card>

      <Card style={{ gap: 10 }}>
        <FormField
          label="Sunucu adresi"
          value={draftUrl}
          onChangeText={(v) => {
            setDraftUrl(v);
            setTestResult(null);
          }}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          mono
        />
        {testResult && (
          <Text variant="label" color={testResult === 'ok' ? 'primary' : 'danger'}>
            {testResult === 'ok' ? 'Bağlantı başarılı, adres kaydedildi.' : 'Sunucuya ulaşılamadı.'}
          </Text>
        )}
        <Button title="Bağlantıyı sına" variant="deep" onPress={testConnection} loading={testing} />
      </Card>

      <Button title="Çıkış yap" variant="ghost" onPress={logout} />
    </Screen>
  );
}
```

- [ ] **Step 2: `mobile/src/features/admin/SistemEkrani.tsx`**

```tsx
import { View } from 'react-native';
import { useSistem } from '@/api/hooks';
import { formatNumber } from '@/lib/format';
import { Card, Chip, ErrorState, HeroCard, Screen, Skeleton, Text } from '@/ui';

const TABLO_ADI: Record<string, string> = {
  hasta: 'Hasta dosyası',
  ziyaret: 'Ziyaret notu',
  ilac_kullanimi: 'İlaç kaydı',
  semptom_kaydi: 'Semptom kaydı',
  ilac_sozluk: 'Sözlükteki ilaç',
  kullanici: 'Kullanıcı',
};

export function SistemEkrani() {
  const query = useSistem();
  const data = query.data;
  return (
    <Screen refreshing={query.isRefetching} onRefresh={() => query.refetch()}>
      <Text variant="title">Sistem</Text>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !data ? (
        <Skeleton height={260} radius={22} />
      ) : (
        <>
          <HeroCard>
            <Text variant="label" color="onDeep" style={{ opacity: 0.7 }}>
              Veritabanı
            </Text>
            <Text variant="display" color="onDeep">
              {`${data.db_boyutu_mb} MB`}
            </Text>
            <View style={{ flexDirection: 'row', gap: 6, marginTop: 8 }}>
              <Chip label={data.semptom_indeksi ? 'Semptom indeksi hazır' : 'Semptom indeksi yok'} tone={data.semptom_indeksi ? 'accent' : 'danger'} />
              <Chip label={data.ollama ? 'Ollama açık' : 'Ollama kapalı'} tone={data.ollama ? 'accent' : 'neutral'} />
            </View>
          </HeroCard>
          <Card style={{ gap: 10 }}>
            {Object.entries(data.tablolar).map(([table, count]) => (
              <View key={table} style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <Text variant="bodySmall">{TABLO_ADI[table] ?? table}</Text>
                <Text variant="mono" color="inkMuted">
                  {formatNumber(count)}
                </Text>
              </View>
            ))}
          </Card>
        </>
      )}
    </Screen>
  );
}
```

- [ ] **Step 3: `mobile/src/features/admin/KullanicilarEkrani.tsx`**

```tsx
import { View } from 'react-native';
import { useKullanicilar } from '@/api/hooks';
import { initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { Card, Chip, ErrorState, Screen, Skeleton, Text } from '@/ui';

const ROL_ADI = { doktor: 'Doktor', hemsire: 'Hemşire', admin: 'Admin' } as const;

export function KullanicilarEkrani() {
  const { colors } = useTheme();
  const query = useKullanicilar();
  return (
    <Screen refreshing={query.isRefetching} onRefresh={() => query.refetch()}>
      <Text variant="title">Kullanıcılar</Text>
      <Text variant="bodySmall" color="inkMuted">
        Aşama 1'de hesaplar sunucudaki seed scriptiyle oluşturulur; buradan düzenlenmez.
      </Text>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !query.data ? (
        <Skeleton height={200} radius={18} />
      ) : (
        query.data.map((user) => (
          <Card key={user.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <View style={{ width: 42, height: 42, borderRadius: 13, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' }}>
              <Text variant="bodySmall" weight={800} color="primary">
                {initials(user.ad_soyad)}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text variant="body" weight={700}>
                {user.ad_soyad}
              </Text>
              <Text variant="mono" color="inkMuted">
                {user.kullanici_adi}
              </Text>
            </View>
            <View style={{ alignItems: 'flex-end', gap: 4 }}>
              <Chip label={ROL_ADI[user.rol]} tone="primary" />
              <Text variant="label" weight={500} color="inkMuted">
                {user.google_bagli ? 'Google bağlı' : 'Google yok'}
              </Text>
            </View>
          </Card>
        ))
      )}
    </Screen>
  );
}
```

- [ ] **Step 4: Rota dosyaları**

`mobile/app/(tabs)/ayarlar.tsx`:

```tsx
import { AyarlarEkrani } from '@/features/ayarlar/AyarlarEkrani';

export default function Ayarlar() {
  return <AyarlarEkrani />;
}
```

`mobile/app/(tabs)/sistem.tsx`:

```tsx
import { RoleGuard } from '@/auth/RoleGuard';
import { SistemEkrani } from '@/features/admin/SistemEkrani';

export default function Sistem() {
  return (
    <RoleGuard allow={['admin']}>
      <SistemEkrani />
    </RoleGuard>
  );
}
```

`mobile/app/(tabs)/kullanicilar.tsx`:

```tsx
import { RoleGuard } from '@/auth/RoleGuard';
import { KullanicilarEkrani } from '@/features/admin/KullanicilarEkrani';

export default function Kullanicilar() {
  return (
    <RoleGuard allow={['admin']}>
      <KullanicilarEkrani />
    </RoleGuard>
  );
}
```

- [ ] **Step 5: Run tests and type check**

Run: `cd mobile && npx jest && npx tsc --noEmit`
Expected: tümü geçer

- [ ] **Step 6: Cihazda doğrulama**

Ayarlar: tema Sistem/Açık/Koyu anında değişir ve uygulama yeniden açılınca korunur; koyu temada tüm ekranlar okunaklı. "Bağlantıyı sına" doğru adreste yeşil mesaj, yanlış adreste kırmızı mesaj verir. Çıkış girişe döner. Admin: Sistem'de DB boyutu ve tablo sayıları (`Hasta dosyası 434`), Kullanıcılar'da üç hesap; admin hiçbir hasta adı görmez.

- [ ] **Step 7: Commit**

```bash
git add mobile/src/features/ayarlar mobile/src/features/admin "mobile/app/(tabs)/ayarlar.tsx" "mobile/app/(tabs)/sistem.tsx" "mobile/app/(tabs)/kullanicilar.tsx"
git commit -m "feat(mobil): ayarlar (tema, sunucu, Google yer tutucu) ve admin ekranları"
```

---

### Task 17: Uçtan uca doğrulama ve son kontroller

**Files:**
- Modify: `mobile/README.md` (sorun giderme bölümü)

- [ ] **Step 1: Worktree'ye gerçek veri bağlantıları** (ana çalışma ağacı yolu `MAIN`)

```bash
MAIN=/Users/ilkaygokbudak/Development/Projects/TRSM_Bitirme
ln -sf "$MAIN/trsm.db" trsm.db
ln -sf "$MAIN/models" models
mkdir -p data
ln -sf "$MAIN/data/symptom_index.npz" data/symptom_index.npz
ln -sf "$MAIN/data/tedavi_gecis_istatistikleri.json" data/tedavi_gecis_istatistikleri.json
git status --short   # symlink'ler .gitignore kapsamında olmalı; listede çıkmamalı
```

> Not: seed scripti gerçek `trsm.db`'ye `kullanici` tablosu ekler (symlink olduğu için ana DB değişir). Bu, `CREATE TABLE IF NOT EXISTS` ile geriye uyumludur; yine de önce yedek al: `cp "$MAIN/trsm.db" "$MAIN/trsm.before_mobile_users_$(date +%Y%m%d).db"`.

- [ ] **Step 2: Sunucu testleri ve seed**

```bash
uv run pytest -q
uv run python scripts/seed_mobile_users.py
TRSM_HOST=0.0.0.0 uv run python demo_server.py
```
Expected: tüm testler geçer; seed üç hesabı oluşturur; sunucu `0.0.0.0:8765`'te açılır.

- [ ] **Step 3: Mobil testler ve doktor kontrolü**

```bash
cd mobile && npm test && npx tsc --noEmit && npx expo-doctor
```
Expected: tümü temiz.

- [ ] **Step 4: Cihazda tam tur** (`.env`'de `EXPO_PUBLIC_API_URL=http://<bilgisayar-IP>:8765`, `npx expo start`, Expo Go)

Kontrol listesi (her madde gözle doğrulanır):
1. Doktor: Özet (434 / 41.676 / grafikler animasyonlu), Dosyalar (arama, filtreler), Dosya detayı (sonsuz kaydırma, tarihsiz notlar sonda, vurgular), Yeni (taslak akışı), Ayarlar.
2. Hemşire: Özet, Dosyalar, Ayarlar; Yeni sekmesi yok.
3. Admin: Sistem, Kullanıcılar, Ayarlar; hasta verisi hiçbir yerde yok.
4. Koyu tema: tüm ekranlar.
5. iOS'ta Ayarlar → Erişilebilirlik → Hareketi Azalt açıkken: sayılar doğrudan son değerle gelir, giriş animasyonları atlanır.
6. Sunucuyu kapat → bir ekranı yenile: "Sunucuya ulaşılamıyor" ve "Tekrar dene"; uygulamayı yeniden açınca bağlantı hatası ekranı "Adresi değiştir" sunar; sunucu açılınca "Tekrar dene" ile devam eder.
7. Sunucuda `data/mobile_secret.key`'i silip sunucuyu yeniden başlat → uygulamada ilk istekte oturum kapanır ve giriş ekranına dönülür.

- [ ] **Step 5: `mobile/README.md` sonuna sorun giderme ekle**

````markdown
## Sorun giderme

- **"Sunucuya ulaşılamıyor"**: Telefon ve bilgisayar aynı Wi-Fi'da mı? Sunucu
  `TRSM_HOST=0.0.0.0` ile mi açıldı? macOS güvenlik duvarı Python'a gelen
  bağlantılara izin veriyor mu? Ayarlar → Sunucu adresinden IP'yi güncelleyin.
- **Port 5000 kullanmayın**: macOS'ta AirPlay Receiver tarafından işgal edilir;
  varsayılan 8765'tir.
- **Oturum aniden kapandı**: Token 12 saat geçerlidir; sunucunun
  `data/mobile_secret.key` dosyası değişirse tüm oturumlar düşer.
- **Google ile giriş**: Aşama 2'dedir; development build ve Google Cloud OAuth
  istemcileri gerektirir, Expo Go ile çalışmaz.
````

- [ ] **Step 6: Commit**

```bash
git add mobile/README.md
git commit -m "docs(mobil): uçtan uca çalıştırma ve sorun giderme"
```

---

## Spec Kapsam Eşlemesi

| Spec bölümü | Görev |
| --- | --- |
| §2 Aşama 1 kapsamı | Task 1–17 |
| §3 Roller ve yetkiler | Task 5 (sunucu), Task 8 `roleTabs`, Task 12 `RoleGuard` + sekme filtreleme |
| §4.1–4.4 Görsel kimlik, token'lar, tipografi, hareket | Task 7, 10, 11 |
| §4.5 Bileşen kataloğu | Task 10, 11 (`DateField` Task 15'te) |
| §5 Mobil mimari | Task 7, 9, 12 (tek `(tabs)` grubu sapması yukarıda açıklandı) |
| §6.1–6.3 Sunucu | Task 1–6 |
| §7 Ekranlar ve durumlar | Task 12–16 |
| §8 Aşama 2 | Bu planda uygulanmaz |
| §9 Gizlilik | Global Constraints, Task 5 (admin 403, `sifre_hash` dışarıda), Task 6 (`TRSM_HOST`), Task 17 (yedek) |
| §10 Test | Task 1–5 (pytest), Task 7–11, 14, 15 (jest), Task 17 (uçtan uca) |

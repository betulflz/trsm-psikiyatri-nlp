# Devam promptu — 19.10.2026 (Windows'a taşıma)

Yeni bilgisayarda VS Code'da Claude Code'a şunu yazın:

> `docs/devam_prompt_2026-10-19.md dosyasını oku ve projeyi bu Windows bilgisayarda çalışır hale getir.`

---

## 0. Önce oku: kurallar (önceki oturumlardan)

- **GİZLİLİK KURALI (en önemlisi):** Hasta sayfalarını, PDF/görsel dosya adlarını (dosya adları hasta adıdır), OCR metinlerini ve veritabanındaki ziyaret metinlerini Claude **okumaz, ekrana yazdırmaz**. Claude'un gördüğü her şey buluta gider. Yalnızca sayısal özetlerle çalış (sayım, oran, süre, boyut). Bir dosyanın içeriğini ya da adını görmen gerekiyorsa, adları gizleyen/sayıya çeviren bir komut kullan. Metinleri ve görselleri kullanıcı yerelde (`rapor.html`, etiketleme sayfası) inceler.
- Kullanıcı geliştirici, klinisyen değil. İlaç/tıbbi bilgileri kullanıcının görüşüne göre değil literatüre göre doğrula.
- Veritabanı: PostgreSQL 16, Docker'da, `127.0.0.1:5434`. Tek tık Windows demo paketi bilerek SQLite'ta.
- `spikes/ocr_karsilastirma/cikti/` hasta verisi içerir, gitignore'da; paylaşılmaz.

## 1. Bu bilgisayarın durumu

Kullanıcı bu Windows bilgisayarı (Monster, 16 GB RAM, NVIDIA GPU) proje bitene kadar ödünç aldı; 9B OCR modeli Mac'te (8 GB) çalışmadığı için. İş bitince her şey silinecek. Proje Mac'ten (21.10.2026) **tek bir zip** ile geldi: `TRSM_tasima.zip`. Açılınca `TRSM_tasima\` oluşur. `TRSM_tasima/ICERIK.txt` beklenen dosya sayılarını yazar; açtıktan sonra say ve karşılaştır.

Yapı:

```
TRSM_tasima/
  TRSM_Bitirme/        proje (.git dahil). models/, data/, .env, yedekler/ içinde.
                       spikes/ocr_karsilastirma/cikti/ = OCR deneme sonuçları + test_seti/
                       (Kitap1.xlsx + TestData/ içinde 10 referans görüntü)
  mobil/               Expo mobil uygulama (.git dahil)
```

**Zip'e bilerek konmayanlar (sen yeniden oluşturursun):**
- `.venv` → `uv sync`
- `node_modules` (`TRSM_Bitirme/mobile` ve `mobil`) → her ikisinde `npm install`
- Ollama modelleri → `ollama pull` (adım 7)
- Eski `trsm.before_*.db` SQLite anlık görüntüleri (yalnızca geri dönüş amaçlıydı; güncel `trsm.db` zip'te)
- **Arşiv PDF'leri (`TRSM-devamı`, `TRSM:MUGLA`, toplam 7,4 GB)**: veritabanı zaten bunlardan üretildi (yedek zip'te). Asıl ölçüt `referans_karsilastir.py` yalnızca `test_seti`'ni kullanır. Arşiv sadece `calistir*.py` (arşivden rastgele 12 sayfa) için gerekir. Bu betikler arşiv yoksa sayfa bulamaz; o durumda kullanıcıya arşivi ayrıca getirmesi gerektiğini söyle, kendin arama yapma.

Commit edilmemiş değişiklikler var (`tek-tik-kurulum` dalı, ~95 dosya: PostgreSQL taşıması + OCR denemeleri). Kullanıcı istemeden commit etme; istenirse `postgresql-gecis` dalına commit et.

## 2. Kurulum adımları (Claude yapar, kullanıcı onaylar)

Kullanıcının elle yapması gerekenler (yönetici izni/yeniden başlatma): **Docker Desktop** kurulumu, **NVIDIA sürücüsü** güncellemesi, VS Code + Claude Code girişi. Diğerlerini `winget` ile kurabilirsin.

1. **Yerleşim.** Zip'i `C:\Users\<kullanıcı>\` altına açtıysa:
   - `TRSM_tasima\TRSM_Bitirme` → `C:\Users\<kullanıcı>\TRSM_Bitirme`
   - `TRSM_tasima\mobil` → `C:\Users\<kullanıcı>\mobil`
   - Arşiv sonradan gelirse: `TRSM-devamı` ve `TRSM-MUGLA` doğrudan `C:\Users\<kullanıcı>\` altına (kod `Path.home()` altında arar: `spikes/ocr_karsilastirma/calistir.py` → `ARCHIVE_ROOTS`). Türkçe karakterli ad bozuk açıldıysa düzelt; kod NFC normalize ederek karşılaştırır.
2. **Araçlar:** Git for Windows (Git Bash; `scripts/*.sh` bununla çalışır), `uv`, Ollama, Node.js LTS. Kontrol: `git --version`, `uv --version`, `ollama --version`, `node --version`, `docker --version`, `nvidia-smi`.
3. **Satır sonları:** `git config --global core.autocrlf false`. `docker/postgres-init/*.sql` ve `.sh` betikleri LF kalmalı.
4. **Veritabanı:** Docker Desktop açıkken proje kökünde `docker compose up -d`; sağlık durumu `healthy` olunca Git Bash'te `scripts/yedekten_don.sh yedekler/<en yeni "tasima" yedeği>` (onay sorusuna `evet`). `trsm_test` veritabanını `docker/postgres-init/01_test_db.sql` ilk açılışta oluşturur.
5. **Python:** `uv sync` (Python 3.11–3.12; `pyproject.toml` CPU PyTorch indeksi kullanır). `models/paraphrase-multilingual-MiniLM-L12-v2` zip'ten gelir; internetten indirilmez.
6. **Doğrulama:** `uv run pytest` → Mac'te **206 test geçiyordu**. Veritabanı satır sayıları (yalnızca sayı): `ziyaret`, `ilac_kullanimi`, `semptom_kaydi` (96.693), `ilac_sozluk` (61).
7. **OCR modeli:** `ollama pull qwen3.5:9b` (~6,6 GB). `nvidia-smi` ile modelin GPU'ya yüklendiğini kontrol et (`ollama ps` → GPU yüzdesi). Sonra `spikes/ocr_karsilastirma/calistir.py` içinde `VARSAYILAN_MODEL = "qwen3.5:9b"` yap.
8. **Mobil:** `TRSM_Bitirme\mobile` ve `mobil` klasörlerinde `npm install`. Flask sunucusu yerel ağa `TRSM_HOST=0.0.0.0` ile açılır (`docs/superpowers/specs/2026-10-12-mobil-uygulama-iskelet-design.md`).

## 3. OCR çalışmasında nerede kaldık

**Karar (danışman):** Doktor kamerayla el yazısı belgenin fotoğrafını çeker → sunucuda yerel görüntü-dil modeli okur → doktor fotoğraf ile metni yan yana görüp düzeltir ve onaylar → veritabanına yalnızca onaylı metin girer → düzeltmeler ileride ince ayar (LoRA) verisi olur. Veri buluta gitmez (KVKK).

**Betikler** (`spikes/ocr_karsilastirma/`, kalıcı kod değil; hepsi ekrana yalnızca sayı yazar):

| Betik | Ne yapar |
|---|---|
| `referans_karsilastir.py` | **Asıl ölçüt.** Kullanıcının 10 sayfadan elle yazdığı metne (`cikti/test_seti/Kitap1.xlsx`, "Blok" sütunları) karşı CER/WER/kelime yakalama. Excel'deki Gemini/Copilot/Mistral/OlmOCR/Tesseract sonuçlarını da puanlar. `--sadece-puanla` modelsiz çalışır. Yeni model için `YEREL` listesine ekle. |
| `calistir.py`, `calistir2.py`, `calistir_model.py` | Arşivden 12 sayfayı farklı yapılandırmalarla okur (`cikti/sonuclar.json`). |
| `etiketle.py`, `analiz.py` | 12 sayfada tıklamayla ilaç etiketleme ve ilaç isabet/yakalama ölçümü (`cikti/etiketler.json`). |
| `duzeltme_dene.py`, `sozcuk_duzelt.py` | OCR sonrası düzeltme denemeleri (sonuç: işe yaramadı, aşağıda). |

**Referans 10 sayfada sonuçlar (19.10.2026, Mac M1 8 GB):**

| Araç | CER | WER | Kelime yakalama | sn/sayfa |
|---|---|---|---|---|
| Gemini (bulut) | %7,9 | %13,3 | %95,6 | – |
| Copilot (bulut) | %21,2 | %37,7 | %74,1 | – |
| Mistral (bulut) | %24,4 | %37,7 | %80,9 | – |
| OlmOCR | %27,8 | %52,7 | %61,9 | – |
| **qwen3.5:4b + sözlük** (yerel) | %34,8 | %55,4 | %65,7 | 50 |
| qwen3.5:4b sözlüksüz | %37,3 | %57,7 | %60,9 | 60 |
| qwen3-vl:4b + sözlük | %54,7 | %81,2 | %54,4 | 103 |
| Tesseract | %77,0 | %91,1 | %15,5 | – |

- Arkadaşın testi: **qwen3.5:9b** (LM Studio, "qwen_qwen3.5-9b_gorsel") → **%63,33 | %79,65**. Büyük ihtimalle kelime doğruluğu (1−WER) ve karakter doğruluğu (1−CER); doğrulanmadı. Doğruysa Copilot düzeyi. **İlk iş:** 9B'yi `referans_karsilastir.py` ile aynı ölçütle ölç.
- Mac'te 9B çalışmadı (6,3 GB model 8 GB'a sığmadı, 15 dakikada 1 sayfa bitmedi).
- Talimata ilaç sözlüğü eklemek iyi (`qwen3.5:4b`'de CER %37,3 → %34,8). 2B modeller sözlüğü kopyalıyor; kullanma.
- `qwen3-vl` için mutlaka `-instruct` etiketi; `qwen3.5` için `think=False` gerekir, yoksa "düşünen" model boş çıktı verir.

**OCR sonrası düzeltme (aynı 10 sayfa):** Hiçbiri anlamlı iyileştirmedi.
- Metinden düzeltme (`qwen3.5:4b`, görüntüsüz): 39 kelime değişti, 16'sı doğru, 17 doğru kelime bozuldu.
- Görüntüyle düzeltme: model kendi taslağını onaylıyor, 4 kelimeye dokundu.
- Klinik kelime hazinesi + RapidFuzz (70.554 kelime): fark yok.
- **Neden:** Yanlış kelimelerin çoğu gerçek ve akla yatkın kelimeler (taslakta hazinede olmayan kelime yalnızca %12,9; yanlış ~%35). Metinden ayırt edilemiyor; iyileştirme okumanın kendisinden gelmeli (daha büyük model, ince ayar).
- Kullanıcı "bağlamla tahmin + tahmin edilen kelimeyi sarıyla işaretle" fikrini savunuyor; 9B ya da daha büyük bir metin modeliyle tekrar ölçülebilir.

**Belirsiz kelime işaretleme işe yarıyor:** `qwen3.5:4b` okuması ile **farklı bir modelin** (`qwen3-vl:4b`) okumasının ayrıştığı kelimeler sarıya boyanırsa yanlışların %78'i işaretli olur ve işaretsiz kelimelerde yanlış %40 → %18 düşer (kelimelerin ~%51'i işaretlenir). Aynı modelin sözlüklü/sözlüksüz ikilisi zayıf (%42). Modeller kendiliğinden `[?]` yazmıyor; bu yöntem gerekli.

**Arşivdeki 12 sayfada ilaç ölçümü** (kullanıcı etiketledi; 31 gerçek ilaç): `qwen3-vl:4b + sözlük` isabet %95, yakalama %65–71, doz doğru %44; eski OCR yakalama %48–52. Önceki sayfanın ilaç listesi tek başına %58 yakalama / %82 isabet → "önceki ziyarette vardı, devam ediyor mu?" önerisi olarak gösterilmeli; talimata bağlam eklemek dozları kötüleştirdi (%44 → %35). Şerit (sayfayı 3'e bölme) 2,3 kat yavaş, iyileştirme yok.

**Yan bulgu:** `semptom_kaydi.kategori` kullanılamaz: 96.693 kaydın 95.604'ü tek kümede (`cluster_1`). Asıl şema `trsm/symptom_categories.py` içindeki 13 tema.

## 4. Sıradaki adımlar

1. Bu bilgisayarda kurulumu bitir ve testleri geçir.
2. `qwen3.5:9b`'yi 10 referans sayfasında ölç (`referans_karsilastir.py`, `YEREL` listesine `{"ad": "qwen3.5:9b + sözlük", "model": "qwen3.5:9b", "sozluk": True}` ekle). Sonra iki model ayrışması (9B + 4B) ile işaretleme ölçümünü tekrarla.
3. Ürün özelliğini tasarla: mobil kamera → `/api/m/ocr` → arka planda iki model okur → ayrışan kelimeler sarı → doktor düzeltir ve onaylar → onaylı metin + düzeltmeler saklanır. Model adı tek bir ayar olsun (ör. `TRSM_OCR_MODEL`).
4. PostgreSQL değişikliklerini `postgresql-gecis` dalına commit et (kullanıcı onayıyla). `docs/proje_okuma_rehberi.md` ve `docs/danisman_mini_sunum.md` hâlâ SQLite diyor.
5. İade öncesi: son yedek (`scripts/yedek_al.sh`) + kodun git paketi kullanıcıya; sonra bilgisayardan her şey silinir.

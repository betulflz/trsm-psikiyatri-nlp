# HANDOFF — 28.10.2026

Bu belge, yeni bir Claude oturumunun kaldığımız yerden devam edebilmesi için yazıldı.
Sunucu, erişim bilgileri ve şifreler için **`AGENTS.md`** dosyasına bakın.

## Bağlam
- Proje Betül Filiz'in bitirme projesi (TRSM / Psikord). İlkay sunucuyu kurdu ve bu klasörü zip olarak Betül'e devrediyor.
- Betül zip'i açıp kendi orijinal klasörünün üzerine kopyalayacak. `.git` klasörü onun orijinal klasöründe duruyor.
- Bu oturumda **commit atılmadı.** Betül'ün klasöründe aşağıdaki değişiklikler "değişmiş" ya da "yeni dosya" olarak görünecek.
- Daha önceki iş geçmişi (SQLite'tan PostgreSQL'e geçiş, OCR denemesi, gizlilik kuralı): `docs/devam_prompt_2026-10-16.md`.

## Bu oturumda yapılanlar

### 1. Barındırma araştırması ve kararı
- **Hedef:** Qwen3.5 9B modelini bedava ve sürekli açık bir yerde çalıştırmak. Betül'ün bilgisayarı ve İlkay'ın M1 8 GB Mac'i bu modeli kaldırmıyor.
- **Elenen seçenekler:**
  - Azure for Students: bölge politikası hatası, GPU kapalı, kredisi yetersiz.
  - Hugging Face Spaces: bedava katman belirsiz ve çok yavaş.
  - Colab/Kaggle: oturumlar kapanıyor.
  - Ücretli seçenekler de konuşuldu: Contabo ~€14/ay (CPU), Modal ($30/ay bedava kredi, sunucusuz GPU), Vast.ai (~$30–45/ay, 7/24 GPU).
- **Seçilen:** **Oracle Cloud Always Free**, ARM A1 (2 OCPU / 12 GB; bedava kota Haziran 2026'da 4/24'ten düşürüldü).

### 2. Oracle sunucusu kuruldu
Kurulanlar: Ubuntu 24.04 ARM, 4 GB swap, Ollama + `qwen3.5:9b`, Docker + PostgreSQL 16, uv + Python paketleri, TRSM Flask servisi, Tailscale, Funnel. Ayrıntılar `AGENTS.md` §2–§5'te.

### 3. Veri kararı: önce yalnızca kod
- Proje sahibi gerçek hasta verisini şimdilik sunucuya taşımamayı seçti.
- Sunucuda `scripts/seed_synthetic_demo.py` ile üretilmiş **300 sahte hasta** var.

### 4. Kod değişiklikleri (yerelde ve sunucuda aynı; 206 testin hepsi sunucuda geçti)
| Dosya | Değişiklik |
|---|---|
| `trsm/ollama_support.py` | `think_kwargs()` eklendi: `TRSM_LLM_THINK=false` ayarı Ollama çağrılarına `think=False` gönderiyor. `get_ollama_client` zaman aşımını `TRSM_OLLAMA_TIMEOUT`'tan okuyor (varsayılan 60). |
| `trsm/recommendation.py` | İki `client.chat` çağrısına `**think_kwargs()` eklendi. |
| `trsm/qwen_symptom_labeling.py` | `client.chat` çağrısına `**think_kwargs()` eklendi. |
| `demo_server.py` | Sabit yazılmış `qwen_status("qwen2.5:3b")` kaldırıldı; artık `LLM_MODEL_NAME` / `QWEN_LABEL_MODEL` kullanılıyor (ortam değişkenlerinden okunuyor). |
| `scripts/seed_synthetic_demo.py` | **Yeni.** Boş veritabanına şema, ilaç sözlüğü ve sahte hasta, ziyaret, semptom ve ilaç kayıtları yazıyor. Doğum tarihi `GG.AA.YYYY` biçiminde (`calculate_age_at_visit` bunu bekliyor). |
| `mobile/.env` | `EXPO_PUBLIC_API_URL=https://trsm-sunucu.tail42dcb3.ts.net`. Eski adres `mobile/.env.yerel.local` dosyasında. |
| `AGENTS.md`, `HANDOFF.md`, `CLAUDE.md` | **Yeni.** Bu belgeler. `AGENTS.md` şifre içerdiği için `.gitignore`'a eklendi. |

Varsayılan davranış korunuyor: ortam değişkenleri verilmezse kod eskisi gibi `qwen2.5:3b` modelini kullanıyor ve `think` göndermiyor. Yereldeki akış bozulmadı.

### 5. Uçtan uca doğrulananlar (28.10.2026)
- **Mobil giriş:** `/api/m/giris` (doktor) ve `/api/m/ozet` hem Tailscale hem Funnel üzerinden çalışıyor.
- **Semptom sorgusu:** `/api/sorgu` ile "uykusuzluk ve mutsuzluk", 34 yaş, Kadın sorgusu 113 ziyaret / 42 hastayla eşleşti, ilaç dağılımı geldi. `ozet_iste: true` ile not `ozet_kaynagi: "qwen"` olarak döndü; model soğukken 141 sn sürdü.
- **Funnel:** `https://trsm-sunucu.tail42dcb3.ts.net/api/m/saglik` ve `/betus/` adresleri internetten açılıyor.
- **Güvenlik duvarı:** Ollama'ya public IP'den erişilemiyor.

### 6. Devralma sonrası düzeltme (29.10.2026)
- Zip'teki kod `6ab5a9b` (Tesseract OCR) commitinden eskiydi; üzerine kopyalanınca OCR dosyaları, `mobile/assets/` ikonları, `docs/devam_prompt_2026-10-19.md` ve `spikes/ocr_karsilastirma/` betikleri silinmiş görünüyordu. Hepsi `HEAD`'den geri alındı; İlkay'ın 4 dosyadaki değişikliği (yukarıdaki tablo) korundu.
- **Tesseract kaldırıldı, OCR artık Qwen 9B ile** (proje sahibinin kararı). `trsm/mobile_api/ocr.py` içinde tek işçili bellek içi kuyruk var:
  - `POST /api/m/rapor/ocr`: fotoğrafı alır, 202 ve `is_id` döner.
  - `GET /api/m/rapor/ocr/<is_id>`: durum (`sirada`, `okunuyor`, `bitti`, `hata`) ve metni döner.
  - Mobil 5 saniyede bir sorar. Fotoğraf yalnızca bellekte tutulur. İşler bir saat sonra unutulur ve sunucu yeniden başlarsa kaybolur.
- Ölçüm: sahte, basılı, kısa bir sayfa doğrudan Ollama ile 401 sn, internetten mobil API üzerinden uçtan uca 633 sn sürdü. Metin iki denemede de birebir doğru okundu. El yazısı ölçülmedi.
- Sunucuya gönderildi. 219 Python testi (yerel ve sunucu) ve 74 mobil test geçti.
- **Sıradaki (KVKK planı):**
  1. Funnel'dan gelen kimlik doğrulamasız istekleri kapatmak.
  2. Mobilde kimlik satırlarını karartmak.
  3. Sunucuda otomatik kimlik temizliği yapmak.
  4. Doktor onayından sonra yalnızca anonim kaydı (rastgele kod, yaş, cinsiyet, semptom, ilaç) saklamak.
  5. Sahte el yazısı sayfalarla ölçüm yapmak.
  - Gerçek sayfalar etik onaydan önce yüklenmeyecek.

## Açık konular ve riskler
1. **Funnel ile kimlik doğrulamasız erişim:**
   - Durum: Funnel'dan gelen istekler `127.0.0.1` gibi göründüğü için `network_guard` devre dışı kalıyor. Demo sayfası ve `/api/*` herkese açık.
   - Neden kabul edildi: Sahte veriyle bilerek kabul edildi.
   - Yapılacak: Gerçek veri gelmeden önce düzeltilmeli. Örneğin Funnel isteklerinde Tailscale'in eklediği `Tailscale-Funnel-Request` ya da `X-Forwarded-For` başlıklarına bakılabilir, ya da demo sayfasına giriş eklenebilir.
2. **Demo şifreleri:** Mobil demo şifreleri README'de yazılı ve değiştirilmedi; proje sahibinin kararı.
3. **Flask geliştirme sunucusu:** Az sayıda kullanıcı için yeterli. Yük artarsa gunicorn ya da waitress gerekir.
4. **Qwen yavaş:** ~2,9 token/sn. Aynı anda birkaç kişi Qwen notu isterse istekler kuyruğa girer.
5. **Oracle'ın boşta kalan makineyi geri alması:** 7 gün boyunca kullanım çok düşük kalırsa makine geri alınabilir. Gerekirse hafif bir zamanlanmış görev eklenebilir.
6. **Public IP Ephemeral:** Instance silinirse IP değişir. Tailscale ve Funnel adresleri değişmez; uygulama Funnel adresini kullanıyor.
7. **Belgeler eski kalmış olabilir:** `docs/proje_okuma_rehberi.md` ve `docs/danisman_mini_sunum.md` hâlâ SQLite diyor (önceki oturumdan kalan iş).

## Sıradaki adımlar
1. **Devretme (28.10.2026'da başladı):**
   - ✅ Betül `ssh-keygen -t ed25519 -f ~/.ssh/trsm-oracle.key` ile anahtarını oluşturdu. Public key'i (`ssh-ed25519 … betul`) sunucuya eklendi.
   - ✅ **İlkay'ın erişimi bilerek korunuyor.** Hem `ssh-rsa` anahtarı hem Tailscale'deki `lkay-macbook-air` cihazı duruyor, ki sorun çıkarsa yardım edebilsin. Kaldırmak istenirse adımlar `AGENTS.md` §3'te.
   - ✅ Betül kendi Mac'inden (parolalı anahtarla) bağlandı. Dört servis `active`, sağlık kontrolü `{"durum":"ok"}`. Sunucunun host anahtarı `SHA256:ABnvGEI5q3YiM4zFgX7PCr8ycuLQRaHR7zVRqIOcPQg`.
   - ⏳ Proje klasörü zip olarak Betül'e gönderilecek; Betül kendi orijinal klasörünün üzerine kopyalayacak.
   - ⏳ Oracle'da iki adımlı doğrulama QR'ı bir sohbette paylaşıldı. Betül doğrulama cihazını kaldırıp yeniden eklemeli ve Oracle şifresini değiştirmeli.
2. **Hoca ve doktorlar:** `https://trsm-sunucu.tail42dcb3.ts.net` linki ve demo hesapları iletilecek.
3. **OCR özelliği (önceki oturumdan devam):**
   - Akış: mobilden fotoğraf → sunucuda görüntü-dil modeli → belirsiz kelimelerin işaretlenmesi → doktor onayı.
   - `qwen3.5:9b` görsel destekli. OCR için ayrı bir `qwen3-vl` yerine bu model denenebilir, ama CPU'da sayfa başına süre çok uzun olacaktır; önce ölçülmeli.
   - Gizlilik kuralı geçerli: gerçek sayfalar Claude'a gösterilmez.
4. **Gerçek veri kararı:** Danışmanla konuşulacak. Taşınacaksa önce 1. açık konu çözülmeli.
5. **İsteğe bağlı:** Gerekirse Oracle boşta kalma önlemi, gunicorn ve `docs/` belgelerinin güncellenmesi.

## Hızlı kontrol (yeni oturumda ilk iş)
```bash
ssh -i ~/.ssh/trsm-oracle.key ubuntu@92.5.151.72 'systemctl is-active ollama trsm betus docker; sudo tailscale funnel status; curl -s localhost:8765/api/m/saglik'
```
Beklenen çıktı: dört kez `active`, Funnel açık ve `{"durum":"ok"}`.

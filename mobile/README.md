# Psikord (mobil)

TRSM arşivindeki hasta dosyalarını doktor ve hemşire için gösteren Expo uygulaması.

## Çalıştırma

1. Bilgisayarda sunucuyu yerel ağa açın (repo kökünde):
   `uv run python scripts/seed_mobile_users.py` ve `TRSM_HOST=0.0.0.0 uv run python demo_server.py`
2. Bilgisayarın yerel IP'sini bulun (macOS: `ipconfig getifaddr en0`).
3. `cp .env.example .env` ve `EXPO_PUBLIC_API_URL`'i `http://<IP>:8765` yapın.
4. `npm install` ve `npx expo start`; telefonda Expo Go ile QR kodu okutun.
   Telefon ve bilgisayar aynı Wi-Fi'da olmalı.

Adres değişirse uygulamada Ayarlar → Sunucu satırından güncelleyebilirsiniz.

Demo hesapları: `doktor` / `psikord-doktor`, `hemsire` / `psikord-hemsire`, `admin` / `psikord-admin`.

## Test

`npm test`

## Fotoğraftan rapor okuma (yerel OCR)

Yeni dosya → Rapor sayfaları bölümünde kameradan veya galeriden fotoğraf
eklenince otomatik olarak `/api/m/rapor/ocr` adresine yüklenir. Sayfalar sırayla
okunur; metin, hata ve yeniden okuma düğmesi her sayfanın altında görünür.
Taslağı kaydet fotoğrafları ve OCR metinlerini cihazda saklar; kayıtlı taslakta
“Metni gör” ile sonuç açılır. Hasta henüz sunucu veri tabanına kaydedilmez.

Sunucuda `uv sync` ve Tesseract gerekir (macOS: `brew install tesseract`,
Ubuntu: `sudo apt install tesseract-ocr`). Bu bilgisayarda Tesseract ve `eng`
modeli zaten kurulu. Başlangıçta hafif İngilizce model kullanılır; Türkçe
karakterlerde ve el yazısında doğruluk düşük olabilir. Qwen indirilmez.

```bash
TRSM_HOST=0.0.0.0 TRSM_OCR_LANG=eng uv run python demo_server.py
```

Türkçe dil dosyası kurulduğunda `TRSM_OCR_LANG=tur+eng` kullanılabilir
(`tesseract --list-langs` ile kontrol edin). Bu ayarlar sunucu ortam değişkenidir;
projenin `.env` dosyasından otomatik okunmaz. `TRSM_TESSERACT_CMD` ile çalıştırılabilir
dosyanın yolu değiştirilebilir. `TRSM_OCR_BACKEND` varsayılanı `tesseract`tır;
gelecekte Qwen veya başka bir model için `trsm/mobile_api/ocr.py` içindeki
`read_report` motor seçimine yeni sağlayıcı ekleyin. Mobilin beklediği yanıt
`{metin, motor, dil}` olduğundan mobil yükleme akışı değişmez.

Sunucu en fazla 12 MB / 25 megapiksel görsel kabul eder, uzun kenarı 2000 piksele
indirir ve Tesseract'ı tek iş parçacığıyla en fazla 45 saniye çalıştırır.
Her sunucu sürecinde aynı anda tek OCR çalışır; yoğunken tekrar deneme mesajı
döner. Görseller geçici dizinde işlenir ve işlem bitince silinir; bulut servisine
gönderilmez. Telefonun eriştiği Flask sunucusunun yeniden başlatılması gerekir.

## Sorun giderme

- **"Sunucuya ulaşılamıyor"**: Telefon ve bilgisayar aynı Wi-Fi'da mı? Sunucu
  `TRSM_HOST=0.0.0.0` ile mi açıldı? macOS güvenlik duvarı Python'a gelen
  bağlantılara izin veriyor mu? Ayarlar → Sunucu adresinden IP'yi güncelleyin
  (adres değişince güvenlik için oturum kapanır, yeniden giriş gerekir).
- **Port 5000 kullanmayın**: macOS'ta AirPlay Receiver tarafından işgal edilir;
  varsayılan 8765'tir.
- **Oturum aniden kapandı**: Token 12 saat geçerlidir; sunucunun
  `data/mobile_secret.key` dosyası değişirse tüm oturumlar düşer.
- **`demo_server.py` başlangıçta "too many SQL variables" veriyor**: Eski demo
  sayfasının kategori hesabı bazı SQLite sürümlerinde takılır. Mobil API bu
  hesaba bağlı değildir; sunucuyu doğrudan çalıştırın:
  `uv run python -c "import demo_server as d; d.app.run(host='0.0.0.0', port=8765)"`
- **Ağa açıkken eski demo**: `TRSM_HOST=0.0.0.0` iken eski kimliksiz uç noktalar
  (`demo.html` dahil) yalnızca sunucunun çalıştığı bilgisayardan erişilebilir;
  ağdaki cihazlar sadece `/api/m` kullanır.
- **Google ile giriş**: Aşama 2'dedir; development build ve Google Cloud OAuth
  istemcileri gerektirir, Expo Go ile çalışmaz.

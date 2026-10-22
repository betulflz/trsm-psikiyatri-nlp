# TRSM İlaç Analiz Demosu

Geçmiş ziyaret kayıtlarındaki semptom benzerliği ile yaş ve cinsiyet profilini
birlikte kullanan, yerel istatistiksel ilaç-kayıt özeti demosu.

## Hoca için çalıştırma

> Not: Tek tık dağıtım paketi (`Baslat.bat` / `Baslat.command`) henüz
> PostgreSQL'e uyarlanmadı; şimdilik eski SQLite sürümüyle oluşturulmuş paket
> içindir.

Dağıtım zipini tamamen bir klasöre çıkarın ve Windows'ta `Baslat.bat`, macOS'ta
`Baslat.command` dosyasını çalıştırın. Ayrıntılı, teknik olmayan yönergeler
paketteki `KURULUM.txt` dosyasındadır.

Uygulama yerel olarak `http://127.0.0.1:8765` adresinde açılır. Qwen/Ollama
kurulu değilse ana analiz çalışmaya devam eder; yalnızca Qwen düğmeleri pasif
kalır.

## Veritabanı (PostgreSQL)

Veriler yerel bir PostgreSQL 16 sunucusunda tutulur. Sunucu Docker içinde
çalışır ve yalnızca bu bilgisayardan (`127.0.0.1:5434`) erişilebilir; veri
buluta veya ağa çıkmaz.

İlk kurulum (Docker Desktop açık olmalı):

```bash
cp .env.example .env        # sonra .env içindeki şifreyi değiştirin
docker compose up -d        # PostgreSQL'i başlatır (trsm + trsm_test veritabanları)
```

Bağlantı adresi `.env` içindeki `DATABASE_URL` değerinden okunur; `.env` Git'e
eklenmez. Bütün betikler bu adresi kullanır, farklı bir veritabanı için
`--database-url` verilebilir.

Eski SQLite dosyasından bir kerelik taşıma (dosya salt-okunur açılır, her satır
taşındıktan sonra karşılaştırılır):

```bash
uv run python scripts/migrate_sqlite_to_postgres.py trsm.db
```

Yedek alma ve geri yükleme (riskli bir işlemden önce yedek alın):

```bash
scripts/yedek_al.sh pipeline_oncesi       # yedekler/trsm_<tarih>_pipeline_oncesi.dump
scripts/yedekten_don.sh yedekler/<dosya>.dump
```

Testler gerçek veriye dokunmaz: her test `trsm_test` veritabanında kendine ait
boş bir şemada çalışır. Testlerden önce PostgreSQL'in çalışıyor olması gerekir.

## Geliştirici çalıştırması

Geliştirme makinesinde uv ile (PostgreSQL çalışıyor olmalı):

```bash
uv sync --no-dev
uv run python demo_server.py
```

MiniLM modeli proje içindeki `models/paraphrase-multilingual-MiniLM-L12-v2/`
klasöründen çevrimdışı yüklenir. Bu klasörü ilk kez hazırlamak için:

```bash
uv run python scripts/download_model.py
```

## Veri hazırlığı

Ham OCR Excel dosyasından veritabanı oluşturma, embedding indeksi üretme ve
doğrulama araçları `scripts/` altındadır. Bunlar dağıtım paketine dahil edilmez.
Gerçek veri dosyaları Git dışında tutulur.

## Eski / geliştirici Streamlit arayüzü

`app.py` Streamlit arayüzü korunmaktadır; dağıtım paketinin bir parçası değildir.
Geliştirici kullanımı için gerekli ek paketlerle şu komut kullanılabilir:

```bash
uv sync --group dev
uv run streamlit run app.py
```

Uygulama, PostgreSQL'e bağlanamazsa veya `data/symptom_index.npz` bulunamazsa hangi komutu
çalıştırmanız gerektiğini belirten bir hata mesajı gösterip duracaktır.

## Profil bazlı sorgu

Kullanıcı yaşını, cinsiyetini ve semptomunu girer. Sistem semantik olarak
benzer geçmiş semptomları bulur; ardından yalnızca aynı cinsiyette ve geçmiş
ziyaret tarihinde aynı yaş grubunda (15-17, 18-29, 30-44, 45-59, 60+) olan
doğrulanmış kayıtları toplulaştırır. Ekrana hasta adı veya geçmişte yazılmış
ham semptom cümlesi verilmez.

Sonuç tedavi önerisi değildir: yalnızca bu demografik profil ve semptomla
uyumlu geçmiş kayıtlardaki ilaç örüntüsünü, kişi/ziyaret sayısı ile birlikte
gösterir. Örneklem 20 ziyaretten veya 5 kişiden küçükse sonuç açıkça uyarılı
olarak gösterilir.

## Mobil uygulama (Psikord)

Sunucu tarafı `demo_server.py` içinde `/api/m` önekiyle çalışır. İlk kurulumda
demo hesaplarını oluşturun (varsa dokunmaz):

```bash
uv run python scripts/seed_mobile_users.py
```

Demo hesapları: `doktor` / `psikord-doktor`, `hemsire` / `psikord-hemsire`,
`admin` / `psikord-admin` (şifreler `TRSM_SEED_PASSWORD_<ROL>` ile değiştirilebilir).

Telefonun erişebilmesi için sunucuyu yerel ağa açın (yalnızca güvenilir Wi-Fi):

```bash
TRSM_HOST=0.0.0.0 uv run python demo_server.py
```

Mobil uygulama `mobile/` klasöründedir; ayrıntılar `mobile/README.md`.

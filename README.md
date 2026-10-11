# TRSM İlaç Analiz Demosu

Geçmiş ziyaret kayıtlarındaki semptom benzerliği ile yaş ve cinsiyet profilini
birlikte kullanan, yerel istatistiksel ilaç-kayıt özeti demosu.

## Hoca için çalıştırma

Dağıtım zipini tamamen bir klasöre çıkarın ve Windows'ta `Baslat.bat`, macOS'ta
`Baslat.command` dosyasını çalıştırın. Ayrıntılı, teknik olmayan yönergeler
paketteki `KURULUM.txt` dosyasındadır.

Uygulama yerel olarak `http://127.0.0.1:8765` adresinde açılır. Qwen/Ollama
kurulu değilse ana analiz çalışmaya devam eder; yalnızca Qwen düğmeleri pasif
kalır.

## Geliştirici çalıştırması

Geliştirme makinesinde uv ile:

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

Uygulama, `trsm.db` veya `data/symptom_index.npz` bulunamazsa hangi komutu
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

## Veri gizliliği (KVKK)

Bu depo yalnızca kaynak kodu, testleri ve dokümantasyonu içerir. Projede
kullanılan hasta kayıtları (ham PDF/OCR çıktıları, Excel dosyaları, SQLite
veritabanı, embedding indeksleri ve bunlardan türetilen CSV/JSON dosyaları)
6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında özel nitelikli
kişisel veri olduğundan depoya **eklenmemiştir** ve `.gitignore` ile dışarıda
tutulur. Testler yalnızca sentetik örnek metinler kullanır. Notebook'lar çıktısız
paylaşılmıştır; çalıştırmak için kendi yetkili veri kaynağınız gerekir.

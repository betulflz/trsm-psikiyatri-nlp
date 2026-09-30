# TRSM İlaç Öneri Asistanı

Geçmiş hasta ziyaretlerindeki semptom benzerliği ile seçilen yaş ve cinsiyet
profilini birlikte kullanan, istatistiksel ilaç-kayıt özeti üreten tamamen yerel
bir Streamlit uygulaması. Hiçbir hasta verisi bu makineden dışarı gönderilmez;
özet metni yerel bir Ollama LLM'i ile üretilir.

## Kurulum

```bash
pip install -r requirements.txt
```

Yerel LLM'i çalıştırmak için Ollama gereklidir:

```bash
brew services start ollama   # veya: ollama serve
ollama pull gemma2:2b
```

### Veri hazırlığı

1. Ham OCR Excel dosyasından SQLite veritabanını oluşturun:

   ```bash
   python3 scripts/run_pipeline.py <excel_yolu> trsm.db
   ```

2. Semptom benzerlik indeksini (embedding) oluşturun:

   ```bash
   python3 scripts/build_symptom_index.py trsm.db data/symptom_index.npz
   ```

Her iki dosya da (`trsm.db`, `data/symptom_index.npz`) `.gitignore` ile
izlenmez; uygulamayı çalıştırmadan önce yukarıdaki adımları tamamlamanız
gerekir.

## Çalıştırma

```bash
python3 -m streamlit run app.py
```

Not: Bu makinede `streamlit` konsol komutu (shim) bozuk olabilir; bu yüzden
`python3 -m streamlit run app.py` biçimi kullanılmalıdır.

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

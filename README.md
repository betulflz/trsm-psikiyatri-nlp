# TRSM İlaç Öneri Asistanı

Geçmiş hasta ziyaretlerindeki semptom benzerliğine dayanarak istatistiksel ilaç
özeti üreten, tamamen yerel çalışan bir Streamlit uygulaması. Hiçbir hasta
verisi bu makineden dışarı gönderilmez; özet metni yerel bir Ollama LLM'i ile
üretilir.

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

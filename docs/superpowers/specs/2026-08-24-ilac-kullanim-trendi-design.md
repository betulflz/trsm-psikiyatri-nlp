# İlaç Kullanım Trendi Analizi — Tasarım Dokümanı

## Genel Bakış

Bu, TRSM bitirme projesinin 2. alt sistemi: alt proje 1'in ürettiği `trsm.db` SQLite
veritabanını kullanarak, psikiyatrik ilaç kullanımının yıllar içindeki değişimini
görselleştiren bir Jupyter notebook.

**Bağımlılık:** Alt proje 1 (veri temizleme & varlık çıkarımı) tamamlanmış olmalı —
`trsm.db` içinde dolu `hasta`, `ziyaret`, `ilac_kullanimi` tabloları gerekir.

**Kapsam (v1):** Sadece "ilaç kullanım trendi (yıllara göre)" — ilaç geçiş örüntüleri,
semptom-ilaç ilişkisi ve hasta bazlı özet istatistikler bu alt projenin kapsamı
dışında, ileride ayrı alt projeler olarak ele alınabilir.

## Veri Kalitesi Yaklaşımı

`ilac_kullanimi.eslesme_guveni` (bulanık eşleştirme güven skoru) düşük olan kayıtlar
trend grafiklerini çarpıtabileceğinden, bir eşik değeri altındaki kayıtlar filtrelenir.

- Varsayılan eşik: **90** (fuzzy match skoru 0-100 arası)
- Notebook'un en üstünde `GUVEN_ESIGI = 90` şeklinde tek bir değişken olarak
  tanımlanır — böylece farklı eşiklerle sonucun nasıl değiştiği kolayca gösterilebilir
  (tez metodoloji/tartışma bölümü için).

## Zaman Granularitesi

Yıllık gruplama. `ziyaret.tarih` (ISO format `YYYY-MM-DD`, alt proje 1'de zaten
normalize edilmiş) alanından yıl çıkarılır (`tarih[:4]`). Tarihi olmayan (`NULL`)
ziyaretlere bağlı ilaç kayıtları yıllık trendden hariç tutulur (ayrıca kaç kaydın
bu şekilde hariç tutulduğu notebook'ta raporlanır, veri kaybı şeffaf olsun diye).

## Analiz Adımları (notebook hücreleri)

1. **Veri yükleme:** `sqlite3`/`pandas.read_sql` ile `ilac_kullanimi` ⋈ `ziyaret`
   (JOIN üzerinden `tarih` alınır), `eslesme_guveni >= GUVEN_ESIGI` filtresi.
2. **Yıl çıkarımı:** `tarih` alanından `yil` kolonu türetilir; `tarih IS NULL` olan
   kayıtların sayısı ayrıca raporlanır.
3. **Gruplama:** `(yil, ilac_adi_normalize)` bazında kayıt sayısı (`groupby().size()`).
4. **En sık N ilaç:** Tüm zaman aralığında en sık geçen ilk 10 ilaç belirlenir
   (grafiği okunaklı tutmak için — 42 ilacın hepsini tek grafikte göstermek
   karmaşıklaşır).
5. **Trend grafiği:** Bu 10 ilaç için yıllara göre kullanım sayısı — çizgi grafiği
   (her ilaç bir çizgi), ayrıca bir özet pivot tablo (yıl × ilaç, hücrelerde sayı).
6. **Genel özet:** Toplam ilaç kaydı, filtrelenen (düşük güvenli) kayıt sayısı,
   tarihsiz kayıt sayısı, veri kapsanan yıl aralığı — kısa bir metin özeti.

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Veri erişimi | `sqlite3`, `pandas.read_sql` |
| Analiz | `pandas` (groupby, pivot_table) |
| Görselleştirme | `matplotlib`, `seaborn` |
| Ortam | Jupyter notebook (`notebooks/ilac_kullanim_trendi.ipynb`) |

## Dosya Yapısı

- `notebooks/ilac_kullanim_trendi.ipynb` — tek notebook, yukarıdaki 6 adım ayrı
  hücrelerde, her hücrenin üstünde kısa bir Markdown açıklaması.
- Yeni bir Python modülü/paket gerekmiyor — bu alt proje `trsm` paketini sadece
  okuma amaçlı (veritabanı şeması) kullanıyor, yeni kod trsm/ içine eklenmiyor.

## Kapsam Dışı

- İlaç geçiş örüntüleri (hangi ilaçtan hangi ilaca geçilmiş)
- Semptom kategorisi - ilaç çapraz analizi
- Hasta bazlı özet istatistikler
- İnteraktif dashboard / statik PDF rapor (v1 sadece notebook)

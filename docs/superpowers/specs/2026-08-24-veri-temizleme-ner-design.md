# TRSM Bitirme Projesi — Tasarım Dokümanı

## Proje Genel Bakış

**Başlık:** Toplum Ruh Sağlığı Merkezi Kayıtlarının Optik Karakter Tanıma Yöntemiyle
Dijitalleştirilmesi ve Psikiyatrik İlaç Kullanımının Zaman Trendinin Analizi.

**Amaç:** El yazılı TRSM klinik kayıtlarını (OCR ile zaten Excel'e aktarıldı) yapılandırılmış
veriye dönüştürmek, psikiyatrik ilaç kullanım örüntülerinin zaman içindeki değişimini analiz
etmek ve yeni bir hastanın semptom örüntüsüne göre geçmişte benzer hastalara verilen ilaçları
önerebilen bir sohbet uygulaması geliştirmek.

**Kritik kısıt:** Hasta verisi dışarı çıkmayacak — tüm işleme (NER, embedding, LLM) yerelde,
internete bağlı olmayan modellerle yapılacak. Bu, etik kurul onayının koşullarından biri.

**Donanım:** MacBook Air, Apple M1, 8GB RAM, entegre GPU. Büyük yerel LLM'ler (7B+) bu
makinede pratik değil; hafif/CPU-dostu modeller tercih edilir.

## Alt Projelere Bölünme

Proje üç bağımlı alt sisteme ayrılmıştır, her biri ayrı spec → plan → implementasyon
döngüsünden geçecektir:

1. **Veri temizleme & varlık çıkarımı (bu doküman)** — serbest metinden ilaç adı, doz,
   tarih, semptom/duygu durumu çıkarımı; ilaç isimlerini normalize etme; SQLite'a yükleme.
2. **Zaman trendi analizi** — hangi ilaç hangi dönemde ne sıklıkla kullanılmış, hangi
   semptom kümesiyle hangi ilaç ilişkili; görselleştirme + istatistik. (Alt proje 1'e bağımlı.)
3. **Öneri/chat sistemi** — yeni hastanın semptom örüntüsüne göre geçmişte benzer hastalara
   verilen ilaçları öneren yerel LLM tabanlı sohbet arayüzü. (Alt proje 1 ve 2'ye bağımlı.)

## Mevcut Veri Seti (keşif bulguları)

Kaynak: `~/Excel_Toplu/TRSM_Tum_Raporlar_Birlesik.xlsx`

- **41.676 satır, 547 benzersiz hasta** (`Dosya` kolonu = orijinal PDF adı)
- Kolonlar: `Dosya`, `Sayfa`, `Tarih`, `Müdahale` (serbest metin), `Sonuç` (serbest metin,
  çoğunlukla ilaç bilgisi içerir)
- Hasta başına ortalama 76 satır (min 1, maks 799)
- `Tarih`: %15 boş (6259/41676), iki farklı format karışık kullanılmış (`09.08.2024` ve
  `15/06/2021`) — boş tarihli satırlar muhtemelen bir önceki dolu tarihin devamı
- `Müdahale`: %5.6 boş (2355/41676), ortalama 61 karakter, maks 1059 karakter
- `Sonuç`: %24 boş (10146/41676), ortalama 35 karakter, maks 1643 karakter
- İlaç isimleri OCR/el yazısı kaynaklı yazım varyasyonlarıyla dolu (örn. "Venerys" / "Venegres"
  muhtemelen aynı ilaç), net bir çizelge formatı yok — serbest metin içine gömülü

## Alt Proje 1: Mimari / Pipeline

```
Excel (ham OCR çıktısı)
   → [Aşama A] Temizleme: tarih normalizasyonu (iki format → tek format),
                boş tarihli satırları hasta bazında bir önceki dolu tarihe bağlama
                (forward-fill), gürültü/boş satır filtreleme
   → [Aşama B] İlaç çıkarımı: sözlük + fuzzy matching (RapidFuzz) ile
                Müdahale/Sonuç metninden ilaç adı + doz + sıklık çıkarımı,
                TİTCK ilaç listesine normalize etme
   → [Aşama C] Semptom/duygu durumu çıkarımı: Türkçe BERT-NER/embedding modeli ile
                serbest metinden ifade çıkarımı, ardından kümeleme (clustering)
                ile organik kategori seti oluşturma (DSM değil, veriden çıkan kategoriler)
   → [Aşama D] SQLite'a yükleme: normalize edilmiş ilişkisel tablolar
```

Her aşama ayrı, bağımsız test edilebilir bir Python modülü olacak (örn. ilaç sözlüğünü
genişletmek NER kodunu etkilemeyecek).

## Veri Modeli (SQLite)

```
hasta (patient)
  id, dosya_adi

ziyaret (visit)
  id, hasta_id (FK), tarih, sayfa_no, ham_mudahale_metni, ham_sonuc_metni

ilac_kullanimi (medication_use)
  id, ziyaret_id (FK), ilac_adi_normalize, ilac_adi_ham,
  doz, siklik, eslesme_guveni

semptom_kaydi (symptom_record)
  id, ziyaret_id (FK), ifade_ham, kategori

ilac_sozluk (drug_dictionary)
  id, resmi_ad, bilinen_varyasyonlar (JSON/ayrı tablo, zamanla öğrenilir)
```

Tasarım kararı: **ham metin asla silinmez** — her çıkarım orijinal kaynak metne referans
verir (izlenebilirlik + tez savunması + yeniden işleme imkanı). `eslesme_guveni` (confidence
score) düşük eşleşmeleri manuel gözden geçirme/raporlama için işaretler.

## İlaç Sözlüğü & Normalizasyon

- Başlangıç sözlüğü: TİTCK'nin halka açık ilaç listesinden psikiyatride kullanılan etken
  madde/ticari isimler (antipsikotik, antidepresan, duygudurum dengeleyici, anksiyolitik).
- RapidFuzz (Levenshtein tabanlı) ile her ham ilaç adı adayı sözlükteki en yakın resmi isme
  eşlenir, benzerlik skoru üretilir.
- Eşik altı (belirsiz) eşleşmeler düşük `eslesme_guveni` ile işaretlenir; manuel gözden
  geçirme sonrası düzeltmeler `bilinen_varyasyonlar` tablosuna eklenerek sözlük öğrenir
  (yarı-otomatik, insan-döngüde süreç).
- Doz/sıklık çıkarımı: regex kalıpları ("400mg", "3x1", "1x1 gece" gibi standart formatlar).

## Semptom Kümeleme

- Hafif Türkçe cümle gömme modeli (sentence-transformers, CPU) ile semptom ifadeleri
  vektöre çevrilir.
- HDBSCAN/k-means ile benzer ifadeler kümelenir.
- Kümeler oluştuktan sonra kullanıcı (gerekirse danışmanla) her kümeye anlamlı etiket verir
  (örn. "artmış enerji/elevasyon", "uyku bozukluğu", "anksiyete") — yarı-denetimli.

## Doğrulama

547 hastadan rastgele bir örneklem (30-50 hasta) elle etiketlenip altın standart oluşturulur;
pipeline çıktısı bununla karşılaştırılıp precision/recall raporlanır (tez metodoloji bölümü
için gerekli).

## Teknoloji Yığını

| Katman | Teknoloji | Neden |
|---|---|---|
| Veri işleme | Python, pandas | OCR çıktısı zaten Excel'de |
| İlaç eşleştirme | RapidFuzz | Hafif, hızlı, GPU gerektirmez |
| Semptom NER/embedding | HuggingFace Transformers + Türkçe BERT (BERTurk türevi), sentence-transformers | CPU'da 8GB RAM'e sığar |
| Kümeleme | scikit-learn (HDBSCAN/KMeans) | Standart, hafif |
| Veritabanı | SQLite (`sqlite3`/SQLAlchemy) | Kurulumsuz, ilişkisel, taşınabilir |
| Doğrulama | pandas + manuel etiketleme | Precision/recall raporlama |
| (Alt proje 3 için ileride) | Ollama + küçük yerel LLM (Gemma2-2B/Llama3.2-3B) | Dışa veri çıkmadan sohbet/öneri |

## Kapsam Dışı (bu alt proje için)

- Zaman trendi görselleştirme (alt proje 2)
- Öneri/chatbot sistemi (alt proje 3)
- Demografik veri zenginleştirme (OCR çıktısında yoksa eklenmeyecek)

# Öneri/Chat Sistemi — Tasarım Dokümanı

## Genel Bakış

Bu, TRSM bitirme projesinin 3. (ve son) alt sistemi: yeni bir hastanın yazdığı
semptom ifadesine (örn. "halsizim") göre, geçmişte benzer semptomlu hastalara
verilen ilaçları istatistiksel olarak gösteren ve yerel bir LLM ile doğal dile
çeviren bir sohbet uygulaması.

**Bağımlılık:** Alt proje 1 (veri temizleme & varlık çıkarımı) tamamlanmış ve
`trsm.db` dolu olmalı — özellikle `semptom_kaydi.ifade_ham` ve `ilac_kullanimi`
tabloları.

**Kritik kısıt (proje genelinde geçerli):** Tüm işleme yerelde çalışır, hiçbir
hasta verisi dışarı gönderilmez. LLM olarak yerel Ollama + Gemma2-2B kullanılır
(zaten kuruldu ve test edildi, `ollama list` ile doğrulanabilir).

**Kritik tasarım kararı:** LLM'e asla ham hasta verisi gönderilmez — sadece
önceden hesaplanmış, agregat istatistik (ilaç adı + yüzde) prompt olarak
verilir. Bu hem gizliliği korur hem de LLM'in veri uydurma (halüsinasyon)
riskini azaltır, çünkü model sadece verilen sayıları cümleye döküyor.

## Eşleştirme Yöntemi

Alt proje 1'in `semptom_kaydi` tablosundaki HDBSCAN küme etiketleri
(`cluster_N`) henüz anlamlı biçimde manuel etiketlenmediği için, yeni bir
sorguyu doğrudan bu kümelere atamak yerine **doğrudan semantik en-yakın-komşu
arama** kullanılır:

1. `semptom_kaydi.ifade_ham` içindeki tüm ifadeler, alt proje 1'de kullanılan
   aynı embedding modeliyle (`paraphrase-multilingual-MiniLM-L12-v2`) vektöre
   çevrilip diske kaydedilir (bir kerelik hazırlık adımı, `.npy` dosyası +
   `ziyaret_id` eşleşme listesi).
2. Kullanıcının sorgusu aynı modelle vektöre çevrilir.
3. Kayıtlı vektörlerle kosinüs benzerliği hesaplanır (numpy, brute-force —
   veri ölçeği ~80-100k ifade için ayrı bir vektör veritabanı gerekmez).
4. En benzer N (varsayılan 50) tarihsel ifade bulunur.
5. Bu ifadelerin bağlı olduğu `ziyaret_id`'lerdeki `ilac_kullanimi` kayıtları
   toplanır ve ilaç bazında yüzde/oran hesaplanır.

## Veri Kalitesi ve Hata Yönetimi

- Benzerlik skoru bir eşiğin altındaysa (varsayılan cosine similarity < 0.5),
  sistem "bu semptoma yeterince benzer geçmiş veri bulunamadı" yanıtı verir —
  uydurma cevap üretmez.
- İlaç istatistiği hesaplanırken, alt proje 1'deki `eslesme_guveni >= 90`
  filtresi burada da uygulanır (alt proje 2'deki `GUVEN_ESIGI` mantığıyla
  tutarlı) — düşük güvenli ilaç eşleşmeleri öneriye dahil edilmez.

## Tıbbi Uyarı (zorunlu)

Arayüzde her yanıtın altında sabit, kaldırılamaz bir uyarı metni gösterilir:
"Bu bir istatistiksel özet olup tıbbi tavsiye değildir, tedavi kararı hekim
tarafından verilmelidir." Tez metninde de bu sınırlama açıkça belirtilecek.

## Analiz Akışı

```
Kullanıcı sorgusu ("halsizim")
   → [Aşama A] Embedding: sorgu vektöre çevrilir
   → [Aşama B] Benzerlik arama: en yakın 50 tarihsel ifade bulunur
                (benzerlik eşiği altındaysa "veri yok" yanıtı)
   → [Aşama C] İstatistik: bu ifadelere bağlı ziyaretlerdeki ilaç_kullanimi
                kayıtları (eslesme_guveni >= 90) toplanır, ilaç bazında
                yüzde hesaplanır
   → [Aşama D] LLM özeti: istatistik tablosu Ollama/Gemma2-2B'ye prompt
                olarak verilir, doğal dilde özet üretilir (ham veri LLM'e
                gitmez, sadece agregat sayılar)
   → [Aşama E] Streamlit arayüzü: istatistik tablo + LLM özeti + sabit
                tıbbi uyarı gösterilir
```

## Dosya Yapısı

- `trsm/symptom_similarity.py` — embedding indeksi oluşturma
  (`build_symptom_index`) ve sorgu zamanı en-yakın-komşu arama
  (`find_similar_phrases`) fonksiyonları.
- `trsm/recommendation.py` — ilaç istatistiği hesaplama
  (`compute_drug_statistics`) ve LLM prompt oluşturma/çağırma
  (`generate_summary`) fonksiyonları.
- `scripts/build_symptom_index.py` — bir kerelik CLI: `semptom_kaydi`'ni
  okuyup embedding indeksini diske yazar.
- `app.py` (repo kökü, Streamlit konvansiyonu) — sohbet arayüzü, yukarıdaki
  modülleri çağırır.
- Yeni SQLite tablosu YOK — embedding indeksi diskte ayrı bir dosya
  (`.npy`/`.pkl`), `trsm.db`'ye yazılmıyor (büyük ikili veri, veritabanı
  şişirmemek için).

## Teknoloji Yığını

| Katman | Teknoloji | Neden |
|---|---|---|
| Embedding | sentence-transformers (aynı model, alt proje 1 ile tutarlı) | Zaten kurulu, aynı vektör uzayı |
| Benzerlik arama | numpy (cosine similarity) | Veri küçük ölçekli, ekstra bağımlılık gerekmez |
| LLM | Ollama + Gemma2-2B (yerel, `ollama` Python client) | 8GB RAM M1'e uygun, zaten kurulu ve test edildi |
| Arayüz | Streamlit | Hızlı kurulur, tez sunumu için sohbet hissi verir |
| Veri erişimi | `sqlite3`/`pandas` (`trsm.db`, salt-okunur) | Mevcut şemayla tutarlı |

## Kapsam Dışı

- Küme etiketlerinin (cluster_N) manuel olarak anlamlı isimlerle
  etiketlenmesi (ayrı, isteğe bağlı bir iyileştirme)
- Çoklu-turn sohbet geçmişi / bağlam takibi (v1 tek-turn soru-cevap)
- Kullanıcı kimlik doğrulama / çoklu kullanıcı desteği (tek kullanıcılı,
  yerel araştırma aracı)

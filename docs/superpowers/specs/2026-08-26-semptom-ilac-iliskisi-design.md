# Semptom-İlaç İlişkisi Bulgusu — Tasarım Dokümanı

## Genel Bakış

TRSM bitirme projesinin asıl analitik bulgusu: `trsm.db`'deki tüm veri seti
(96.693 semptom kaydı, 41.676 ziyaret) üzerinden, bilinen psikiyatrik semptom
kategorileri ile bu kategorilere karşılık gelen ziyaretlerde en sık kullanılan
ilaçlar arasında sistematik, tekrarlanabilir bir ilişki tablosu/grafiği
üretmek. Bu, tezin "bulgular" bölümüne girecek.

**Bağımlılık:** Alt proje 1 (veri temizleme & varlık çıkarımı) ve alt proje 3
(öneri/chat sistemi — `trsm/symptom_similarity.py`, `trsm/recommendation.py`)
tamamlanmış olmalı. `data/symptom_index.npz` güncel (filtrelenmiş semptom
verisiyle inşa edilmiş) olmalı.

**Neden kümeleme değil, önceden tanımlı kategoriler:** `trsm/symptom_clustering.py`
içindeki HDBSCAN tabanlı kümeleme, embedding'ler normalize edilmeden
kullanıldığı için pratikte anlamsız (96.693 kayıttan 95.604'ü tek bir dev
kümeye düşüyor). Normalize edilince kümeleme teknik olarak düzelebiliyor
(8.000'lik örneklemde 125 anlamlı küme), ama ortaya çıkan kümelerin klinik
olarak tutarlı temaları temsil ettiğinin garantisi yok, ve kümeleri
anlamlandırmak (etiketlemek) başlı başına bir yorum riski taşıyor. Bunun
yerine, zaten test edilmiş ve 0.9-1.0 benzerlik skorlarıyla çalıştığı
doğrulanmış `find_similar_phrases` mekanizması, literatürden alınan bilinen
semptom kategorileriyle "çoklu sorgu" olarak kullanılacak — sonuçlar daha
yorumlanabilir ve savunulabilir.

**Kapsam (v1):** Tanımlayıcı/istatistiksel bir ilişki bulgusu ("bu semptom
grubuyla ilişkili ziyaretlerde en sık şu ilaçlar kullanılmış"). Nedensellik
iddiası (bu ilaç bu semptomu tedavi ediyor) kapsam dışı — tez metninde bu
ayrımın yapılması kullanıcının sorumluluğu.

## Semptom Kategorileri

Literatürden alınan, tanı koymayan geniş tema başlıkları. Her kategori için
birden fazla Türkçe örnek ifade (arama sorgusu olarak kullanılacak):

| Kategori | Örnek sorgu ifadeleri |
|---|---|
| Uyku bozukluğu | uykusuzluk, uyku düzensizliği, aşırı uyku hali |
| Öfke / ajitasyon | öfke nöbeti, ajitasyon, saldırganlık, huzursuzluk |
| Anksiyete / gerginlik | anksiyete, gerginlik, kaygı, endişe hali |
| Depresif belirtiler | çökkünlük, isteksizlik, mutsuzluk, enerji azlığı |
| Manik / taşkın belirtiler | taşkınlık, aşırı enerji, hızlı konuşma, elevasyon |
| Halüsinasyon / hezeyan | halüsinasyon, sesler duyma, hezeyan, şüphecilik |
| İştah / kilo değişimi | iştahsızlık, aşırı iştah, kilo alımı, kilo kaybı |
| Sosyal içe kapanma | içe kapanma, sosyal izolasyon, işlevsellik kaybı |
| Madde kullanımı | madde kullanımı, alkol kullanımı, bağımlılık |
| Tedaviye uyumsuzluk | ilaç bırakma, düzensiz ilaç kullanımı, tedaviyi reddetme |

Bu liste kullanıcı ile birlikte gözden geçirilip spec onayı sırasında
netleştirilecek; ekleme/çıkarma serbest.

## Yöntem

1. **Kategori embedding'i:** Her kategorinin örnek ifadeleri
   `paraphrase-multilingual-MiniLM-L12-v2` ile ayrı ayrı encode edilir, ortalaması
   alınarak tek bir "kategori sorgu vektörü" elde edilir.
2. **Eşleşen ziyaretler:** `find_similar_phrases` ile her kategori vektörü,
   `data/symptom_index.npz`'deki tüm 96.693 kayda karşı taranır
   (`min_similarity=0.75`, `top_n` yüksek bir değer — örn. 500 — çünkü burada
   amaç "en yakın 5" değil, kategoriye giren tüm ziyaretler). Eşleşen
   kayıtların `ziyaret_id`'leri tekilleştirilir.
3. **İlaç istatistiği:** Her kategorinin ziyaret_id kümesi
   `compute_drug_statistics(conn, ziyaret_ids, guven_esigi=90)` ile ilaç
   dağılımına çevrilir (mevcut trend notebook'uyla tutarlı güven eşiği).
4. **Küçük örneklem uyarısı:** Bir kategoriye eşleşen ziyaret sayısı düşükse
   (örn. <20), tabloda/grafikte açıkça "küçük örneklem, dikkatli
   yorumlanmalı" notu düşülür.
5. **Örtüşme:** Bir ziyaret birden fazla kategoriye girebilir (örn. hem uyku
   hem anksiyete eşiği geçebilir) — zorla tek kategoriye atama yapılmaz, bu
   veriye daha sadık bir yaklaşım.

## Çıktı

Yeni notebook: `notebooks/semptom_ilac_iliskisi.ipynb`, mevcut
`ilac_kullanim_trendi.ipynb` ile aynı stil/yapı:

1. Veri yükleme (db bağlantısı, symptom_index yükleme, model yükleme)
2. Kategori tanımları ve sorgu vektörlerinin hesaplanması
3. Her kategori için eşleşen ziyaret sayısı — özet tablo
4. Her kategori için ilk 5-10 ilaç + yüzdeleri — tablo
5. Görselleştirme: kategori × ilaç ısı haritası (heatmap) veya her kategori
   için ayrı bar chart (küçük çoklu grafikler / small multiples)
6. Genel özet metni: toplam kaç ziyaret en az bir kategoriye girdi, hangi
   kategoriler en büyük/en küçük örnekleme sahip, metodolojik sınırlama notu
   (tanımlayıcı bulgu, nedensellik değil)

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Semptom benzerlik | `trsm.symptom_similarity` (mevcut, değişmeyecek) |
| İlaç istatistiği | `trsm.recommendation.compute_drug_statistics` (mevcut, değişmeyecek) |
| Embedding modeli | `sentence-transformers`, `paraphrase-multilingual-MiniLM-L12-v2` |
| Analiz/görselleştirme | `pandas`, `matplotlib`/`seaborn` |
| Ortam | Jupyter notebook |

## Dosya Yapısı

- `notebooks/semptom_ilac_iliskisi.ipynb` — yeni notebook, yukarıdaki 6 adım
- Yeni bir `trsm/` modülü gerekmiyor — mevcut `symptom_similarity` ve
  `recommendation` modülleri olduğu gibi kullanılıyor. Kategori tanımları
  (isim + örnek ifadeler) notebook içinde bir Python sözlüğü olarak tutulur;
  ayrı bir veri dosyasına çıkarmaya gerek yok (küçük, sabit, tek yerde
  kullanılan bir liste).

## Kapsam Dışı

- HDBSCAN kümelemesinin düzeltilmesi (ayrı, isteğe bağlı bir iyileştirme —
  bu spec'in parçası değil)
- Nedensellik analizi / klinik etkinlik iddiası
- Kategori listesinin klinik olarak "doğru" veya "eksiksiz" olduğunun
  doğrulanması (kullanıcı yazılımcı, klinik değil; danışmanla birlikte
  gözden geçirilmesi önerilir)
- İnteraktif dashboard (v1 sadece notebook)

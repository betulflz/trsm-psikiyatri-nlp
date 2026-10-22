# TRSM projesini koddan anlayarak okuma rehberi

Bu rehberin amacı projeyi sadece çalıştırmak değil, her çıktının **hangi veriden,
hangi kuralla ve hangi kod yolundan** geldiğini takip edebilmektir. Proje,
geçmiş TRSM ziyaret kayıtlarından ilaç örüntülerini betimleyen yerel bir analiz
uygulamasıdır. Bir tedavi/reçete sistemi değildir.

## Önce büyük resmi kur

```text
OCR Excel
  │
  ▼
scripts/run_pipeline.py
  │
  ├─ Excel'i doğrula ve tarihleri tamamla
  ├─ SQLite tablolarını oluştur / ziyaretleri kaydet
  ├─ Demografik bilgiyi form metninden çıkar
  ├─ İlaç sözlüğüyle ilaç, doz ve sıklık yakala
  └─ Semptom gibi görünen metin parçalarını çıkar ve kümele
  │
  ├────────────► trsm.db       (kalıcı, sorgulanabilir kayıtlar)
  └────────────► symptom_index.npz (semantik arama vektörleri)
                           │
                           ▼
                    demo_server.py / Flask API
                           │
                           ▼
                       demo.html
```

İki ayrı çalışma aşaması vardır:

1. **Veri hazırlama:** Ham Excel'i `trsm.db` veritabanına dönüştürür. Bu işlem
   geliştirici işidir; `scripts/run_pipeline.py` ile başlar.
2. **Demo/sorgu:** Önceden hazırlanmış veritabanını ve semptom indeksini açar,
   tarayıcıya API sunar. Bu işlem `demo_server.py` ile başlar.

Bu ayrım önemlidir: arayüz Excel okumaz ve yeni semptom kümesi üretmez. Hazır
çıktıları sorgular.

## Okuma sırası: 90 dakikalık ilk tur

Dosyaları aşağıdaki sırayla okuyun. Her dosyada önce fonksiyon imzalarına,
sonra çağrıldığı yere, son olarak testine bakın. Böylece ayrıntılar arasında
kaybolmadan kontrol akışını öğrenirsiniz.

| Sıra | Dosya | Okurken cevaplanacak soru |
| --- | --- | --- |
| 1 | `README.md` | Ürün neyi yapıyor, neyi özellikle yapmıyor? |
| 2 | `trsm/schema.sql` | Hangi varlıklar saklanıyor ve ilişkileri ne? |
| 3 | `trsm/pipeline.py` | Hazırlama işlemlerinin kesin sırası ne? |
| 4 | `trsm/cleaning.py`, `data_loading.py`, `visit_loading.py` | Excel satırı nasıl `ziyaret` satırına dönüşüyor? |
| 5 | `trsm/medication_pipeline.py` | Serbest OCR metninden ilaç kaydı nasıl çıkıyor? |
| 6 | `trsm/symptom_extraction.py`, `symptom_pipeline.py` | Metnin hangi parçaları semptom sayılıyor? |
| 7 | `trsm/symptom_similarity.py` | Benzer semptomlar nasıl bulunuyor? |
| 8 | `trsm/profiled_recommendation.py` | Yaş/cinsiyet filtresi gizliliği koruyarak nasıl uygulanıyor? |
| 9 | `trsm/transparent_symptom_query.py` | Kullanıcı anlatısı tema ve arama sonucuna nasıl dönüyor? |
| 10 | `demo_server.py` | Tarayıcı isteği yukarıdaki mantığa nasıl bağlanıyor? |
| 11 | İlgili `tests/test_*.py` | Davranışın beklenen sınırları neler? |

Özellikle 3. adımdan sonra her fonksiyon için şu üç notu alın: **girdi**,
**dönüş değeri/yan etkisi**, **neden bu kontrol var**. Bu alışkanlık, AI ile
yazılmış olsa dahi kodun sahibi olmayı sağlar.

## Veri modeli: veritabanını bir harita gibi oku

`trsm/schema.sql` proje için en güvenilir sözleşmedir.

```text
hasta (1) ─────< ziyaret (1) ─────< ilac_kullanimi
                  │
                  └──────────────< semptom_kaydi

ilac_sozluk (1) ─────< ilac_varyasyon
```

- `hasta`: İlk başta `dosya_adi` üzerinden oluşturulan kişi. Cinsiyet ve doğum
  tarihi ayrıca kaynak bilgileriyle saklanır.
- `ziyaret`: Bir Excel satırından gelen, tarih/sayfa/OCR metni taşıyan olay.
  Analizin merkezi tablosu budur.
- `ilac_kullanimi`: Bir ziyaret metninde sözlükle eşleşmiş ilaç. `ham` değer
  izlenebilirlik için, `normalize` değer toplulaştırma için tutulur.
- `semptom_kaydi`: Semptom kabul edilen ham ifade ve küme etiketi. Ham ifade
  daha sonra denetlenebilmesi için tutulur.
- `ilac_sozluk` ve `ilac_varyasyon`: OCR yazım hatası ve farklı yüzey biçimleri
  için resmi ilaç adını varyasyonlardan ayırır.

Bir sorgu sonucunu doğrularken önce şu SQL ile gerçek tablo biçimini görün:

```bash
sqlite3 trsm.db ".schema"
sqlite3 trsm.db "SELECT * FROM ziyaret LIMIT 3;"
```

Kişisel sağlık verisi içerdiği için gerçek satırları terminal çıktısına, Git'e
veya dış servislere taşımayın.

## Hazırlama hattı, adım adım

Ana orkestratör `trsm.pipeline.run_pipeline(...)` fonksiyonudur. Bu fonksiyonun
kendisi bilinçli olarak kısa tutulmuştur: ayrıntıların hangi modülde olduğunu
hemen gösterir.

1. `load_raw_excel`: Pandas ile Excel'i açar ve beş zorunlu sütunu kontrol eder:
   `Dosya`, `Sayfa`, `Tarih`, `Müdahale`, `Sonuç`. Eksik şema varsa erken hata
   verir; yanlış veriyi sessizce işlememek burada amaçtır.
2. `fill_missing_dates`: `parse_tarih` tarihi ISO biçimine (`YYYY-MM-DD`) çevirir.
   Ardından aynı `Dosya` içindeki boş tarihleri `ffill()` ile önceki tarihle
   doldurur. Bu, kaynak Excel'in sıralı olduğu varsayımına dayanır.
3. `create_schema` ve `load_visits`: Şemayı çalıştırır; her yeni dosya adını bir
   `hasta`, her Excel kaydını bir `ziyaret` yapar. `hasta_id_cache`, tekrar tekrar
   aynı kişiyi sorgulamamak için küçük bir bellek önbelleğidir.
4. `run_demographic_extraction`: Sadece `RH.FR.002` form etiketli sayfalarda
   doğum tarihi ve işaretli cinsiyet kutusunu arar. Birden fazla çelişen değer
   varsa değer üretmek yerine `None` bırakır. Yaş, bugüne göre değil en erken
   ziyaret tarihine göre makul kabul edilir.
5. İlaç sözlüğü CSV'den hem belleğe hem de DB'ye yüklenir. `surface_form_index`,
   örneğin bir varyasyondan resmi ilaç adına giden sözlüktür.
6. `run_medication_extraction`: Her ziyaretin müdahale ve sonuç metnini birleştirip
   ilaç, doz, sıklık çıkarır.
7. `run_symptom_extraction`: Metni parçalara böler, belirti dışı kayıtları eler,
   cümleleri vektörleştirir ve benzerlerini kümeleyerek `semptom_kaydi`na yazar.

Pipeline tekrar çalıştırıldığında mevcut DB'yi varsayılan olarak ezmez.
`overwrite=True` yalnızca bilinçli yeniden üretim için vardır. Bu davranış
`tests/test_pipeline.py` içinde sınanır.

## İlaç çıkarımı: kural + bulanık eşleştirme

Bu bölümün giriş noktası `extract_medications_from_text`tir.

1. `extract_candidates` (`drug_matching.py`) OCR metnindeki kelimeleri konumlarıyla
   yakalar ve 1, 2, 3 kelimelik adaylar üretir. Konumlar (`start`, `end`) daha
   sonra dozun hangi ilaca ait olduğuna karar vermek için gereklidir.
2. `match_drug`, her adayı sözlükteki varyasyonlarla RapidFuzz `fuzz.ratio`
   üzerinden karşılaştırır. Skor 85'in altındaysa aday reddedilir.
3. Aynı resmi ilaç çok yakın konumlarda bulunmuşsa `PROXIMITY_GAP=3` ile daha
   zayıf tekrar atılır.
4. İlaç adından sonra en fazla 40 karakterlik pencerede `extract_dose_frequency`
   çalışır. Sonraki ilacın başlangıcı pencerenin üst sınırıdır; bu "dozun sonraki
   ilaca sızması" hatasını önler.

Buradaki önemli fikir şudur: eşleşme kesin tanıma değildir. `eslesme_guveni`
fuzzy skorudur. Analiz sorguları çoğunlukla `>= 90` eşiğiyle daha güvenilir
kayıtları kullanır. `tests/test_medication_pipeline.py`ni satır satır okuyun;
özellikle iki ardışık ilacın doz penceresi testi tasarım niyetini açık eder.

## Semptom işlemesi: iki farklı kavramı karıştırma

Projede iki ayrı "kategori" mekanizması bulunur:

| Mekanizma | Kod | Amaç |
| --- | --- | --- |
| Keşif kümesi | `symptom_pipeline.py`, `symptom_clustering.py` | Geçmiş OCR ifadelerini gözetimsiz olarak benzer gruplara ayırmak (`cluster_0` vb.) |
| Görünür geniş tema | `symptom_categories.py`, `transparent_symptom_query.py` | Kullanıcıya açıklanabilir, önceden gözden geçirilebilir etiket sunmak |

İlki HDBSCAN kullanır: MiniLM vektörleri uzayında yoğun ifade grupları bulur;
gruba girmeyenleri `-1`/`kategorisiz` yapar. Bu bir tanı sınıflandırıcısı
değildir.

İkincisi ürün ekranında kullanılır. `KATEGORILER` sözlüğündeki görünür tohum
ifadeler MiniLM ile vektörleştirilir. Kullanıcı cümlesi bu tohumlarla kosinüs
benzerliği üzerinden eşleşir:

```text
kosinüs benzerliği = normalize(kullanıcı vektörü) · normalize(tohum vektörü)
```

- Cümlede tohum açıkça geçiyorsa `ifade` eşleşmesi daha güçlü kanıttır.
- Aksi halde skor en az `0.60` olmalı ve en iyi temadan `0.12`den fazla geride
  olmamalıdır.
- Açık olumsuzlama (ör. "uykusuzluk yok") ilgili otomatik temayı bastırır.
- En fazla iki tema gösterilir; belirsizlik ayrıca API sonucunda belirtilir.

`classify_record_phrase` semptom indeksine girecek geçmiş metin için daha önce
çalışan koruyucudur. Form metni, randevu, telefon, doz/ilaç ve "şikâyet yok"
gibi parçaları ayırır. Bu nedenle semantik aramaya giren metin "her OCR
cümlesi" değildir.

## Kullanıcının sorgusu ekrana gelene kadar ne olur?

İstemci `POST /api/sorgu` ile `sorgu`, `yas`, `cinsiyet` gönderir. Sunucunun
çağırdığı `analyze_transparent_symptom_query` şu hattı izler:

```text
Kullanıcı anlatısı
  → split_user_symptoms
  → yüksek risk kontrolü
  → geniş tema açıklaması
  → her cümleyi MiniLM ile vektörleştirme
  → symptom_index.npz içinde kosinüs benzerliği araması
  → ziyaret başına en yüksek skora indirgeme
  → doğrulanmış cinsiyet + ziyaret günündeki yaş grubu filtresi
  → ilaçların SQL ile sayılması
  → yalnızca toplulaştırılmış JSON
```

`symptom_index.npz` üç paralel dizi taşır: `embeddings`, `ziyaret_ids`,
`phrases`. Aynı indeks numarası bunların aynı semptom kaydına ait olduğunu
anlatır. `find_similar_phrases` sorgu vektörüyle tüm indeks vektörlerinin
kosinüs benzerliğini hesaplar, en iyi sonuçları alır ve minimum benzerlik
eşiği uygular.

`profile_matched_visits` kritik gizlilik/istatistik fonksiyonudur. Aynı ziyarette
birden fazla benzer ifade bulunsa bile `_best_similarity_by_visit` o ziyareti
bir kez sayar. Sonra yalnızca doğrulanmış demografik kaynaklara sahip ve aynı
geniş yaş grubundaki geçmiş ziyaretleri geçirir. Geniş yaş grupları: 15–17,
18–29, 30–44, 45–59, 60+.

`compute_drug_statistics` ilacı reçete etmez: seçilen ziyaretlerdeki yüksek
güvenli `ilac_kullanimi` kayıtlarını sayar ve yüzdeleri bu ilaç kayıtlarının
toplamına göre hesaplar. 20 ziyaretten veya 5 kişiden az örneklem ayrıca
işaretlenir.

Yüksek riskli kendine zarar/intihar ifadelerinde sistem ilaç örüntüsü üretmez.
Bu kontrol modelden önce, kural tabanlı olarak yapılır.

## Flask katmanı: API'yi takip et

`demo_server.py` uygulamanın bileşim köküdür. Başlangıçta yerel MiniLM modelini,
NPZ indeksini ve tema tohum vektörlerini bir kez yükler. Bu, her istekte modeli
tekrar açmaktan kaçınır.

| Uç nokta | Sorumluluk |
| --- | --- |
| `GET /api/genel` | Veritabanındaki temel sayılar |
| `GET /api/trend` | Yıllara göre en sık altı ilaç |
| `GET /api/kategoriler` | Tema bazlı önbelleğe alınmış özet |
| `POST /api/sorgu` | Ana, açıklanabilir profil sorgusu |
| `POST /api/ikinci-gorus` | Varsa yerel Qwen ile isteğe bağlı yöntem karşılaştırması |
| `GET /api/hasta-tedavi-gecis` | Pseudonymous kişi için gözlenen ilaç-listesi değişimi |

`build_evidence_summary` sayıları ve ilaç adlarını doğrudan Python sonucundan
oluşturur; LLM'nin olgusal sonuç üretmesine güvenmez. Qwen yalnızca isteğe bağlı
kontrollü açıklama notu için kullanılır ve güvenlik denetiminden geçemezse sabit
metne geri dönülür. Bu, üretken modelin rolünü kasıtlı biçimde sınırlayan iyi
bir tasarım kararıdır.

## Tedavi geçişi bölümü ne söylüyor, ne söylemiyor?

`treatment_timeline.py` aynı günün ilaç kayıtlarını birleştirir ve ardışık
ilaç listeleri arasındaki ekleme/çıkarma/değişim adaylarını bulur.
`treatment_response_analysis.py` değişimden sonraki en fazla 90 gün içindeki
ilk semptom kayıtlı takibi karşılaştırır.

Bu bölüm **nedensel etki analizi değildir**. Bir temanın sonraki notta görünmemesi
iyileşme kanıtı; yeni görünmesi yan etki veya kötüleşme kanıtı değildir. Kodun
`sinirlilik_notu` alanlarında bu uyarıyı taşıması rastlantı değil, ürün
sınırının bir parçasıdır.

## Testleri öğrenme aracı yap

Tüm testleri çalıştırmak için:

```bash
uv run pytest -q
```

Önce küçük bir test dosyasını ayrıntılı okuyup çalıştırmak daha öğreticidir:

```bash
uv run pytest tests/test_medication_pipeline.py -q
uv run pytest tests/test_transparent_symptom_query.py -q
uv run pytest tests/test_profiled_recommendation.py -q
```

Test adlarını doğal dilde gereksinim gibi okuyun. Örneğin:

- `test_run_symptom_extraction_filters_out_non_symptom_phrases`: randevu/ilaç
  gibi satırların semptom indeksine sızmaması gerekir.
- `test_unclassified_clause_is_still_included_in_combined_semantic_evidence`:
  görünür teması belirsiz bir kullanıcı cümlesi, genel semantik kanıttan
  otomatik silinmemelidir.
- `test_profiled_recommendation_uses_same_gender_and_historical_age_group_only`:
  profil filtresinin ana iş kuralıdır.
- `test_high_risk_expression_does_not_produce_medication_pattern`: güvenlik
  sınırıdır.

Bir fonksiyonu değiştirmeden önce önce ilgili testi okuyun, sonra testi bilinçli
olarak bozan küçük bir değişikliği ayrı çalışma alanında deneyin, en son geri
alın. Böylece testin gerçekten neyi koruduğunu öğrenirsiniz.

## İnceleme sırasında dikkat edilecek varsayımlar ve geliştirme noktaları

Bu maddeler hata iddiası değil; proje sahibi olarak izlemeniz gereken kararlar:

1. Tarih ileri doldurma, Excel satırlarının hasta içinde kronolojik ve bağlam
   olarak doğru sıralandığını varsayar.
2. `Dosya` alanı başlangıçta hasta kimliği yerine kullanılır. Dosya birleşmesi
   için sonradan `hasta_dosya` ve hasta birleştirme araçları vardır; bu ayrımı
   inceleyin.
3. İlaç eşleştirme eşiği (85), analiz eşiği (90), semptom arama eşiği (0.50)
   ve tema eşiği (0.60) ampirik ürün parametreleridir. Veri değişirse doğrulama
   örneklemiyle yeniden değerlendirilmelidir; "model gerçeği" değildir.
4. `np.load(..., allow_pickle=True)` yalnızca projenin kendi ürettiği yerel
   indeks için kabul edilmiştir. Dışarıdan gelen `.npz` dosyasında kullanılmamalı.
5. Otomatik çıkarımın güvenilirliği klinik doğruluk anlamına gelmez. `docs/`
   altındaki doğrulama protokolü ve raporlar bu nedenle ürün mantığının
   tamamlayıcı parçasıdır.

## Aktif öğrenme planı

İlk gün yalnızca okumak yerine şu dört mini egzersizi yapın:

1. Kağıda bir Excel satırının `ziyaret`, `ilac_kullanimi` ve `semptom_kaydi`
   tablolarında hangi satırlara dönüşeceğini çizin.
2. `extract_medications_from_text` için yeni bir OCR yazım hatası testi yazın.
   Önce test kırmızı, sonra sözlük varyasyonu ekleyince yeşil olsun.
3. `split_user_symptoms`e virgüllü bir Türkçe örnek verin; neden bölünüp
   bölünmediğini `has_predicate` üzerinden açıklayın.
4. `compute_profiled_recommendation` dönüşündeki bir sayıyı seçin ve SQL'den
   başlayıp API JSON'una kadar her ara değişkeni elle takip edin.

Bir hafta sonra daha anlamlı bir geliştirme hedefi seçebilirsiniz: ölçülmüş
bir yanlış ilaç eşleşmesini sözlüğe/teste eklemek, doğrulama örneklemi üzerinden
eşik analizi yapmak veya demografik belirsizliği arayüzde daha görünür kılmak.
Önce mevcut test, sonra küçük değişiklik, sonra tüm test paketi sırası bu
projede güvenli çalışma biçimidir.

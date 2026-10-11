# TRSM Bitirme Projesi — Mini Sunum Notları

Bu metin 7–10 dakikalık danışman sunumu için hazırlanmıştır. Köşeli parantez
içindeki notlar slayta konmak zorunda değildir; konuşurken kullanılabilir.

## 1. Problem ve hedef

**Slayta yazılacak:**

> El yazısı/OCR kaynaklı TRSM kayıtlarını yapılandırılmış yerel bir veri setine
> dönüştürmek; ilaç, semptom, zaman, yaş ve cinsiyeti birlikte analiz etmek.

**Anlatım:**

Başlangıç verimiz serbest metin ağırlıklı OCR çıktısıydı. Bu nedenle “hangi
semptomla hangi ilaç kaydı birlikte geçiyor?” sorusu doğrudan sorgulanamıyordu.
Projenin amacı, bu kayıtları izlenebilir biçimde yapılandırmak ve yeni bir
kullanıcı profili için geçmişteki **benzer kayıtların istatistiksel özetini**
üretmekti. Sistem klinik karar veya reçete vermez.

## 2. Kaynak veri ve bugün ulaşılan veri seti

**Slayta yazılacak:**

| Katman | Güncel büyüklük |
|---|---:|
| Kaynak PDF | 547 |
| Gerçek kişi | 434 |
| Ziyaret | 41.676 |
| İlaç kaydı | 22.726 |
| Semptom ifadesi | 96.693 |
| Normalize edilmiş ilaç adı | 61 |

**Anlatım:**

Başlangıçta her PDF ayrı hasta gibi görünüyordu. Aynı kişinin örneğin `Ad Soyad
1.pdf` ve `Ad Soyad 2.pdf` şeklinde birden fazla raporu olabiliyor. Kaynak
klasör yapısını kullanarak bu PDF'leri tek gerçek kişi altında birleştirdik.
547 kaynak dosya ve bütün ziyaretler korunurken analizde artık 434 kişi baz
alınıyor.

## 3. Uçtan uca teknik mimari

```text
OCR Excel
  → metin/tarih temizleme
  → ilaç, doz ve sıklık çıkarımı
  → semptom ifadelerinin çıkarımı ve embedding indeksi
  → SQLite ilişkisel veritabanı
  → trend + semptom + demografik analiz
  → yaş + cinsiyet + semptomlu yerel sorgu ekranı
```

**Anlatım:**

Her aşama bağımsız Python modülü olarak yazıldı ve test edildi. Bu yapı, örneğin
ilaç sözlüğünü iyileştirirken semptom aramasını veya arayüzü bozmamayı sağlar.
Ana veri deposu SQLite; bu sayede sunucu, bulut veritabanı veya dış servise
ihtiyaç yok.

## 4. OCR metninden ilaç bilgisini nasıl çıkardık?

**Slayta yazılacak:**

- İlaç sözlüğü + yazım varyasyonları
- RapidFuzz `fuzz.ratio` ile bulanık eşleştirme
- Regex ile doz ve kullanım sıklığı
- Güven puanı: analizde `>= 90/100`

**Anlatım:**

OCR ve el yazısı nedeniyle aynı ilaç farklı yazılabiliyor. Metindeki bir, iki
veya üç kelimelik aday parçaları ilaç sözlüğüyle karşılaştırıyoruz. RapidFuzz,
Levenshtein benzeri karakter benzerliği kullanarak en yakın adı ve 0–100 arası
güven puanını veriyor. `fuzz.ratio` seçildi; kısa metin parçalarının yanlışlıkla
ilaç adı sayılmasını azaltıyor. İlaç çevresindeki sınırlı metin penceresinde
`400 mg`, `3x1` gibi regex kalıplarıyla doz/sıklık da aranıyor.

Bu bir kural + sözlük + bulanık eşleştirme yaklaşımıdır; kara kutu bir ilaç
tahmin modeli değildir. Ham metin silinmez, her sonuç kaynak ziyarete bağlı
kalır.

## 5. Semptom bilgisini nasıl temsil ettik?

**Slayta yazılacak:**

- Gürültülü form başlıkları, telefon numaraları ve ilaç-doz satırları elendi.
- Metin uygun parçalara ayrıldı.
- `paraphrase-multilingual-MiniLM-L12-v2` ile vektör (embedding) üretildi.
- Kosinüs benzerliği ile en yakın geçmiş semptomlar bulundu.

**Anlatım:**

Semptom alanında yalnızca kelime eşleştirme yeterli değil; “mutsuzum” ile
“çökkün hissediyorum” yazım olarak farklı olsa da anlamca yakın olabilir.
Sentence-Transformers'ın çok dilli MiniLM modeli her ifadeyi sayısal bir vektöre
çeviriyor. Yeni ifade de aynı uzaya çevriliyor; kosinüs benzerliğiyle en yakın
geçmiş ifadeler bulunuyor.

HDBSCAN kümeleme, veri keşfi için kullanıldı. Ancak gerçek zamanlı öneride
klinik olarak isimlendirilmemiş kümelere zorla atama yapmak yerine doğrudan
en-yakın-komşu semantik araması kullanılıyor. Bu, konuşma dilindeki yeni
ifadelerde daha tutarlı ve açıklanabilir oldu.

## 6. Veri kalitesini nasıl kontrol ettik?

**Slayta yazılacak:**

- Elle etiketlenmiş doğrulama örneği
- İlaç çıkarımı: Precision **1,00**, Recall **0,98**, F1 **0,99**
- Düşük güvenli eşleşmeler analizin dışında
- Otomatik testler: **111 test başarılı**

**Anlatım:**

Sistem çıktısını elle kontrol edilmiş örnekle karşılaştırdık. İlaç çıkarımında
150 doğru pozitif, 0 yanlış pozitif ve 3 kaçırılmış kayıt görüldü; buna göre
precision 1,00, recall 0,98, F1 0,99. Bu metrikler ilaç çıkarımı bileşeni için
geçerlidir; klinik etkinlik doğrulaması anlamına gelmez. Ayrıca her kod
değişikliğinde otomatik birim ve entegrasyon testleri çalışıyor.

## 7. Yaş ve cinsiyet nasıl güvenli biçimde eklendi?

**Slayta yazılacak:**

- Aynı kişiye ait çoklu PDF → tek kişi
- 433 kişide doğrulanmış cinsiyet
- 397 kişide tam doğum tarihi
- Yaş, bugüne göre değil **ziyaret tarihinde** hesaplanır
- Yaş grupları: 15–17, 18–29, 30–44, 45–59, 60+

**Anlatım:**

Doğum tarihi ve cinsiyet OCR formundan çıkarılabildiği yerde alındı; sonrasında
manuel incelenmiş Excel verisi birincil kaynak kabul edildi. Eksik veya soru
işaretli tarihler yaş analizi için kullanılmıyor. Doğum tarihi doğru olsa bile
yaş her geçmiş ziyaretin günü için hesaplanıyor. Böylece 2021'deki ve 2025'teki
kayıt aynı kişinin farklı yaşını doğru yansıtıyor.

İsimden cinsiyet tahmini analitik kaynağa dönüştürülmedi; yalnızca doğrulanmış
Kadın/Erkek bilgisi kullanıldı.

## 8. Canlı sistem bugün ne yapıyor?

**Slayta yazılacak:**

```text
Kullanıcı: 25 yaş + erkek + “mutsuzum, bunalmış hissediyorum”
  → semantik olarak benzer geçmiş semptomlar
  → aynı cinsiyet ve aynı yaş grubundaki ziyaretler
  → güven puanı ≥90 ilaç kayıtlarının yüzdeleri
  → kişi/ziyaret sayısı ve küçük örneklem uyarısı
```

**Anlatım:**

Sistemde yaş, cinsiyet ve semptom birlikte kullanılıyor. Semptom araması önce
geniş bir aday küme buluyor; sonra yalnızca seçilen cinsiyet ve geçmiş ziyaret
tarihinde aynı yaş grubunda olan doğrulanmış kayıtlar kalıyor. Aynı ziyaret
içindeki birden fazla benzer semptom ifadesi tek ziyaret sayılıyor.

Örnek canlı kontrolde bu semptomla 25 yaş erkek profilinde 17 kişi/41 ziyaret,
25 yaş kadın profilinde 15 kişi/42 ziyaret bulundu. İlaç dağılımları farklı
çıktı; yani yaş ve cinsiyet filtreleri arka planda etkili biçimde çalışıyor.

## 9. Gizlilik ve yerel çalışma

**Slayta yazılacak:**

- Tüm veri ve modeller yerelde çalışır.
- Hasta adı ve geçmiş ham semptom cümleleri arayüz/API'ye verilmez.
- LLM'e yalnızca toplulaştırılmış ilaç adı, sayı ve yüzde gider.
- Yerel LLM: Ollama üzerinden `gemma2:2b`.

**Anlatım:**

Embedding modeli ve opsiyonel dil modeli bu bilgisayarda çalışıyor. Gemma2-2B
yalnızca hesaplanmış tabloyu iki-üç cümle Türkçe özete dönüştürüyor; ilaç
seçmiyor, hasta metni görmüyor ve yeni bilgi üretmemesi isteniyor. Ham geçmiş
ifadeler ekrana dahi gönderilmiyor.

## 10. Bilimsel sınır ve sonraki adım

**Slayta yazılacak:**

> “Bu sistem tedavi önermez; geçmiş kayıtlar üzerinde tanımlayıcı örüntü
> analizi yapar.”

**Anlatım:**

Bu tek merkezli, gözlemsel ve OCR kaynaklı bir veri setidir. Tanı, doz, tedavi
süresi, komorbidite ve klinik sonuç kontrol edilmeden bir ilacın bir semptomu
tedavi ettiği veya bir grup için üstün olduğu söylenemez. Küçük örneklemde
sistem bunu ayrıca uyarır.

Bir sonraki bilimsel iyileştirme; danışman/klinik uzmanla semptom kategori
tohumlarını gözden geçirmek, doğrulama örneklemini büyütmek ve sonuçları zaman
penceresi, tanı veya doz gibi ek değişkenlerle kontrollü biçimde incelemektir.

## Kapanış cümlesi

> “Projede ham OCR kayıtlarını izlenebilir bir veritabanına dönüştürdük;
> ilaçları normalize ettik, semptomları anlamsal olarak eşleştirdik, demografik
> bilgiyi ziyaret tarihine göre güvenli biçimde ekledik ve bunu yerelde çalışan,
> gizlilik korumalı bir istatistiksel karar-destek prototipine bağladık.”

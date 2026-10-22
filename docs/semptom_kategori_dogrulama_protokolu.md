# Semptom kategori doğrulama protokolü

Bu protokol, canlı uygulamadaki geniş semptom tema etiketlerinin klinik olarak
ölçülmesini sağlar. Etiketler tanı değildir; yalnızca rapordaki ifadenin
betimleyici bir temaya bağlanıp bağlanamayacağını değerlendirir.

## Dosyayı oluşturma

```bash
cd /Users/betulfiliz/TRSM_Bitirme
python scripts/export_symptom_category_validation_sample.py \
  trsm.db data/semptom_dogrulama_pilot.csv \
  --per-category 15 --uncertain 30
```

Komut iki dosya oluşturur:

- `data/semptom_dogrulama_pilot.csv`: iki değerlendiricinin dolduracağı dosya.
- `data/semptom_dogrulama_pilot_sistem.csv`: sistem tahminleri. İnsan
  etiketleme tamamlanana kadar değerlendiricilere gösterilmez.

Dosyalar hasta adı, dosya adı ve ziyaret kimliği içermez. Yalnızca semptom
ifadesi ve `SYM-xxxx` örnek kodu vardır.

## Etiketleme kuralları

İki değerlendirici `degerlendirici_1_kategoriler` ve
`degerlendirici_2_kategoriler` sütunlarını birbirinden bağımsız doldurur.

- Birden fazla tema varsa tema adlarını `|` ile ayırın.
- Hiçbir tema güvenle uygun değilse hücreye `Belirsiz` yazın.
- Bir ifadeyi tanıya çevirmeyin. Örneğin “kötü düşünceler”, açık kanıt yoksa
  intihar düşüncesi, psikoz veya OKB olarak etiketlenmez.
- Negatif ifadeye dikkat edin: “uykusuzluk yok” uyku bozukluğu değildir.
- Belirsiz bağlamı `degerlendirme_notu` sütununa yazın.

İki etiketleme bittikten sonra uzlaşıyı `uzlasim_kategoriler` sütununa yazın;
tamamlanan her satırda `uzlasim_tamamlandi` alanına `evet` girin.

## Mevcut yöntemi ölçme

```bash
python scripts/compute_symptom_category_metrics.py \
  data/semptom_dogrulama_pilot.csv \
  --prediction-column sistem_kategoriler \
  --prediction-csv data/semptom_dogrulama_pilot_sistem.csv
```

Rapor; kategori bazlı precision/recall/F1, macro ve micro F1, tam etiket kümesi
doğruluğu ve iki değerlendirici arasındaki kategori bazlı Cohen's kappa değerini
üretir.

## Qwen karşılaştırması

Qwen yalnızca aday etiket üretir; üretim veritabanını veya insan uzlaşısını
değiştirmez.

```bash
python scripts/label_symptom_validation_with_qwen.py \
  data/semptom_dogrulama_pilot.csv \
  data/semptom_dogrulama_pilot_qwen.csv

python scripts/compute_symptom_category_metrics.py \
  data/semptom_dogrulama_pilot_qwen.csv \
  --prediction-column qwen_kategoriler
```

Qwen yalnızca izinli tema adlarını, metinde aynen bulunan bir kanıt parçasını ve
JSON şemasını sağlarsa geçerli kabul edilir. Aksi halde boş etiket ve insan
inceleme gereksinimi yazılır. Bu nedenle Qwen sonucu, uzman uzlaşısı olmadan
doğruluk veya klinik gerçek olarak kullanılmaz.

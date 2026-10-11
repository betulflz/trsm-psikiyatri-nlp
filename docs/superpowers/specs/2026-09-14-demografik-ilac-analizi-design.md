# Demografik İlaç Analizi — Tasarım Notu

## Amaç

TRSM kayıtlarındaki doğrulanabilir doğum tarihi ve cinsiyet bilgisini, ilaç
kullanımının tanımlayıcı analizine eklemek. Çıktılar klinik öneri veya
nedensellik iddiası değildir; yalnızca gözlenen kayıt dağılımlarını gösterir.

## Veri güvenilirliği

- Doğum tarihi yalnızca `RH.FR.002` form sayfalarından alınır.
- OCR tarihinin gerçek bir takvim tarihi olması, 1900--2008 aralığında olması
  ve hastanın en erken tarihli ziyaretinde 18--120 yaş aralığında bulunması
  gerekir. Bu katı kural yalnızca otomatik OCR çıkarımı içindir.
- Manuel doğrulanmış tam tarih, birincil kaynaktır. Yaş-kırılımlı analizde
  yalnızca ziyaret günü 15 yaş ve üzerindeki kayıtlar kullanılır; daha erken
  tarihli/çelişkili bir ziyaret, doğrulanmış doğum tarihini geçersiz kılmaz.
- Aynı hastanın form sayfalarında birden fazla farklı, makul doğum tarihi ya
  da cinsiyet bulunursa alan otomatik doldurulmaz; yerel inceleme listesine
  yazılır.
- Cinsiyet, yalnızca OCR'da tek bir işaretli Kadın/Erkek kutusu varsa otomatik
  doldurulur. İsimden cinsiyet tahmini, klinik kayıt için güvenilir olmadığı
  için analizde kullanılmaz. Kullanıcı doğrulaması `manual_review` kaynaklı
  düzeltme olarak kaydedilebilir.

## Yaş

Yaş bugüne göre değil, her `ziyaret.tarih` günü için tamamlanmış yaş olarak
hesaplanır. Tarihsiz ziyaretler yaş-kırılımlı tabloların dışında bırakılır.
Önerilen gruplar: 15--17, 18--29, 30--44, 45--59, 60+.

## Çıktılar ve sınırlamalar

- Yaş grubu ve form/doğrulama kaynaklı cinsiyete göre ilaç dağılımı.
- Her grupta ilaç kayıt sayısı, grup içi yüzde, benzersiz hasta ve ziyaret
  sayısı görüntülenir.
- Küçük gruplar açıkça işaretlenir: hem benzersiz hasta hem ziyaret sayısı
  20'nin altında olmamalıdır. Aynı hastanın çoklu ziyaretleri nedeniyle
  sonuçlar ziyaret/ilaç-kayıt bazlıdır ve hasta popülasyonu prevalansı olarak
  yorumlanmaz.

## Uygulama

- `trsm/patient_consolidation.py`: aynı kaynak klasöründeki PDF'leri tek
  gerçek kişi altında birleştirir. PDF adları `hasta_dosya` tablosunda,
  her ziyaretin özgün PDF'si de `ziyaret.kaynak_dosya_adi` alanında korunur.
- `trsm/demographic_extraction.py`: kaynak ve yaş-kuralı ile çıkarım.
- `scripts/extract_demographics.py`: yerel OCR inceleme listesi ve isteğe
  bağlı manuel düzeltme uygulaması.
- `scripts/import_manual_demographics.py`: kullanıcı tarafından incelenmiş
  `dosya_adi`, `dogum_tarihi`, `cinsiyet` Excel'ini birincil kaynak olarak
  içe aktarır. Soru işaretli/eksik ya da yetişkinlik kuralını geçmeyen
  tarihler yaş analizine alınmaz; dosya adı güvenle eşleşmeyen satırlar
  yerel inceleme CSV'sine yazılır.
- `trsm/demographic_analysis.py`: yaş/cinsiyet kırılımlı toplulaştırılmış
  ilaç istatistikleri.
- `scripts/export_demographic_drug_analysis.py`: iki CSV tabloyu üretir.

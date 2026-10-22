# Demografik Semptom-İlaç Öneri Akışı

## Amaç

Kullanıcının yaşı, cinsiyeti ve serbest metin semptomunu birlikte kullanarak,
benzer **geçmiş kayıtların** toplulaştırılmış ilaç örüntüsünü göstermek.
Çıktı bir ilaç reçetesi veya tedavi tavsiyesi değildir.

## Sorgu akışı

```text
Yaş + cinsiyet + semptom
  → semptom embedding'i ve en yakın geçmiş semptom ifadeleri
  → aynı cinsiyet + ziyaret gününde aynı yaş grubu filtresi
  → yüksek güvenli ilaç kayıtlarının toplulaştırılması
  → örneklem büyüklüğü ve sabit tıbbi uyarıyla sonuç ekranı
```

Yaş grupları: 15-17, 18-29, 30-44, 45-59, 60+.

## Güvenlik ve veri kısıtları

- Tarihsel yaş, doğum tarihi ile ziyaret tarihi farkından hesaplanır; bugünkü
  yaş kullanılmaz.
- Cinsiyet ve doğum tarihi yalnızca `manual_review` veya güvenilir OCR kaynaklı
  ise filtreye katılır.
- Aynı ziyaret içinde birden çok benzer semptom ifadesi varsa ziyaret bir kez
  sayılır (en yüksek benzerlik tutulur).
- API ve arayüz hasta adı ile ham tarihsel semptom metnini döndürmez. Yerel
  LLM'e yalnızca ilaç adı, sayı, yüzde ve kullanıcının kendi profili gider.
- 20'den az ziyaret veya 5'ten az kişi varsa `kucuk_orneklem` uyarısı zorunlu.
- Semptomla uyumlu olsa bile profil filtresinden geçmeyen kayıt için ilaç
  sonucu üretilmez.

## Uygulama noktaları

- `trsm/profiled_recommendation.py`: demografik filtresi ve toplulaştırılmış
  yanıt.
- `app.py`: Streamlit yaş/cinsiyet/semptom giriş ekranı.
- `demo_server.py` ve `demo.html`: yerel demo API ve arayüzü.

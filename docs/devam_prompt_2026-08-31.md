# TRSM Bitirme Projesi — Devam Prompt'u (2026-08-31)

PROJE: Toplum Ruh Sağlığı Merkezi (TRSM) kayıtlarının OCR ile dijitalleştirilmesi
ve psikiyatrik ilaç kullanım örüntülerinin analizi. Repo: `/Users/betulfiliz/TRSM_Bitirme`
(git deposu, main dalı). Ben yazılımcıyım, doktor değilim — ilaç/klinik
doğrulamaları kendi görüşüme değil literatüre dayandırılmalı.

## Tamamlanan 4 alt proje (main'de)

1. **Veri temizleme & varlık çıkarımı** (`trsm/` paketi) — Excel'den (41.676 satır ham
   OCR verisi) SQLite'a (`trsm.db`) temizlenmiş veri: tarih normalizasyonu, bulanık
   ilaç eşleştirme (rapidfuzz `fuzz.ratio`, `WRatio` DEĞİL), semptom ifadesi çıkarımı
   + embedding kümeleme + gürültü filtresi.
   Çalıştırma: `/opt/anaconda3/bin/python3 scripts/run_pipeline.py <excel> trsm.db --overwrite`
   (~1.5 saat sürüyor, arka planda çalıştırılmalı).
   Excel kaynağı: `/Users/betulfiliz/Excel_Toplu/TRSM_Tum_Raporlar_Birlesik.xlsx`
2. **İlaç kullanım trendi analizi** — `notebooks/ilac_kullanim_trendi.ipynb`
3. **Öneri/chat sistemi** — `app.py` (Streamlit) + `trsm/symptom_similarity.py` +
   `trsm/recommendation.py`. Yerel Ollama+Gemma2-2B ile Türkçe özet, ham veri LLM'e
   hiç gönderilmiyor (gizlilik kısıtı).
4. **Semptom-ilaç ilişkisi bulgusu** — `notebooks/semptom_ilac_iliskisi.ipynb`. 10
   literatür temelli semptom kategorisi (uyku, öfke/ajitasyon, anksiyete, depresif,
   manik, halüsinasyon/hezeyan, iştah, sosyal içe kapanma, madde kullanımı, tedaviye
   uyumsuzluk), her biri için tohum ifadelerin AYRI AYRI sorgulanmasıyla (ortalama
   vektör DEĞİL — bu, gerçek veriyle test edilip düzeltilen bir tasarım hatasıydı)
   eşleşen ziyaretler bulunuyor, ilaç dağılımı genel (baseline) oranla karşılaştırmalı
   çıkarılıyor. Spec: `docs/superpowers/specs/2026-08-26-semptom-ilac-iliskisi-design.md`,
   Plan: `docs/superpowers/plans/2026-08-26-semptom-ilac-iliskisi.md`.

**Ortam notu:** Bu makinede paketler (pandas, sentence-transformers, flask, vb.)
sistem python3'ünde değil, `/opt/anaconda3/bin/python3`'te kurulu — HER ZAMAN bu
interpreter'ı kullan (`jupyter` için de `/opt/anaconda3/bin/jupyter`).

## Bu oturumda (2026-08-25 → 2026-08-31) yapılanlar

1. **İlaç sözlüğü doğrulama tamamlandı**: 45 → 61 ilaç, 154 yazım varyasyonu.
   "Daprin" ilacı kaynak PDF'den kontrol edildi, el yazısı belirsiz kaldı (Mutlu
   Ermiş2.pdf), sözlüğe eklenmedi. "Humira" psikiyatrik olmadığı için kapsam dışı
   bırakıldı.
2. **Pipeline güncel sözlükle yeniden çalıştırıldı**: `ilac_kullanimi` 18.937 →
   22.726 kayıt.
3. **Semptom çıkarım kalitesi sorunu bulundu ve TDD ile düzeltildi**: form
   şablonu/ilaç dozu gürültüsü `trsm/symptom_extraction.py`'deki
   `is_probable_symptom()` ile filtrelendi (~%11-16 azalma). `trsm/symptom_clustering.py`
   0-1 örnek durumunu artık çökmeden ele alıyor.
4. **Precision/recall ölçüm script'i yazıldı**: `trsm/validation_metrics.py` +
   `scripts/compute_precision_recall.py`. Sonuç: **Precision 1.00, Recall 0.98, F1 0.99**
   (5 hasta, 517 kayıt, elle doğrulanmış). Rapor: `docs/validation_reports/`.
   ÖNEMLİ ders: script'in ilk versiyonu eski notları güncel bulgularla
   karşılaştırmadan güveniyordu, yanlış %87 recall veriyordu — düzeltildi.
5. **Semptom-ilaç ilişkisi notebook'u** subagent-driven-development ile
   uygulandı (5 görev + final whole-branch review). Final review'da **kritik bir
   hata bulundu**: `find_similar_phrases`'in `top_n`'i `min_similarity` filtresinden
   ÖNCE uyguladığı fark edilmedi, `TOP_N_PER_SEED=500` sabiti yoğun kategorilerin
   gerçek eşleşme sayısının %40-79'unu sessizce kesiyordu. Düzeltildi (artık
   `embeddings.shape[0]` kullanılıyor). Güncel doğru sayı: **7.490 ziyaret (%18.0)
   en az bir kategoriye giriyor** (düzeltmeden önce yanlışlıkla 3.659/%8.8
   raporlanmıştı).
6. **İki demo yapıldı**:
   - Artifact (statik, dondurulmuş gerçek veri): sadece görsel sunum amaçlı.
   - **`demo_server.py` + `demo.html`** — gerçek çalışan Flask API + arayüz.
     `/opt/anaconda3/bin/python3 demo_server.py` → `http://localhost:8765`
     (port 5000 macOS AirPlay tarafından işgal edildiği için 8765 kullanıldı).
     Canlı sorgu, gerçek embedding araması + gerçek Gemma2 özeti (opsiyonel buton,
     ~13 sn). Henüz commit edilmedi.
7. **Danışmana bilgilendirme mesajı hazırlandı** (proje özeti + teknik detaylar +
   sorulacak sorular) — kullanıcıya verildi, repoya kaydedilmedi.

## AÇIK, ÖNEMLİ BULGU — henüz hiçbir kod yazılmadı

Danışman "cinsiyet/yaş/meslek ekleyip tahmin yapabilir miyiz" diye sordu.
Araştırma sonucu:

- `hasta`/`ziyaret` tablolarında bu alanlar YOK.
- Kaynak PDF'lerde ayrı bir form türü var: **"Hasta Bilgi Formu" (RH.FR.002)**
  — doğum tarihi, cinsiyet (checkbox), eğitim, medeni durum, meslek, gelir,
  barınma, aile/madde kullanım öyküsü içeriyor.
- **Doğrulandı**: bu form verisi aslında ham Excel'de zaten var (`ham_mudahale_metni`/
  `ham_sonuc_metni` içinde, "RH.FR.002" etiketli satırların arasında dağınık halde) —
  yeni bir PDF OCR turu GEREKMİYOR, bir regex/filtreleme çıkarımı yeterli.
  Örnek (Gül Akdemir, `hasta.id=195`):
  ```
  'RH.FR.002 | Yayın Tarihi'
  'Gül Hastanesi | TC Kimlik No :'
  'Dolaman | '
  '07.01.1989 | Cinsiyet:'
  ```
  Doğum tarihi ("07.01.1989") metinde var → yaş çıkarılabilir.
  **Cinsiyet muhtemelen çıkarılamaz** — form alanı bir checkbox (☑/☐), OCR sadece
  "Cinsiyet:" etiketini yakalıyor, işaretlenen kutuyu değil.
  Meslek alanı henüz kontrol edilmedi.
- **Yapılmadı**: kaç hastada bu blok var (kapsam), meslek alanının çıkarılabilirliği,
  ve asıl çıkarım kodu (regex/parsing pipeline'ı, muhtemelen yeni bir `trsm/` modülü).
  Bu, ayrı bir **brainstorming + TDD** süreci gerektiren yeni bir alt-proje adayı.

## Sıradaki adımlar (kullanıcıyla konuşulacak, otomatik yapılmayacak)

1. RH.FR.002 bloğunun kapsamını örnekleyerek netleştir (kaç hasta, meslek de var mı).
2. Uygunsa, demografik veri çıkarım alt-projesini brainstorming ile tasarla.
3. `demo_server.py`/`demo.html`'i commit edip etmeyeceğine karar ver.
4. Danışmanla görüşme sonrası gelecek geri bildirime göre önceliklendirme.
5. Semptom kümelerinin (HDBSCAN, hâlâ bozuk — %99'u tek kümede) anlamlı etiketlenmesi
   — isteğe bağlı, düşük öncelik (semptom-ilaç bulgusu buna bağlı değil).

## Kritik teknik/süreç dersleri (tekrar keşfetmemek için)

- `find_similar_phrases` top_n'i min_similarity'den ÖNCE uyguluyor — yüksek
  `top_n` kullanmadan yoğun sorgularda sessiz veri kaybı olur.
- Türkçe `'İ'.lower()` → `'i' + U+0307`, plain `'i'` değil — string eşleştirmede dikkat.
- `hasta.dosya_adi` bazı kayıtlarda NFD (ayrışık unicode) formatında saklı —
  Python literal karşılaştırması NFC ile eşleşmeyebilir, `unicodedata.normalize`
  şart.
- macOS'ta port 5000 AirPlay Receiver tarafından işgal ediliyor, başka port kullan.
- Kullanıcı TDD, brainstorming-önce-kod, subagent-driven-development (büyük
  alt-projeler için) süreçlerini onaylıyor ve bekliyor — bunları atlamadan devam et.

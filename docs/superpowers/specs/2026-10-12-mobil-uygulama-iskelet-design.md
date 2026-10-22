# Kartela mobil uygulaması: iskelet, tema ve gerçek veriyle demo

Tarih: 2026-10-12
Durum: Tasarım onaylandı, spec incelemesi bekleniyor

## 1. Amaç ve bağlam

TRSM'in OCR'dan geçmiş geçmiş ziyaret notlarını (`trsm.db`: 434 hasta dosyası,
41.676 ziyaret, 22.726 ilaç kaydı, 96.693 semptom kaydı) doktor ve hemşirenin
telefondan inceleyebileceği bir React Native uygulaması başlatılacak. Danışmanın
istekleri: üç rol (admin, doktor, hemşire), doktorun yeni kayıt açabilmesi,
Google ile giriş.

Bu spec'in **uygulama hedefi Aşama 1**'dir: tema ve iskeleti bitmiş, seed
hesaplarla giriş yapılan, Özet ve Dosyalar ekranlarının mevcut Flask sunucusu
üzerinden gerçek veriyi gösterdiği bir canlı demo. Aşama 2 burada yalnızca
tasarlanır; ayrı bir uygulama planı olur.

**Başarı ölçütü (Aşama 1):** Telefonda Expo Go ile açılan uygulamada her üç
seed hesapla giriş yapılır; doktor ve hemşire gerçek hasta dosyalarını ve OCR
notlarını (ilaç/belirti vurgularıyla) zaman sırasıyla görür; admin klinik veri
görmeden sistem durumunu ve kullanıcıları görür; Açık/Koyu/Sistem teması çalışır.

### Kapsam dışı (bilinçli olarak)

- Hastaların doktora göre ayrılması: doktor tüm dosyaları görür.
- OCR çıkarım döngüsü: yüklenen rapor görselleri işlenmez.
- Kapsamlı kimlik yönetimi (kayıt olma, şifre sıfırlama, kullanıcı CRUD).
- İnternete açık dağıtım: sunucu yalnızca güvenilir yerel ağda çalışır.

## 2. Aşamalar

**Aşama 1 (bu spec'in uygulaması)**

- `mobile/` altında Expo + Expo Router + TypeScript projesi (Expo Go ile çalışır).
- Tasarım sistemi, tema (Açık/Koyu/Sistem), özel bileşenler ve animasyonlar.
- Gerçek veriyle çalışan ekranlar: Giriş, Özet, Dosyalar, Dosya detayı, admin Sistem.
- Yalnızca arayüzü olan ekranlar: Yeni hasta (yerel taslak), Ayarlar'daki Google
  satırı ("Yakında"), admin Kullanıcılar (salt okunur liste; veri gerçek).
- Flask'a `mobile_api` blueprint'i, `kullanici` tablosu, seed scripti.

**Aşama 2 (yalnızca tasarım, bkz. §8)**

- Yeni hasta ve rapor görsellerinin sunucuya kaydı, hemşirenin rapor yüklemesi.
- Google hesabı bağlama ve Google ile giriş (development build + Google Cloud
  OAuth istemcileri gerektirir; Expo Go yeterli değildir).

## 3. Roller ve yetkiler

| Rol | Sekmeler | Klinik veri | Aşama 1 yetenekleri |
| --- | --- | --- | --- |
| doktor | Özet · Dosyalar · Yeni · Ayarlar | Tüm dosyalar | Okuma; Yeni hasta formu (yerel taslak) |
| hemşire | Özet · Dosyalar · Ayarlar | Tüm dosyalar | Okuma (Aşama 2'de rapor görseli yükleme) |
| admin | Sistem · Kullanıcılar · Ayarlar | Yok | Sistem durumu, kullanıcı listesi |

Mobilde sekme gizleme yalnızca sunumdur; yetki her uç noktada sunucuda
kontrol edilir. Admin klinik uç noktalara erişirse 403 alır.

## 4. Görsel kimlik ve tasarım sistemi

### 4.1 İlkeler

- **Kimlik:** Uygulamanın çalışma adı "Kartela" (arşiv dosyasından yaşayan kayda).
  Kimliği renk değil bileşenler taşır: OCR metninde fosforlu kalemle işaretlenen
  ilaçlar, altı çizili belirtiler, zaman çizgisi, "Henüz okunmadı" kaşesi,
  hap biçimli tab bar.
- **Renk dağılımı 60-30-10:** %60 renge hafif çalan nötr zemin, %30 koyu
  "mürekkep" taban (hero kart, başlık blokları, tab bar), %10 vurgu (aktif sekme,
  önemli rozetler). Ana renk zümrüt, vurgu açık nane; ikisi aynı renk ailesinde,
  düşük doygunlukta.
- **Ton basamakları** OKLCH mantığıyla seçilir; metin/zemin çiftleri WCAG AA
  (gövde metni ≥ 4.5:1) karşılar.

### 4.2 Renk token'ları

| Token | Açık | Koyu | Kullanım |
| --- | --- | --- | --- |
| `bg` | `#F3F4F4` | `#0E1013` | Ekran zemini |
| `surface` | `#FFFFFF` | `#171A1F` | Kart |
| `surfaceRaised` | `#FFFFFF` | `#1E2228` | Açılır sayfa, menü |
| `ink` | `#111418` | `#ECEFF1` | Birincil metin |
| `inkMuted` | `#5F656D` | `#9AA1A9` | İkincil metin, etiket |
| `line` | `#E4E6E9` | `#262A31` | Ayraç, kenarlık |
| `deep` | `#15181D` | `#1B1F25` | Hero kart, başlık bloğu, tab bar |
| `onDeep` | `#FFFFFF` | `#ECEFF1` | Derin zemin üstü metin |
| `primary` | `#1E8C6E` | `#34B48F` | Ana eylem, belirti altçizgisi, grafik |
| `primarySoft` | `#DCEFE7` | `#12302A` | Ana rengin zemin tonu |
| `accent` | `#9ED9C3` | `#9ED9C3` | Aktif sekme, rozet, "son not" noktası |
| `onAccent` | `#15181D` | `#0E1013` | Vurgu üstü metin |
| `accentSoft` | `#E2F4EC` | `#1A3A30` | Vurgu halesi |
| `highlight` | `#F3E08A` | `#E6CF6A` | Fosforlu ilaç işareti (üstündeki metin her zaman `#111418`) |
| `danger` | `#E5484D` | `#FF6369` | Hata, "okunmadı" kaşesi |
| `dangerSoft` | `#FDECEC` | `#3A1A1C` | Hata zemini |

Tema tercihi `sistem | acik | koyu` AsyncStorage'da tutulur; `sistem`
`useColorScheme()` ile çözülür. Tema değişimi renk geçişiyle (≈250 ms) olur.

### 4.3 Tipografi

- Arayüz: **Geist** (`@expo-google-fonts/geist`), ağırlıklar 400/500/600/700/800.
- OCR ve ham metin, dosya no, sayısal tablolar: **Geist Mono**
  (`@expo-google-fonts/geist-mono`). Mono yazı "bu metin makineden okundu"
  anlamını taşır; başka yerde kullanılmaz.
- Ölçek (pt): `display` 44/800, `title` 24/800, `heading` 18/700, `body` 15/500,
  `bodySmall` 13/500, `label` 11/600, `mono` 12/400. Dynamic Type desteklenir,
  `maxFontSizeMultiplier` 1.3 ile sınırlanır.

### 4.4 Şekil, boşluk, hareket

- Boşluk ölçeği 4'ün katları (4, 8, 12, 16, 20, 24, 32). Kenar yuvarlama: kart
  18, hero 22, çip 8, tab bar 22.
- Gölge yalnızca açık temada ve hafif; koyu temada katman farkı `surface`
  tonlarıyla verilir.
- Animasyonlar Reanimated ile; giriş animasyonları ≤ 600 ms, kademeli
  gecikme ≤ 60 ms/öğe. Basınca küçülme (`scale 0.97`) tüm dokunulabilir kartlarda.
  İşletim sistemi "hareketi azalt" açıksa giriş animasyonları atlanır, sayaçlar
  son değerle başlar.
- İkonlar: `lucide-react-native`, çizgi kalınlığı 2.

### 4.5 Bileşen kataloğu (`mobile/src/ui`)

| Bileşen | Sorumluluk |
| --- | --- |
| `Text` | Tipografi ölçeğini ve tema rengini uygular |
| `Card`, `HeroCard` | Yüzey; `HeroCard` `deep` zeminli, köşede `primary` halka süslü |
| `PillTabBar` | Expo Router için özel tab bar; aktif sekme genişleyip etiketini açan `accent` hap, yaylı geçiş |
| `StatTile` | Etiket + sayarak gelen rakam + isteğe bağlı ilerleme çubuğu |
| `BarChart` | Dikey yıl çubukları (svg + Reanimated, yaylanarak büyür) |
| `Donut` | İki dilimli halka (kendini çizer) |
| `HBarList` | Yatay çubuklu sıralı liste (en sık ilaçlar) |
| `OcrText` | Metni `vurgular` aralıklarına böler; ilaç = fosforlu sweep, belirti = altçizgi; mono yazı |
| `Timeline`, `TimelineItem` | Dikey çizgi (yukarıdan aşağı çizilir), en son not için `accent` haleli nokta |
| `Stamp` | Eğik kaşe ("Henüz okunmadı"), yaylanarak basılma animasyonu |
| `Chip`, `FilterChips` | Rozet ve filtre çipleri |
| `SearchField`, `FormField`, `DateField`, `SegmentedControl` | Form öğeleri |
| `Button` | `primary` / `deep` / `ghost` varyantları, basma geri bildirimi |
| `EmptyState`, `ErrorState`, `Skeleton` | Boş, hata ve yükleme durumları |

Mockup referansı: `.superpowers/brainstorm/…/content/renk-lab-v2.html`
("Mürekkep + Zümrüt" paleti), `kartela-v2.html` (bileşen ve hareket fikirleri).

## 5. Mobil mimari

```
mobile/
  app/
    _layout.tsx            # fontlar, ThemeProvider, QueryClientProvider, AuthGate
    giris.tsx
    (doktor)/_layout.tsx   # PillTabBar: ozet, dosyalar, yeni, ayarlar
    (hemsire)/_layout.tsx  # ozet, dosyalar, ayarlar
    (admin)/_layout.tsx    # sistem, kullanicilar, ayarlar
    dosya/[id].tsx         # dosya detayı (doktor + hemşire)
  src/
    theme/                 # tokens.ts, ThemeProvider, useTheme, tema tercihi
    ui/                    # §4.5 bileşenleri
    features/
      ozet/ dosyalar/ dosya-detay/ yeni-hasta/ ayarlar/ admin/
    api/                   # client.ts (fetch + token + hata eşleme), types.ts, hooks.ts
    auth/                  # AuthContext, tokenStore (expo-secure-store)
    lib/                   # tcKimlik.ts, turkishSearch.ts, roleTabs.ts
```

- Her rol grubunun ekranları `features/` içindeki ortak ekran bileşenlerini
  yeniden kullanır; route dosyaları ince kalır.
- `AuthGate`: token yoksa `giris`'e; varsa `/ben` ile doğrular ve role göre
  `(doktor)`, `(hemsire)` veya `(admin)` grubuna yönlendirir.
- Sunucu durumu TanStack Query ile; token `expo-secure-store`'da, tema ve sunucu
  adresi AsyncStorage'da. Ayrı global state kütüphanesi yok.
- Sunucu adresi varsayılanı `EXPO_PUBLIC_API_URL`; Ayarlar'daki "Sunucu"
  satırından değiştirilebilir (demo sırasında IP değişirse).
- Liste için `@shopify/flash-list`; rapor görselleri için `expo-image-picker`;
  tarih için `@react-native-community/datetimepicker`.

## 6. Sunucu: veri modeli ve API

### 6.1 Yerleşim

- Yeni paket `trsm/mobile_api/` (`__init__.py` blueprint, `auth.py`,
  `queries.py`, `highlights.py`). `demo_server.py` blueprint'i `/api/m`
  önekiyle kaydeder; mevcut uç noktalar ve `demo.html` değişmez.
- Ek bağımlılık yok: şifre için `werkzeug.security`, token için `itsdangerous`
  (`URLSafeTimedSerializer`, 12 saat geçerlilik). İmza anahtarı
  `TRSM_SECRET_KEY` ortam değişkeninden; yoksa ilk açılışta `data/` altında
  rastgele üretilip `data/mobile_secret.key` dosyasında saklanır
  (`.gitignore`'a eklenir).
- Sunucu yerel ağdan erişim için `TRSM_HOST=0.0.0.0` ile açılabilir; varsayılan
  `127.0.0.1` korunur.

### 6.2 Şema (Aşama 1)

```sql
CREATE TABLE IF NOT EXISTS kullanici (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT NOT NULL UNIQUE,
    ad_soyad TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('admin', 'doktor', 'hemsire')),
    sifre_hash TEXT NOT NULL,
    google_sub TEXT UNIQUE,
    google_eposta TEXT,
    olusturma_zamani TEXT NOT NULL
);
```

`trsm/schema.sql`'e eklenir (`CREATE TABLE IF NOT EXISTS` olduğu için mevcut
DB'lere güvenle uygulanır). `scripts/seed_mobile_users.py` üç hesabı
(`doktor`, `hemsire`, `admin`) idempotent ekler; şifreler
`TRSM_SEED_PASSWORD_<ROL>` ortam değişkenlerinden, yoksa belgelenmiş demo
şifrelerinden alınır. Script mevcut kullanıcının şifresini ezmez.

### 6.3 Uç noktalar

Giriş dışındaki tüm uç noktalar `Authorization: Bearer <token>` ister. Hata
gövdesi her zaman `{"hata": "<Türkçe mesaj>", "kod": "<makine kodu>"}`.

| Yöntem ve yol | Rol | Yanıt |
| --- | --- | --- |
| `POST /api/m/giris` | — | `{token, kullanici: {id, ad_soyad, rol}}`; hatalı bilgide 401 |
| `GET /api/m/ben` | hepsi | `{id, ad_soyad, rol, google_bagli}` |
| `GET /api/m/ozet` | doktor, hemşire | `toplam_dosya, toplam_not, ilacli_not, yillik_not[{yil, sayi}]` (2021–2025), `cinsiyet{erkek, kadin, bilinmiyor}`, `en_sik_ilaclar[{ilac, sayi}]` (ilk 5, güven ≥ 90), `okunmamis_rapor` (Aşama 1'de 0) |
| `GET /api/m/hastalar` | doktor, hemşire | Tüm dosyalar: `id, ad, cinsiyet, yas, not_sayisi, son_ziyaret, yogunluk[12], okunmamis` |
| `GET /api/m/hastalar/<id>` | doktor, hemşire | `id, ad, cinsiyet, yas, dosya_no, tc_maskeli (null), not_sayisi, ilac_sayisi, ilk_kayit, son_kayit`; yoksa 404 |
| `GET /api/m/hastalar/<id>/notlar?once=<id>&limit=20` | doktor, hemşire | `{notlar: [{id, tarih, sayfa_no, metin, vurgular[{bas, son, tur}], ilaclar[{ad, doz, siklik}], belirti_sayisi, gorsel_var}], sonraki: <id or null>}` |
| `GET /api/m/sistem` | admin | Tablo satır sayıları, DB boyutu, semptom indeksi var mı, Ollama erişilebilir mi |
| `GET /api/m/kullanicilar` | admin | `[{id, kullanici_adi, ad_soyad, rol, google_bagli}]` |

Ayrıntılar:

- `ad` = `hasta.dosya_adi` (NFC'ye normalize edilmiş). `dosya_no` = `hasta.id`
  dört haneye sıfırla doldurulmuş metin (`#0195`). `yas`, `dogum_tarihi`'nden
  bugüne göre hesaplanır; yoksa `null`.
- `yogunluk[12]`: hastanın ilk ve son ziyareti arasındaki süre 12 eşit kovaya
  bölünür, her kovadaki not sayısı 0–3 aralığına ölçeklenir (listede nokta dizisi).
- `ilac_sayisi` ve ilaç listeleri yalnızca `eslesme_guveni >= 90` kayıtları
  sayar (mevcut analizlerle aynı eşik).
- Notlar `tarih DESC, id DESC` sırasında; `once` imleci son görülen notun
  `id`'si, sıralama `(tarih, id)` üzerinden kararlıdır. `metin` =
  `ham_mudahale_metni` ve `ham_sonuc_metni`'nin boş olmayanlarının
  `\n\n` ile birleşimi.
- `vurgular` (`highlights.py`): o ziyaretin `ilac_kullanimi.ilac_adi_ham`
  (güven ≥ 90) ve `semptom_kaydi.ifade_ham` değerleri metinde aranır. Arama
  NFC normalizasyonu ve Türkçe büyük/küçük harf katlamasıyla (İ→i, I→ı) yapılır;
  dönen `bas/son` orijinal metnin karakter konumlarıdır. Bulunamayan ifade
  vurgu üretmez. Çakışan aralıklarda ilaç önceliklidir; aralıklar sıralı ve
  çakışmasız döner.
- `gorsel_var` arşiv notları için her zaman `false`; "Ham sayfa" düğmesi bu
  durumda gizlenir.

## 7. Ekranlar (Aşama 1)

- **Giriş:** `deep` zeminli tam ekran, logo, kullanıcı adı ve şifre, pasif
  "Google ile giriş (yakında)". Geliştirme ortamında (`__DEV__`) üç hızlı giriş
  çipi. Hatalı girişte alan sarsma animasyonu ve mesaj.
- **Özet (doktor, hemşire):** başlık (tarih, "Arşiv özeti", kullanıcı baş
  harfleri). `HeroCard` (toplam dosya + `BarChart` yıllık not). `StatTile`
  (not sayısı + ilaçlı not oranı), `Donut` (cinsiyet), `HBarList` (en sık
  ilaçlar). Aşağı çekerek yenileme.
- **Dosyalar:** başlık, `SearchField` (istemci tarafı, Türkçe katlamalı arama),
  `FilterChips` (Tümü, Son ziyaret, Okunmadı), FlashList kartları (sol şerit,
  ad, not sayısı ve son ziyaret, yoğunluk noktaları). Kartlar kademeli girer.
- **Dosya detayı:** `deep` başlık bloğu (baş harf rozeti, ad, cinsiyet/yaş/dosya
  no, üç sayaç: not, ilaç, ilk kayıt), altında `Timeline`. Her not kartı:
  tarih ve sayfa, `OcrText` (ilk 4 satır; dokununca tamamı açılır ve vurgu
  animasyonu oynar), ilaç ve belirti çipleri. Kaydırdıkça sonsuz yükleme.
  Notu olmayan dosyada `Stamp` ile "Henüz okunmadı" boş durumu.
- **Yeni (doktor):** iki adımlı form. Adım 1: ad soyad (zorunlu), cinsiyet
  (`SegmentedControl`), doğum tarihi (`DateField`), TC Kimlik No (11 hane +
  resmi kontrol hanesi algoritması, giriş sırasında maskelenebilir). Adım 2:
  rapor sayfaları (kamera veya galeri, çoklu; küçük resimler, sıralama, silme).
  Gönder: taslak cihazda tutulur (AsyncStorage, görseller uygulama
  dizininde), `Stamp` animasyonu ve "Sunucu kaydı bir sonraki aşamada"
  bilgisi. Taslak bu ekranda listelenir ve silinebilir.
- **Ayarlar (hepsi):** profil kartı (ad, rol), Tema (`SegmentedControl`:
  Sistem/Açık/Koyu), Google hesabı ("Yakında" rozetiyle pasif satır), Sunucu
  adresi (düzenlenebilir, "Bağlantıyı sına"), Çıkış.
- **Sistem (admin):** satır sayıları, DB boyutu, indeks ve Ollama durumu
  rozetleri. **Kullanıcılar (admin):** üç hesap, rol çipi, Google bağlı mı.

### Durumlar ve hatalar

- Yükleme: her ekranda içerik biçimli `Skeleton`.
- Ağ hatası / zaman aşımı (10 sn): `ErrorState`, sunucu adresiyle birlikte
  "Tekrar dene" ve "Adresi değiştir".
- 401: token silinir, girişe dönülür ("Oturum süresi doldu").
- 403: "Bu alan rolünüze kapalı" `ErrorState`.
- 404 (dosya): "Dosya bulunamadı" ve geri düğmesi.
- Boş: arama sonucu yok, notu olmayan dosya için özel `EmptyState`.

## 8. Aşama 2 tasarımı (uygulanmayacak, plan ayrı)

- `hasta`'ya sütunlar: `tc_kimlik_no TEXT`, `kaynak TEXT DEFAULT 'arsiv'`
  (`arsiv | mobil`), `olusturan_kullanici_id INTEGER`, `olusturma_zamani TEXT`.
  SQLite `ALTER TABLE ADD COLUMN` ile, sütun yoksa eklenir.
- Yeni tablo `rapor_gorseli(id, hasta_id, yukleyen_kullanici_id, dosya_yolu,
  sayfa_sirasi, yuklenme_zamani, ocr_durumu DEFAULT 'bekliyor')`. Dosyalar
  `data/uploads/<hasta_id>/` altında, Git dışı.
- `POST /api/m/hastalar` (doktor): multipart, aynı `dosya_adi` varsa 409
  ve mobilde "Bu isimde dosya var, mevcut dosyaya rapor ekle?" akışı.
  `POST /api/m/hastalar/<id>/raporlar` (doktor, hemşire): sayfa görselleri.
  `GET /api/m/raporlar/<id>/gorsel`: yetkili görsel sunumu.
- TC Kimlik No sunucuda tekrar doğrulanır, yanıtlarda yalnızca maskeli
  (`123******90`) ve yalnızca dosya detayında döner; listelerde hiç dönmez.
- Google bağlama: mobil `expo-auth-session` ile Google `id_token` alır;
  `POST /api/m/google/bagla` token'ı Google'ın doğrulama uç noktasıyla doğrular,
  `google_sub` ve e-postayı oturumdaki kullanıcıya yazar (e-posta farklı olabilir).
  `POST /api/m/google/giris` yalnızca bağlı `google_sub` için token verir.
  Development build ve Google Cloud OAuth istemcileri (iOS, Android, Web) gerekir.

## 9. Gizlilik ve güvenlik

- Sunucu gerçek hasta verisi taşır; yalnızca güvenilir yerel ağda demo amaçlı
  çalıştırılır. İnternete açılmaz.
- Admin klinik veri görmez. Hasta adı ve OCR metni yalnızca doktor/hemşire
  uç noktalarında döner.
- Token cihazda `expo-secure-store`'da tutulur; uygulama günlüklerine hasta
  verisi yazılmaz.
- Testler gerçek DB yerine geçici SQLite fixture'larıyla çalışır; gerçek
  satırlar test çıktısına, Git'e veya dış servislere taşınmaz.

## 10. Test

**Sunucu (pytest, `tests/test_mobile_api_*.py`):**

- Şema ve seed idempotent (iki kez çalıştırma tek kopya; şifre ezilmez).
- Giriş: doğru şifre token verir; yanlış şifre ve bilinmeyen kullanıcı 401;
  süresi dolmuş veya bozuk token 401.
- Rol matrisi: admin `/ozet`, `/hastalar*` için 403; doktor ve hemşire
  `/sistem`, `/kullanicilar` için 403.
- `/ozet` sayıları küçük bir fixture DB'de beklenen değerleri verir.
- `highlights`: Türkçe İ/ı katlama, NFD metin, bulunamayan ifade, çakışan
  aralıkta ilaç önceliği, sıralı çıktı.
- `/notlar` sayfalama: aynı tarihli notlarda kararlı imleç, `sonraki` sonda `null`.

**Mobil (Jest + React Native Testing Library):**

- `tcKimlik` doğrulama (geçerli/geçersiz örnekler), `turkishSearch` katlama,
  `roleTabs` (rol → sekme eşlemesi), tema çözümleme (`sistem` + cihaz modu).
- `OcrText` aralık bölme (çakışmasız, sınırlar, boş vurgu).
- `api/client` hata eşleme (401 → çıkış, 403/404/ağ hatası türleri).

**Uçtan uca kontrol:** Sunucu `TRSM_HOST=0.0.0.0` ile, uygulama Expo Go ile
açılır; üç rolle giriş, tüm sekmeler, Açık/Koyu tema, ağ kesintisi senaryosu
elle gezilir.

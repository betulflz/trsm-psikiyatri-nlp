# Devam promptu — 16.10.2026

Aşağıdaki metni yeni oturumun ilk mesajı olarak yapıştırın.

---

TRSM_Bitirme projesinde kaldığımız yerden devam ediyoruz. Önce `docs/devam_prompt_2026-10-16.md` dosyasını oku.

**16.10.2026'da tamamlananlar**
1. **SQLite → PostgreSQL taşıması bitti.** PostgreSQL 16 Docker'da çalışıyor (`docker-compose.yml`, port `127.0.0.1:5434`; 5432'de ilgisiz bir Homebrew PG14 var, 5433 dolu). Bağlantı `.env` içindeki `DATABASE_URL` ile kuruluyor (`trsm/db.py`, psycopg 3). Testler `trsm_test` veritabanında her test için ayrı bir şemada çalışıyor (`tests/pg.py`); 206 test geçiyor. Veri `scripts/migrate_sqlite_to_postgres.py` ile taşındı ve her satır doğrulandı. Yedekleme için `scripts/yedek_al.sh` / `scripts/yedekten_don.sh` var. Tek tık Windows demo paketi bilerek SQLite'ta bırakıldı. Değişiklikler **henüz commit edilmedi**; `tek-tik-kurulum` dalında kullanıcının daha önceki commit edilmemiş işiyle karışık duruyor.
2. Disk temizlendi (yaklaşık 21 GB boş alan). iMovie'yi kullanıcı kendisi silecek.
3. **OCR kararı (danışman tavsiyesi):** Yeni hasta kaydında doktor kamerayla el yazısı belgenin fotoğrafını çekecek; belge yerelde OCR ile okunup hastanın verisi olarak işlenecek. Veri buluta kesinlikle gitmeyecek (KVKK). Üzerinde anlaştığımız yapı:
   - Görüntüye bakan bir görüntü-dil modeli (VLM) bağlamla okur.
   - İlaç adları RapidFuzz ile `ilac_sozluk`'e, dozlar `dose_extraction` ile eşleştirilir.
   - İki bağımsız model okur; ayrıştıkları kelimeler "belirsiz" olarak işaretlenir.
   - Doktor telefonda fotoğraf ve metni yan yana görüp düzeltir ve onaylar. Veritabanına yalnızca onaylanmış metin girer.
   - Düzeltmeler etiketli veri seti olarak birikir ve ileride ince ayar (LoRA) için kullanılır.
   - Metinden düzeltme yapan ikinci bir dil modeli bilerek kullanılmayacak, çünkü görüntüyü görmeden "uydurur".

**Devam eden iş: OCR denemesi (spike, kalıcı kod değil)**
- Betik: `spikes/ocr_karsilastirma/calistir.py`.
- Çalıştırma: `uv run --with pypdfium2 python spikes/ocr_karsilastirma/calistir.py --sayfa 12`.
- Arşivden rastgele 12 sayfa üç yapılandırmayla okunuyor: `qwen3-vl:4b-instruct` + sözlük, `qwen3-vl:2b-instruct` + sözlük, `qwen3-vl:4b-instruct` sözlüksüz.
- Çıktılar `spikes/ocr_karsilastirma/cikti/` içinde: `rapor.html`, `sonuclar.json`, `calisma.log`. Bu klasör hasta verisi içerir ve gitignore'da.
- Önemli: varsayılan `qwen3-vl` etiketleri "düşünen" modeller ve boş çıktı veriyor; mutlaka `-instruct` etiketleri kullanılmalı.
- 1 sayfalık ön sonuç:
  - Süre: 2B ≈ 57 sn/sayfa, 4B ≈ 100–200 sn/sayfa (M1, 8 GB RAM).
  - 2B + sözlük döngüye giriyor (179 satırın 43'ü farklı).
  - 4B + sözlük, eski OCR'dan daha fazla ilaç adı yazdı; ilaç sözlüğünü talimata eklemek uydurma riski taşıyor olabilir.
  - 4B sözlüksüz, eski OCR'a en yakın sonuç (%62 benzerlik).

**GİZLİLİK KURALI:** Hasta sayfalarını, PDF/dosya adlarını (bunlar hasta adı) ve OCR metinlerini Claude okumamalı ya da ekrana yazdırmamalı, çünkü Claude'un gördüğü her şey buluta gider. Claude yalnızca sayısal özetlere bakar; metinleri ve fotoğrafları kullanıcı yerel `rapor.html` dosyasında inceler.

**Sıradaki adımlar**
1. Deneme bitmediyse yeniden çalıştır. Bittiyse `calisma.log` içindeki sayısal özeti yorumla.
2. Ben `rapor.html` dosyasını inceleyip hangi yapılandırmanın daha iyi okuduğunu söyleyeceğim.
3. Döngüyü önlemek için ayar dene (`repeat_penalty`, `num_predict`'i eski metin uzunluğuna göre sınırlama). Sözlüğü talimata eklemek yerine sonradan RapidFuzz ile eşleştirmeyi dene.
4. Sonra asıl özelliği tasarla: mobil fotoğraf → sunucuda VLM → belirsiz yerlerin işaretlenmesi → doktor onayı → düzeltmelerin saklanması.
5. Ayrıca yapılacaklar: PostgreSQL değişikliklerini ayrı bir dalda (örn. `postgresql-gecis`) commit etmek. `docs/proje_okuma_rehberi.md` ve `docs/danisman_mini_sunum.md` hâlâ SQLite diyor; güncellenebilir.

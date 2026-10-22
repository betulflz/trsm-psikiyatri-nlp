#!/usr/bin/env bash
# Bir yedeği geri yükler. MEVCUT VERİTABANI İÇERİĞİ SİLİNİR.
# Kullanım: scripts/yedekten_don.sh yedekler/trsm_YYYYMMDD_HHMMSS.dump
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

kaynak="${1:?Kullanım: scripts/yedekten_don.sh <yedek.dump>}"
[ -f "$kaynak" ] || { echo "Yedek bulunamadı: $kaynak" >&2; exit 1; }
read -r -p "'$POSTGRES_DB' veritabanı '$kaynak' ile değiştirilecek. Emin misiniz? (evet/hayır) " cevap
[ "$cevap" = "evet" ] || { echo "İptal edildi."; exit 1; }

docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner --single-transaction < "$kaynak"
echo "Geri yükleme tamamlandı: $kaynak"

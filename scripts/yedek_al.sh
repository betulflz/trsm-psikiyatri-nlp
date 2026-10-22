#!/usr/bin/env bash
# PostgreSQL veritabanının tam yedeğini alır: yedekler/trsm_YYYYMMDD_HHMMSS.dump
# Riskli bir işlemden (pipeline --overwrite, toplu güncelleme vb.) önce çalıştırın.
# Kullanım: scripts/yedek_al.sh [aciklama]
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

mkdir -p yedekler
etiket="${1:+_$1}"
hedef="yedekler/trsm_$(date +%Y%m%d_%H%M%S)${etiket}.dump"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$hedef"
# Yedeğin okunabilir olduğunu doğrula (bozuk/boş dosya bırakma).
docker compose exec -T db pg_restore --list < "$hedef" > /dev/null
chmod 600 "$hedef"
echo "Yedek alındı: $hedef ($(du -h "$hedef" | cut -f1))"

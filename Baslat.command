#!/bin/zsh
set -u
cd "$(dirname "$0")"
export TRSM_DATA_DIR="$PWD/data"
export TRSM_PORT="${TRSM_PORT:-8765}"

echo ""
echo "TRSM Demo baslatiliyor..."

if ! command -v uv >/dev/null 2>&1; then
  echo "Ilk kurulum icin uv araci yukleniyor..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv yuklenemedi. Internet baglantinizi kontrol edip tekrar deneyin."
  echo "Kapatmak icin bir tusa basin."
  read -k 1
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Ilk kurulum yapiliyor, birkac dakika surebilir..."
fi
uv sync --no-dev
if [[ $? -ne 0 ]]; then
  echo "Kurulum tamamlanamadi. Internet baglantisini ve diskte bos alan olup olmadigini kontrol edin."
  echo "Kapatmak icin bir tusa basin."
  read -k 1
  exit 1
fi

if command -v ollama >/dev/null 2>&1; then
  if ! ollama list 2>/dev/null | grep -q '^qwen2.5:3b'; then
    echo "Qwen modeli hazirlaniyor. Bu adim uzun surebilir; basarisiz olursa ana analiz yine acilir."
    ollama pull qwen2.5:3b || echo "Qwen indirilemedi. Qwen olmadan devam ediliyor."
  fi
else
  echo "Qwen olmadan devam ediliyor."
fi

( for i in {1..45}; do
    if curl -fsS --max-time 2 "http://127.0.0.1:${TRSM_PORT}/api/status" >/dev/null 2>&1; then
      open "http://127.0.0.1:${TRSM_PORT}"
      exit 0
    fi
    sleep 1
  done ) &
echo "Uygulama aciliyor; tarayici birazdan kendiliginden acilacak."
uv run --no-sync python demo_server.py
status=$?
if [[ $status -ne 0 ]]; then
  echo ""
  echo "Uygulama hata ile kapandi. Yukaridaki hata metninin ekran goruntusunu bize iletin."
fi
echo "Kapatmak icin bir tusa basin."
read -k 1

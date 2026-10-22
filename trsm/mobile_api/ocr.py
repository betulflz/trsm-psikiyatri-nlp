"""Yerel OCR sınırı: yeni motorlar yalnızca read_report içinden bağlanır."""
import io
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 12 * 1024 * 1024
_slot = threading.BoundedSemaphore(1)


class OcrError(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def read_report(data):
    """Geçici görsel silinir; metin/görsel sunucuda kalıcı olarak saklanmaz."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise OcrError("Fotoğraf boş veya 12 MB sınırını aşıyor.", 413)
    if not _slot.acquire(blocking=False):
        raise OcrError("Başka bir rapor okunuyor. Biraz sonra tekrar deneyin.", 429)
    try:
        backend = os.environ.get("TRSM_OCR_BACKEND", "tesseract")
        if backend != "tesseract":
            raise OcrError("Yapılandırılan OCR motoru desteklenmiyor.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                with Image.open(io.BytesIO(data)) as source:
                    if source.width * source.height > 25_000_000:
                        raise OcrError("Fotoğraf en fazla 25 megapiksel olabilir.", 400)
                    source.load()
                    image = ImageOps.exif_transpose(source).convert("RGB")
            except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
                    Image.DecompressionBombWarning) as exc:
                raise OcrError("Fotoğraf okunamadı. JPEG veya PNG seçin.", 400) from exc
        image.thumbnail((2000, 2000))
        language = os.environ.get("TRSM_OCR_LANG", "eng")
        with tempfile.TemporaryDirectory(prefix="trsm-ocr-") as folder:
            path = Path(folder) / "report.png"
            image.save(path)
            try:
                result = subprocess.run(
                    [os.environ.get("TRSM_TESSERACT_CMD", "tesseract"), str(path), "stdout",
                     "-l", language, "--psm", "3"],
                    capture_output=True, text=True, encoding="utf-8", timeout=45,
                    env={**os.environ, "OMP_THREAD_LIMIT": "1"}, check=True,
                )
            except FileNotFoundError as exc:
                raise OcrError("Sunucuda Tesseract kurulu değil.") from exc
            except subprocess.TimeoutExpired as exc:
                raise OcrError("Raporun okunması çok uzun sürdü. Daha küçük bir fotoğraf deneyin.", 504) from exc
            except subprocess.CalledProcessError as exc:
                raise OcrError("OCR çalışamadı. Sunucunun Tesseract dil kurulumunu kontrol edin.") from exc
        return {"metin": result.stdout.strip(), "motor": backend, "dil": language}
    finally:
        _slot.release()

"""Rapor fotoğraflarını Ollama'daki görsel destekli Qwen ile okur.

CPU sunucusunda bir sayfa dakikalar sürdüğü için okuma arka planda, sırayla
yapılır: istek iş numarası döner, mobil sonucu bu numarayla sorar.
Fotoğraf yalnızca bellekte tutulur ve okunduktan sonra bırakılır.
"""
import io
import os
import queue
import secrets
import threading
import time
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from trsm.ollama_support import get_ollama_client, think_kwargs

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_SIDE = 1280
MAX_WAITING = 10
KEEP_SECONDS = 3600
OCR_MODEL = os.getenv("TRSM_OCR_MODEL", os.getenv("TRSM_LLM_MODEL", "qwen3.5:9b"))

TALIMAT = (
    "Bu görüntü bir psikiyatri polikliniğine ait, Türkçe el yazısıyla tutulmuş "
    "bir muayene/takip notudur. Görüntüdeki metni, gördüğün sırayla ve satır "
    "satır, olduğu gibi yaz. Düzeltme, özetleme veya yorum yapma; görmediğin "
    "hiçbir şeyi ekleme. Okuyamadığın ya da emin olmadığın kelimenin yerine "
    "[?] yaz. Yalnızca metni yaz."
)


class OcrError(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def prepare_image(data):
    """Fotoğrafı doğrular, döndürür, küçültür ve JPEG baytı olarak döner."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise OcrError("Fotoğraf boş veya 12 MB sınırını aşıyor.", 413)
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
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()


def read_with_qwen(jpeg):
    client = get_ollama_client(timeout=float(os.getenv("TRSM_OCR_TIMEOUT", "1200")))
    if client is None:
        raise OcrError("Sunucuda ollama paketi kurulu değil.")
    try:
        response = client.chat(
            model=OCR_MODEL,
            messages=[{"role": "user", "content": TALIMAT, "images": [jpeg]}],
            options={"temperature": 0, "num_predict": 1500},
            **think_kwargs(),
        )
    except Exception as exc:  # bağlantı, zaman aşımı veya model hatası
        raise OcrError("Qwen raporu okuyamadı. Ollama servisini kontrol edin.") from exc
    return response["message"]["content"].strip()


class OcrQueue:
    """Tek işçili kuyruk: Qwen aynı anda tek sayfa okur, diğerleri sırada bekler."""

    def __init__(self, reader=read_with_qwen, max_waiting=MAX_WAITING, start_worker=True):
        self._reader = reader
        self._max_waiting = max_waiting
        self._start_worker = start_worker
        self._pending = queue.Queue()
        self._jobs = {}
        self._order = []
        self._lock = threading.Lock()
        self._worker = None

    def submit(self, data, owner_id):
        jpeg = prepare_image(data)
        with self._lock:
            self._forget_old()
            if len(self._order) >= self._max_waiting:
                raise OcrError("Okuma kuyruğu dolu. Biraz sonra tekrar deneyin.", 429)
            job_id = secrets.token_urlsafe(9)
            self._jobs[job_id] = {"owner": owner_id, "durum": "sirada", "zaman": time.time()}
            self._order.append(job_id)
            self._pending.put((job_id, jpeg))
            if self._start_worker and (self._worker is None or not self._worker.is_alive()):
                self._worker = threading.Thread(target=self._run, name="trsm-ocr", daemon=True)
                self._worker.start()
            return self._public(job_id)

    def status(self, job_id, owner_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job["owner"] != owner_id:
                return None
            return self._public(job_id)

    def run_pending(self):
        """Bekleyen işleri bu iş parçacığında okur (testler için)."""
        while not self._pending.empty():
            self._process(*self._pending.get())

    def _run(self):
        while True:
            self._process(*self._pending.get())

    def _process(self, job_id, jpeg):
        self._update(job_id, durum="okunuyor", baslangic=time.time())
        try:
            text = self._reader(jpeg)
            self._update(job_id, durum="bitti", metin=text)
        except OcrError as exc:
            self._update(job_id, durum="hata", hata=str(exc))
        except Exception:
            self._update(job_id, durum="hata", hata="Rapor okunamadı.")
        finally:
            with self._lock:
                if job_id in self._order:
                    self._order.remove(job_id)

    def _update(self, job_id, **fields):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(fields)

    def _public(self, job_id):
        job = self._jobs[job_id]
        result = {"is_id": job_id, "durum": job["durum"], "motor": OCR_MODEL}
        if job["durum"] == "sirada":
            result["sira"] = self._order.index(job_id)
        if job["durum"] in ("okunuyor", "bitti", "hata") and "baslangic" in job:
            result["gecen_sn"] = int(time.time() - job["baslangic"])
        if job["durum"] == "bitti":
            result["metin"] = job["metin"]
        if job["durum"] == "hata":
            result["hata"] = job["hata"]
        return result

    def _forget_old(self):
        limit = time.time() - KEEP_SECONDS
        for job_id in [k for k, v in self._jobs.items() if v["zaman"] < limit and k not in self._order]:
            del self._jobs[job_id]

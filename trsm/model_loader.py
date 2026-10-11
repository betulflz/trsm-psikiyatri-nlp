"""Offline-only loading of the MiniLM model packaged with the application."""

import os
from pathlib import Path

MODEL_DIRECTORY_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def local_model_path(project_root=None):
    root = Path(project_root) if project_root else PROJECT_ROOT
    return root / "models" / MODEL_DIRECTORY_NAME


def load_local_minilm(project_root=None):
    """Load the packaged model without ever falling back to the internet."""
    model_path = local_model_path(project_root)
    if not model_path.is_dir():
        raise RuntimeError(
            "Yerel MiniLM modeli bulunamadı. 'models/" + MODEL_DIRECTORY_NAME
            + "' klasörü eksik. Uygulama paketini zip içinden değil, tamamen "
            "çıkarılmış klasörden çalıştırdığınızdan emin olun."
        )
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(str(model_path), local_files_only=True)
    except Exception as exc:
        raise RuntimeError(
            "Yerel MiniLM modeli okunamadı. Paket eksik veya bozuk olabilir; "
            "paketi yeniden çıkarıp tekrar deneyin."
        ) from exc

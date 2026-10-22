"""Runtime paths, optionally redirected to a packaged data directory."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def runtime_data_paths():
    configured = os.getenv("TRSM_DATA_DIR")
    if configured:
        data_dir = Path(configured).expanduser().resolve()
        return {
            "data_dir": data_dir,
            "index": data_dir / "symptom_index.npz",
            "transition_stats": data_dir / "tedavi_gecis_istatistikleri.json",
        }
    return {
        "data_dir": PROJECT_ROOT / "data",
        "index": PROJECT_ROOT / "data" / "symptom_index.npz",
        "transition_stats": PROJECT_ROOT / "data" / "tedavi_gecis_istatistikleri.json",
    }

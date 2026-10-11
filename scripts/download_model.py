"""Download the approved MiniLM model once for inclusion in the local package."""

import shutil
import sys
from pathlib import Path
from urllib.request import urlretrieve

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.model_loader import MODEL_DIRECTORY_NAME, local_model_path

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main():
    from huggingface_hub import hf_hub_download
    from sentence_transformers import SentenceTransformer

    destination = local_model_path()
    if destination.exists():
        print(f"Model klasörü zaten var: {destination}")
    else:
        print("MiniLM modeli indiriliyor; bu işlem ilk seferde birkaç dakika sürebilir...")
        SentenceTransformer(MODEL_ID).save(str(destination))

    # Preserve the publisher's model card and licence notice alongside the
    # packaged weights.  These files do not contain project data.
    for source_name, target_name in (("README.md", "MODEL_CARD.md"),):
        try:
            downloaded = hf_hub_download(repo_id=MODEL_ID, filename=source_name)
        except Exception:
            raise
        shutil.copy2(downloaded, destination / target_name)
    license_path = destination / "LICENSE-2.0.txt"
    if not license_path.exists():
        urlretrieve("https://www.apache.org/licenses/LICENSE-2.0.txt", license_path)
    (destination / "MODEL_SOURCE.txt").write_text(
        f"Model: {MODEL_ID}\nLicense: Apache-2.0\n",
        encoding="utf-8",
    )
    print(f"Yerel model hazır: {destination}")


if __name__ == "__main__":
    main()

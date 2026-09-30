"""Build a minimal, explicitly-approved distribution package for the Flask demo."""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = PROJECT_ROOT / "dist"
PACKAGE_NAME = "TRSM_Demo"
REQUIRED_DATA_FILES = (
    "trsm.db",
    "symptom_index.npz",
    "tedavi_gecis_istatistikleri.json",
)
RUNTIME_TRSM_FILES = (
    "__init__.py",
    "db.py",
    "schema.sql",
    "model_loader.py",
    "runtime_paths.py",
    "ollama_support.py",
    "recommendation.py",
    "qwen_symptom_labeling.py",
    "symptom_similarity.py",
    "symptom_clustering.py",
    "drug_matching.py",
    "symptom_extraction.py",
    "symptom_categories.py",
    "transparent_symptom_query.py",
    "profiled_recommendation.py",
    "demographic_analysis.py",
    "demographic_extraction.py",
    "treatment_timeline.py",
    "treatment_response_analysis.py",
)


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser(description="TRSM Flask demo paketini üretir")
    parser.add_argument("--data-dir", required=True, help="Üç çalışma verisini içeren klasör")
    parser.add_argument(
        "--gercek-veri-onayli", action="store_true",
        help="Gerçek hasta verisinin pakete kopyalanmasına açık onay verir",
    )
    args = parser.parse_args()
    if not args.gercek_veri_onayli:
        parser.error("Gerçek veri için --gercek-veri-onayli bayrağı zorunludur.")

    source_data = Path(args.data_dir).expanduser().resolve()
    missing = [name for name in REQUIRED_DATA_FILES if not (source_data / name).is_file()]
    if missing:
        parser.error("Eksik çalışma verisi: " + ", ".join(missing))
    model_dir = PROJECT_ROOT / "models"
    if not model_dir.is_dir():
        parser.error("models/ klasörü bulunamadı. Önce scripts/download_model.py çalıştırılmalı.")

    package_dir = DIST_ROOT / PACKAGE_NAME
    zip_base = DIST_ROOT / PACKAGE_NAME
    # The deletion target is fixed inside this repository's dist/ directory.
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)

    for filename in (
        "demo_server.py", "demo.html", "pyproject.toml", "uv.lock",
        "Baslat.bat", "Baslat.command", "KURULUM.txt", "Windows_Test_Kontrol_Listesi.txt",
    ):
        copy_file(PROJECT_ROOT / filename, package_dir / filename)
    for filename in RUNTIME_TRSM_FILES:
        copy_file(PROJECT_ROOT / "trsm" / filename, package_dir / "trsm" / filename)
    shutil.copytree(model_dir, package_dir / "models")
    for filename in REQUIRED_DATA_FILES:
        copy_file(source_data / filename, package_dir / "data" / filename)

    zip_path = Path(str(zip_base) + ".zip")
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_base), "zip", DIST_ROOT, PACKAGE_NAME)

    files = sorted(path for path in package_dir.rglob("*") if path.is_file())
    total_size = sum(path.stat().st_size for path in files)
    print(f"Paket hazır: {package_dir}")
    print(f"Zip hazır: {zip_path}")
    print(f"Dosya sayısı: {len(files)}, toplam boyut: {total_size / 1024 / 1024:.1f} MiB")
    print("Paket dosyaları:")
    for path in files:
        print(path.relative_to(package_dir))


if __name__ == "__main__":
    main()

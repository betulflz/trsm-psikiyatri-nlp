"""DENEME (spike): aynı 12 sayfayı başka bir yerel modelle "sözlüklü" talimatla okur.

Okumalar sonuclar.json'a "<model> + sözlük" anahtarıyla eklenir; analiz.py ve
etiketle.py bunları da görür. Ekrana yalnızca sayfa no, süre ve takas (swap)
kullanımı yazılır.

Çalıştırma (proje kökünden):
    uv run --with pypdfium2 python -u spikes/ocr_karsilastirma/calistir_model.py --model qwen3.5:9b --limit 2
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import ollama

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from calistir import OUT, SOZLUK_EKI, TALIMAT, drug_report, nfc  # noqa: E402
from trsm.db import get_connection  # noqa: E402
from trsm.drug_matching import build_surface_form_index_from_db  # noqa: E402


def swap_used_mb():
    out = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
    match = re.search(r"used = ([\d.]+)M", out)
    return float(match.group(1)) if match else -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--num-ctx", type=int, default=8192)
    args = parser.parse_args()

    results_path = OUT / "sonuclar.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    with get_connection() as conn:
        index = build_surface_form_index_from_db(conn)
        drug_names = [r[0] for r in conn.execute("SELECT resmi_ad FROM ilac_sozluk ORDER BY resmi_ad")]
    prompt = TALIMAT + SOZLUK_EKI.format(ilaclar=", ".join(drug_names))
    name = f"{args.model.removesuffix('-instruct')} + sözlük"
    print(f"Başlangıç takas: {swap_used_mb():.0f} MB")

    for r in results[: args.limit]:
        if name in r["okumalar"]:
            continue
        start = time.time()
        response = ollama.chat(
            model=args.model,
            messages=[{"role": "user", "content": prompt, "images": [r["gorsel"]]}],
            options={"temperature": 0, "num_ctx": args.num_ctx, "num_predict": 1500},
            think=False,
        )
        seconds = time.time() - start
        text = nfc(response["message"]["content"]).strip()
        meds, strong, weak = drug_report(text, index)
        r["okumalar"][name] = {"metin": text, "sure": seconds, "ilaclar": meds, "guclu": sorted(strong), "zayif": sorted(weak)}
        results_path.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
        print(f"  {name}: sayfa {r['no']} {seconds:.0f} sn, {len(text)} karakter, takas {swap_used_mb():.0f} MB")

    ollama.generate(model=args.model, prompt="", keep_alive=0)
    print("Bitti.")


if __name__ == "__main__":
    main()

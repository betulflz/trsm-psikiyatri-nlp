import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from trsm.db import get_connection
from trsm.demographic_analysis import (
    demographic_coverage_summary,
    demographic_drug_distribution,
    demographic_patient_drug_distribution,
)


def _write_markdown_report(path, coverage, age_patients, gender_patients):
    """Write a concise, reproducible interpretation guide for the CSV files."""
    def top_lines(frame):
        lines = []
        for group, rows in frame.groupby("demografik_grup", sort=True):
            first = rows.iloc[0]
            lines.append(
                f"- {group}: {first['ilac']} "
                f"({first['hasta_yuzdesi']}%; n={first['ilaci_olan_hasta_sayisi']}/"
                f"{first['grupta_ilac_kaydi_olan_hasta_sayisi']} kişi)"
            )
        return lines

    lines = [
        "# Demografik ilaç-kayıt analizi",
        "",
        "Bu rapor betiği çalıştırıldığında yeniden üretilir. İlaçlar, raporlarda "
        "yüksek güvenle tanınan ilaç kayıtlarıdır; reçete, doz, tanı, etkinlik veya "
        "nedensel tedavi etkisi anlamına gelmez.",
        "",
        "## Kapsam",
        "",
        f"- Toplam gerçek kişi: {coverage['toplam_hasta']}",
        f"- Doğrulanmış tam doğum tarihi: {coverage['dogum_tarihi_dogrulanmis_hasta']}",
        f"- Tarihli ziyareti olan ve yaş analizi yapılabilen kişi: {coverage['yas_analizine_uygun_hasta']}",
        f"- Doğrulanmış cinsiyet bilgisi: {coverage['cinsiyet_dogrulanmis_hasta']}",
        "",
        "## Nasıl okunmalı?",
        "",
        "- `yas_grubu_ilac_dagilimi.csv` ve `cinsiyet_ilac_dagilimi.csv`: tüm ilaç-kayıtlarının grup içindeki payı. Aynı kişinin tekrarlayan ziyaretleri birden fazla kayıt üretir.",
        "- `*_hasta_ilac_kullanimi.csv`: her kişi bir ilaç için en fazla bir kez sayılır; grup içindeki **en az bir kez kayıtlı** kişi yüzdesini gösterir. Grupları karşılaştırmak için öncelikli tablodur.",
        "- Yaş, çalıştırma tarihinde değil, her ziyaret tarihinde hesaplanır. Yaşı 15'in altındaki ziyaretler dışarıda bırakılır.",
        "- `kucuk_orneklem=True` olan sonuçlar yalnızca keşif amaçlıdır. Özellikle 15-17 grubu için yorum yapılmamalıdır.",
        "",
        "## Her grupta hasta düzeyinde en sık görülen ilaç kaydı",
        "",
        "### Yaş grupları",
        "",
        *top_lines(age_patients),
        "",
        "### Cinsiyet",
        "",
        *top_lines(gender_patients),
        "",
        "## Kısıtlar",
        "",
        "Bu tek merkezli, gözlemsel OCR verisidir. Tanı, doz, tedavi süresi, klinik endikasyon ve eksik/yanlış OCR olasılığı kontrol edilmeden gruplar arasında klinik üstünlük veya fark iddia edilemez.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Doğrulanmış yaş/cinsiyet verisine göre tanımlayıcı ilaç tabloları üretir"
    )
    parser.add_argument("db_path", help="Mevcut SQLite veritabanı")
    parser.add_argument(
        "--output-dir",
        default="docs/analysis_reports",
        help="Toplulaştırılmış CSV çıktı klasörü",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = get_connection(args.db_path)
    try:
        coverage = demographic_coverage_summary(conn)
        age_df = demographic_drug_distribution(conn, "yas_grubu")
        gender_df = demographic_drug_distribution(conn, "cinsiyet")
        age_patient_df = demographic_patient_drug_distribution(conn, "yas_grubu")
        gender_patient_df = demographic_patient_drug_distribution(conn, "cinsiyet")
    finally:
        conn.close()

    age_path = output_dir / "yas_grubu_ilac_dagilimi.csv"
    gender_path = output_dir / "cinsiyet_ilac_dagilimi.csv"
    age_patient_path = output_dir / "yas_grubu_hasta_ilac_kullanimi.csv"
    gender_patient_path = output_dir / "cinsiyet_hasta_ilac_kullanimi.csv"
    coverage_path = output_dir / "demografik_kapsam_ozeti.csv"
    report_path = output_dir / "demografik_ilac_analizi_raporu.md"
    age_df.to_csv(age_path, index=False, encoding="utf-8")
    gender_df.to_csv(gender_path, index=False, encoding="utf-8")
    age_patient_df.to_csv(age_patient_path, index=False, encoding="utf-8")
    gender_patient_df.to_csv(gender_patient_path, index=False, encoding="utf-8")
    pd.DataFrame(
        [{"metrik": key, "deger": value} for key, value in coverage.items()]
    ).to_csv(coverage_path, index=False, encoding="utf-8")
    _write_markdown_report(
        report_path, coverage, age_patient_df, gender_patient_df
    )
    print("Kapsam:")
    for key, value in coverage.items():
        print(f"- {key}: {value}")
    print(f"Yaş grubu tablosu: {age_path} ({len(age_df)} satır)")
    print(f"Cinsiyet tablosu: {gender_path} ({len(gender_df)} satır)")
    print(f"Hasta düzeyi yaş tablosu: {age_patient_path} ({len(age_patient_df)} satır)")
    print(f"Hasta düzeyi cinsiyet tablosu: {gender_patient_path} ({len(gender_patient_df)} satır)")
    print(f"Rapor: {report_path}")


if __name__ == "__main__":
    main()

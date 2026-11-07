"""
Haftalik Tum Turnuvalari (CL, UEL, ECL) Sirayla Calistiran Otomasyon Scripti.
Windows Gorev Zamanlayici veya tek basina dogrudan Python tarafindan calistirilir.
Arka planda sessizce tum turnuvalari gunceller, 10.000 simulasyon kosar ve raporlari uretir.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Proje ana dizini
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_weekly_pipeline import run_pipeline


def main():
    print("=" * 80)
    print("  FUTBOL SIMULATOR - TUM TURNUVALAR HAFTALIK OTOMATIK GUNCELLEME")
    print(f"  Baslangic Zamani: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    tournaments = ["CL", "UEL", "ECL"]
    for comp in tournaments:
        print(f"\n>>> [{comp}] Guncellemesi Baslatiliyor...")
        try:
            report_path = run_pipeline(
                competition_code=comp,
                open_notepad=False,  # Zamanlanmis gorevde arka planda sessiz calismali
                n_simulations=10000,
                skip_fetch=False,
            )
            print(f">>> [{comp}] Basariyla Tamamlandi: {report_path}")
        except Exception as e:
            print(f">>> [HATA] [{comp}] Calisirken hata olustu: {e}")

    print("\n" + "=" * 80)
    print(f"  TUM ISLEMLER TAMAMLANDI: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()

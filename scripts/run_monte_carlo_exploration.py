"""
Monte Carlo 10.000 Simulasyon Calistirici ve Hizli Veri Inceleme Scripti
Simulasyon sonuclarini diske onbellekler. Ilk calistirmadan sonra 0 saniyede acilir.
Istedigin simulasyonun puan tablosunu ve TUM mac skorlarini hafta hafta inceler.
"""
import sys
import os
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.simulator.monte_carlo_engine import MonteCarloSimulator, SimulationResults
from src.core.storage import get_now_timestamp, get_date_dir, list_available_dates, find_matching_date_dir

BASE_SIM_DIR = Path(__file__).resolve().parents[1] / "data" / "simulations"
LATEST_CACHE_FILE = BASE_SIM_DIR / "mc_10000_results.pkl.gz"


def get_or_run_simulations(
    n_simulations: int = 10000, force_new: bool = False, sim_date: Optional[str] = None
) -> SimulationResults:
    # 1. Eğer belirli bir tarih/saat istenmişse öncelikle eşleşen klasöre bak
    if sim_date and not force_new:
        matched_dir = find_matching_date_dir(BASE_SIM_DIR, sim_date)
        if matched_dir:
            for cand in [f"mc_{n_simulations}_results.pkl.gz", "mc_10000_results.pkl.gz"]:
                f_path = matched_dir / cand
                if f_path.exists():
                    print(f"[*] Tarihli önbellekten ({matched_dir.name}) simülasyon verisi yükleniyor: {f_path.name}...")
                    results = SimulationResults.load(str(f_path))
                    print(f"[OK] 0 saniyede yüklendi! (Toplam {results.n_simulations:,} simülasyon)")
                    return results

    # 2. Eğer tarih belirtilmemişse ve ana önbellek dosyası varsa oradan oku
    if sim_date is None and LATEST_CACHE_FILE.exists() and not force_new:
        print(f"[*] Güncel önbellekten {n_simulations:,} simülasyon verisi yükleniyor...")
        results = SimulationResults.load(str(LATEST_CACHE_FILE))
        print(f"[OK] 0 saniyede yüklendi! (Toplam {results.n_simulations:,} simülasyon)")
        return results

    # 3. Yeniden simüle et
    league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", "cl_2026_27.json"))
    simulator = MonteCarloSimulator(
        league_file=league_file, k_factor=30.0, home_advantage=75.0, as_of_date=sim_date
    )
    results = simulator.run(n_simulations=n_simulations)

    # Hem tarih-saat klasörüne hem de en güncel referans dosyasına kaydet
    target_ts = get_now_timestamp()
    dated_dir = get_date_dir(BASE_SIM_DIR, target_ts)
    dated_cache_file = dated_dir / f"mc_{n_simulations}_results.pkl.gz"

    print(f"[*] Sonuçlar tarih ve saat klasörüne arşivleniyor: {dated_cache_file}")
    results.save(str(dated_cache_file))

    print(f"[*] Sonuçlar en güncel referansa kaydediliyor: {LATEST_CACHE_FILE}")
    results.save(str(LATEST_CACHE_FILE))
    print(f"[OK] Başarıyla kaydedildi!\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo Simulasyon ve Detayli Mac Skorlari Inceleyici")
    parser.add_argument("-s", "--sim-id", type=int, default=1, help="Gosterilecek simulasyon numarasi (1-10000, varsayilan: 1)")
    parser.add_argument("-n", "--simulations", type=int, default=10000, help="Simulasyon sayisi (varsayilan: 10000)")
    parser.add_argument("-a", "--all-matches", action="store_true", help="O simulasyondaki kalan TUM maclarin skorlarini hafta hafta listele")
    parser.add_argument("-r", "--round", type=int, default=None, help="Sadece belirli bir haftanin (4-8) mac skorlarini listele")
    parser.add_argument("-t", "--match-team", nargs="+", default=None, help="Belirli bir takimin kalan maclarini listele (orn: Galatasaray veya Paris SG)")
    parser.add_argument("-f", "--force-new", action="store_true", help="Onbellegi yok say ve sifirdan 10.000 simulasyonu yeniden calistir")
    parser.add_argument("-d", "--date", type=str, default=None, help="Geçmiş bir tarihe ait simülasyonu incele veya o tarihe özel çalıştır (YYYY-MM-DD)")
    parser.add_argument("--list-dates", action="store_true", help="Kayıtlı simülasyon tarihlerini listele")
    args = parser.parse_args()

    if args.list_dates:
        dates = list_available_dates(BASE_SIM_DIR)
        print("=" * 50)
        print(" KAYITLI SIMÜLASYON TARİHLERİ")
        print("=" * 50)
        if not dates:
            print("Henüz arşivlenmiş tarih klasörü bulunmuyor.")
        for d in dates:
            d_path = BASE_SIM_DIR / d
            files = list(d_path.glob("*.pkl.gz"))
            f_names = ", ".join(f.name for f in files) if files else "dosya yok"
            print(f"  * {d} -> {f_names}")
        print("=" * 50)
        return

    # Takim adi birlestirme (orn: ['Paris', 'SG'] -> 'Paris SG')
    team_query = " ".join(args.match_team) if args.match_team else None

    # 1. Sonuclari al
    results = get_or_run_simulations(n_simulations=args.simulations, force_new=args.force_new, sim_date=args.date)

    target_idx = max(0, min(args.sim_id - 1, results.n_simulations - 1))

    # 2. Puan tablosunu bas
    print("\n" + results.display_simulation_standings(target_idx))

    # 3. Mac skorlarini filtrele ve bas
    print("\n" + "=" * 90)
    print(f"                     SIMÜLASYON #{target_idx + 1} MAÇ SKORLARI")
    print("=" * 90)

    matches_to_show = results.unplayed_matches

    # Hafta filtresi
    if args.round:
        matches_to_show = [m for m in matches_to_show if m.round == args.round]

    # Takim filtresi
    if team_query:
        team_l = team_query.lower()
        matches_to_show = [
            m for m in matches_to_show
            if team_l in m.home_team.lower() or team_l in m.away_team.lower()
        ]

    # Eger hic filtre verilmemisse ve --all-matches denmemisse ilk 10 maci goster ve bilgi ver
    if not args.all_matches and not args.round and not args.match_team:
        print(f"[*] Ozet olarak ilk 10 mac gosteriliyor. (Tumunu gormek icin --all-matches veya -a ekleyin)\n")
        display_matches = matches_to_show[:10]
    else:
        display_matches = matches_to_show

    current_round = None
    for m in display_matches:
        if m.round != current_round:
            current_round = m.round
            print(f"\n--- {current_round}. HAFTA MAÇLARI ---")

        match_info = results.get_match_result_in_simulation(m.match_id, target_idx)
        if len(match_info) == 6:
            hg, ag, h_elo, a_elo, d_h, d_a = match_info
            elo_str = f"({h_elo:0.1f}) [{hg} - {ag}] ({a_elo:0.1f})"
            delta_str = f"[Fark: {d_h:+5.1f} / {d_a:+5.1f}]"
            print(f"  {m.home_team:<22} {elo_str:^26} {m.away_team:<22} {delta_str}")
        else:
            hg, ag = match_info[:2]
            print(f"  {m.home_team:<24} [{hg} - {ag}]  {m.away_team:<24}")

    print("\n" + "=" * 90)
    print("[KULLANIM İPUÇLARI]:")
    print(f"  * Tüm 90 maçın skorlarını görmek için : python scripts/run_monte_carlo_exploration.py --sim-id {target_idx + 1} -a")
    print(f"  * Sadece 4. haftayı görmek için        : python scripts/run_monte_carlo_exploration.py --sim-id {target_idx + 1} -r 4")
    print(f"  * Belirli bir takımı görmek için       : python scripts/run_monte_carlo_exploration.py --sim-id {target_idx + 1} -t Galatasaray")
    print("=" * 90)


if __name__ == "__main__":
    main()

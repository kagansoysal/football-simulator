"""
Dinamik Elo Guncelleme Demo Scripti
AkilOyunu CSV verisini kesinlikle degistirmeden, simulasyon suresince
takimlarin mac sonuclarina gore degisen Elo puanlarini takip eder.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.models import LeagueTable
from src.data_loader.league_loader import LeagueLoader
from src.simulator.elo_tracker import DynamicEloTracker
from src.models.match_engine import MatchEngine


def run_dynamic_elo_demo():
    league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", "cl_2026_27.json"))
    loader = LeagueLoader(league_file)
    engine = MatchEngine(home_advantage=75.0)

    # Dinamik Elo Takipcisi: AkilOyunu'ndan veriyi alir ama AkilOyunu'nu asla degistirmez!
    elo_tracker = DynamicEloTracker(teams=loader.teams, k_factor=30.0, home_advantage=75.0)
    table = LeagueTable(loader.teams)

    print("=" * 95)
    print(" DINAMIK ELO GUNCELLEMELI SIMULASYON (HER MACTAN SONRA ELO PUANLARI DEGISIR)")
    print("=" * 95)

    for round_num in range(1, 4):
        fixtures = loader.get_round_fixtures(round_num)
        print("\n" + "-" * 95)
        print(f"                                   {round_num}. HAFTA MACLARI")
        print("-" * 95)
        print(f"{'Ev Sahibi':<24} {'Elo':<7} {'Skor':^7} {'Deplasman':<24} {'Elo':<7} {'Elo Degisimleri':<25}")
        print("-" * 95)

        for match in fixtures:
            # Guncel simulasyon Elo'larini al
            h_elo_before = elo_tracker.get_elo(match.home_team)
            a_elo_before = elo_tracker.get_elo(match.away_team)

            # Maci simule et
            hg, ag = engine.simulate_match(h_elo_before, a_elo_before, is_neutral=match.is_neutral)
            table.add_result(match.home_team, match.away_team, hg, ag)

            # Elo puanlarini guncelle
            update_info = elo_tracker.record_match_result(match.home_team, match.away_team, hg, ag, is_neutral=match.is_neutral)

            d_h = update_info["home_delta"]
            d_a = update_info["away_delta"]

            delta_str = f"Ev: {d_h:+5.1f} | Dep: {d_a:+5.1f}"

            print(
                f"{match.home_team:<24} {h_elo_before:<7.1f} [{hg} - {ag}]  "
                f"{match.away_team:<24} {a_elo_before:<7.1f} {delta_str:<25}"
            )

    # 3 Hafta Sonunda En Cok Elo Kazananlar ve Kaybedenler
    print("\n" + "=" * 95)
    print("       3 HAFTA SONUNDA EN COK ELO KAZANAN VE KAYBEDEN TAKIMLAR")
    print("=" * 95)
    changes = elo_tracker.get_rating_changes()
    sorted_teams = sorted(changes.items(), key=lambda item: item[1]["delta"], reverse=True)

    print(f"{'Sıra':<5}{'Takım':<26}{'Başlangıç Elo':<16}{'3. Hafta Sonu Elo':<20}{'Net Değişim':<15}")
    print("-" * 95)
    for i, (t_name, stats) in enumerate(sorted_teams, 1):
        print(
            f"{i:<5}{t_name:<26}"
            f"{stats['initial']:<16.1f}"
            f"{stats['current']:<20.1f}"
            f"{stats['delta']:<+15.1f}"
        )
    print("=" * 95)


if __name__ == "__main__":
    run_dynamic_elo_demo()


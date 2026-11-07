"""
Sampiyonlar Ligi 2026-27 Sezonu - Ilk 3 Hafta Simulasyon Scripti
1., 2. ve 3. haftanin maclarini Dixon-Coles Poisson MatchEngine ve guncel Elo puanlariyla simule eder,
haftalik sonuclari ve 3. hafta sonundaki puan tablosunu gosterir.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.models import LeagueTable
from src.data_loader.league_loader import LeagueLoader
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine


def run_first_3_weeks_simulation():
    # 1. Lig ve fiksturu yukle
    league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", "cl_2026_27.json"))
    loader = LeagueLoader(league_file)
    print(f"\nLig Yuklendi: {loader.name} ({loader.season})")
    print(f"Toplam Takim: {len(loader.teams)} | Format: {loader.data.get('format')}")

    # 2. Elo Fetcher ve Match Engine'i baslat
    elo_fetcher = AkilOyunuEloFetcher()
    engine = MatchEngine(home_advantage=75.0)

    # 3. Puan Tablosunu baslat
    table = LeagueTable(loader.teams)

    # 4. Ilk 3 haftayi hafta hafta simule et
    for round_num in range(1, 4):
        fixtures = loader.get_round_fixtures(round_num)
        print("\n" + "=" * 80)
        print(f"                    {loader.name.upper()} - {round_num}. HAFTA MACLARI")
        print("=" * 80)

        for match in fixtures:
            home_elo = elo_fetcher.get_elo(match.home_team)
            away_elo = elo_fetcher.get_elo(match.away_team)

            # Maci simule et
            home_score, away_score = engine.simulate_match(home_elo, away_elo, is_neutral=match.is_neutral)
            
            # Puan tablosunu guncelle
            table.add_result(match.home_team, match.away_team, home_score, away_score)

            print(
                f"  {match.home_team:<26} ({int(home_elo):<4})  "
                f"[{home_score} - {away_score}]  "
                f"{match.away_team:<26} ({int(away_elo):<4})"
            )

    # 5. 3. Hafta Sonunda Olusan Puan Durumu
    print("\n" + "=" * 80)
    print(f"       3. HAFTA SONUNDA GENEL PUAN TABLOSU (36 TAKIM)")
    print("=" * 80)
    print(table.display())
    print("=" * 80)

    # Ilk 8 ve 9-24 ozeti
    standings = table.get_standings()
    print("\n[BILGI - YENI FORMAT]:")
    print(f"  * Ilk 8 (Son 16 Turuna Dogrudan Gidenler) : {', '.join([t.name for t in standings[:8]])}")
    print(f"  * 9-24 (Play-off Turu Oynayacaklar)       : {', '.join([t.name for t in standings[8:24]])}")
    print(f"  * 25-36 (Elenenler)                       : {', '.join([t.name for t in standings[24:]])}")


if __name__ == "__main__":
    run_first_3_weeks_simulation()


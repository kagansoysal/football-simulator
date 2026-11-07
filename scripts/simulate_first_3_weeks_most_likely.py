"""
UEFA Champions League 2026-27 - Ilk 3 Hafta: EN YUKSEK OLASILIKLI SKORLAR (MODE)
Her mac icin 10.000 simulasyon / Dixon-Coles olasilik dagilimindan en olasi tek skor alinir.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.models import LeagueTable
from src.data_loader.league_loader import LeagueLoader
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine


def run_most_likely_simulation():
    league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", "cl_2026_27.json"))
    loader = LeagueLoader(league_file)
    elo_fetcher = AkilOyunuEloFetcher()
    engine = MatchEngine(home_advantage=75.0)

    table = LeagueTable(loader.teams)

    print("=" * 95)
    print(" UEFA CHAMPIONS LEAGUE (2026-27) - ILK 3 HAFTA: EN YUKSEK OLASILIKLI SKORLAR (DETERMINISTIC / MODE)")
    print("=" * 95)

    for round_num in range(1, 4):
        fixtures = loader.get_round_fixtures(round_num)
        print("\n" + "-" * 95)
        print(f"                                   {round_num}. HAFTA MACLARI")
        print("-" * 95)
        print(f"{'Ev Sahibi':<24} {'Elo':<6} {'Skor':^7} {'Deplasman':<24} {'Elo':<6} {'Olasilik':<10} {'1 / X / 2':<15}")
        print("-" * 95)

        for match in fixtures:
            home_elo = elo_fetcher.get_elo(match.home_team)
            away_elo = elo_fetcher.get_elo(match.away_team)

            # En yuksek olasilikli skoru al
            hg, ag, score_prob, probs = engine.get_most_likely_score(home_elo, away_elo, is_neutral=match.is_neutral)

            # Puan tablosuna ekle
            table.add_result(match.home_team, match.away_team, hg, ag)

            prob_str = f"%{score_prob * 100:.1f}"
            odds_str = f"%{probs.home_win*100:.0f} / %{probs.draw*100:.0f} / %{probs.away_win*100:.0f}"

            print(
                f"{match.home_team:<24} {int(home_elo):<6} [{hg} - {ag}]  "
                f"{match.away_team:<24} {int(away_elo):<6} {prob_str:<10} {odds_str:<15}"
            )

    print("\n" + "=" * 95)
    print("       EN YUKSEK OLASILIKLI SKORLARLA OLUSAN 3. HAFTA PUAN TABLOSU (36 TAKIM)")
    print("=" * 95)
    print(table.display())
    print("=" * 95)

    standings = table.get_standings()
    print("\n[SIRALAMA DETAYLARI]:")
    print(f"  * Ilk 8 (Dogrudan Son 16) : {', '.join([t.name for t in standings[:8]])}")
    print(f"  * 9-24 (Play-off Potasi)   : {', '.join([t.name for t in standings[8:24]])}")
    print(f"  * 25-36 (Elenenler)        : {', '.join([t.name for t in standings[24:]])}")


if __name__ == "__main__":
    run_most_likely_simulation()


"""
UEFA Champions League 2026-27 - Oynanmis Ilk 3 Haftanin Gercek Puan Durumu
Hicbir simulasyon yapmaz, sadece veritabanina girilen gercek mac sonuclarini listeler.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.models import LeagueTable
from src.data_loader.league_loader import LeagueLoader


def display_real_standings(league_filename: str = "cl_2026_27.json"):
    league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", league_filename))
    if not os.path.exists(league_file):
        league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", "cl_2026_27.json"))
    loader = LeagueLoader(league_file)

    played_matches = loader.get_played_fixtures()
    unplayed_matches = loader.get_unplayed_fixtures()

    print("=" * 80)
    print(f" {loader.name.upper()} ({loader.season}) - OYNANMIS MACLAR VE GERCEK PUAN DURUMU")
    print(f" Toplam Takim: {len(loader.teams)} | Oynanmis Mac: {len(played_matches)} | Kalan Mac: {len(unplayed_matches)}")
    print("=" * 80)

    table = LeagueTable(loader.teams)
    for m in played_matches:
        table.add_result(m.home_team, m.away_team, m.home_score, m.away_score)

    print("\n" + table.display())
    print("=" * 80)

    standings = table.get_standings()
    print("\n[MEVCUT GERCEK DURUM - YENI FORMAT]:")
    print(f"  * Ilk 8 (Son 16 Turuna Dogrudan Gidenler) : {', '.join([t.name for t in standings[:8]])}")
    print(f"  * 9-24 (Play-off Potasi)                  : {', '.join([t.name for t in standings[8:24]])}")
    print(f"  * 25-36 (Elenme Potasi)                   : {', '.join([t.name for t in standings[24:]])}")


if __name__ == "__main__":
    display_real_standings()


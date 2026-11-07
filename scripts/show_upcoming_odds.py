"""
Gelecek Haftanin Maclari Icin En Olası Skorlar (1. Kategori) Scripti
UEFA Sampiyonlar Ligi (CL), Avrupa Ligi (UEL) ve Konferans Ligi (ECL) turnuvalarinda
siradaki haftanin tum maclarini tarar ve %5.0 veya uzeri olasiliga sahip
en muhtemel (1. Kategori) skorlari ozet ve detayli olarak listeler.
"""
import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

# Proje ana dizinini sys.path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine

COMP_INFO = {
    "CL": {
        "name": "UEFA ŞAMPİYONLAR LİGİ",
        "file": PROJECT_ROOT / "data" / "leagues" / "cl_2026_27.json",
    },
    "UEL": {
        "name": "UEFA AVRUPA LİGİ",
        "file": PROJECT_ROOT / "data" / "leagues" / "uel_2026_27.json",
    },
    "ECL": {
        "name": "UEFA KONFERANS LİGİ",
        "file": PROJECT_ROOT / "data" / "leagues" / "ecl_2026_27.json",
    },
}


def analyze_match_tier1_scores(engine: MatchEngine, h_elo: float, a_elo: float, is_neutral: bool = False):
    probs = engine.calculate_match_probabilities(h_elo, a_elo, is_neutral=is_neutral)
    matrix = probs.score_matrix

    scores = []
    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = matrix[h, a]
            scores.append((h, a, float(p)))

    scores.sort(key=lambda x: x[2], reverse=True)
    # 1. Kategori: Olasılığı >= %5.0 olan skorlar
    tier1 = [s for s in scores if s[2] >= 0.05]
    return probs, tier1


def get_next_round_matches(league_json_path: Path, round_override: int = None):
    if not league_json_path.exists():
        return None, []

    with open(league_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixtures = data.get("fixtures", [])
    if round_override is not None:
        target_round = round_override
    else:
        unplayed = [m for m in fixtures if not m.get("is_played", False)]
        if not unplayed:
            return None, []
        target_round = unplayed[0]["round"]

    matches = [m for m in fixtures if m.get("round") == target_round]
    return target_round, matches


def show_upcoming_odds(competitions: List[str] = None, round_override: int = None, min_prob: float = 0.05):
    if not competitions:
        competitions = ["CL", "UEL", "ECL"]

    fetcher = AkilOyunuEloFetcher()
    engine = MatchEngine(home_advantage=75.0, max_goals=7)

    print("\n" + "=" * 110)
    print("      GELECEK HAFTANIN EN MUHTEMEL MAÇ SKORLARI (1. KATEGORİ SKORLAR: >= %5.0)")
    print("=" * 110)

    for comp_code in competitions:
        comp_code_upper = comp_code.upper()
        if comp_code_upper not in COMP_INFO:
            continue

        info = COMP_INFO[comp_code_upper]
        target_round, matches = get_next_round_matches(info["file"], round_override=round_override)

        if not matches:
            print(f"\n[BİLGİ] {info['name']} için oynanacak maç bulunamadı.")
            continue

        unplayed_matches = [m for m in matches if not m.get("is_played", False)]
        played_matches = [m for m in matches if m.get("is_played", False)]

        print("\n" + "#" * 110)
        print(f"  {info['name']} - HAFTA {target_round} (Toplam {len(matches)} Maç | Oynanacak: {len(unplayed_matches)} | Oynanmış: {len(played_matches)})")
        print("#" * 110)

        for idx, m in enumerate(matches, 1):
            h_team = m["home_team"]
            a_team = m["away_team"]
            is_neutral = m.get("is_neutral", False)
            date_str = m.get("date", "-")

            if m.get("is_played", False):
                # Zaten oynanmış maç
                print(f"\n[{idx:02d}] {date_str} | {h_team} {m['home_score']} - {m['away_score']} {a_team} [OYNANDI]")
                continue

            h_elo = fetcher.get_elo(h_team)
            a_elo = fetcher.get_elo(a_team)

            probs, tier1 = analyze_match_tier1_scores(engine, h_elo, a_elo, is_neutral=is_neutral)

            neutral_tag = " [TARAFSIZ SAHA]" if is_neutral else ""
            print(f"\n[{idx:02d}] {date_str} | {h_team} ({h_elo:.0f}) vs {a_team} ({a_elo:.0f}){neutral_tag}")
            print(f"     1: %{probs.home_win*100:<4.1f} | X: %{probs.draw*100:<4.1f} | 2: %{probs.away_win*100:<4.1f}  "
                  f"(xG: {probs.expected_home_goals:.2f} - {probs.expected_away_goals:.2f})")

            # 1. Kategori Skorlar
            tier1_str_list = [f"{h}-{a} (%{p*100:.1f})" for h, a, p in tier1]
            cum_pct = sum(p for _, _, p in tier1) * 100
            print(f"     -> 1. Kategori Skorlar (Toplam {len(tier1)} Skor, Kümülatif %{cum_pct:.1f}):")
            print(f"        {',  '.join(tier1_str_list)}")

    print("\n" + "=" * 110 + "\n")


def main():
    parser = argparse.ArgumentParser(description="3 Turnuva İçin Gelecek Haftanın 1. Kategori Skor Tahminleri")
    parser.add_argument(
        "-c", "--competition", nargs="+", default=["CL", "UEL", "ECL"],
        help="Listelenecek turnuva(lar) (CL, UEL, ECL). Varsayılan: Hepsi"
    )
    parser.add_argument("-r", "--round", type=int, default=None, help="Belirli bir haftayı görüntülemek için (örn: 4)")
    args = parser.parse_args()

    show_upcoming_odds(competitions=args.competition, round_override=args.round)


if __name__ == "__main__":
    main()

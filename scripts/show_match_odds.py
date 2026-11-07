import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine


def main():
    parser = argparse.ArgumentParser(description="İki Takım Arasındaki Maçın Olası Skor Dağılımlarını Göster")
    parser.add_argument("home_team", nargs="?", default="Slovan Bratislava", help="Ev sahibi takım adı")
    parser.add_argument("away_team", nargs="?", default="Real Betis", help="Deplasman takımı adı")
    args = parser.parse_args()

    fetcher = AkilOyunuEloFetcher()
    engine = MatchEngine(home_advantage=75.0, max_goals=7)

    h_elo = fetcher.get_elo(args.home_team)
    a_elo = fetcher.get_elo(args.away_team)

    probs = engine.calculate_match_probabilities(h_elo, a_elo)

    print("=" * 80)
    print(f" MAÇ ANALİZİ: {args.home_team} (Ev) vs {args.away_team} (Deplasman)")
    print(f" Ev Sahibi Elo : {h_elo:.1f} (+75 Ev Avantajı = {h_elo + 75:.1f})")
    print(f" Deplasman Elo : {a_elo:.1f} (Net Elo Farkı: {h_elo + 75 - a_elo:+.1f})")
    print(f" Beklenen Gol  : {args.home_team} = {probs.expected_home_goals:.2f} | {args.away_team} = {probs.expected_away_goals:.2f}")
    print(f" 1-X-2 İhtimal : 1 ({args.home_team}) = %{probs.home_win*100:.1f} | X = %{probs.draw*100:.1f} | 2 ({args.away_team}) = %{probs.away_win*100:.1f}")
    print("=" * 80)

    scores = []
    matrix = probs.score_matrix
    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = matrix[h, a]
            scores.append((h, a, p))

    scores.sort(key=lambda x: x[2], reverse=True)

    tier1 = [s for s in scores if s[2] >= 0.05]
    tier2 = [s for s in scores if 0.01 <= s[2] < 0.05]
    tier3 = [s for s in scores if 0.001 <= s[2] < 0.01]
    tier4 = [s for s in scores if 0.00001 <= s[2] < 0.001]
    tier5 = [s for s in scores if s[2] < 0.00001]

    def print_tier(title, score_list):
        if not score_list:
            return
        print(f"\n>>> {title} (Toplam {len(score_list)} Skor, Kümülatif: %{sum(s[2] for s in score_list)*100:.2f})")
        print("-" * 80)
        row = []
        for h, a, p in score_list:
            prob_pct = p * 100
            matches_in_10k = p * 10000
            row.append(f"{h}-{a} (%{prob_pct:<6.3f} ~{matches_in_10k:>4.1f}/10k)")
            if len(row) == 3:
                print("  |  ".join(row))
                row = []
        if row:
            print("  |  ".join(row))

    print_tier("1. KATEGORİ: EN MUHTEMEL SKORLAR (>= %5.0)", tier1)
    print_tier("2. KATEGORİ: ORTA İHTİMALLİ STANDART SKORLAR (%1.0 - %5.0)", tier2)
    print_tier("3. KATEGORİ: SÜRPRİZ VE GOLLÜ SKORLAR (%0.1 - %1.0)", tier3)
    print_tier("4. KATEGORİ: TARİHİ VE EKSTREM SKORLAR (%0.001 - %0.1)", tier4)
    print_tier("5. KATEGORİ: MUCİZE / UÇ SKORLAR (< %0.001)", tier5)

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

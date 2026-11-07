import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine

fetcher = AkilOyunuEloFetcher()
engine = MatchEngine(home_advantage=75.0, max_goals=7)

home_team = "Galatasaray"
away_team = "Stuttgart"

h_elo = fetcher.get_elo(home_team)
a_elo = fetcher.get_elo(away_team)

probs = engine.calculate_match_probabilities(h_elo, a_elo)

print("=" * 80)
print(f" TÜM SKOR OLASILIKLARI: {home_team} vs {away_team}")
print(f" Ev Elo: {h_elo:.1f} (+75 = {h_elo+75:.1f}) | Dep Elo: {a_elo:.1f}")
print(f" xG: {home_team}={probs.expected_home_goals:.2f} | {away_team}={probs.expected_away_goals:.2f}")
print("=" * 80)

scores = []
matrix = probs.score_matrix
for h in range(matrix.shape[0]):
    for a in range(matrix.shape[1]):
        p = matrix[h, a]
        scores.append((h, a, p))

# Olasiliga gore sirala
scores.sort(key=lambda x: x[2], reverse=True)

# Kategorize et
tier1 = [s for s in scores if s[2] >= 0.05]                          # >= %5 (En yaygın)
tier2 = [s for s in scores if 0.01 <= s[2] < 0.05]                  # %1 - %5 (Normal)
tier3 = [s for s in scores if 0.001 <= s[2] < 0.01]                 # %0.1 - %1 (Sürpriz)
tier4 = [s for s in scores if 0.00001 <= s[2] < 0.001]              # %0.001 - %0.1 (Tarihi / Ekstrem)
tier5 = [s for s in scores if s[2] < 0.00001]                       # < %0.001 (Mucize)

def print_tier(title, score_list):
    print(f"\n>>> {title} (Toplam {len(score_list)} Skor, Kümülatif Olasılık: %{sum(s[2] for s in score_list)*100:.2f})")
    print("-" * 80)
    # Her satira 4 skor basalim
    row = []
    for h, a, p in score_list:
        prob_pct = p * 100
        # 10.000 macta kac kez cikar?
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
print(f"Toplam Olasılık: %{sum(s[2] for s in scores)*100:.4f}")
print("=" * 80)

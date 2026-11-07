"""
Match Engine Test & Dogrulama Scripti
Farkli Elo senaryolarinda motorun urettigi olasiliklari ve 10.000 maclik simulasyon sonuclarini test eder.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import numpy as np
from src.models.match_engine import MatchEngine


def test_match_engine():
    engine = MatchEngine(home_advantage=75.0)

    test_fixtures = [
        {"name": "Denk Mac (Esit Elo)", "home_elo": 1800, "away_elo": 1800},
        {"name": "Ev Sahibi Agir Favori (Bayern vs Zagreb tarzi)", "home_elo": 1950, "away_elo": 1600},
        {"name": "Deplasman Agir Favori (Slovan vs Man City tarzi)", "home_elo": 1550, "away_elo": 2000},
        {"name": "Kafa Kafaya Dev Mac (Real Madrid vs Man City)", "home_elo": 1980, "away_elo": 2010},
    ]

    print("=" * 75)
    print("MATCH ENGINE (ELO + POISSON + DIXON-COLES) TESTI")
    print("=" * 75)

    for fix in test_fixtures:
        print(f"\n>>> Senaryo: {fix['name']}")
        print(f"    Ev Sahibi Elo: {fix['home_elo']} (+75 Ev Avantaji = {fix['home_elo'] + 75})")
        print(f"    Deplasman Elo: {fix['away_elo']}")
        
        probs = engine.calculate_match_probabilities(fix['home_elo'], fix['away_elo'])
        print(f"    Beklenen Gol (xG): Ev={probs.expected_home_goals:.2f} | Dep={probs.expected_away_goals:.2f}")
        print(f"    Olasiliklar: 1 (Ev)={probs.home_win*100:.1f}% | X (Ber)={probs.draw*100:.1f}% | 2 (Dep)={probs.away_win*100:.1f}%")
        
        # En olasi 3 skor
        flat_idx = np.argsort(probs.score_matrix.flatten())[::-1][:3]
        top_scores = []
        for idx in flat_idx:
            hg, ag = divmod(idx, engine.max_goals + 1)
            p = probs.score_matrix[hg, ag] * 100
            top_scores.append(f"{hg}-{ag} (%{p:.1f})")
        print(f"    En Muhtemel Skorlar: {', '.join(top_scores)}")

    # 10.000 maclik Monte Carlo hiz ve tutarlilik testi
    print("\n" + "=" * 75)
    print("10.000 MACLIK MONTE CARLO SIMULASYON PERFORMANS TESTI")
    print("=" * 75)
    start_time = time.time()
    sim_results = engine.simulate_n_matches(1850, 1800, n=10000)
    elapsed = time.time() - start_time

    home_wins = np.sum(sim_results[:, 0] > sim_results[:, 1])
    draws = np.sum(sim_results[:, 0] == sim_results[:, 1])
    away_wins = np.sum(sim_results[:, 0] < sim_results[:, 1])
    avg_home_g = np.mean(sim_results[:, 0])
    avg_away_g = np.mean(sim_results[:, 1])

    print(f"10.000 mac simule edildi. Gecen sure: {elapsed*1000:.2f} ms")
    print(f"Simulasyon Sonuclari:")
    print(f"  Ev Galibiyeti : {home_wins} ({home_wins/100:.1f}%)")
    print(f"  Beraberlik    : {draws} ({draws/100:.1f}%)")
    print(f"  Dep Galibiyeti: {away_wins} ({away_wins/100:.1f}%)")
    print(f"  Ortalama Skor : {avg_home_g:.2f} - {avg_away_g:.2f}")
    print("=" * 75)


if __name__ == "__main__":
    test_match_engine()


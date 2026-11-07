"""
UEFA Champions League 2026-27 - Ilk 3 Hafta: 10.000 TEKRARLI MONTE CARLO SIMULASYONU
10.000 farkli evrende ilk 3 hafta oynatilir, her takimin:
- Ortalama (Mean) Puan Tablosu
- Medyan (Median) Puan Tablosu
- Ilk 8 ve Ilk 24'te bitirme olasiliklari hesaplanir.
"""
import sys
import os
import time
import numpy as np
import pandas as pd
from typing import Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader.league_loader import LeagueLoader
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine


def run_monte_carlo_3_weeks(n_simulations: int = 10000):
    league_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "leagues", "cl_2026_27.json"))
    loader = LeagueLoader(league_file)
    elo_fetcher = AkilOyunuEloFetcher()
    engine = MatchEngine(home_advantage=75.0)

    teams = loader.teams
    team_to_idx = {name: i for i, name in enumerate(teams)}
    n_teams = len(teams)

    # Ilk 3 haftanin maclarini al (54 mac)
    fixtures = loader.get_fixtures_up_to_round(3)
    n_matches = len(fixtures)

    print("=" * 105)
    print(f" UEFA CHAMPIONS LEAGUE (2026-27) - ILK 3 HAFTA: {n_simulations:,} MONTE CARLO SEZON SIMULASYONU")
    print(f" Toplam Takim: {n_teams} | Toplam Mac (Ilk 3 Hafta): {n_matches} | Toplam Oynatilacak Mac: {n_matches * n_simulations:,}")
    print("=" * 105)

    # 1. Maclarin olasılık dagilimlarini ve 10.000'er skorunu onceden vektorize uret
    print("\n[1/3] Maclarin 10.000'er simule edilmis skorlari uretiliyor...")
    start_time = time.time()

    # match_sim_scores: shape (n_matches, n_simulations, 2)
    match_sim_scores = np.zeros((n_matches, n_simulations, 2), dtype=np.int32)
    match_meta = []

    for m_idx, match in enumerate(fixtures):
        home_elo = elo_fetcher.get_elo(match.home_team)
        away_elo = elo_fetcher.get_elo(match.away_team)
        # 10.000 mac simule et
        scores = engine.simulate_n_matches(home_elo, away_elo, n=n_simulations, is_neutral=match.is_neutral)
        match_sim_scores[m_idx] = scores
        match_meta.append((team_to_idx[match.home_team], team_to_idx[match.away_team]))

    # 2. Her simulasyon icin takim istatistiklerini hesapla
    print("[2/3] 10.000 sezon icin puan tablolari derleniyor...")
    
    # points: (n_simulations, n_teams)
    sim_points = np.zeros((n_simulations, n_teams), dtype=np.int32)
    sim_gf = np.zeros((n_simulations, n_teams), dtype=np.int32)
    sim_ga = np.zeros((n_simulations, n_teams), dtype=np.int32)
    sim_wins = np.zeros((n_simulations, n_teams), dtype=np.int32)
    sim_draws = np.zeros((n_simulations, n_teams), dtype=np.int32)
    sim_losses = np.zeros((n_simulations, n_teams), dtype=np.int32)

    for m_idx, (h_idx, a_idx) in enumerate(match_meta):
        h_goals = match_sim_scores[m_idx, :, 0]
        a_goals = match_sim_scores[m_idx, :, 1]

        # Goller
        sim_gf[:, h_idx] += h_goals
        sim_ga[:, h_idx] += a_goals
        sim_gf[:, a_idx] += a_goals
        sim_ga[:, a_idx] += h_goals

        # Mac sonuclari
        h_win = h_goals > a_goals
        draw = h_goals == a_goals
        a_win = h_goals < a_goals

        sim_points[:, h_idx] += h_win * 3 + draw * 1
        sim_points[:, a_idx] += a_win * 3 + draw * 1

        sim_wins[:, h_idx] += h_win
        sim_draws[:, h_idx] += draw
        sim_losses[:, h_idx] += a_win

        sim_wins[:, a_idx] += a_win
        sim_draws[:, a_idx] += draw
        sim_losses[:, a_idx] += h_win

    sim_gd = sim_gf - sim_ga

    # 3. Her simulasyonda takimlarin siralamasini (rank) bul
    # UEFA tie-break: Points -> GD -> GF -> Wins
    # Cok hizli siralamak icin tek bilesik skor olusturuyoruz:
    composite_score = (
        sim_points.astype(np.int64) * 1_000_000_000
        + (sim_gd + 500).astype(np.int64) * 1_000_000
        + sim_gf.astype(np.int64) * 1_000
        + sim_wins.astype(np.int64)
    )

    # sim_ranks: her simulasyon icin her takimin sirasi (1-36 arasi)
    # argsort[::-1] ile azalan sirala
    sorted_indices = np.argsort(-composite_score, axis=1)
    sim_ranks = np.zeros((n_simulations, n_teams), dtype=np.int32)
    for sim_i in range(n_simulations):
        for rank_i in range(n_teams):
            t_idx = sorted_indices[sim_i, rank_i]
            sim_ranks[sim_i, t_idx] = rank_i + 1

    elapsed = time.time() - start_time
    print(f"[3/3] Simulasyon tamamlandi! Gecen sure: {elapsed:.2f} saniye.\n")

    # Sonuclari toparla
    results = []
    for t_idx, team_name in enumerate(teams):
        pts = sim_points[:, t_idx]
        gd = sim_gd[:, t_idx]
        gf = sim_gf[:, t_idx]
        ga = sim_ga[:, t_idx]
        w = sim_wins[:, t_idx]
        d = sim_draws[:, t_idx]
        l = sim_losses[:, t_idx]
        rnk = sim_ranks[:, t_idx]

        results.append({
            "team": team_name,
            "mean_points": float(np.mean(pts)),
            "median_points": float(np.median(pts)),
            "p25_points": float(np.percentile(pts, 25)),
            "p75_points": float(np.percentile(pts, 75)),
            "mean_gd": float(np.mean(gd)),
            "median_gd": float(np.median(gd)),
            "mean_gf": float(np.mean(gf)),
            "mean_ga": float(np.mean(ga)),
            "mean_wins": float(np.mean(w)),
            "mean_draws": float(np.mean(d)),
            "mean_losses": float(np.mean(l)),
            "mean_rank": float(np.mean(rnk)),
            "median_rank": float(np.median(rnk)),
            "prob_top8": float(np.mean(rnk <= 8) * 100),
            "prob_playoff": float(np.mean((rnk >= 9) & (rnk <= 24)) * 100),
            "prob_eliminated": float(np.mean(rnk >= 25) * 100),
        })

    # =========================================================================
    # TABLO A: ORTALAMA (MEAN) PUAN DURUMU TABLOSU
    # =========================================================================
    df_mean = pd.DataFrame(results).sort_values(by=["mean_points", "mean_gd", "mean_gf"], ascending=False).reset_index(drop=True)
    
    print("=" * 105)
    print("                TABLO A: ORTALAMA (MEAN) DEĞERLER PUAN DURUMU (10.000 SIMULASYON)")
    print("=" * 105)
    header_a = f"{'Sıra':<5}{'Takım':<25}{'Ort.P':<8}{'Ort.G':<7}{'Ort.B':<7}{'Ort.M':<7}{'Ort.AG':<8}{'Ort.YG':<8}{'Ort.AV':<8}{'Ort.Sıra':<9}"
    print(header_a)
    print("-" * 105)
    for i, row in df_mean.iterrows():
        print(
            f"{i+1:<5}{row['team']:<25}"
            f"{row['mean_points']:<8.2f}"
            f"{row['mean_wins']:<7.2f}"
            f"{row['mean_draws']:<7.2f}"
            f"{row['mean_losses']:<7.2f}"
            f"{row['mean_gf']:<8.2f}"
            f"{row['mean_ga']:<8.2f}"
            f"{row['mean_gd']:<+8.2f}"
            f"{row['mean_rank']:<9.1f}"
        )
    print("=" * 105)

    # =========================================================================
    # TABLO B: MEDYAN (MEDIAN) PUAN DURUMU TABLOSU
    # =========================================================================
    df_median = pd.DataFrame(results).sort_values(by=["median_points", "median_gd", "mean_points"], ascending=False).reset_index(drop=True)

    print("\n" + "=" * 105)
    print("                TABLO B: MEDYAN (MEDIAN) DEĞERLER PUAN DURUMU (10.000 SIMULASYON)")
    print("=" * 105)
    header_b = f"{'Sıra':<5}{'Takım':<25}{'Med.P':<8}{'Çeyrekler[25-75%]':<20}{'Med.AV':<9}{'Med.Sıra':<10}{'Top 8 (%)':<12}{'Playoff(%)':<12}"
    print(header_b)
    print("-" * 105)
    for i, row in df_median.iterrows():
        iqr = f"[{int(row['p25_points'])} - {int(row['p75_points'])} Puan]"
        print(
            f"{i+1:<5}{row['team']:<25}"
            f"{row['median_points']:<8.1f}"
            f"{iqr:<20}"
            f"{row['median_gd']:<+9.1f}"
            f"{row['median_rank']:<10.1f}"
            f"%{row['prob_top8']:<11.1f}"
            f"%{row['prob_playoff']:<11.1f}"
        )
    print("=" * 105)


if __name__ == "__main__":
    run_monte_carlo_3_weeks(10000)


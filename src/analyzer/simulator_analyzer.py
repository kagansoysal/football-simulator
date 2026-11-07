import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.simulator.monte_carlo_engine import SimulationResults


class SimulationAnalyzer:
    """
    Monte Carlo simulasyon sonuclarini matematiksel ve istatistiksel
    olarak analiz eden, esik ve olasilik matrislerini hesaplayan ve kaydeden sinif.
    """

    def __init__(self, results: SimulationResults):
        self.results = results
        self.n_sims = results.n_simulations
        self.teams = results.teams
        self.n_teams = len(self.teams)

        # Matrisleri cikaralim
        self._extract_matrices()

    def _extract_matrices(self):
        """
        standings_history uzerinden hizli hesaplama icin numpy matrislerini olusturur.
        """
        # team_name -> index
        self.team_to_idx = {name: i for i, name in enumerate(self.teams)}

        # points_mat: (n_sims, n_teams)
        # gd_mat: (n_sims, n_teams)
        # gf_mat: (n_sims, n_teams)
        # ga_mat: (n_sims, n_teams)
        # wins_mat, draws_mat, losses_mat: (n_sims, n_teams)
        # ranks_mat: (n_sims, n_teams)  (1-36 arasi bitis sirasi)

        self.points_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.gd_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.gf_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.ga_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.wins_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.draws_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.losses_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)
        self.ranks_mat = np.zeros((self.n_sims, self.n_teams), dtype=np.int32)

        for sim_i, table in enumerate(self.results.standings_history):
            for rank_i, t in enumerate(table, 1):
                idx = self.team_to_idx[t.name]
                self.points_mat[sim_i, idx] = t.points
                self.gd_mat[sim_i, idx] = t.goal_difference
                self.gf_mat[sim_i, idx] = t.goals_for
                self.ga_mat[sim_i, idx] = t.goals_against
                self.wins_mat[sim_i, idx] = t.won
                self.draws_mat[sim_i, idx] = t.drawn
                self.losses_mat[sim_i, idx] = t.lost
                self.ranks_mat[sim_i, idx] = rank_i

    def analyze_team_performances(self) -> List[Dict[str, Any]]:
        """
        Her takimin ortalama/medyan puan, averaj, G/B/M dagilimini hesaplar.
        """
        team_summaries = []
        for idx, team_name in enumerate(self.teams):
            pts = self.points_mat[:, idx]
            gd = self.gd_mat[:, idx]
            gf = self.gf_mat[:, idx]
            ga = self.ga_mat[:, idx]
            w = self.wins_mat[:, idx]
            d = self.draws_mat[:, idx]
            l = self.losses_mat[:, idx]
            rnk = self.ranks_mat[:, idx]

            team_summaries.append({
                "team": team_name,
                "mean_points": float(np.mean(pts)),
                "median_points": float(np.median(pts)),
                "p25_points": float(np.percentile(pts, 25)),
                "p75_points": float(np.percentile(pts, 75)),
                
                # Sadece ortalama G-B-M (toplami tam 8 mac)
                "mean_wins": float(np.mean(w)),
                "mean_draws": float(np.mean(d)),
                "mean_losses": float(np.mean(l)),

                "mean_gf": float(np.mean(gf)),
                "median_gf": float(np.median(gf)),
                "mean_ga": float(np.mean(ga)),
                "median_ga": float(np.median(ga)),
                "mean_gd": float(np.mean(gd)),
                "median_gd": float(np.median(gd)),

                "mean_rank": float(np.mean(rnk)),
                "median_rank": float(np.median(rnk)),
                "best_rank": int(np.min(rnk)),
                "worst_rank": int(np.max(rnk)),

                "prob_top8": float(np.mean(rnk <= 8) * 100),
                "prob_playoff": float(np.mean((rnk >= 9) & (rnk <= 24)) * 100),
                "prob_eliminated": float(np.mean(rnk >= 25) * 100),
            })

        # Ortalama puana gore sirala
        team_summaries.sort(key=lambda x: (x["mean_points"], x["mean_gd"]), reverse=True)
        return team_summaries

    def analyze_qualification_thresholds(self) -> Dict[str, Any]:
        """
        10.000 simulasyonda 8. ve 24. sirada bitiren takimlarin puan ve averajlarini
        inceleyerek kesin, ortalama ve alt baraj puanlarini cikarir.
        """
        # Her simulasyonda 8. siradaki ve 24. siradaki takimin puan ve averaji
        top8_cutoff_points = []
        top8_cutoff_gd = []
        top24_cutoff_points = []
        top24_cutoff_gd = []

        for sim_i, table in enumerate(self.results.standings_history):
            # 8. takim (index 7)
            t8 = table[7]
            top8_cutoff_points.append(t8.points)
            top8_cutoff_gd.append(t8.goal_difference)

            # 24. takim (index 23)
            t24 = table[23]
            top24_cutoff_points.append(t24.points)
            top24_cutoff_gd.append(t24.goal_difference)

        p8 = np.array(top8_cutoff_points)
        gd8 = np.array(top8_cutoff_gd)
        p24 = np.array(top24_cutoff_points)
        gd24 = np.array(top24_cutoff_gd)

        return {
            "top_8_threshold": {
                "description": "Son 16 Turuna Doğrudan Katılım Barajı (8. Sıra)",
                "mean_points": float(np.mean(p8)),
                "median_points": float(np.median(p8)),
                "mean_gd": float(np.mean(gd8)),
                "median_gd": float(np.median(gd8)),
                "guaranteed_points_99pct": int(np.percentile(p8, 99)),  # %99 kesin garanti
                "safe_points_90pct": int(np.percentile(p8, 90)),         # %90 guvenli
                "minimum_possible_points": int(np.min(p8)),              # En sansli senaryo
                "maximum_possible_points": int(np.max(p8)),              # En zorlu senaryo
                "distribution": {int(k): float(v) for k, v in pd.Series(p8).value_counts(normalize=True).sort_index().items()}
            },
            "top_24_threshold": {
                "description": "Play-off Turuna Kalma Barajı (24. Sıra)",
                "mean_points": float(np.mean(p24)),
                "median_points": float(np.median(p24)),
                "mean_gd": float(np.mean(gd24)),
                "median_gd": float(np.median(gd24)),
                "guaranteed_points_99pct": int(np.percentile(p24, 99)), # %99 kesin garanti
                "safe_points_90pct": int(np.percentile(p24, 90)),        # %90 guvenli
                "minimum_possible_points": int(np.min(p24)),             # En sansli senaryo
                "maximum_possible_points": int(np.max(p24)),             # En zorlu senaryo
                "distribution": {int(k): float(v) for k, v in pd.Series(p24).value_counts(normalize=True).sort_index().items()}
            }
        }

    def analyze_points_to_outcome_matrix(self) -> List[Dict[str, Any]]:
        """
        'Hangi puani alirsam ne olur?' sorusunun olasilik matrisi.
        Her olasi puan (3 - 24 arasi) icin o puani alan takimin
        ilk 8'de, play-off'ta veya elenme potasinda bitirme yuzdesini hesaplar.
        """
        # Tum (sim, team) kombinasyonlarini duzlestirelim
        flat_points = self.points_mat.flatten()
        flat_ranks = self.ranks_mat.flatten()

        matrix = []
        possible_pts = sorted(list(set(flat_points)))

        for pt in possible_pts:
            mask = (flat_points == pt)
            count = int(np.sum(mask))
            if count == 0:
                continue

            ranks_with_pt = flat_ranks[mask]
            prob_top8 = float(np.mean(ranks_with_pt <= 8) * 100)
            prob_playoff = float(np.mean((ranks_with_pt >= 9) & (ranks_with_pt <= 24)) * 100)
            prob_elim = float(np.mean(ranks_with_pt >= 25) * 100)
            avg_rank = float(np.mean(ranks_with_pt))

            matrix.append({
                "points": int(pt),
                "sample_count": count,
                "avg_rank": avg_rank,
                "prob_top8": prob_top8,
                "prob_playoff": prob_playoff,
                "prob_eliminated": prob_elim,
            })

        return matrix

    def analyze_team_position_probabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Her takimin 1.'den 36.'ya kadar her bir sirada bitirme olasiligini (% cinsinden) cikarir.
        """
        team_pos_probs = {}
        for idx, team_name in enumerate(self.teams):
            rnk = self.ranks_mat[:, idx]
            counts = np.bincount(rnk, minlength=self.n_teams + 1)
            # 1'den 36'ya olasiliklar
            probs_by_rank = {rank: float((counts[rank] / self.n_sims) * 100) for rank in range(1, self.n_teams + 1)}
            
            # En yuksek olasilikli sira (mode rank)
            mode_rank = int(np.argmax(counts[1:])) + 1

            team_pos_probs[team_name] = {
                "mode_rank": mode_rank,
                "prob_top8": float(np.mean(rnk <= 8) * 100),
                "prob_playoff": float(np.mean((rnk >= 9) & (rnk <= 24)) * 100),
                "prob_eliminated": float(np.mean(rnk >= 25) * 100),
                "rank_probabilities": probs_by_rank,
            }

        return team_pos_probs

    def run_full_analysis(self) -> Dict[str, Any]:
        """Tum analizleri tek cati altinda birlestirir."""
        return {
            "meta": {
                "n_simulations": self.n_sims,
                "n_teams": self.n_teams,
                "total_rounds": 8,
            },
            "team_performances": self.analyze_team_performances(),
            "qualification_thresholds": self.analyze_qualification_thresholds(),
            "points_to_outcome": self.analyze_points_to_outcome_matrix(),
            "team_position_probabilities": self.analyze_team_position_probabilities(),
        }

    def save_analysis(self, output_path: str) -> str:
        """Tum analizleri JSON olarak kaydeder."""
        data = self.run_full_analysis()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return output_path

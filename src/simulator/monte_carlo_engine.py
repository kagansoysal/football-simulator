import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from src.core.models import Match, LeagueTable, TeamStats
from src.data_loader.league_loader import LeagueLoader
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.simulator.elo_tracker import DynamicEloTracker
from src.models.match_engine import MatchEngine


@dataclass
class SimulationResults:
    """
    10.000 simulasyonun tum ham verilerini tutan konteyner.
    """
    n_simulations: int
    teams: List[str]
    played_matches: List[Match]
    unplayed_matches: List[Match]
    
    # standings_history[sim_idx] = List[TeamStats] (1'den 36'ya sirali)
    standings_history: List[List[TeamStats]]
    
    # match_scores[match_id][sim_idx] = (home_score, away_score, home_elo_before, away_elo_before, d_home, d_away)
    match_scores: Dict[int, List[Tuple[int, int, float, float, float, float]]]

    def get_simulation_standings(self, sim_id: int) -> List[TeamStats]:
        """Belirli bir simulasyonun (0 - n_simulations-1) nihai puan durumunu dondurur."""
        if not (0 <= sim_id < self.n_simulations):
            raise IndexError(f"Gecersiz simulasyon ID: {sim_id}. (0 ile {self.n_simulations - 1} arasinda olmali)")
        return self.standings_history[sim_id]

    def display_simulation_standings(self, sim_id: int) -> str:
        """Belirli bir simulasyonun puan tablosunu guzel bir metin olarak formatlar."""
        standings = self.get_simulation_standings(sim_id)
        header = f"{'Sıra':<5}{'Takım':<25}{'O':<4}{'G':<4}{'B':<4}{'M':<4}{'AG':<5}{'YG':<5}{'AV':<5}{'P':<4}"
        lines = [
            f"=== SIMÜLASYON #{sim_id + 1} NİHAİ PUAN DURUMU (8 HAFTA SONU) ===",
            header,
            "-" * len(header)
        ]
        for i, t in enumerate(standings, 1):
            lines.append(
                f"{i:<5}{t.name:<25}{t.played:<4}{t.won:<4}{t.drawn:<4}"
                f"{t.lost:<4}{t.goals_for:<5}{t.goals_against:<5}{t.goal_difference:<+5}{t.points:<4}"
            )
        return "\n".join(lines)

    def get_match_result_in_simulation(self, match_id: int, sim_id: int) -> Tuple[int, int, float, float, float, float]:
        """Belirli bir macin belirli bir simulasyondaki skorunu ve Elo detaylarini dondurur."""
        return self.match_scores[match_id][sim_id]

    def save(self, file_path: str):
        """Sonuclari sikistirilmis dosya olarak kaydeder."""
        import pickle
        import gzip
        from pathlib import Path
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(file_path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, file_path: str) -> "SimulationResults":
        """Sikistirilmis sonuclari 0.1 saniyede okur."""
        import pickle
        import gzip
        with gzip.open(file_path, "rb") as f:
            return pickle.load(f)



class MonteCarloSimulator:
    """
    Oynanmis gercek maclari baz alip, kalan fiksturu N kez dinamik Elo ile simule eden motor.
    """

    def __init__(
        self,
        league_file: str,
        k_factor: float = 30.0,
        home_advantage: float = 75.0,
        as_of_date: Optional[str] = None,
    ):
        self.loader = LeagueLoader(league_file)
        self.teams = self.loader.teams
        self.played_fixtures = self.loader.get_played_fixtures()
        self.unplayed_fixtures = self.loader.get_unplayed_fixtures()

        self.engine = MatchEngine(home_advantage=home_advantage)
        elo_fetcher = AkilOyunuEloFetcher(as_of_date=as_of_date) if as_of_date else None
        self.elo_tracker = DynamicEloTracker(
            teams=self.teams, elo_fetcher=elo_fetcher, k_factor=k_factor, home_advantage=home_advantage
        )

    def run(self, n_simulations: int = 10000) -> SimulationResults:
        """
        Kalan tum maclari N kez simule eder ve sonuclari dondurur.
        """
        start_time = time.time()
        print(f"\n[MonteCarloSimulator] {n_simulations:,} sezon simulasyonu baslatiliyor...")
        print(f"  * Toplam Takim        : {len(self.teams)}")
        print(f"  * Oynanmis Gercek Mac : {len(self.played_fixtures)} (Puan durumuna onceden islendi)")
        print(f"  * Kalan Simule Mac    : {len(self.unplayed_fixtures)} mac / sezon")
        print(f"  * Toplam Simule Edilecek: {len(self.unplayed_fixtures) * n_simulations:,} mac")

        standings_history: List[List[TeamStats]] = []
        match_scores: Dict[int, List[Tuple[int, int]]] = {
            m.match_id: [] for m in self.unplayed_fixtures
        }

        # Kalan maclari haftalara gore gruplayalim (Dinamik Elo hafta bazinda dogru aksin)
        rounds = sorted(list(set(m.round for m in self.unplayed_fixtures)))
        round_matches = {
            r: [m for m in self.unplayed_fixtures if m.round == r] for r in rounds
        }

        for sim_i in range(n_simulations):
            if (sim_i + 1) % 2500 == 0 or sim_i == 0:
                print(f"  ... Simülasyon {sim_i + 1:,} / {n_simulations:,} tamamlandı.")

            # 1. Elo puanlarini baslangic AkilOyunu degerlerine resetle
            self.elo_tracker.reset()

            # 2. Puan tablosunu baslat ve oynanmis gercek maclari ekle
            table = LeagueTable(self.teams)
            for m in self.played_fixtures:
                table.add_result(m.home_team, m.away_team, m.home_score, m.away_score)

            # 3. Kalan maclari hafta hafta simule et ve Elo'lari guncelle
            for r in rounds:
                for match in round_matches[r]:
                    h_elo = self.elo_tracker.get_elo(match.home_team)
                    a_elo = self.elo_tracker.get_elo(match.away_team)

                    # Maci simule et
                    hg, ag = self.engine.simulate_match(h_elo, a_elo, is_neutral=match.is_neutral)

                    # Puan tablosunu guncelle
                    table.add_result(match.home_team, match.away_team, hg, ag)

                    # Elo'yu dinamik guncelle
                    update_info = self.elo_tracker.record_match_result(
                        match.home_team, match.away_team, hg, ag, is_neutral=match.is_neutral
                    )

                    # Mac skorunu ve o anki Elo durumunu kaydet
                    match_scores[match.match_id].append((
                        hg, ag, h_elo, a_elo, update_info["home_delta"], update_info["away_delta"]
                    ))

            # 4. Bu simulasyonun nihai puan durumunu kaydet
            standings_history.append(table.get_standings())

        elapsed = time.time() - start_time
        print(f"[MonteCarloSimulator] Bitti! Toplam gecen sure: {elapsed:.2f} saniye.\n")

        return SimulationResults(
            n_simulations=n_simulations,
            teams=self.teams,
            played_matches=self.played_fixtures,
            unplayed_matches=self.unplayed_fixtures,
            standings_history=standings_history,
            match_scores=match_scores,
        )

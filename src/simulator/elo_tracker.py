from typing import Dict, List, Optional
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.elo_updater import EloUpdater


class DynamicEloTracker:
    """
    Simulasyon sirasinda takimlarin Elo degisimlerini yoneten sinif.
    
    ONEMLI PRENSIP:
    AkilOyunu CSV verisi asla degistirilmez, salt okunurdur.
    Tum guncellemeler bu sinifin hafizasindaki 'current_ratings' sozlügunde tutulur.
    """

    def __init__(self, teams: List[str], elo_fetcher: Optional[AkilOyunuEloFetcher] = None, k_factor: float = 30.0, home_advantage: float = 75.0):
        self.fetcher = elo_fetcher or AkilOyunuEloFetcher()
        self.updater = EloUpdater(k_factor=k_factor, home_advantage=home_advantage)
        self.teams = teams

        # AkilOyunu'ndan baslangic Elo puanlarini al (Read-Only referans)
        self.initial_ratings: Dict[str, float] = {
            team: self.fetcher.get_elo(team) for team in teams
        }
        
        # Simulasyon boyunca degisecek olan aktif sozluk
        self.current_ratings: Dict[str, float] = self.initial_ratings.copy()

    def get_elo(self, team: str) -> float:
        """Takimin guncel simulasyon Elo'sunu dondurur."""
        return self.current_ratings.get(team, 1500.0)

    def record_match_result(
        self, home_team: str, away_team: str, home_goals: int, away_goals: int, is_neutral: bool = False
    ) -> Dict[str, float]:
        """
        Oynanan macin ardindan iki takimin simule edilmis Elo puanlarini gunceller.
        Dondurur: { "home_old": ..., "home_new": ..., "home_delta": ..., "away_old": ..., ... }
        """
        h_elo = self.get_elo(home_team)
        a_elo = self.get_elo(away_team)

        d_home, d_away = self.updater.calculate_elo_change(h_elo, a_elo, home_goals, away_goals, is_neutral)

        new_h_elo = h_elo + d_home
        new_a_elo = a_elo + d_away

        self.current_ratings[home_team] = new_h_elo
        self.current_ratings[away_team] = new_a_elo

        return {
            "home_old": h_elo,
            "home_new": new_h_elo,
            "home_delta": d_home,
            "away_old": a_elo,
            "away_new": new_a_elo,
            "away_delta": d_away,
        }

    def reset(self):
        """Simulasyon puanlarini bastaki AkilOyunu gercek degerlerine sifirlar."""
        self.current_ratings = self.initial_ratings.copy()

    def get_rating_changes(self) -> Dict[str, Dict[str, float]]:
        """Takimlarin baslangica gore net Elo degisimlerini dondurur."""
        changes = {}
        for team in self.teams:
            init_r = self.initial_ratings[team]
            curr_r = self.current_ratings[team]
            changes[team] = {
                "initial": init_r,
                "current": curr_r,
                "delta": curr_r - init_r,
            }
        return changes

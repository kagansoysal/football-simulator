import math
from typing import Tuple, Dict


class EloUpdater:
    """
    Resmi FIFA / World Football Elo standartlarina uygun dinamik Elo guncelleyici.
    
    Formul:
        New_Elo = Old_Elo + K * G * (W - We)
    
    Burada:
        W: Mac sonucu (1.0 = Galibiyet, 0.5 = Beraberlik, 0.0 = Maglubiyet)
        We: Beklenen sonuc (Lojistik egri uzerinden beklenen galibiyet olasiligi)
        K: Mac onemi katsayisi (Sampiyonlar Ligi standardi = 30.0 veya 40.0)
        G: Gol farki carpani (Margin of victory)
    """

    def __init__(self, k_factor: float = 30.0, home_advantage: float = 75.0):
        self.k_factor = k_factor
        self.home_advantage = home_advantage

    def calculate_expected_result(self, elo_a: float, elo_b: float) -> float:
        """A takiminin B takimina karsi beklenen sonucunu (0.0 ile 1.0 arasi) hesaplar."""
        delta = elo_a - elo_b
        return 1.0 / (1.0 + 10.0 ** (-delta / 400.0))

    def calculate_goal_margin_multiplier(self, home_goals: int, away_goals: int) -> float:
        """
        World Football Elo Ratings standardina gore gol farki carpani (G).
        - Beraberlik veya 1 fark: G = 1.0
        - 2 fark: G = 1.5
        - 3+ fark: G = (1.75 + (diff - 3) / 8)
        """
        diff = abs(home_goals - away_goals)
        if diff <= 1:
            return 1.0
        elif diff == 2:
            return 1.5
        else:
            return (1.75 + (diff - 3) / 8.0)

    def calculate_elo_change(
        self,
        home_elo: float,
        away_elo: float,
        home_goals: int,
        away_goals: int,
        is_neutral: bool = False,
    ) -> Tuple[float, float]:
        """
        Oynanan macin ardindan her iki takimin Elo puanindaki net degisimi (delta) dondurur.
        Dondurur: (home_delta, away_delta)
        """
        eff_home_adv = 0.0 if is_neutral else self.home_advantage

        # Ev ve deplasman icin beklenen sonuc (We)
        we_home = self.calculate_expected_result(home_elo + eff_home_adv, away_elo)
        we_away = 1.0 - we_home

        # Gerceklesen sonuc (W)
        if home_goals > away_goals:
            w_home, w_away = 1.0, 0.0
        elif home_goals == away_goals:
            w_home, w_away = 0.5, 0.5
        else:
            w_home, w_away = 0.0, 1.0

        # Gol farki carpani (G)
        g = self.calculate_goal_margin_multiplier(home_goals, away_goals)

        # Elo puan degisimi
        delta_home = self.k_factor * g * (w_home - we_home)
        delta_away = self.k_factor * g * (w_away - we_away)

        return delta_home, delta_away

    def update_match(
        self,
        home_elo: float,
        away_elo: float,
        home_goals: int,
        away_goals: int,
        is_neutral: bool = False,
    ) -> Tuple[float, float]:
        """Yeni Elo puanlarini (new_home_elo, new_away_elo) dondurur."""
        d_home, d_away = self.calculate_elo_change(home_elo, away_elo, home_goals, away_goals, is_neutral)
        return home_elo + d_home, away_elo + d_away

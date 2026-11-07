import math
import numpy as np
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MatchProbabilities:
    home_win: float
    draw: float
    away_win: float
    expected_home_goals: float
    expected_away_goals: float
    score_matrix: np.ndarray  # Shape: (max_goals + 1, max_goals + 1)


class MatchEngine:
    """
    Elo tabanli, Poisson ve Dixon-Coles duzeltmeli mac tahmin ve simulasyon motoru.
    
    Ozellikler:
    - Ev sahibi avantaji (varsayilan +75 Elo)
    - Elo farkindan beklenen gol (lambda) hesaplama
    - Dixon-Coles dusuk skor ve beraberlik korelasyon duzeltmesi (rho)
    - 1-X-2 olasiliklari ve skor dagilimi matrisi uretimi
    - Hizli Monte Carlo simule etme metodu (tek mac veya N adet mac)
    """

    def __init__(
        self,
        home_advantage: float = 75.0,
        base_home_goals: float = 1.65,
        base_away_goals: float = 1.35,
        elo_scale: float = 450.0,
        dixon_coles_rho: float = -0.11,
        max_goals: int = 8,
        max_home_xg: float = 3.50,
        max_away_xg: float = 3.20,
        min_home_xg: float = 0.35,
        min_away_xg: float = 0.30,
    ):
        """
        Args:
            home_advantage: Ev sahibine eklenecek ekstra Elo puani (varsayilan 75.0).
            base_home_goals: Esit gucteki maclarda ev sahibinin beklenen gol sayisi (~1.65).
            base_away_goals: Esit gucteki maclarda deplasmanin beklenen gol sayisi (~1.35).
            elo_scale: Sigmoid doygunluk olcegi (varsayilan 450.0 Elo farki).
            dixon_coles_rho: Dusuk skor korelasyon katsayisi (-0.15 ile -0.05 arasi idealdir, varsayilan -0.11).
            max_goals: Olasilik matrisi icin hesaplanacak maksimum gol sayisi.
            max_home_xg: Bir ev sahibinin cikabilecegi maksimum gercekci xG tavani (~3.50).
            max_away_xg: Bir deplasman takiminin cikabilecegi maksimum gercekci xG tavani (~3.20).
            min_home_xg: Bir ev sahibinin inebilecegi minimum taban xG (~0.35).
            min_away_xg: Bir deplasman takiminin inebilecegi minimum taban xG (~0.30).
        """
        self.home_advantage = home_advantage
        self.base_home_goals = base_home_goals
        self.base_away_goals = base_away_goals
        self.elo_scale = elo_scale
        self.rho = dixon_coles_rho
        self.max_goals = max_goals
        self.max_home_xg = max_home_xg
        self.max_away_xg = max_away_xg
        self.min_home_xg = min_home_xg
        self.min_away_xg = min_away_xg

        # 4 golden sonra gercekci futbol frenlemesi (takimlarin fark acilinca rolantiye almasi)
        self.goal_dampening = {
            0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0,
            5: 0.75, 6: 0.50, 7: 0.25, 8: 0.10
        }

    def calculate_expected_goals(
        self, home_elo: float, away_elo: float, is_neutral: bool = False
    ) -> Tuple[float, float]:
        """
        Iki takimin Elo puanlarindan Sigmoid (Tanh) Doygunluk Modeli ile
        ev ve deplasman beklenen gol (lambda / xG) degerlerini hesaplar.
        Asiri Elo farklarinda (700+) xG'nin kontrolsuz 6.0+'ya firlamasini onler,
        dogal futbol tavaninda (3.50) dengeler.
        """
        effective_home_adv = 0.0 if is_neutral else self.home_advantage
        delta_elo = (home_elo + effective_home_adv) - away_elo

        # Sigmoid (Tanh) Doygunluk Carpanı: -1.0 ile +1.0 arasinda yumusak S-Curve egrisi
        shift = float(np.tanh(delta_elo / self.elo_scale))

        if shift >= 0:
            # Ev sahibi avantajli: Ev xG tavana dogru yumusar, dep tabana dogru iner
            lambda_home = self.base_home_goals + shift * (self.max_home_xg - self.base_home_goals)
            lambda_away = self.base_away_goals - shift * (self.base_away_goals - self.min_away_xg)
        else:
            # Deplasman avantajli: Ev tabana dogru iner, dep tavana dogru yumusar
            pos_shift = abs(shift)
            lambda_home = self.base_home_goals - pos_shift * (self.base_home_goals - self.min_home_xg)
            lambda_away = self.base_away_goals + pos_shift * (self.max_away_xg - self.base_away_goals)

        return float(lambda_home), float(lambda_away)

    def _poisson_pmf(self, k: int, lam: float) -> float:
        """Tekil Poisson olasiligi hesaplar."""
        return (lam ** k * math.exp(-lam)) / math.factorial(k)

    def _dixon_coles_tau(self, x: int, y: int, lam_home: float, lam_away: float) -> float:
        """
        Dixon-Coles korelasyon faktoru: Sadece 0-0, 1-0, 0-1 ve 1-1 skorlari icin uygulanir.
        Diger skorlar icin carpan 1.0'dir.
        """
        if x == 0 and y == 0:
            return 1.0 - (lam_home * lam_away * self.rho)
        elif x == 0 and y == 1:
            return 1.0 + (lam_home * self.rho)
        elif x == 1 and y == 0:
            return 1.0 + (lam_away * self.rho)
        elif x == 1 and y == 1:
            return 1.0 - self.rho
        else:
            return 1.0

    def calculate_match_probabilities(
        self, home_elo: float, away_elo: float, is_neutral: bool = False
    ) -> MatchProbabilities:
        """
        Iki takim arasindaki macin tum skor olasiliklarini ve 1-X-2 ihtimallerini hesaplar.
        Sigmoid xG + Dixon-Coles dusuk skor duzeltmesi + Yuksek skor sonumlemesi uygular.
        """
        lam_home, lam_away = self.calculate_expected_goals(home_elo, away_elo, is_neutral)

        # 0'dan max_goals'e kadar Poisson PMF listeleri (Sonumleme carpanlari ile)
        p_home = [
            self._poisson_pmf(i, lam_home) * self.goal_dampening.get(i, 0.05)
            for i in range(self.max_goals + 1)
        ]
        p_away = [
            self._poisson_pmf(j, lam_away) * self.goal_dampening.get(j, 0.05)
            for j in range(self.max_goals + 1)
        ]

        # Skor olasilik matrisi olustur ve Dixon-Coles uygula
        matrix = np.zeros((self.max_goals + 1, self.max_goals + 1), dtype=np.float64)
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                tau = self._dixon_coles_tau(i, j, lam_home, lam_away)
                matrix[i, j] = max(0.0, p_home[i] * p_away[j] * tau)

        # Matrisi toplami 1 olacak sekilde normalize et
        total_p = matrix.sum()
        if total_p > 0:
            matrix /= total_p

        # 1-X-2 Olasiliklari
        home_win_p = float(np.tril(matrix, -1).sum())  # i > j (Ev sahibi > Deplasman)
        draw_p = float(np.trace(matrix))               # i == j (Beraberlik)
        away_win_p = float(np.triu(matrix, 1).sum())   # i < j (Deplasman > Ev sahibi)

        return MatchProbabilities(
            home_win=home_win_p,
            draw=draw_p,
            away_win=away_win_p,
            expected_home_goals=lam_home,
            expected_away_goals=lam_away,
            score_matrix=matrix,
        )

    def simulate_match(
        self, home_elo: float, away_elo: float, is_neutral: bool = False
    ) -> Tuple[int, int]:
        """
        Tek bir mac simule eder ve gercekci bir skor (ev_gol, dep_gol) dondurur.
        Dixon-Coles skor matrisi uzerinden rastgele ornekleme yapar.
        """
        probs = self.calculate_match_probabilities(home_elo, away_elo, is_neutral)
        flat_probs = probs.score_matrix.flatten()
        choice_idx = np.random.choice(len(flat_probs), p=flat_probs)
        home_goals, away_goals = divmod(choice_idx, self.max_goals + 1)
        return int(home_goals), int(away_goals)

    def simulate_n_matches(
        self,
        home_elo: float,
        away_elo: float,
        n: int = 10000,
        is_neutral: bool = False,
    ) -> np.ndarray:
        """
        Monte Carlo icin ayni maci N kez cok hizli simule eder.
        Dondurulen ndarray shape'i: (n, 2) -> her satir [ev_gol, dep_gol]
        """
        probs = self.calculate_match_probabilities(home_elo, away_elo, is_neutral)
        flat_probs = probs.score_matrix.flatten()
        choices = np.random.choice(len(flat_probs), size=n, p=flat_probs)
        home_goals, away_goals = np.divmod(choices, self.max_goals + 1)
        return np.column_stack((home_goals, away_goals))

    def get_most_likely_score(
        self, home_elo: float, away_elo: float, is_neutral: bool = False
    ) -> Tuple[int, int, float, MatchProbabilities]:
        """
        Iki takim arasindaki en yuksek olasiliga sahip skoru (mode) dondurur.
        Dondurur: (ev_gol, dep_gol, olasilik_yuzdesi, match_probabilities)
        """
        probs = self.calculate_match_probabilities(home_elo, away_elo, is_neutral)
        max_idx = int(np.argmax(probs.score_matrix))
        home_goals, away_goals = divmod(max_idx, self.max_goals + 1)
        prob = float(probs.score_matrix[home_goals, away_goals])
        return home_goals, away_goals, prob, probs



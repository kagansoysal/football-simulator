import pytest
from src.models.match_engine import MatchEngine, MatchProbabilities


class TestMatchEngine:
    def setup_method(self):
        self.engine = MatchEngine(
            home_advantage=75.0,
            base_home_goals=1.65,
            base_away_goals=1.35,
            elo_scale=450.0,
            dixon_coles_rho=-0.11,
            max_goals=8,
        )

    def test_expected_goals_home_advantage(self):
        """Equal Elo teams: home team should have higher expected goals due to home advantage."""
        home_xg, away_xg = self.engine.calculate_expected_goals(1800.0, 1800.0)
        assert home_xg > away_xg
        assert home_xg > 1.65  # Base + 75 Elo advantage boost
        assert away_xg < 1.35

    def test_expected_goals_strong_favorite(self):
        """Very strong favorite team vs weak team."""
        home_xg, away_xg = self.engine.calculate_expected_goals(2100.0, 1500.0)
        assert home_xg > 2.5
        assert away_xg < 0.8
        assert home_xg <= self.engine.max_home_xg
        assert away_xg >= self.engine.min_away_xg

    def test_calculate_match_probabilities_sum_to_one(self):
        """Probabilities of 1, X, 2 must sum to 1.0 (within float tolerance)."""
        probs = self.engine.calculate_match_probabilities(1900.0, 1750.0)
        assert isinstance(probs, MatchProbabilities)
        total_p = probs.home_win + probs.draw + probs.away_win
        assert pytest.approx(total_p, abs=1e-3) == 1.0
        assert probs.home_win > 0
        assert probs.draw > 0
        assert probs.away_win > 0

    def test_score_matrix_dimensions_and_sum(self):
        """Score matrix should be (max_goals + 1) x (max_goals + 1) and sum close to 1."""
        probs = self.engine.calculate_match_probabilities(1850.0, 1850.0)
        matrix = probs.score_matrix
        assert matrix.shape == (9, 9)
        assert pytest.approx(matrix.sum(), abs=1e-2) == 1.0

    def test_simulate_match_single(self):
        """Single match simulation should return valid integer goal counts."""
        h_goals, a_goals = self.engine.simulate_match(1950.0, 1700.0)
        assert isinstance(h_goals, int)
        assert isinstance(a_goals, int)
        assert h_goals >= 0
        assert a_goals >= 0

    def test_simulate_n_matches_distribution(self):
        """Simulating 1,000 matches between heavy favorite and underdog."""
        home_wins, draws, away_wins = 0, 0, 0
        n = 1000
        for _ in range(n):
            h, a = self.engine.simulate_match(2100.0, 1500.0)
            if h > a:
                home_wins += 1
            elif h == a:
                draws += 1
            else:
                away_wins += 1

        # Real Madrid at home against an underdog should win majority (>60%)
        assert home_wins > 500
        assert home_wins > away_wins

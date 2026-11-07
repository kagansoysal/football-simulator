from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


# -------------------------------------------------------------
# Takım Şemaları
# -------------------------------------------------------------
class TeamBase(BaseModel):
    name: str
    country: Optional[str] = None
    current_elo: float


class TeamStandingsOut(TeamBase):
    id: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    rank: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Fikstür Şemaları
# -------------------------------------------------------------
class FixtureOut(BaseModel):
    id: int
    round: int
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    is_played: bool
    match_date: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Turnuva Şemaları
# -------------------------------------------------------------
class CompetitionOut(BaseModel):
    id: int
    code: str
    name: str
    season: str
    total_rounds: int
    total_teams: int

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Simülasyon Analiz Şemaları
# -------------------------------------------------------------
class TeamSimulationStatOut(BaseModel):
    team_name: str
    current_elo: float
    current_points: int
    mean_points: float
    median_points: float
    std_points: float
    mean_rank: float
    median_rank: float
    top_8_prob: float
    playoff_prob: float
    elimination_prob: float
    rank_distribution: Optional[Dict[str, Any]] = None
    points_distribution: Optional[Dict[str, Any]] = None


class SimulationSummaryOut(BaseModel):
    competition_code: str
    competition_name: str
    sim_date: str
    num_simulations: int
    thresholds: Optional[Dict[str, Any]]
    teams: List[TeamSimulationStatOut]


# -------------------------------------------------------------
# Maç Tahmin ve Olasılık Şeması
# -------------------------------------------------------------
class MatchOddsRequest(BaseModel):
    home_team: str
    away_team: str
    home_advantage: float = 75.0


class MatchScoreProbability(BaseModel):
    score: str
    probability: float


class MatchOddsResponse(BaseModel):
    home_team: str
    away_team: str
    home_elo: float
    away_elo: float
    effective_home_elo: float
    home_xg: float
    away_xg: float
    probabilities: Dict[str, float]  # {"home_win": 0.55, "draw": 0.25, "away_win": 0.20}
    top_scores: List[MatchScoreProbability]


# -------------------------------------------------------------
# Asenkron Celery Simülasyon Görevi Şemaları
# -------------------------------------------------------------
class SimulationTriggerRequest(BaseModel):
    competition_code: str = "CL"
    num_simulations: int = 10000


class SimulationTriggerResponse(BaseModel):
    task_id: str
    competition_code: str
    num_simulations: int
    status: str
    message: str


class SimulationTaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    progress: Optional[int] = 0
    current_step: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


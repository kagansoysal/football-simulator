from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Match:
    match_id: int
    round: int  # Hafta veya tur no (orn: 1, 2, 3...)
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    is_played: bool = False
    is_neutral: bool = False

    @property
    def is_finished(self) -> bool:
        return self.is_played and self.home_score is not None and self.away_score is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "round": self.round,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "is_played": self.is_played,
            "is_neutral": self.is_neutral,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Match":
        return cls(
            match_id=data["match_id"],
            round=data["round"],
            home_team=data["home_team"],
            away_team=data["away_team"],
            home_score=data.get("home_score"),
            away_score=data.get("away_score"),
            is_played=data.get("is_played", False),
            is_neutral=data.get("is_neutral", False),
        )


@dataclass
class TeamStats:
    name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    away_goals: int = 0

    def update_match(self, scored: int, conceded: int, is_away: bool = False):
        self.played += 1
        self.goals_for += scored
        self.goals_against += conceded
        self.goal_difference = self.goals_for - self.goals_against
        if is_away:
            self.away_goals += scored

        if scored > conceded:
            self.won += 1
            self.points += 3
        elif scored == conceded:
            self.drawn += 1
            self.points += 1
        else:
            self.lost += 1


class LeagueTable:
    """
    Herhangi bir lig veya turnuva icin genel puan durumu tablosu.
    UEFA kurallarina uygun siralama:
    Puan -> Genel Averaj -> Atilan Gol -> Deplasman Golu -> Galibiyet Sayisi
    """

    def __init__(self, team_names: List[str]):
        self.teams: Dict[str, TeamStats] = {name: TeamStats(name=name) for name in team_names}

    def add_result(self, home_team: str, away_team: str, home_score: int, away_score: int):
        if home_team in self.teams and away_team in self.teams:
            self.teams[home_team].update_match(home_score, away_score, is_away=False)
            self.teams[away_team].update_match(away_score, home_score, is_away=True)

    def get_standings(self) -> List[TeamStats]:
        """UEFA standartlarina gore sirali tabloyu dondurur."""
        return sorted(
            self.teams.values(),
            key=lambda t: (
                t.points,
                t.goal_difference,
                t.goals_for,
                t.away_goals,
                t.won,
            ),
            reverse=True,
        )

    def display(self, top_n: Optional[int] = None) -> str:
        standings = self.get_standings()
        if top_n:
            standings = standings[:top_n]

        header = f"{'Sıra':<5}{'Takım':<25}{'O':<4}{'G':<4}{'B':<4}{'M':<4}{'AG':<5}{'YG':<5}{'AV':<5}{'P':<4}"
        lines = [header, "-" * len(header)]
        for i, t in enumerate(standings, 1):
            line = (
                f"{i:<5}{t.name:<25}{t.played:<4}{t.won:<4}{t.drawn:<4}"
                f"{t.lost:<4}{t.goals_for:<5}{t.goals_against:<5}{t.goal_difference:<+5}{t.points:<4}"
            )
            lines.append(line)
        return "\n".join(lines)

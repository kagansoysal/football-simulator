import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from src.database.database import Base


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)  # CL, UEL, ECL
    name = Column(String(100), nullable=False)
    season = Column(String(20), nullable=False, default="2026-27")
    total_rounds = Column(Integer, nullable=False, default=8)
    total_teams = Column(Integer, nullable=False, default=36)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="competition", cascade="all, delete-orphan")
    fixtures = relationship("Fixture", back_populates="competition", cascade="all, delete-orphan")
    simulation_runs = relationship("SimulationRun", back_populates="competition", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False, index=True)
    country = Column(String(50), nullable=True)
    current_elo = Column(Float, nullable=False, default=1500.0)
    
    # Gerçek puan durumu istatistikleri
    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_diff = Column(Integer, default=0)
    points = Column(Integer, default=0)
    rank = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("competition_id", "name", name="uq_competition_team"),
    )

    # Relationships
    competition = relationship("Competition", back_populates="teams")
    simulation_stats = relationship("TeamSimulationStat", back_populates="team", cascade="all, delete-orphan")


class Fixture(Base):
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    round = Column(Integer, nullable=False, index=True)
    home_team = Column(String(100), nullable=False, index=True)
    away_team = Column(String(100), nullable=False, index=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    is_played = Column(Boolean, default=False, nullable=False)
    match_date = Column(String(50), nullable=True)

    # Relationships
    competition = relationship("Competition", back_populates="fixtures")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    sim_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    num_simulations = Column(Integer, default=10000)
    total_matches_simulated = Column(Integer, default=0)
    thresholds = Column(JSON, nullable=True)  # top_8_points, playoff_points, vs.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    competition = relationship("Competition", back_populates="simulation_runs")
    team_stats = relationship("TeamSimulationStat", back_populates="simulation_run", cascade="all, delete-orphan")


class TeamSimulationStat(Base):
    __tablename__ = "team_simulation_stats"

    id = Column(Integer, primary_key=True, index=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    mean_points = Column(Float, nullable=False)
    median_points = Column(Float, nullable=False)
    std_points = Column(Float, nullable=False)
    mean_rank = Column(Float, nullable=False)
    median_rank = Column(Float, nullable=False)
    top_8_prob = Column(Float, nullable=False)
    playoff_prob = Column(Float, nullable=False)
    elimination_prob = Column(Float, nullable=False)
    
    # Sıralama ve puan dağılımları (Histogram / JSON)
    rank_distribution = Column(JSON, nullable=True)  # {1: 0.15, 2: 0.12, ...}
    points_distribution = Column(JSON, nullable=True)

    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="team_stats")
    team = relationship("Team", back_populates="simulation_stats")

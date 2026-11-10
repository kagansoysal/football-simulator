import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.database import Base
from src.database.models import Competition, Team, Fixture

# In-memory SQLite engine for fast, isolated testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all database tables in SQLite for testing."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provides a clean database session per test with rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_competition(db_session):
    """Seed a sample competition, teams, and fixture."""
    comp = Competition(code="CL", name="UEFA Champions League", season="2024-2025")
    db_session.add(comp)
    db_session.flush()

    t1 = Team(competition_id=comp.id, name="Real Madrid", current_elo=1980.0, points=15, goal_diff=10, goals_for=18)
    t2 = Team(competition_id=comp.id, name="Manchester City", current_elo=2010.0, points=16, goal_diff=12, goals_for=20)
    t3 = Team(competition_id=comp.id, name="Galatasaray", current_elo=1650.0, points=10, goal_diff=1, goals_for=11)
    db_session.add_all([t1, t2, t3])
    db_session.flush()

    fix = Fixture(
        competition_id=comp.id,
        round=7,
        home_team="Real Madrid",
        away_team="Manchester City",
        is_played=False,
    )
    db_session.add(fix)
    db_session.commit()
    return comp

from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from src.main import health_check
from src.api.endpoints import (
    get_competitions,
    get_standings,
    get_fixtures,
    calculate_match_odds,
    trigger_simulation,
    get_simulation_status,
)
from src.api.schemas import MatchOddsRequest, SimulationTriggerRequest


def test_health_check_endpoint():
    result = health_check()
    assert result["status"] == "healthy"
    assert "app" in result
    assert result["docs"] == "/docs"


def test_get_competitions_unit(db_session, sample_competition):
    competitions = get_competitions(db=db_session)
    assert len(competitions) >= 1
    assert any(c.code == "CL" for c in competitions)


def test_get_standings_unit_success(db_session, sample_competition):
    standings = get_standings(code="CL", db=db_session)
    assert len(standings) == 3
    # Ordered by points desc
    assert standings[0].name == "Manchester City"
    assert standings[1].name == "Real Madrid"
    assert standings[2].name == "Galatasaray"


def test_get_standings_unit_not_found(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_standings(code="NON_EXISTENT", db=db_session)
    assert exc_info.value.status_code == 404
    assert "Turnuva bulunamadı" in exc_info.value.detail


def test_get_fixtures_unit(db_session, sample_competition):
    fixtures = get_fixtures(code="CL", round_num=7, db=db_session)
    assert len(fixtures) == 1
    assert fixtures[0].round == 7
    assert fixtures[0].home_team == "Real Madrid"
    assert fixtures[0].away_team == "Manchester City"


@patch("src.api.endpoints.AkilOyunuEloFetcher")
def test_calculate_match_odds_unit(mock_fetcher_cls, db_session):
    mock_fetcher = MagicMock()
    mock_fetcher.get_elo.side_effect = lambda team: 1950.0 if "Real" in team else 1750.0
    mock_fetcher_cls.return_value = mock_fetcher

    req = MatchOddsRequest(
        home_team="Real Madrid",
        away_team="Galatasaray",
        home_advantage=75.0,
    )
    result = calculate_match_odds(payload=req, db=db_session)
    assert result.probabilities["home_win"] > result.probabilities["away_win"]
    assert pytest.approx(result.probabilities["home_win"] + result.probabilities["draw"] + result.probabilities["away_win"], abs=1.0) == 100.0
    assert len(result.top_scores) <= 6


@patch("src.worker.tasks.run_simulation_task.delay")
def test_trigger_simulation_unit(mock_task_delay):
    mock_async_result = MagicMock()
    mock_async_result.id = "test-celery-id-1234"
    mock_task_delay.return_value = mock_async_result

    req = SimulationTriggerRequest(competition_code="CL", num_simulations=100)
    response = trigger_simulation(payload=req)

    assert response.task_id == "test-celery-id-1234"
    assert response.status == "PENDING"
    mock_task_delay.assert_called_once_with(competition_code="CL", n_simulations=100)


@patch("celery.result.AsyncResult")
def test_get_simulation_status_unit(mock_async_result_cls):
    mock_instance = MagicMock()
    mock_instance.state = "PROGRESS"
    mock_instance.info = {"status": "Simüle Ediliyor", "progress": 45, "current_step": "Çalışıyor"}
    mock_async_result_cls.return_value = mock_instance

    response = get_simulation_status(task_id="test-celery-id-1234")
    assert response["task_id"] == "test-celery-id-1234"
    assert response["status"] == "PROGRESS"
    assert response["progress"] == 45
    assert response["current_step"] == "Çalışıyor"

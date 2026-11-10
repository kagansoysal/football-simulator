from unittest.mock import patch, MagicMock
from src.worker.tasks import run_simulation_task


@patch("src.worker.tasks.SessionLocal")
@patch("src.worker.tasks.SimulationAnalyzer")
@patch("src.worker.tasks.MonteCarloSimulator")
@patch("os.path.exists", return_value=True)
def test_run_simulation_task(mock_exists, mock_sim_cls, mock_analyzer_cls, mock_session_local):
    """Test Celery simulation task workflow and progress updates with mocks."""
    # Mock Database Session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    mock_comp = MagicMock()
    mock_comp.id = 1
    mock_comp.code = "CL"
    mock_db.query().filter().first.return_value = mock_comp

    mock_team = MagicMock()
    mock_team.name = "Real Madrid"
    mock_team.id = 10
    mock_db.query().filter().all.return_value = [mock_team]

    # Mock Simulator run & save
    mock_sim = MagicMock()
    mock_sim_cls.return_value = mock_sim
    mock_results = MagicMock()
    mock_sim.run.return_value = mock_results

    # Mock Analyzer full analysis
    mock_analyzer = MagicMock()
    mock_analyzer_cls.return_value = mock_analyzer
    mock_analyzer.run_full_analysis.return_value = {
        "qualification_thresholds": {"top8_min_points": 15},
        "team_performances": [
            {
                "team": "Real Madrid",
                "mean_points": 16.5,
                "median_points": 16.0,
                "mean_rank": 4.2,
                "median_rank": 4.0,
                "prob_top8": 0.85,
                "prob_playoff": 0.14,
                "prob_eliminated": 0.01,
            }
        ],
        "team_position_probabilities": {
            "Real Madrid": {"1": 0.2, "2": 0.15}
        }
    }

    # Call the original function directly with a mock task self instance
    task_self = MagicMock()
    raw_task_fn = run_simulation_task.__wrapped__.__func__
    result = raw_task_fn(task_self, competition_code="CL", n_simulations=50)

    assert result["competition_code"] == "CL"
    assert result["simulations"] == 50
    assert "duration_seconds" in result
    assert result["status"] == "COMPLETED"
    assert result["progress"] == 100

    # Verify task state updates
    assert task_self.update_state.call_count >= 3

    # Verify db interaction
    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.close.assert_called()

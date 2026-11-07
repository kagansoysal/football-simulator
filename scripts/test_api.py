import sys
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_get_competitions():
    response = client.get("/api/v1/competitions")
    assert response.status_code == 200
    comps = response.json()
    assert len(comps) == 3
    codes = [c["code"] for c in comps]
    assert "CL" in codes
    assert "UEL" in codes
    assert "ECL" in codes


def test_get_standings():
    response = client.get("/api/v1/competitions/CL/standings")
    assert response.status_code == 200
    standings = response.json()
    assert len(standings) == 36
    # Puan durumunun puana göre sıralı olduğunu kontrol et
    assert standings[0]["points"] >= standings[-1]["points"]


def test_get_simulation_analysis():
    response = client.get("/api/v1/competitions/CL/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["competition_code"] == "CL"
    assert data["num_simulations"] == 10000
    assert len(data["teams"]) == 36
    assert "top_8_threshold" in data["thresholds"]


def test_calculate_match_odds():
    payload = {
        "home_team": "Galatasaray",
        "away_team": "Real Madrid",
        "home_advantage": 75.0
    }
    response = client.post("/api/v1/match/odds", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "probabilities" in data
    assert "home_win" in data["probabilities"]
    assert "draw" in data["probabilities"]
    assert "away_win" in data["probabilities"]
    assert len(data["top_scores"]) > 0


def test_trigger_and_status_simulation():
    payload = {
        "competition_code": "CL",
        "num_simulations": 100
    }
    response = client.post("/api/v1/simulations/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"
    task_id = data["task_id"]

    # Durum sorgulama testi
    status_resp = client.get(f"/api/v1/simulations/status/{task_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["task_id"] == task_id
    assert status_data["status"] in ["PENDING", "STARTED", "PROGRESS", "SUCCESS"]


if __name__ == "__main__":
    print("[*] API Testleri Çalıştırılıyor...")
    test_health_check()
    print("  -> test_health_check: [OK]")
    test_get_competitions()
    print("  -> test_get_competitions: [OK]")
    test_get_standings()
    print("  -> test_get_standings: [OK]")
    test_get_simulation_analysis()
    print("  -> test_get_simulation_analysis: [OK]")
    test_calculate_match_odds()
    print("  -> test_calculate_match_odds: [OK]")
    test_trigger_and_status_simulation()
    print("  -> test_trigger_and_status_simulation: [OK]")
    print("\n[TEBRİKLER] Tüm API testleri başarıyla geçti!")



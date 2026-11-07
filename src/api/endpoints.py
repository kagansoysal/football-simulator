from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.database.database import get_db
from src.database.models import Competition, Team, Fixture, SimulationRun, TeamSimulationStat
from src.api.schemas import (
    CompetitionOut, TeamStandingsOut, FixtureOut,
    SimulationSummaryOut, TeamSimulationStatOut,
    MatchOddsRequest, MatchOddsResponse, MatchScoreProbability,
    SimulationTriggerRequest, SimulationTriggerResponse, SimulationTaskStatusResponse
)
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.models.match_engine import MatchEngine

router = APIRouter(prefix="/api/v1", tags=["Football Simulator"])


# -------------------------------------------------------------
# 1. Turnuvalar
# -------------------------------------------------------------
@router.get("/competitions", response_model=List[CompetitionOut], summary="Kayıtlı Turnuvaları Listele")
def get_competitions(db: Session = Depends(get_db)):
    """Kayıtlı olan tüm turnuvaları (CL, UEL, ECL) listeler."""
    return db.query(Competition).all()


# -------------------------------------------------------------
# 2. Güncel Puan Durumu
# -------------------------------------------------------------
@router.get("/competitions/{code}/standings", response_model=List[TeamStandingsOut], summary="Gerçek Puan Durumunu Getir")
def get_standings(code: str, db: Session = Depends(get_db)):
    """
    Belirtilen turnuvanın (CL, UEL, ECL) gerçekte oynanmış maçlara göre
    oluşan güncel 36 takımlı puan durumunu getirir.
    """
    comp = db.query(Competition).filter(Competition.code == code.upper()).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Turnuva bulunamadı: {code}")

    teams = db.query(Team).filter(Team.competition_id == comp.id).order_by(
        desc(Team.points),
        desc(Team.goal_diff),
        desc(Team.goals_for)
    ).all()
    return teams


# -------------------------------------------------------------
# 3. Fikstür ve Maç Sonuçları
# -------------------------------------------------------------
@router.get("/competitions/{code}/fixtures", response_model=List[FixtureOut], summary="Turnuva Fikstürünü Getir")
def get_fixtures(
    code: str,
    round_num: Optional[int] = Query(None, alias="round", description="Sadece belirli bir haftayı filtreler (Örn: 4)"),
    only_unplayed: bool = Query(False, description="Sadece henüz oynanmamış maçları getirir"),
    db: Session = Depends(get_db)
):
    """Fikstürü haftalık ve oynanma durumuna göre filtreleyerek listeler."""
    comp = db.query(Competition).filter(Competition.code == code.upper()).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Turnuva bulunamadı: {code}")

    query = db.query(Fixture).filter(Fixture.competition_id == comp.id)
    if round_num is not None:
        query = query.filter(Fixture.round == round_num)
    if only_unplayed:
        query = query.filter(Fixture.is_played == False)

    return query.order_by(Fixture.round, Fixture.id).all()


# -------------------------------------------------------------
# 4. 10.000 Simülasyon Analizi & Barajlar
# -------------------------------------------------------------
@router.get("/competitions/{code}/analysis", response_model=SimulationSummaryOut, summary="Simülasyon Analizini Getir")
def get_simulation_analysis(code: str, db: Session = Depends(get_db)):
    """
    En son çalıştırılan 10.000 Monte Carlo simülasyonunun sonuçlarını,
    ilk 8 ve play-off baraj puanlarını ve takım olasılıklarını döndürür.
    """
    comp = db.query(Competition).filter(Competition.code == code.upper()).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Turnuva bulunamadı: {code}")

    # En son simülasyon koşusunu bul
    sim_run = db.query(SimulationRun).filter(
        SimulationRun.competition_id == comp.id
    ).order_by(desc(SimulationRun.created_at)).first()

    if not sim_run:
        raise HTTPException(status_code=404, detail=f"{code} için henüz simülasyon analizi kaydedilmemiş.")

    stats_rows = db.query(TeamSimulationStat, Team).join(
        Team, TeamSimulationStat.team_id == Team.id
    ).filter(
        TeamSimulationStat.simulation_run_id == sim_run.id
    ).order_by(
        desc(TeamSimulationStat.mean_points)
    ).all()

    team_stats_out = []
    for stat, team in stats_rows:
        team_stats_out.append(TeamSimulationStatOut(
            team_name=team.name,
            current_elo=team.current_elo,
            current_points=team.points,
            mean_points=stat.mean_points,
            median_points=stat.median_points,
            std_points=stat.std_points,
            mean_rank=stat.mean_rank,
            median_rank=stat.median_rank,
            top_8_prob=stat.top_8_prob,
            playoff_prob=stat.playoff_prob,
            elimination_prob=stat.elimination_prob,
            rank_distribution=stat.rank_distribution,
            points_distribution=stat.points_distribution
        ))

    return SimulationSummaryOut(
        competition_code=comp.code,
        competition_name=comp.name,
        sim_date=sim_run.sim_date,
        num_simulations=sim_run.num_simulations,
        thresholds=sim_run.thresholds,
        teams=team_stats_out
    )


# -------------------------------------------------------------
# 5. İki Takım Arası Maç Tahmin ve Skor Olasılıkları Motoru
# -------------------------------------------------------------
@router.post("/match/odds", response_model=MatchOddsResponse, summary="Maç Oran ve Olasılık Hesaplayıcı")
def calculate_match_odds(payload: MatchOddsRequest, db: Session = Depends(get_db)):
    """
    Dixon-Coles ve Poisson olasılık motorunu kullanarak girilen iki takımın
    xG değerlerini, 1-X-2 yüzdelerini ve en muhtemel skor dağılımlarını hesaplar.
    """
    elo_fetcher = AkilOyunuEloFetcher()
    home_elo = elo_fetcher.get_elo(payload.home_team)
    away_elo = elo_fetcher.get_elo(payload.away_team)

    engine = MatchEngine(home_advantage=payload.home_advantage)
    probs = engine.calculate_match_probabilities(home_elo, away_elo)

    # En yüksek olasılıklı 6 skoru sırala
    scored_list = []
    matrix = probs.score_matrix
    max_g = matrix.shape[0]
    for h_g in range(max_g):
        for a_g in range(max_g):
            scored_list.append({"score": f"{h_g}-{a_g}", "prob": matrix[h_g, a_g]})

    scored_list.sort(key=lambda x: x["prob"], reverse=True)

    top_scores = [
        MatchScoreProbability(score=s["score"], probability=round(float(s["prob"]) * 100, 2))
        for s in scored_list[:6]
    ]

    return MatchOddsResponse(
        home_team=payload.home_team,
        away_team=payload.away_team,
        home_elo=home_elo,
        away_elo=away_elo,
        effective_home_elo=home_elo + payload.home_advantage,
        home_xg=round(float(probs.expected_home_goals), 2),
        away_xg=round(float(probs.expected_away_goals), 2),
        probabilities={
            "home_win": round(float(probs.home_win) * 100, 2),
            "draw": round(float(probs.draw) * 100, 2),
            "away_win": round(float(probs.away_win) * 100, 2),
        },
        top_scores=top_scores
    )


# -------------------------------------------------------------
# 6. Asenkron Celery Simülasyon Tetikleme & Durum Sorgulama
# -------------------------------------------------------------
@router.post("/simulations/run", response_model=SimulationTriggerResponse, summary="Asenkron Simülasyon Başlat (Celery Worker)")
def trigger_simulation(payload: SimulationTriggerRequest):
    """
    10.000 Monte Carlo simülasyonunu arka plandaki Celery Worker havuzuna asenkron olarak iletir.
    İstek beklemeden hemen bir 'task_id' döndürür.
    """
    from src.worker.tasks import run_simulation_task

    comp_code = payload.competition_code.upper()
    if comp_code not in ["CL", "UEL", "EL", "ECL", "UECL"]:
        raise HTTPException(status_code=400, detail=f"Desteklenmeyen turnuva kodu: {payload.competition_code}. (CL, UEL veya ECL olmalıdır)")

    # Celery kuyruğuna işi fırlat
    async_result = run_simulation_task.delay(
        competition_code=comp_code,
        n_simulations=payload.num_simulations
    )

    return SimulationTriggerResponse(
        task_id=async_result.id,
        competition_code=comp_code,
        num_simulations=payload.num_simulations,
        status="PENDING",
        message="Simülasyon görevi başarıyla Celery kuyruğuna eklendi. Durumu /simulations/status/{task_id} adresinden takip edebilirsiniz."
    )


@router.get("/simulations/status/{task_id}", response_model=SimulationTaskStatusResponse, summary="Simülasyon Görevinin Durumunu Sorgula")
def get_simulation_status(task_id: str):
    """
    Celery görev kuyruğundaki simülasyonun anlık durumunu, ilerleme yüzdesini (%20, %80 vb.)
    ve bittiyse sonuç özetini döndürür.
    """
    from celery.result import AsyncResult
    from src.worker.celery_app import celery_app

    async_result = AsyncResult(task_id, app=celery_app)

    state = async_result.state
    response = {
        "task_id": task_id,
        "status": state,
        "progress": 0,
        "current_step": None,
        "result": None
    }

    if state == "PENDING":
        response["current_step"] = "Kuyrukta worker bekleniyor..."
    elif state == "PROGRESS":
        info = async_result.info or {}
        response["progress"] = info.get("progress", 0)
        response["current_step"] = info.get("current_step", "")
    elif state == "SUCCESS":
        response["progress"] = 100
        response["current_step"] = "Simülasyon başarıyla tamamlandı!"
        response["result"] = async_result.result
    elif state == "FAILURE":
        response["progress"] = 0
        response["current_step"] = f"Hata: {str(async_result.info)}"

    return response


import os
import json
import logging
from datetime import datetime
from pathlib import Path

from src.worker.celery_app import celery_app
from src.core.storage import get_project_root, get_date_dir, resolve_timestamp
from src.simulator.monte_carlo_engine import MonteCarloSimulator
from src.analyzer.simulator_analyzer import SimulationAnalyzer
from src.database.database import SessionLocal
from src.database.models import Competition, Team, SimulationRun, TeamSimulationStat

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.worker.tasks.run_simulation_task")
def run_simulation_task(self, competition_code: str = "CL", n_simulations: int = 10000):
    """
    Arka planda Celery Worker uzerinde calisan 10.000 Monte Carlo Sezon Simulasyonu gorevi.
    Gorev adimlarini Celery state uzerinden canli gunceller (PROGRESS).
    """
    comp_code = competition_code.upper()
    comp_map = {
        "CL": ("cl", "UEFA Champions League"),
        "UEL": ("uel", "UEFA Europa League"),
        "EL": ("uel", "UEFA Europa League"),
        "ECL": ("ecl", "UEFA Conference League"),
        "UECL": ("ecl", "UEFA Conference League"),
    }
    comp_lower, comp_name = comp_map.get(comp_code, ("cl", "UEFA Champions League"))
    current_ts = resolve_timestamp()
    project_root = get_project_root()

    # 1. Adım: Başlangıç Durumu
    self.update_state(state="PROGRESS", meta={"status": "Başlatılıyor", "progress": 5, "current_step": "Dosyalar Hazırlanıyor"})

    league_file = str(project_root / "data" / "leagues" / f"{comp_lower}_2026_27.json")
    if not os.path.exists(league_file):
        raise FileNotFoundError(f"Lig fikstür dosyası bulunamadı: {league_file}")

    # 2. Adım: Monte Carlo Simülasyonu
    self.update_state(state="PROGRESS", meta={"status": "Simüle Ediliyor", "progress": 20, "current_step": f"{n_simulations:,} Sezon Simülasyonu Çalıştırılıyor"})
    
    start_time = datetime.now()
    simulator = MonteCarloSimulator(
        league_file=league_file,
        k_factor=30.0,
        home_advantage=75.0,
        as_of_date=current_ts
    )
    results = simulator.run(n_simulations=n_simulations)
    sim_duration = (datetime.now() - start_time).total_seconds()

    # Sonuçları diske kaydet
    self.update_state(state="PROGRESS", meta={"status": "Kaydediliyor", "progress": 65, "current_step": "Simülasyon Sonuçları Arşivleniyor"})
    sim_base_dir = project_root / "data" / "simulations"
    dated_sim_dir = get_date_dir(sim_base_dir, current_ts)
    dated_sim_file = dated_sim_dir / f"mc_{comp_lower}_{n_simulations}_results.pkl.gz"
    latest_sim_file = sim_base_dir / f"mc_10000_results_{comp_lower}.pkl.gz"

    results.save(str(dated_sim_file))
    results.save(str(latest_sim_file))

    # 3. Adım: İstatistiksel Analizler
    self.update_state(state="PROGRESS", meta={"status": "Analiz Ediliyor", "progress": 80, "current_step": "Baraj Puanları ve Olasılıklar Hesaplanıyor"})
    analyzer = SimulationAnalyzer(results)
    full_data = analyzer.run_full_analysis()

    analysis_base_dir = project_root / "data" / "analysis"
    dated_analysis_dir = get_date_dir(analysis_base_dir, current_ts)
    dated_analysis_json = dated_analysis_dir / f"simulation_analysis_{comp_lower}_2026_27.json"
    latest_analysis_json = analysis_base_dir / f"simulation_analysis_{comp_lower}_2026_27.json"

    analyzer.save_analysis(str(dated_analysis_json))
    analyzer.save_analysis(str(latest_analysis_json))

    # 4. Adım: PostgreSQL Veritabanını Güncelle
    self.update_state(state="PROGRESS", meta={"status": "Veritabanına Yazılıyor", "progress": 90, "current_step": "PostgreSQL Tabloları Güncelleniyor"})
    db = SessionLocal()
    try:
        comp = db.query(Competition).filter(Competition.code == comp_code).first()
        if comp:
            sim_date = datetime.now().strftime("%Y-%m-%d")
            sim_run = SimulationRun(
                competition_id=comp.id,
                sim_date=sim_date,
                num_simulations=n_simulations,
                thresholds=full_data.get("qualification_thresholds", {})
            )
            db.add(sim_run)
            db.commit()
            db.refresh(sim_run)

            team_db_map = {t.name: t.id for t in db.query(Team).filter(Team.competition_id == comp.id).all()}
            pos_probs = full_data.get("team_position_probabilities", {})

            for t_stats in full_data.get("team_performances", []):
                t_name = t_stats.get("team")
                team_id = team_db_map.get(t_name)
                if team_id:
                    stat_row = TeamSimulationStat(
                        simulation_run_id=sim_run.id,
                        team_id=team_id,
                        mean_points=t_stats.get("mean_points", 0.0),
                        median_points=t_stats.get("median_points", 0.0),
                        std_points=0.0,
                        mean_rank=t_stats.get("mean_rank", 0.0),
                        median_rank=t_stats.get("median_rank", 0.0),
                        top_8_prob=t_stats.get("prob_top8", 0.0),
                        playoff_prob=t_stats.get("prob_playoff", 0.0),
                        elimination_prob=t_stats.get("prob_eliminated", 0.0),
                        rank_distribution=pos_probs.get(t_name, {}),
                        points_distribution={}
                    )
                    db.add(stat_row)
            db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Simülasyon veritabanına kaydedilirken hata: {db_err}")
    finally:
        db.close()

    # 5. Adım: Tamamlandı
    return {
        "competition_code": comp_code,
        "competition_name": comp_name,
        "simulations": n_simulations,
        "duration_seconds": round(sim_duration, 2),
        "thresholds": full_data.get("qualification_thresholds", {}),
        "status": "COMPLETED",
        "progress": 100
    }

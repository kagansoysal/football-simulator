"""
Mevcut diskteki JSON verilerini (Elo, ligler, fikstür, oynanmış maçlar ve simülasyon analizleri)
PostgreSQL veritabanına aktaran senkronizasyon scripti.
"""
import sys
import json
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.database.database import SessionLocal, engine, Base
from src.database.models import Competition, Team, Fixture, SimulationRun, TeamSimulationStat
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.data_loader.league_loader import LeagueLoader
from src.core.models import LeagueTable


def sync_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("[*] Veritabanı senkronizasyonu başlatılıyor...")
        
        # 1. Elo Nesnesini Başlat
        elo_fetcher = AkilOyunuEloFetcher()

        competitions_data = [
            {"code": "CL", "name": "UEFA Champions League", "rounds": 8, "teams": 36, "file": "data/leagues/cl_2026_27.json"},
            {"code": "UEL", "name": "UEFA Europa League", "rounds": 8, "teams": 36, "file": "data/leagues/uel_2026_27.json"},
            {"code": "ECL", "name": "UEFA Conference League", "rounds": 6, "teams": 36, "file": "data/leagues/ecl_2026_27.json"},
        ]

        for comp_meta in competitions_data:
            code = comp_meta["code"]
            print(f"\n--- {comp_meta['name']} ({code}) İşleniyor ---")

            # A) Turnuvayı Ekle veya Güncelle
            comp = db.query(Competition).filter(Competition.code == code).first()
            if not comp:
                comp = Competition(
                    code=code,
                    name=comp_meta["name"],
                    season="2026-27",
                    total_rounds=comp_meta["rounds"],
                    total_teams=comp_meta["teams"]
                )
                db.add(comp)
                db.commit()
                db.refresh(comp)

            # B) Lig Fikstürünü LeagueLoader İle Yükle
            league_path = str(project_root / comp_meta["file"])
            loader = LeagueLoader(league_path)
            fixtures = loader.fixtures
            teams_set = loader.teams

            # Oynanmış maçlardan mevcut puan durumunu hesapla
            table = LeagueTable(team_names=teams_set)
            for m in loader.get_played_fixtures():
                table.add_result(m.home_team, m.away_team, m.home_score, m.away_score)

            standings = table.get_standings()
            standings_dict = {
                t.name: {
                    "P": t.played, "W": t.won, "D": t.drawn, "L": t.lost,
                    "GF": t.goals_for, "GA": t.goals_against, "GD": t.goal_difference,
                    "Pts": t.points, "rank": idx + 1
                }
                for idx, t in enumerate(standings)
            }

            # Takımları kaydet / güncelle
            for team_name in sorted(teams_set):
                team = db.query(Team).filter(
                    Team.competition_id == comp.id,
                    Team.name == team_name
                ).first()

                current_elo = elo_fetcher.get_elo(team_name)
                stats = standings_dict.get(team_name, {})

                if not team:
                    team = Team(
                        competition_id=comp.id,
                        name=team_name,
                        current_elo=current_elo,
                        played=stats.get("P", 0),
                        won=stats.get("W", 0),
                        drawn=stats.get("D", 0),
                        lost=stats.get("L", 0),
                        goals_for=stats.get("GF", 0),
                        goals_against=stats.get("GA", 0),
                        goal_diff=stats.get("GD", 0),
                        points=stats.get("Pts", 0),
                        rank=stats.get("rank", None)
                    )
                    db.add(team)
                else:
                    team.current_elo = current_elo
                    team.played = stats.get("P", team.played)
                    team.won = stats.get("W", team.won)
                    team.drawn = stats.get("D", team.drawn)
                    team.lost = stats.get("L", team.lost)
                    team.goals_for = stats.get("GF", team.goals_for)
                    team.goals_against = stats.get("GA", team.goals_against)
                    team.goal_diff = stats.get("GD", team.goal_diff)
                    team.points = stats.get("Pts", team.points)
                    team.rank = stats.get("rank", team.rank)

            db.commit()

            # C) Maçları / Fikstürü Kaydet
            db.query(Fixture).filter(Fixture.competition_id == comp.id).delete()
            for m in fixtures:
                fixture_row = Fixture(
                    competition_id=comp.id,
                    round=m.round,
                    home_team=m.home_team,
                    away_team=m.away_team,
                    home_score=m.home_score,
                    away_score=m.away_score,
                    is_played=m.is_played
                )
                db.add(fixture_row)
            db.commit()
            print(f"  -> {len(teams_set)} Takım ve {len(fixtures)} Fikstür maçı kaydedildi.")

            # D) Varsa Simülasyon Analiz Dosyasını Aktar
            analysis_file = project_root / f"data/analysis/simulation_analysis_{code.lower()}_2026_27.json"
            if analysis_file.exists():
                with open(analysis_file, "r", encoding="utf-8") as f:
                    analysis_data = json.load(f)

                sim_date = "2026-10-31"
                num_sims = analysis_data.get("meta", {}).get("n_simulations", 10000)
                thresholds = analysis_data.get("qualification_thresholds", {})

                # Sim run kaydı
                sim_run = db.query(SimulationRun).filter(
                    SimulationRun.competition_id == comp.id,
                    SimulationRun.sim_date == sim_date
                ).first()

                if not sim_run:
                    sim_run = SimulationRun(
                        competition_id=comp.id,
                        sim_date=sim_date,
                        num_simulations=num_sims,
                        thresholds=thresholds
                    )
                    db.add(sim_run)
                    db.commit()
                    db.refresh(sim_run)
                else:
                    sim_run.thresholds = thresholds
                    db.commit()

                # Takım simülasyon istatistiklerini ekle
                db.query(TeamSimulationStat).filter(
                    TeamSimulationStat.simulation_run_id == sim_run.id
                ).delete()

                team_db_map = {t.name: t.id for t in db.query(Team).filter(Team.competition_id == comp.id).all()}
                pos_probs = analysis_data.get("team_position_probabilities", {})

                for t_stats in analysis_data.get("team_performances", []):
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
                print(f"  -> 10.000 simülasyon analiz metrikleri veritabanına aktarıldı.")

        print("\n[OK] PostgreSQL senkronizasyonu eksiksiz tamamlandı!")

    except Exception as e:
        db.rollback()
        print(f"[HATA] Senkronizasyon sırasında hata oluştu: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    sync_database()

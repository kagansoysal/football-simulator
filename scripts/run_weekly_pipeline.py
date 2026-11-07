"""
Uçtan Uca Haftalık Otomasyon ve Raporlama Motoru (Pipeline)
Her adımı hem terminale yazar hem de 'logs/pipeline_YYYY-MM-DD_HH-MM.log' dosyasına loglar.
Bir hata olduğunda hatanın detayını, stack trace'ini ve hangi adımda takıldığını açıkça kaydeder.
"""
import sys
import os
import io
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path

# Proje ana dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.storage import get_date_dir, resolve_timestamp, get_now_timestamp
from src.data_loader.fixture_fetcher import FixtureFetcher
from src.data_loader.elo_fetcher import AkilOyunuEloFetcher
from src.simulator.monte_carlo_engine import MonteCarloSimulator
from src.analyzer.simulator_analyzer import SimulationAnalyzer
import scripts.show_simulation_analysis as analysis_viewer


def setup_logger(log_file: Path) -> logging.Logger:
    """Hem dosyaya hem konsola aynı anda formatlı log basan logger kurar."""
    logger = logging.getLogger("WeeklyPipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Dosya yazıcısı (UTF-8)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)

    # Konsol yazıcısı
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def run_pipeline(
    competition_code: str = "CL",
    date_str: str = None,
    open_notepad: bool = False,
    n_simulations: int = 10000,
    skip_fetch: bool = False,
):
    current_ts = resolve_timestamp(date_str)
    comp_upper = competition_code.upper()
    if comp_upper in ["ECL", "UECL"]:
        comp_lower = "ecl"
        comp_name = "UEFA Conference League"
        api_comp = "UECL"
    elif comp_upper in ["EL", "UEL"]:
        comp_lower = "uel"
        comp_name = "UEFA Europa League"
        api_comp = "UEL"
    else:
        comp_lower = "cl"
        comp_name = "UEFA Champions League"
        api_comp = "CL"

    # Log klasörünü ve log dosyasını hazırla
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"pipeline_{comp_lower}_{current_ts}.log"
    latest_log_file = logs_dir / f"latest_pipeline_{comp_lower}.log"

    logger = setup_logger(log_file)

    logger.info("=" * 80)
    logger.info(f"   {comp_name.upper()} - SİMÜLASYON VE ANALİZ İŞ HATTI (ZAMAN: {current_ts})")
    if skip_fetch:
        logger.info("   [BİLGİ] API Veri Çekme Adımları Atlandı (Mevcut Yerel Verilerle Çalışılıyor)")
    logger.info(f"   Log Dosyası: {log_file}")
    logger.info("=" * 80)

    league_file = str(PROJECT_ROOT / "data" / "leagues" / f"{comp_lower}_2026_27.json")

    try:
        if not skip_fetch:
            # 1. ADIM: Fikstürü Senkronize Et
            logger.info("\n>>> [ADIM 1/5] Fikstür ve Oynanmış Skor Senkronizasyonu Başlıyor...")
            try:
                fixture_fetcher = FixtureFetcher()
                league_file = fixture_fetcher.sync_league(competition_code=api_comp, season_year=2026, stage="LEAGUE_STAGE")
                logger.info(f"  [OK] Fikstür ve oynanmış gerçek skorlar başarıyla güncellendi: {league_file}")
            except Exception as e:
                logger.warning(f"  [UYARI] API'den fikstür çekilirken hata oluştu: {e}")
                logger.warning("  [BİLGİ] Mevcut yerel lig dosyası kullanılacak.")

            # 2. ADIM: Güncel Elo Puanlarını Çek
            logger.info("\n>>> [ADIM 2/5] AkilOyunu Kulüp Elo Puanları Çekiliyor...")
            try:
                elo_fetcher = AkilOyunuEloFetcher(as_of_date=current_ts)
                elo_df = elo_fetcher.fetch_data(target_date=current_ts, force_refresh=True)
                logger.info(f"  [OK] Toplam {len(elo_df)} kulübün güncel Elo puanı çekildi ve arşivlendi.")
            except Exception as e:
                logger.warning(f"  [UYARI] API'den Elo çekilirken hata oluştu: {e}")
                logger.warning("  [BİLGİ] Mevcut önbellekteki Elo verisi kullanılacak.")
        else:
            logger.info("\n>>> [BİLGİ] 1. ve 2. Adımlar (API veri çekme) atlandı. Mevcut yerel veritabanı kullanılıyor.")

        # 3. ADIM: Monte Carlo Sezon Simülasyonu
        logger.info(f"\n>>> [ADIM 3/5] {n_simulations:,} Adet Sezon Simülasyonu Başlatılıyor...")
        start_time = datetime.now()
        simulator = MonteCarloSimulator(
            league_file=league_file, k_factor=30.0, home_advantage=75.0, as_of_date=current_ts
        )
        results = simulator.run(n_simulations=n_simulations)
        sim_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"  [OK] {n_simulations:,} simülasyon {sim_duration:.2f} saniyede tamamlandı.")

        # Simülasyonu kaydet
        sim_base_dir = PROJECT_ROOT / "data" / "simulations"
        dated_sim_dir = get_date_dir(sim_base_dir, current_ts)
        dated_sim_file = dated_sim_dir / f"mc_{comp_lower}_{n_simulations}_results.pkl.gz"
        latest_sim_file = sim_base_dir / f"mc_10000_results_{comp_lower}.pkl.gz"

        results.save(str(dated_sim_file))
        results.save(str(latest_sim_file))
        logger.info(f"  [OK] Simülasyon verisi arşivlendi: {dated_sim_file}")

        # 4. ADIM: İstatistiksel Analizleri Hesapla ve Kaydet
        logger.info("\n>>> [ADIM 4/5] İstatistiksel Analizler ve Olasılık Matrisleri Hesaplanıyor...")
        analyzer = SimulationAnalyzer(results)
        full_data = analyzer.run_full_analysis()

        analysis_base_dir = PROJECT_ROOT / "data" / "analysis"
        dated_analysis_dir = get_date_dir(analysis_base_dir, current_ts)
        dated_analysis_json = dated_analysis_dir / f"simulation_analysis_{comp_lower}_2026_27.json"
        latest_analysis_json = analysis_base_dir / f"simulation_analysis_{comp_lower}_2026_27.json"

        analyzer.save_analysis(str(dated_analysis_json))
        analyzer.save_analysis(str(latest_analysis_json))
        logger.info(f"  [OK] Analiz JSON dosyası kaydedildi: {dated_analysis_json}")

        # 5. ADIM: Not Defteri Raporu Oluştur (.txt)
        logger.info("\n>>> [ADIM 5/5] Not Defteri Raporu Hazırlanıyor...")
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_file = reports_dir / f"rapor_{comp_lower}_{current_ts}.txt"

        output_buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        try:
            now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            print("=" * 115)
            print(f"       {comp_name.upper()} 2026-27 - HAFTALIK SİMÜLASYON VE ANALİZ RAPORU")
            print(f"       Rapor Zamanı: {now_str} | Simülasyon Sayısı: {n_simulations:,}")
            print("=" * 115)
            print("\n")

            analysis_viewer.print_team_performances(full_data["team_performances"])
            print("\n\n")

            analysis_viewer.print_thresholds(full_data["qualification_thresholds"], comp_title=comp_name)
            print("\n\n")

            analysis_viewer.print_points_to_outcome(full_data["points_to_outcome"])
            print("\n\n")

            # Öne çıkan takımlar (Turnuvaya göre)
            if comp_lower == "ecl":
                highlight_teams = ["Trabzonspor", "Atalanta", "Ajax", "Brighton", "Monaco"]
            elif comp_lower == "uel":
                highlight_teams = ["Beşiktaş", "Benfica", "Juventus", "Lyon"]
            else:
                highlight_teams = ["Galatasaray", "Fenerbahçe", "Real Madrid", "Paris SG", "Bayern", "Man City"]

            print("=" * 80)
            print("                 ÖNE ÇIKAN TAKIMLARIN SIRALAMA DAĞILIMLARI")
            print("=" * 80)
            for t_name, t_data in full_data["team_position_probabilities"].items():
                if any(h.lower() in t_name.lower() for h in highlight_teams):
                    analysis_viewer.print_team_position_detail(t_name, t_data)
                    print("\n")

            print("=" * 115)
            print(f" RAPOR SONU - Football Simulator 2026-27 ({comp_name})")
            print("=" * 115)
        finally:
            sys.stdout = old_stdout

        report_content = output_buffer.getvalue()
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"  [OK] Not Defteri raporu yazıldı: {report_file}")
        logger.info("=" * 80)
        logger.info(" [TEBRİKLER] TÜM İŞ HATTI BAŞARIYLA VE EKSİKSİZ TAMAMLANDI!")
        logger.info("=" * 80)

        # En güncel log dosyasına da bir kopyasını yaz
        try:
            with open(log_file, "r", encoding="utf-8") as lf, open(latest_log_file, "w", encoding="utf-8") as llf:
                llf.write(lf.read())
        except Exception:
            pass

        if open_notepad:
            try:
                os.system(f'notepad.exe "{report_file}"')
            except Exception:
                pass

        return str(report_file)

    except Exception as fatal_err:
        logger.error("\n" + "!" * 80)
        logger.error(f"[KRİTİK HATA] İş hattı çalışırken beklenmeyen bir hata oluştu: {fatal_err}")
        logger.error("HATA AYRINTISI VE İZİ (STACK TRACE):")
        logger.error(traceback.format_exc())
        logger.error("!" * 80)

        # En güncel log dosyasına da hata durumunu yaz
        try:
            with open(log_file, "r", encoding="utf-8") as lf, open(latest_log_file, "w", encoding="utf-8") as llf:
                llf.write(lf.read())
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Haftalık Otomatik Simülasyon ve Raporlama Pipeline'ı (Loglamalı)")
    parser.add_argument("-c", "--competition", default="CL", help="Turnuva kodu (CL, UEL veya ECL, varsayılan: CL)")
    parser.add_argument("-d", "--date", type=str, default=None, help="İşlem zaman damgası (YYYY-MM-DD_HH-MM)")
    parser.add_argument("-n", "--simulations", type=int, default=10000, help="Simülasyon sayısı (varsayılan 10000)")
    parser.add_argument("--notepad", action="store_true", help="İşlem bittiğinde oluşturulan raporu Not Defteri ile aç")
    parser.add_argument("--skip-fetch", action="store_true", help="API'den veri çekme adımlarını atlayıp doğrudan 3. adımdan (simülasyondan) başla")
    args = parser.parse_args()

    run_pipeline(
        competition_code=args.competition,
        date_str=args.date,
        open_notepad=args.notepad,
        n_simulations=args.simulations,
        skip_fetch=args.skip_fetch,
    )

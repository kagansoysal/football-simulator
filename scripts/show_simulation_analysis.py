"""
Monte Carlo Simulasyon Analiz ve Raporlama Scripti
10.000 simulasyonun sonuclarini matematiksel olarak analiz eder,
JSON olarak kaydeder ve terminalde zengin tablolar halinde sunar.
"""
import sys
import os
import json
import argparse
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.simulator.monte_carlo_engine import SimulationResults
from src.analyzer.simulator_analyzer import SimulationAnalyzer
from src.core.storage import get_now_timestamp, get_date_dir, list_available_dates, find_matching_date_dir, resolve_timestamp

BASE_ANALYSIS_DIR = Path(__file__).resolve().parents[1] / "data" / "analysis"
BASE_SIM_DIR = Path(__file__).resolve().parents[1] / "data" / "simulations"

LATEST_SIM_FILE = BASE_SIM_DIR / "mc_10000_results.pkl.gz"
LATEST_ANALYSIS_JSON = BASE_ANALYSIS_DIR / "simulation_analysis_cl_2026_27.json"


def print_team_performances(performances):
    print("=" * 115)
    print("                      TAKIM BAZLI GENEL PERFORMANS TABLOSU (10.000 SİMÜLASYON)")
    print("=" * 115)
    header = (
        f"{'Sıra':<5}{'Takım':<22}{'Ort.P':<7}{'Med.P':<7}"
        f"{'Ort.G':<7}{'Ort.B':<7}{'Ort.M':<7}"
        f"{'Ort.AG':<8}{'Ort.YG':<8}{'Ort.AV':<8}{'Med.AV':<8}"
        f"{'Top 8(%)':<10}{'Playoff(%)':<12}"
    )
    print(header)
    print("-" * 115)

    for i, t in enumerate(performances, 1):
        print(
            f"{i:<5}{t['team']:<22}"
            f"{t['mean_points']:<7.2f}{t['median_points']:<7.1f}"
            f"{t['mean_wins']:<7.2f}{t['mean_draws']:<7.2f}{t['mean_losses']:<7.2f}"
            f"{t['mean_gf']:<8.2f}{t['mean_ga']:<8.2f}{t['mean_gd']:<+8.2f}{t['median_gd']:<+8.1f}"
            f"%{t['prob_top8']:<9.1f}%{t['prob_playoff']:<11.1f}"
        )
    print("=" * 115)


def print_thresholds(thresholds, comp_title: str = "AVRUPA KUPALARI"):
    print("\n" + "=" * 85)
    print(f"           {comp_title.upper()} BARAJ PUANI VE AVERAJ ANALİZİ (10.000 SİMÜLASYON)")
    print("=" * 85)

    t8 = thresholds["top_8_threshold"]
    print(f"\n>>> 1. İLK 8 BARAJI (Son 16 Turuna Doğrudan Katılım - 8. Sıra):")
    print(f"  * Ortalama / Beklenen Eşik : {t8['mean_points']:.2f} Puan (Medyan: {t8['median_points']:.0f} Puan, Averaj: {t8['mean_gd']:+.1f})")
    print(f"  * %99 Kesin Garanti Barajı : {t8['guaranteed_points_99pct']} Puan (Bu puana ulaşan neredeyse kesin ilk 8'de)")
    print(f"  * %90 Güvenli Baraj       : {t8['safe_points_90pct']} Puan")
    print(f"  * En Şanslı / Alt Baraj    : {t8['minimum_possible_points']} Puan (Simülasyonlardaki en düşük 8. sıra puanı)")
    print(f"  * Puan Gerçekleşme Dağılımı:")
    for pt, pct in sorted(t8["distribution"].items()):
        bar = "#" * int(pct * 40)
        print(f"      {pt:>2} Puan: %{pct*100:<5.1f} {bar}")

    t24 = thresholds["top_24_threshold"]
    print(f"\n>>> 2. İLK 24 BARAJI (Play-off Turuna Katılım - 24. Sıra):")
    print(f"  * Ortalama / Beklenen Eşik : {t24['mean_points']:.2f} Puan (Medyan: {t24['median_points']:.0f} Puan, Averaj: {t24['mean_gd']:+.1f})")
    print(f"  * %99 Kesin Garanti Barajı : {t24['guaranteed_points_99pct']} Puan (Bu puana ulaşan neredeyse kesin play-off'ta)")
    print(f"  * %90 Güvenli Baraj       : {t24['safe_points_90pct']} Puan")
    print(f"  * En Şanslı / Alt Baraj    : {t24['minimum_possible_points']} Puan (Simülasyonlardaki en düşük 24. sıra puanı)")
    print(f"  * Puan Gerçekleşme Dağılımı:")
    for pt, pct in sorted(t24["distribution"].items()):
        bar = "#" * int(pct * 40)
        print(f"      {pt:>2} Puan: %{pct*100:<5.1f} {bar}")
    print("=" * 85)


def print_points_to_outcome(points_matrix):
    print("\n" + "=" * 85)
    print("        'HANGİ PUANI ALIRSAN KAÇINCI OLURSUN?' OLASILIK TABLOSU")
    print("=" * 85)
    header = f"{'Puan':<8}{'Örnek Sayısı':<15}{'Ort. Sıra':<12}{'İlk 8 İhtimali':<18}{'Play-off İhtimali':<20}{'Elenme İhtimali':<18}"
    print(header)
    print("-" * 85)

    for row in points_matrix:
        if row["points"] < 5 or row["points"] > 22:
            continue  # Cok uc degerleri kalabalik yapmasin diye atlayalim
        print(
            f"{row['points']:<8}"
            f"{row['sample_count']:<15,}"
            f"{row['avg_rank']:<12.1f}"
            f"%{row['prob_top8']:<17.1f}"
            f"%{row['prob_playoff']:<19.1f}"
            f"%{row['prob_eliminated']:<17.1f}"
        )
    print("=" * 85)


def print_team_position_detail(team_name, team_data):
    print("\n" + "=" * 80)
    print(f" {team_name.upper()} - SIRALAMA OLASILIK DAĞILIMI (10.000 SİMÜLASYON)")
    print("=" * 80)
    print(f"  * En Olası Bitiş Sırası (Mode) : {team_data['mode_rank']}. Sıra")
    print(f"  * İlk 8'de Bitirme İhtimali    : %{team_data['prob_top8']:.1f}")
    print(f"  * Play-off'a Kalma İhtimali    : %{team_data['prob_playoff']:.1f}")
    print(f"  * Elenme İhtimali              : %{team_data['prob_eliminated']:.1f}")
    print("-" * 80)
    print(f"{'Sıra':<8}{'Olasılık':<12}{'Dağılım Grafiği'}")
    print("-" * 80)

    for rank, prob in sorted(team_data["rank_probabilities"].items(), key=lambda x: int(x[0])):
        if prob >= 0.2:  # %0.2'den buyukleri goster
            bar = "#" * int(prob * 2)
            star = " *" if rank == team_data["mode_rank"] else ""
            print(f"{rank:<8} %{prob:<10.1f} {bar}{star}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo 10.000 Simulasyon Analiz ve Raporlama")
    parser.add_argument("-c", "--competition", type=str, default="CL", choices=["CL", "UEL", "EL", "ECL", "UECL", "cl", "uel", "el", "ecl", "uecl"], help="Turnuva kodu (CL, UEL veya ECL, varsayılan: CL)")
    parser.add_argument("--summary", action="store_true", help="Takim bazli genel performans tablosunu goster")
    parser.add_argument("--thresholds", action="store_true", help="Ilk 8 ve Ilk 24 baraj puanlarini goster")
    parser.add_argument("--points-matrix", action="store_true", help="'Hangi puani alirsan ne olur?' tablosunu goster")
    parser.add_argument("-t", "--team", nargs="+", default=None, help="Belirli bir takimin siralanma olasiliklarini detayli goster (orn: Galatasaray, Besiktas, Trabzonspor)")
    parser.add_argument("-d", "--date", type=str, default=None, help="İncelenecek simülasyon ve analizin tarihi (YYYY-MM-DD)")
    parser.add_argument("--list-dates", action="store_true", help="Kayıtlı analiz tarihlerini listele")
    parser.add_argument("--all", action="store_true", help="Tum analizleri eksiksiz calistir")
    args = parser.parse_args()

    comp_upper = args.competition.upper()
    comp_lower = "ecl" if comp_upper in ["ECL", "UECL"] else ("uel" if comp_upper in ["EL", "UEL"] else "cl")
    comp_title = "UEFA Konferans Ligi" if comp_lower == "ecl" else ("UEFA Avrupa Ligi" if comp_lower == "uel" else "UEFA Şampiyonlar Ligi")

    if args.list_dates:
        dates = list_available_dates(BASE_ANALYSIS_DIR)
        print("=" * 50)
        print(" KAYITLI ANALİZ TARİHLERİ")
        print("=" * 50)
        if not dates:
            print("Henüz arşivlenmiş tarihli analiz bulunmuyor.")
        for d in dates:
            d_path = BASE_ANALYSIS_DIR / d
            files = list(d_path.glob("*.json"))
            f_names = ", ".join(f.name for f in files) if files else "dosya yok"
            print(f"  * {d} -> {f_names}")
        print("=" * 50)
        return

    # 1. Simülasyon dosyasını bul (Önce tarih-saat klasörüne bak, yoksa ana dosyaya)
    target_sim_file = None
    matched_sim_dir = find_matching_date_dir(BASE_SIM_DIR, args.date) if args.date else None

    sim_filename_candidates = [
        f"mc_{comp_lower}_10000_results.pkl.gz",
        f"mc_10000_results_{comp_lower}.pkl.gz",
        "mc_10000_results.pkl.gz" if comp_upper == "CL" else None,
        "mc_200_results.pkl.gz" if comp_upper == "CL" else None,
    ]
    sim_filename_candidates = [c for c in sim_filename_candidates if c]

    if matched_sim_dir:
        for cand in sim_filename_candidates:
            if (matched_sim_dir / cand).exists():
                target_sim_file = matched_sim_dir / cand
                break
    elif not args.date:
        for cand in sim_filename_candidates:
            if (BASE_SIM_DIR / cand).exists():
                target_sim_file = BASE_SIM_DIR / cand
                break

    # 2. Analiz sonuçlarının kaydedileceği / okunacağı dosya yolu
    analysis_file_name = f"simulation_analysis_{comp_lower}_2026_27.json"
    latest_analysis_json = BASE_ANALYSIS_DIR / analysis_file_name

    matched_analysis_dir = find_matching_date_dir(BASE_ANALYSIS_DIR, args.date) if args.date else None
    if matched_analysis_dir:
        dated_analysis_json = matched_analysis_dir / analysis_file_name
    else:
        target_ts = get_now_timestamp()
        dated_analysis_dir = get_date_dir(BASE_ANALYSIS_DIR, target_ts)
        dated_analysis_json = dated_analysis_dir / analysis_file_name

    # Eğer analiz JSON'ı zaten kayıtlıysa, doğrudan oku (0 saniyede açılır)
    if dated_analysis_json.exists():
        print(f"[*] Kayıtlı analiz dosyası yükleniyor: {dated_analysis_json}\n")
        with open(dated_analysis_json, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    elif not args.date and latest_analysis_json.exists():
        print(f"[*] Güncel kayıtlı analiz dosyası yükleniyor: {latest_analysis_json}\n")
        with open(latest_analysis_json, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    else:
        if not target_sim_file or not target_sim_file.exists():
            print(f"[HATA] {comp_upper} için simulasyon dosyası bulunamadı.")
            print(f"Lütfen önce simülasyonu çalıştırın: python scripts/run_weekly_pipeline.py -c {comp_upper}")
            return

        # JSON henüz yoksa simülasyondan hesapla ve arşivle
        results = SimulationResults.load(str(target_sim_file))
        analyzer = SimulationAnalyzer(results)

        analyzer.save_analysis(str(dated_analysis_json))
        analyzer.save_analysis(str(LATEST_ANALYSIS_JSON))
        print(f"[*] Analizler hesaplandı ve arşivlendi:")
        print(f"    -> Tarihli Arşiv: {dated_analysis_json}")
        print(f"    -> Güncel Kopya : {LATEST_ANALYSIS_JSON}\n")
        full_data = analyzer.run_full_analysis()

    # Filtre kontrolu
    team_query = " ".join(args.team) if args.team else None

    # Eger hic parametre verilmediyse veya --all dendiyse ozet bas
    show_all = args.all or (not args.summary and not args.thresholds and not args.points_matrix and not team_query)

    if show_all or args.summary:
        print_team_performances(full_data["team_performances"])

    if show_all or args.thresholds:
        print_thresholds(full_data["qualification_thresholds"], comp_title=comp_title)

    if show_all or args.points_matrix:
        print_points_to_outcome(full_data["points_to_outcome"])

    if team_query:
        # Takimi bul (Turkce karakter ve aksan duyarsiz)
        def normalize_str(s):
            import unicodedata
            return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()

        q_norm = normalize_str(team_query)
        matched = None
        for t_name, t_data in full_data["team_position_probabilities"].items():
            if q_norm in normalize_str(t_name):
                matched = (t_name, t_data)
                break
        if matched:
            print_team_position_detail(matched[0], matched[1])
        else:
            print(f"[UYARI] '{team_query}' adinda takim bulunamadi.")


if __name__ == "__main__":
    main()

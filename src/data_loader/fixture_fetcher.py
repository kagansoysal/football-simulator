import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import argparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FixtureFetcher:
    """
    AkilOyunu API uzerinden lig ve kupa fiksturlerini, oynanmis mac skorlarini
    ve oynanmamis gelecek maclari generic olarak ceken ve kaydeden veri sinifi.
    
    Desteklenen Turnuva Kodlari (Ornekler):
    - 'CL': UEFA Champions League
    - 'EL': UEFA Europa League
    - 'ECL': UEFA Conference League
    - 'WC': FIFA World Cup
    """
    API_URL = "https://football-api.akiloyunu.com/api/v1/competition-matches"

    COMPETITION_NAMES = {
        "CL": "UEFA Champions League",
        "EL": "UEFA Europa League",
        "UEL": "UEFA Europa League",
        "ECL": "UEFA Conference League",
        "UECL": "UEFA Conference League",
    }

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            project_root = Path(__file__).resolve().parents[2]
            self.data_dir = project_root / "data"
        else:
            self.data_dir = Path(data_dir)

        self.leagues_dir = self.data_dir / "leagues"
        self.leagues_dir.mkdir(parents=True, exist_ok=True)

    def fetch_competition_matches(
        self, competition_code: str = "CL", stage: str = "LEAGUE_STAGE", season_year: int = 2026
    ) -> List[Dict[str, Any]]:
        """
        Belirtilen turnuvanin tum maclarini (hem FINISHED hem SCHEDULED) ceker.
        """
        comp_upper = competition_code.upper()
        # AkilOyunu API filtre kodlari: CL, UEL, UECL
        api_filter_code = "UECL" if comp_upper in ["ECL", "UECL"] else ("UEL" if comp_upper in ["EL", "UEL"] else comp_upper)

        logger.info(f"AkilOyunu API'den '{api_filter_code}' ({stage}, Sezon: {season_year}) maclari cekiliyor...")
        all_matches = []
        page = 1
        per_page = 100

        while True:
            params = {
                "filter[competition]": api_filter_code,
                "per_page": per_page,
                "page": page,
            }
            resp = requests.get(self.API_URL, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"API istegi basarisiz (Sayfa {page}): {resp.status_code} - {resp.text}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                # Sezon ve Lig Aşaması filtresi
                m_stage = item.get("stage")
                m_year = item.get("season_year")
                if m_stage == stage and m_year == season_year:
                    all_matches.append(item)

            pagination = data.get("meta", {}).get("pagination", {})
            last_page = pagination.get("last_page", 1)
            logger.info(f"Sayfa {page}/{last_page} tarandi. (Eslesen mac: {len(all_matches)})")

            if page >= last_page:
                break
            page += 1

        return all_matches

    def sync_league(
        self, competition_code: str = "CL", season_year: int = 2026, stage: str = "LEAGUE_STAGE"
    ) -> str:
        """
        Turnuvanin tum fiksturunu ceker, duzenler ve data/leagues/<league_id>.json olarak kaydeder.
        """
        comp_upper = competition_code.upper()
        raw_matches = self.fetch_competition_matches(competition_code, stage=stage, season_year=season_year)
        if not raw_matches:
            raise RuntimeError(f"'{competition_code}' turnuvasi icin mac verisi bulunamadi.")

        # Tarihe gore artan sirala
        raw_matches = sorted(raw_matches, key=lambda m: m.get("utc_date", ""))

        teams_set = set()
        fixtures = []

        # Hafta (round) belirleme: her 18 mac 1 haftadir (36 takim / 2 = 18 mac/hafta)
        # Swiss system icin mac sirasina gore haftalari 1-8 arasi dagitiyoruz
        matches_per_round = 18

        for idx, m in enumerate(raw_matches, 1):
            h_team = m.get("home_team_name")
            a_team = m.get("away_team_name")
            teams_set.add(h_team)
            teams_set.add(a_team)

            status = m.get("status")
            is_played = status == "FINISHED"
            h_score = m.get("home_score")
            a_score = m.get("away_score")

            round_num = ((idx - 1) // matches_per_round) + 1

            # Ozel tarafsiz saha (neutral ground) durumlari
            is_neutral = bool(m.get("is_neutral", False))
            # Ornek: Guvenlik / UEFA karari sebebiyle tarafsiz sahada oynanan maclar
            if ("be" in h_team.lower() and "ik" in h_team.lower() and "beer" in a_team.lower()):
                is_neutral = True

            fixtures.append({
                "match_id": idx,
                "round": round_num,
                "date": m.get("utc_date", "")[:10],
                "home_team": h_team,
                "away_team": a_team,
                "home_score": int(h_score) if (is_played and h_score is not None) else None,
                "away_score": int(a_score) if (is_played and a_score is not None) else None,
                "is_played": is_played,
                "is_neutral": is_neutral,
            })

        sorted_teams = sorted(list(teams_set))
        file_code = "ecl" if comp_upper in ["ECL", "UECL"] else ("uel" if comp_upper in ["EL", "UEL"] else "cl")
        league_id = f"{file_code}_{season_year}_{str(season_year + 1)[-2:]}"
        league_name = self.COMPETITION_NAMES.get(comp_upper, f"Competition {comp_upper}")
        season_str = f"{season_year}-{season_year + 1}"

        total_rounds = max([f["round"] for f in fixtures]) if fixtures else 8

        payload = {
            "league_id": league_id,
            "competition_code": competition_code,
            "name": league_name,
            "season": season_str,
            "format": "swiss_system" if len(sorted_teams) == 36 else "standard",
            "total_rounds": total_rounds,
            "teams": sorted_teams,
            "fixtures": fixtures,
        }

        output_path = self.leagues_dir / f"{league_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        played_count = sum(1 for f in fixtures if f["is_played"])
        unplayed_count = len(fixtures) - played_count

        logger.info(f"Turnuva basariyla senkronize edildi: {output_path}")
        logger.info(f"Toplam Takim: {len(sorted_teams)} | Toplam Mac: {len(fixtures)}")
        logger.info(f"Oynanmis (Gercek Skorlu): {played_count} | Oynanmamis (Fikstur): {unplayed_count}")

        return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="AkilOyunu Fikstur ve Skor Cekici / Guncelleyici")
    parser.add_argument("-c", "--competition", default="CL", help="Turnuva kodu (CL, EL, ECL vb., varsayilan: CL)")
    parser.add_argument("-y", "--year", type=int, default=2026, help="Sezon baslangic yili (varsayilan: 2026)")
    parser.add_argument("-s", "--stage", default="LEAGUE_STAGE", help="Asama adi (varsayilan: LEAGUE_STAGE)")
    args = parser.parse_args()

    fetcher = FixtureFetcher()
    path = fetcher.sync_league(competition_code=args.competition, season_year=args.year, stage=args.stage)
    print(f"\n[BASARILI] Fikstur dosyasi guncellendi:\n-> {path}")


if __name__ == "__main__":
    main()

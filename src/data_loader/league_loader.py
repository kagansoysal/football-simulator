import json
import os
from typing import List, Dict, Optional, Any
from src.core.models import Match


class LeagueLoader:
    """
    Lig ve fikstur JSON dosyalarini yukleyen ve yoneten generic sinif.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self.league_id: str = ""
        self.name: str = ""
        self.season: str = ""
        self.teams: List[str] = []
        self.fixtures: List[Match] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Lig dosyasi bulunamadi: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.league_id = self.data.get("league_id", "")
        self.name = self.data.get("name", "")
        self.season = self.data.get("season", "")
        self.teams = self.data.get("teams", [])
        
        raw_fixtures = self.data.get("fixtures", [])
        self.fixtures = [Match.from_dict(m) for m in raw_fixtures]

    def get_round_fixtures(self, round_num: int) -> List[Match]:
        """Belirli bir haftanin maclarini dondurur."""
        return [m for m in self.fixtures if m.round == round_num]

    def get_fixtures_up_to_round(self, round_num: int) -> List[Match]:
        """Belirli bir haftaya kadar olan (dahil) tum maclari dondurur."""
        return [m for m in self.fixtures if m.round <= round_num]

    def get_unplayed_fixtures(self) -> List[Match]:
        """Oynanmamis maclari dondurur."""
        return [m for m in self.fixtures if not m.is_played]

    def get_played_fixtures(self) -> List[Match]:
        """Oynanmis maclari dondurur."""
        return [m for m in self.fixtures if m.is_played]

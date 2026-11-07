import os
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, List, Any
import pandas as pd
import requests

from src.core.storage import get_now_timestamp, resolve_timestamp, find_matching_date_dir, get_date_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Yaygın kulüp isim farklılıkları için alias eşleme tablosu
DEFAULT_ALIASES = {
    # 36 Şampiyonlar Ligi Kulübünün AkilOyunu CSV İsim Eşleştirmeleri
    "fc bayern münchen": "Bayern",
    "fc bayern munchen": "Bayern",
    "bayern münchen": "Bayern",
    "bayern munich": "Bayern",
    "bayern": "Bayern",

    "atlético de madrid": "Atletico",
    "atletico de madrid": "Atletico",
    "atletico madrid": "Atletico",
    "atlético madrid": "Atletico",
    "atletico": "Atletico",

    "fc barcelona": "Barcelona",
    "barcelona": "Barcelona",

    "fc internazionale milano": "Inter",
    "inter milan": "Inter",
    "internazionale": "Inter",
    "inter": "Inter",

    "psv eindhoven": "PSV",
    "psv": "PSV",

    "rb leipzig": "Leipzig",
    "leipzig": "Leipzig",

    "fc shakhtar donetsk": "Shakhtar",
    "shakhtar donetsk": "Shakhtar",
    "shakhtar": "Shakhtar",

    "sk slavia praha": "Slavia Prag",
    "slavia praha": "Slavia Prag",
    "slavia prague": "Slavia Prag",

    "viking fk": "Viking",
    "viking": "Viking",

    "sabah fc": "Sabah",
    "sabah": "Sabah",

    "vfb stuttgart": "Stuttgart",
    "stuttgart": "Stuttgart",

    "fk bodø/glimt": "Bodø/Glimt",
    "fk bodo/glimt": "Bodø/Glimt",
    "bodo/glimt": "Bodø/Glimt",
    "bodø/glimt": "Bodø/Glimt",
    "bodo glimt": "Bodø/Glimt",

    "šk slovan bratislava": "Slovan Bratislava",
    "sk slovan bratislava": "Slovan Bratislava",
    "slovan bratislava": "Slovan Bratislava",

    "manchester city": "Man City",
    "man city": "Man City",

    "manchester united": "Man United",
    "man united": "Man United",

    "paris saint-germain": "Paris SG",
    "psg": "Paris SG",
    "paris sg": "Paris SG",

    "as roma": "Roma",
    "roma": "Roma",

    "ssc napoli": "Napoli",
    "napoli": "Napoli",

    "fc porto": "Porto",
    "porto": "Porto",

    "losc lille": "Lille",
    "lille": "Lille",

    "aek athens": "AEK",
    "aek": "AEK",

    "rc lens": "Lens",
    "lens": "Lens",

    "borussia dortmund": "Dortmund",
    "dortmund": "Dortmund",

    "sporting cp": "Sporting CP",
    "sporting lisbon": "Sporting CP",

    "benfica lisbon": "Benfica",
    "sl benfica": "Benfica",

    "bayer leverkusen": "Leverkusen",
    "bayer 04 leverkusen": "Leverkusen",
    "leverkusen": "Leverkusen",

    "red star belgrade": "Kızılyıldız",
    "crvena zvezda": "Kızılyıldız",
    "red star": "Kızılyıldız",

    "gnk dinamo zagreb": "Dinamo Zagreb",
    "dinamo zagreb": "Dinamo Zagreb",

    "young boys bern": "Young Boys",
    "young boys": "Young Boys",

    "sparta prague": "Sparta Prag",
    "ac sparta praha": "Sparta Prag",
    "sparta": "Sparta Prag",

    "sturm graz": "Sturm Graz",
}

class AkilOyunuEloFetcher:
    """
    https://www.akiloyunu.com (football-api.akiloyunu.com) API'sinden
    güncel kulüp Elo rating verilerini çeken, önbelleğe alan ve
    generic olarak sorgulama imkanı sunan sınıf.
    """
    API_URL = "https://football-api.akiloyunu.com/api/v1/club-elo"

    def __init__(self, data_dir: Optional[str] = None, as_of_date: Optional[str] = None):
        if data_dir is None:
            # Proje kok dizinini bul (src/data_loader -> src -> root)
            project_root = Path(__file__).resolve().parents[2]
            self.data_dir = project_root / "data"
        else:
            self.data_dir = Path(data_dir)

        self.as_of_date = as_of_date
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.processed_dir / "akiloyunu_club_elo.csv"
        self.alias_file = self.processed_dir / "team_aliases.json"

        self._df: Optional[pd.DataFrame] = None
        self._aliases: Dict[str, str] = self._load_aliases()

    def _load_aliases(self) -> Dict[str, str]:
        """Kayıtlı veya varsayılan alias sözlüğünü yükler."""
        aliases = DEFAULT_ALIASES.copy()
        if self.alias_file.exists():
            try:
                with open(self.alias_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    aliases.update(saved)
            except Exception as e:
                logger.warning(f"Alias dosyası okunamadı: {e}")
        
        # Güncellenmiş alias sözlüğünü tekrar diske kaydet
        with open(self.alias_file, "w", encoding="utf-8") as f:
            json.dump(aliases, f, indent=2, ensure_ascii=False)
        return aliases

    def register_alias(self, alias: str, standard_name: str) -> None:
        """Yeni bir kulüp takma adı ekler ve kaydeder."""
        self._aliases[alias.lower().strip()] = standard_name.strip()
        with open(self.alias_file, "w", encoding="utf-8") as f:
            json.dump(self._aliases, f, indent=2, ensure_ascii=False)

    def fetch_data(self, target_date: Optional[str] = None, force_refresh: bool = False) -> pd.DataFrame:
        """
        AkilOyunu API'sinden belirli bir tarihe ait veya en güncel Elo verisini çeker.
        Tüm sayfaları gezerek tüm kulüpleri alır, hem ana önbelleğe hem de tarih klasörüne CSV olarak kaydeder.
        """
        req_date = target_date or self.as_of_date
        if req_date is None:
            today_str = datetime.now().strftime("%Y-%m-%d")
        else:
            today_str = req_date

        # 1. Belirli bir tarih istenmişse ve o tarihin klasöründe CSV varsa oradan oku
        if req_date and not force_refresh:
            matched_dir = find_matching_date_dir(self.processed_dir, req_date)
            if matched_dir:
                dated_csv = matched_dir / "akiloyunu_club_elo.csv"
                if dated_csv.exists():
                    logger.info(f"Tarihli önbellekten Elo verisi yükleniyor ({matched_dir.name}): {dated_csv}")
                    self._df = pd.read_csv(dated_csv)
                    return self._df

        # 2. Ana önbellek CSV varsa ve force_refresh denmemişse doğrudan oradan oku
        if self.cache_file.exists() and not force_refresh:
            logger.info(f"Önbellekten Elo verisi yükleniyor: {self.cache_file}")
            self._df = pd.read_csv(self.cache_file)
            return self._df

        # 3. API parametresini hazırla (YYYY-MM-DD)
        api_date = req_date[:10] if req_date and len(req_date) >= 10 else datetime.now().strftime("%Y-%m-%d")

        logger.info(f"AkilOyunu API üzerinden Elo verileri çekiliyor (Tarih: {api_date})...")
        all_clubs = []
        page = 1
        per_page = 100

        while True:
            params = {
                "filter[date]": api_date,
                "per_page": per_page,
                "page": page
            }
            resp = requests.get(self.API_URL, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"API isteği başarısız oldu (Sayfa {page}): {resp.status_code} - {resp.text}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                team_info = item.get("team") or {}
                all_clubs.append({
                    "Club": item.get("club"),
                    "Country": item.get("country"),
                    "Elo": float(item.get("elo", 0.0)),
                    "EloDate": item.get("elo_date") or item.get("from"),
                    "Slug": team_info.get("slug"),
                    "LogoUrl": team_info.get("logo_url")
                })

            pagination = data.get("meta", {}).get("pagination", {})
            last_page = pagination.get("last_page", 1)
            logger.info(f"Sayfa {page}/{last_page} çekildi. (Mevcut kulüp sayısı: {len(all_clubs)})")

            if page >= last_page:
                break
            page += 1

        if not all_clubs:
            raise RuntimeError(f"{target_date} tarihi için AkilOyunu API'sinden veri alınamadı.")

        df = pd.DataFrame(all_clubs)
        # Elo puanına göre azalan sırala
        df = df.sort_values(by="Elo", ascending=False).reset_index(drop=True)
        df["Rank"] = df.index + 1

        # Kolon sırası
        cols = ["Rank", "Club", "Country", "Elo", "EloDate", "Slug", "LogoUrl"]
        df = df[cols]

        # 1. Ana Önbelleğe kaydet
        df.to_csv(self.cache_file, index=False, encoding="utf-8")
        logger.info(f"Toplam {len(df)} kulüp verisi ana önbelleğe kaydedildi: {self.cache_file}")

        # 2. Tarih ve Saat bazlı arşiv klasörüne kaydet (data/processed/YYYY-MM-DD_HH-MM/akiloyunu_club_elo.csv)
        ts_now = get_now_timestamp()
        dated_dir = self.processed_dir / ts_now
        dated_dir.mkdir(parents=True, exist_ok=True)
        dated_file = dated_dir / "akiloyunu_club_elo.csv"
        df.to_csv(dated_file, index=False, encoding="utf-8")
        logger.info(f"Tarihli ve saatli arşiv kopyası kaydedildi: {dated_file}")

        self._df = df
        return self._df

    @property
    def dataframe(self) -> pd.DataFrame:
        """Yüklü dataframe'i döndürür, yoksa otomatik çeker."""
        if self._df is None:
            self.fetch_data()
        return self._df

    @staticmethod
    def _normalize(text: str) -> str:
        """Karakterleri kucuk harfe cevirir, turkce/ozel karakterleri ascii'ye yaklastirir."""
        import unicodedata
        t = text.strip().lower()
        t = t.replace("ø", "o").replace("ö", "o").replace("ü", "u").replace("ı", "i").replace("ğ", "g").replace("ş", "s").replace("ç", "c")
        # Unicode aksanlarini temizle (e.g. é -> e)
        nfkd = unicodedata.normalize('NFKD', t)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    def get_club(self, club_name: str) -> Optional[pd.Series]:
        """
        Kulüp adına göre takımı bulur (alias desteği, unicode normalizasyonu ve case-insensitive ile).
        """
        df = self.dataframe
        search_name = club_name.strip()
        lower_name = search_name.lower()
        norm_name = self._normalize(search_name)

        # 1. Alias kontrolü (tam kucuk harf veya normalize)
        if lower_name in self._aliases:
            target = self._aliases[lower_name]
            match = df[df["Club"].str.lower() == target.lower()]
            if not match.empty:
                return match.iloc[0]

        if norm_name in self._aliases:
            target = self._aliases[norm_name]
            match = df[df["Club"].str.lower() == target.lower()]
            if not match.empty:
                return match.iloc[0]

        # 2. Tam eşleşme (orijinal)
        match = df[df["Club"].str.lower() == lower_name]
        if not match.empty:
            return match.iloc[0]

        # 3. Normalize edilmiş tam eşleşme
        df_norm = df["Club"].apply(self._normalize)
        norm_match = df[df_norm == norm_name]
        if not norm_match.empty:
            return norm_match.iloc[0]

        # 4. Kısmi eşleşme
        for idx, row_club in enumerate(df["Club"]):
            c_norm = self._normalize(row_club)
            if c_norm in norm_name or norm_name in c_norm:
                return df.iloc[idx]

        # 5. Kelime bazli eslesme (orn: "SK Slavia Praha" icindeki "slavia" -> "Slavia Prag")
        search_tokens = [tok for tok in norm_name.split() if len(tok) >= 4 and tok not in ["club", "football", "city", "town", "united"]]
        for tok in search_tokens:
            for idx, row_club in enumerate(df["Club"]):
                if tok in self._normalize(row_club):
                    return df.iloc[idx]

        return None

    def get_elo(self, club_name: str, default: float = 1500.0) -> float:
        """Kulübün güncel Elo değerini döndürür."""
        club_data = self.get_club(club_name)
        if club_data is not None:
            return float(club_data["Elo"])
        logger.warning(f"'{club_name}' için AkilOyunu'nda Elo puanı bulunamadı. Varsayılan ({default}) atanıyor.")
        return default

    def get_clubs_by_country(self, country: str) -> pd.DataFrame:
        """Ülke adına göre kulüpleri filtreler (örn. 'Turkey', 'England', 'Spain')."""
        df = self.dataframe
        c_lower = country.strip().lower()
        return df[df["Country"].str.lower() == c_lower]

    def list_countries(self) -> List[str]:
        """Mevcut ülkelerin listesini döndürür."""
        return sorted(list(self.dataframe["Country"].dropna().unique()))

if __name__ == "__main__":
    import argparse
    import sys

    # Proje kök dizinini sys.path'e ekle
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    parser = argparse.ArgumentParser(description="AkilOyunu Elo Veri Çekici ve Güncelleyici")
    parser.add_argument(
        "-r", "--refresh",
        action="store_true",
        help="Önbelleği atlayarak API'den en güncel Elo verilerini yeniden çeker"
    )
    parser.add_argument(
        "-d", "--date",
        type=str,
        default=None,
        help="Belirli bir tarih için Elo verisi çeker (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    fetcher = AkilOyunuEloFetcher(as_of_date=args.date)
    df = fetcher.fetch_data(target_date=args.date, force_refresh=args.refresh)

    print("\n" + "=" * 55)
    print(f"  ELO VERİLERİ HAZIR ({len(df)} Kulüp, {len(fetcher.list_countries())} Ülke)")
    print(f"  En Son Güncelleme: {df['EloDate'].max()}")
    print("=" * 55)
    print("\n--- İlk 5 Kulüp ---")
    print(df[["Rank", "Club", "Country", "Elo", "EloDate"]].head(5).to_string(index=False))
    print("\nBilgi: Simülasyonlar bu yerel önbellekten anında beslenir.")
    print("Yeni maçlar oynandıkça güncellemek için: python src/data_loader/elo_fetcher.py --refresh")


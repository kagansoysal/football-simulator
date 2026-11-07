"""
AkilOyunu Elo Fetcher Test ve Doğrulama Scripti.
"""
import sys
from pathlib import Path

# Proje ana dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import EloFetcher

def main():
    fetcher = EloFetcher()
    # force_refresh=False önbellekten okur, True API'den yeniden çeker
    df = fetcher.fetch_data(force_refresh=False)

    print("\n" + "=" * 60)
    print("           AKIL OYUNU GÜNCEL ELO SIRALAMASI")
    print("=" * 60)
    print(f"Toplam Kulüp Sayısı     : {len(df)}")
    print(f"Temsil Edilen Ülke Sayısı: {len(fetcher.list_countries())}")
    print(f"En Son Veri Tarihi      : {df['EloDate'].max()}")

    print("\n--- İLK 10 AVRUPA KULÜBÜ ---")
    print(df[["Rank", "Club", "Country", "Elo", "EloDate"]].head(10).to_string(index=False))

    print("\n--- TÜRKİYE KULÜPLERİ ---")
    turkey_clubs = fetcher.get_clubs_by_country("Turkey")
    if not turkey_clubs.empty:
        print(turkey_clubs[["Rank", "Club", "Elo", "EloDate"]].to_string(index=False))
    else:
        print("Türkiye kulübü bulunamadı.")

    print("\n--- ÖRNEK SORGULAMALAR (ALİAS DESTEĞİ İLE) ---")
    test_clubs = [
        "Real Madrid",
        "Manchester City",
        "Bayern Munich",
        "Paris Saint-Germain",
        "PSG",
        "Galatasaray",
        "Arsenal",
        "Inter Milan"
    ]
    for club in test_clubs:
        elo = fetcher.get_elo(club)
        print(f"  {club:<25} -> {elo:.2f}")
    print("=" * 60)

if __name__ == "__main__":
    main()


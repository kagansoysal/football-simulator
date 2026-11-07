import requests

url = "https://football-api.akiloyunu.com/api/v1/club-elo"

test_dates = [
    "2026-10-29",
    "2026-10-21",
    "2026-10-14",
    "2026-10-01",
    "2026-09-10",
    "2026-08-01",
    "2026-01-01",
    "2025-10-01",
    "2024-10-01",
]

print("=== AKILOYUNU CLUB-ELO TARIH TESTI ===")
for d in test_dates:
    r = requests.get(url, params={"filter[date]": d, "per_page": 2}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        total = data.get("meta", {}).get("pagination", {}).get("total", 0)
        items = data.get("data", [])
        if items:
            c = items[0]
            print(f"Sorgulanan Tarih: {d} -> Toplam Kayit: {total:<4} | 1. Kulüp: {c.get('club')} ({c.get('elo')}) | Veri Tarihi: {c.get('elo_date')}")
        else:
            print(f"Sorgulanan Tarih: {d} -> Kayit YOK (Bos)")
    else:
        print(f"Sorgulanan Tarih: {d} -> Hata {r.status_code}")

"""
AkilOyunu Competition Matches API Test & Arşiv Scripti
Farklı turnuvaların (CL, EL, WC vb.) maçlarını, oynanmış ve oynanmamış fikstürlerini test etmek için kullanılır.
"""
import requests
import json

BASE_API = "https://football-api.akiloyunu.com/api/v1/competition-matches"


def test_competition_api(competition_code: str = "CL", status: str = "FINISHED", per_page: int = 10):
    params = {
        "filter[competition]": competition_code,
        "filter[status]": status,
        "per_page": per_page,
    }
    print(f"--- AkilOyunu Competition Matches Testi ({competition_code}, Durum: {status}) ---")
    try:
        r = requests.get(BASE_API, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            meta = data.get("meta", {}).get("pagination", {})
            print(f"Toplam Kayıt: {meta.get('total')}, Sayfa: {meta.get('current_page')}/{meta.get('last_page')}")
            for m in data.get("data", [])[:per_page]:
                d = m.get("utc_date", "")[:10]
                stage = m.get("stage")
                score_str = f"{m.get('home_score')} - {m.get('away_score')}" if status == "FINISHED" else "v"
                print(f"  [{d}] ({stage}) {m.get('home_team_name')} {score_str} {m.get('away_team_name')}")
        else:
            print(f"Hata: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"İstek hatası: {e}")


if __name__ == "__main__":
    # 1. Oynanmış maçlar testi
    test_competition_api(competition_code="CL", status="FINISHED", per_page=5)
    print()
    # 2. Gelecek fikstür testi
    test_competition_api(competition_code="CL", status="SCHEDULED", per_page=5)


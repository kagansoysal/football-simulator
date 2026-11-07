"""
Akıl Oyunu (akiloyunu.com) API Keşif ve Analiz Aracı.
Next.js bundle'ları, REST endpointleri ve OpenAPI dökümanını sorgulamak için kullanılır.
"""
import requests
import json

BASE_API = "https://football-api.akiloyunu.com/api/v1"
DOCS_URL = "https://football-api.akiloyunu.com/docs"

def inspect_api_docs():
    print(f"--- 1. OpenAPI Dökümantasyonu Kontrol Ediliyor ({DOCS_URL}) ---")
    try:
        r = requests.get(DOCS_URL, timeout=10)
        if r.status_code == 200:
            doc = r.json()
            print(f"Başlık: {doc.get('info', {}).get('title')}")
            print(f"Versiyon: {doc.get('info', {}).get('version')}")
            print("\nMevcut API Endpointleri:")
            for path, methods in doc.get("paths", {}).items():
                for m, details in methods.items():
                    summary = details.get("summary", details.get("description", ""))
                    print(f"  {m.upper():<6} {path:<45} -> {summary}")
        else:
            print(f"Hata: {r.status_code}")
    except Exception as e:
        print(f"Bağlantı hatası: {e}")

def test_club_elo_endpoint(test_date="2026-10-27"):
    print(f"\n--- 2. Club Elo Endpoint Test Ediliyor ({test_date}) ---")
    url = f"{BASE_API}/club-elo"
    params = {
        "filter[date]": test_date,
        "per_page": 5,
        "page": 1
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Durum Kodu: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            meta = data.get("meta", {}).get("pagination", {})
            print(f"Toplam Kayıt: {meta.get('total')}, Sayfa: {meta.get('current_page')}/{meta.get('last_page')}")
            print("Örnek İlk 2 Kulüp:")
            print(json.dumps(data.get("data", [])[:2], indent=2, ensure_ascii=False))
        else:
            print("Hata yanıtı:", r.text)
    except Exception as e:
        print(f"İstek hatası: {e}")

if __name__ == "__main__":
    inspect_api_docs()
    test_club_elo_endpoint()


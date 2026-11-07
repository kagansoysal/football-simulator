import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader.elo_fetcher import AkilOyunuEloFetcher

fetcher = AkilOyunuEloFetcher()
with open('data/leagues/cl_2026_27.json', 'r', encoding='utf-8') as f:
    league = json.load(f)

print("--- 36 TAKIM ELO KONTROLU ---")
failed = []
for t in league['teams']:
    elo = fetcher.get_elo(t, default=0.0)
    club = fetcher.get_club(t)
    matched_name = club['Club'] if club is not None else 'BULUNAMADI'
    if elo == 0.0:
        failed.append(t)
        print(f"[-] {t:<28} -> {matched_name} (Elo: {elo})")
    else:
        print(f"[+] {t:<28} -> {matched_name:<18} (Elo: {elo:.1f})")

print(f"\nToplam: {len(league['teams'])} | Basarili: {len(league['teams']) - len(failed)} | Hatali: {len(failed)}")


#!/usr/bin/env python3
"""Buat data contoh Hunter (SINTETIS, nama fiktif) dan sisipkan ke site/crypto-sastra.src.html untuk mode pratinjau."""
import json, os, re, sys, time
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
import hunter

def coin(i, sym, name, mc, fdv_x, vol_x, dd, c7, c30):
    price = 1.0
    return {"id": i, "symbol": sym.lower(), "name": name, "market_cap": mc, "fully_diluted_valuation": mc * fdv_x, "total_volume": mc * vol_x,
            "ath": price / (1 - dd), "current_price": price, "price_change_percentage_7d_in_currency": c7, "price_change_percentage_30d_in_currency": c30, "market_cap_rank": 300}
U = [coin("contoh-a", "CNTA", "Contoh Lending", 96e6, 1.12, .06, .78, 1.5, -6), coin("contoh-b", "CNTB", "Contoh Perp", 210e6, 1.9, .09, .66, 4, 12),
     coin("contoh-c", "CNTC", "Contoh Oracle", 48e6, 1.05, .035, .85, -2, 4), coin("contoh-d", "CNTD", "Contoh Meme", 120e6, 1.0, .9, .3, 55, 190),
     coin("contoh-e", "CNTE", "Contoh Bridge", 33e6, 3.4, .02, .93, -4, -18), coin("contoh-f", "CNTF", "Contoh RWA", 150e6, 1.3, .05, .55, 3, 21)]
PROTO = {"contoh-a": {"tvl": 640e6, "slug": "contoh-a", "category": "Lending", "chains": ["Ethereum", "Base"]},
         "contoh-b": {"tvl": 300e6, "slug": "contoh-b", "category": "Derivatives", "chains": ["Arbitrum"]},
         "contoh-c": {"tvl": 90e6, "slug": "contoh-c", "category": "Oracle", "chains": ["Ethereum"]},
         "contoh-e": {"tvl": 20e6, "slug": "contoh-e", "category": "Bridge", "chains": ["Ethereum"]},
         "contoh-f": {"tvl": 260e6, "slug": "contoh-f", "category": "RWA", "chains": ["Ethereum"]}}
REV = {"contoh-a": 1.4e6, "contoh-b": 1.1e6, "contoh-c": 0.55e6, "contoh-e": 0.02e6, "contoh-f": 0.8e6}
POSTS = [{"sub": "CryptoCurrency", "title": "$CNTD Contoh Meme to the moon", "text": "", "score": 2500, "comments": 600, "url": "https://example.invalid/post", "created": 0}] * 5
POSTS += [{"sub": "defi", "title": "DD: Contoh Lending is undervalued, revenue and buyback", "text": "$CNTA accumulating", "score": 12, "comments": 3, "url": "https://example.invalid/dd", "created": 0}]
r = hunter.hunt(U, PROTO, REV, REV, set(), POSTS, [], now=time.time())
r["demo"] = True; r["analyst_notes"] = r.get("analyst_notes", []); r["sources"]["x"] = {"ok": 0, "fail": 0, "off": True}
txt = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
p = os.path.join(root, "site", "crypto-sastra.src.html"); s = open(p, encoding="utf-8").read()
s = re.sub(r"/\*DEMO_HUNT_START\*/.*?/\*DEMO_HUNT_END\*/", lambda m: "/*DEMO_HUNT_START*/const DEMO_HUNT=" + txt + ";/*DEMO_HUNT_END*/", s, flags=re.S)
open(p, "w", encoding="utf-8").write(s)
print("demo hunt:", [(c["symbol"], round(c["score"]), c["tier"], c["viral"]) for c in r["candidates"]])

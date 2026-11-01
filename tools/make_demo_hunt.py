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
def mk(i, sym, name, mc, fdv_x, vol_x, dd, c7, c30): return coin(i, sym, name, mc, fdv_x, vol_x, dd, c7, c30)
U = [coin("contoh-a", "CNTA", "Contoh Lending", 96e6, 1.12, .06, .78, 1.5, -6), coin("contoh-b", "CNTB", "Contoh Perp", 210e6, 1.9, .09, .66, 4, 12),
     coin("contoh-c", "CNTC", "Contoh Oracle", 48e6, 1.05, .035, .85, -2, 4), coin("contoh-d", "CNTD", "Contoh Meme", 120e6, 1.0, .9, .3, 55, 190),
     coin("contoh-e", "CNTE", "Contoh Bridge", 33e6, 3.4, .02, .93, -4, -18), coin("contoh-f", "CNTF", "Contoh RWA", 150e6, 1.3, .22, .55, 3, 21),
     coin("contoh-g", "CNTG", "Contoh Yield Farm", 41e6, 1.1, .012, .93, -3, -9), coin("contoh-h", "CNTH", "Contoh DePIN", 58e6, 1.4, .28, .40, 2, 8)]
PROTO = {"contoh-a": {"tvl": 640e6, "slug": "contoh-a", "category": "Lending", "chains": ["Ethereum", "Base"]},
         "contoh-b": {"tvl": 300e6, "slug": "contoh-b", "category": "Derivatives", "chains": ["Arbitrum"]},
         "contoh-c": {"tvl": 90e6, "slug": "contoh-c", "category": "Oracle", "chains": ["Ethereum"]},
         "contoh-e": {"tvl": 20e6, "slug": "contoh-e", "category": "Bridge", "chains": ["Ethereum"]},
         "contoh-f": {"tvl": 260e6, "slug": "contoh-f", "category": "RWA", "chains": ["Ethereum"]},
         "contoh-g": {"tvl": 12e6, "slug": "contoh-g", "category": "Yield", "chains": ["Ethereum"]}}
def rows(cat, n, tvl, c7, c30, first=None):
    return [{"category": cat, "tvl": tvl, "change_7d": c7, "change_1m": c30, "gecko_id": (first if i == 0 else None)} for i in range(n)]
ROWS = rows("RWA", 4, 90e6, 31, 44, "contoh-f") + rows("Lending", 5, 200e6, 3, 6, "contoh-a") + rows("Derivatives", 4, 120e6, -4, 2, "contoh-b") + \
       rows("Oracle", 3, 90e6, 1, 3, "contoh-c") + rows("Yield", 4, 60e6, -9, -20, "contoh-g") + rows("Dexs", 4, 400e6, 6, 9)
CATS = [{"name": "Decentralized Physical Infrastructure (DePIN)", "market_cap_change_24h": 6.4}, {"name": "Artificial Intelligence (AI)", "market_cap_change_24h": 3.1}]
DET = {"contoh-a": {"age_days": 900, "commits4w": 46, "categories": [], "platforms": {}, "repos": ["x"]}, "contoh-b": {"age_days": 700, "commits4w": 22, "categories": [], "platforms": {}, "repos": ["x"]},
       "contoh-c": {"age_days": 1200, "commits4w": 31, "categories": [], "platforms": {}, "repos": ["x"]}, "contoh-f": {"age_days": 600, "commits4w": 58, "categories": [], "platforms": {}, "repos": ["x"]},
       "contoh-g": {"age_days": 1100, "commits4w": 0, "categories": [], "platforms": {}, "repos": ["x"]}, "contoh-h": {"age_days": 150, "commits4w": 74, "categories": ["Decentralized Physical Infrastructure (DePIN)"], "platforms": {}, "repos": ["x"]},
       "contoh-e": {"age_days": 1500, "commits4w": 2, "categories": [], "platforms": {}, "repos": ["x"]}}
DEX = {"contoh-c": {"chain": "ethereum", "vol24": 1.9e6, "liq": 4.1e6, "buys": 640, "sells": 410, "pool": "0xdemo1", "pairs": 3},
       "contoh-f": {"chain": "base", "vol24": 31e6, "liq": 9e6, "buys": 2100, "sells": 1300, "pool": "0xdemo2", "pairs": 4},
       "contoh-h": {"chain": "solana", "vol24": 15e6, "liq": 3.2e6, "buys": 5400, "sells": 3100, "pool": "0xdemo3", "pairs": 2}}
NEWS = [{"projects": ["CNTF"], "event": "Upgrade / Mainnet", "published": time.time() - 7200, "title": "Contoh RWA umumkan mainnet v2 bulan ini", "url": "https://example.invalid/news"}]
REV = {"contoh-a": 1.4e6, "contoh-b": 1.1e6, "contoh-c": 0.55e6, "contoh-e": 0.02e6, "contoh-f": 0.8e6}
POSTS = [{"sub": "CryptoCurrency", "title": "$CNTD Contoh Meme to the moon", "text": "", "score": 2500, "comments": 600, "url": "https://example.invalid/post", "created": 0}] * 5
POSTS += [{"sub": "defi", "title": "DD: Contoh Lending is undervalued, revenue and buyback", "text": "$CNTA accumulating", "score": 12, "comments": 3, "url": "https://example.invalid/dd", "created": 0}]
r = hunter.hunt(U, PROTO, REV, REV, set(), POSTS, [], now=time.time(), proto_rows=ROWS, cg_cats=CATS, details=DET, dex=DEX, news=NEWS)
r["demo"] = True; r["analyst_notes"] = r.get("analyst_notes", []); r["sources"]["x"] = {"ok": 0, "fail": 0, "off": True}
txt = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
p = os.path.join(root, "site", "crypto-sastra.src.html"); s = open(p, encoding="utf-8").read()
s = re.sub(r"/\*DEMO_HUNT_START\*/.*?/\*DEMO_HUNT_END\*/", lambda m: "/*DEMO_HUNT_START*/const DEMO_HUNT=" + txt + ";/*DEMO_HUNT_END*/", s, flags=re.S)
open(p, "w", encoding="utf-8").write(s)
print("demo hunt:", [(c["symbol"], round(c["score"]), c["narrative_score"], c["tier"], c["viral"], c["ghost"], c["early"]) for c in r["candidates"]], r["top_narratives"])

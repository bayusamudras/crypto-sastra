#!/usr/bin/env python3
"""
Crypto Sastra - Narrative Engine (pelengkap Hunter)

Top-down : sektor mana yang dialiri uang (kecepatan TVL, divergensi TVL vs harga koin, kategori CoinGecko).
Bottom-up: per koin -> TVL_Velocity 40% + Volume_Anomaly 30% + Dev_Activity 20% + Social_Velocity 10% = Narrative_Score 0-100.
Juga: anomali volume DEX (DexScreener), aktivitas developer & umur proyek (CoinGecko), katalis (catalysts.json + berita radar).

Catatan jujur: DefiLlama /categories hanya memetakan kategori ke daftar nama protokol, tanpa TVL. Kecepatan TVL sektor dihitung dari
/protocols (tvl dan change_7d/change_1m per protokol) yang dijumlahkan per sektor. Pelacakan dompet segar/smart money tidak tersedia
gratis; sistem memakai rasio beli/jual DEX 24 jam sebagai proksi akumulasi dan mencatatnya di data_gaps.
"""
import json, math, os, statistics, time
import scan

DAY = 86400
LEGACY = ("yield", "farm", "algo-stable", "reserve currency", "yield aggregator")

def sector_of(llama_category=None, cg_categories=None):
    """-> (tag, legacy, semua_tag). Kategori DefiLlama diutamakan, lalu kategori CoinGecko."""
    tags = []
    c = (llama_category or "").lower()
    if c:
        if "rwa" in c or "real world" in c: tags.append("RWA")
        elif "liquid staking" in c: tags.append("Liquid Staking")
        elif "restaking" in c: tags.append("Restaking")
        elif "lending" in c or "cdp" in c or "borrow" in c: tags.append("Lending")
        elif "derivative" in c or "option" in c or "perp" in c: tags.append("Derivatives")
        elif "dex" in c: tags.append("DEX")
        elif any(w in c for w in LEGACY): tags.append("Yield/Farm (usang)")
        elif "bridge" in c: tags.append("Bridge")
        elif "payment" in c or "stablecoin" in c: tags.append("Payments")
        elif "prediction" in c: tags.append("Prediction Market")
        elif "gaming" in c: tags.append("Gaming")
        else: tags.append(llama_category)
    CG = (("artificial intelligence", "AI"), ("ai agent", "AI"), ("depin", "DePIN"), ("decentralized physical", "DePIN"), ("real world assets", "RWA"),
          ("zero knowledge", "ZK"), ("layer 2", "L2"), ("gaming", "Gaming"), ("privacy", "Privacy"), ("meme", "Meme"), ("restaking", "Restaking"),
          ("liquid staking", "Liquid Staking"), ("perpetual", "Derivatives"), ("prediction market", "Prediction Market"), ("oracle", "Oracle"),
          ("data availability", "Modular/DA"), ("modular", "Modular/DA"))
    for name in cg_categories or []:
        n = name.lower()
        for key, tag in CG:
            if key in n and tag not in tags: tags.append(tag)
    if not tags: return "Tanpa sektor", False, []
    legacy = all(t.endswith("(usang)") for t in tags)
    return tags[0], legacy, tags

# ---------------------------------------------------------------- top-down: sektor
def sector_table(rows, universe, cg_cats=None):
    """rows: daftar protokol DefiLlama mentah. universe: koin CoinGecko. -> daftar sektor terurut menurut skor naratif."""
    agg = {}
    for p in rows or []:
        tag, legacy, _ = sector_of(p.get("category"))
        tvl = p.get("tvl") or 0
        if tvl <= 0: continue
        a = agg.setdefault(tag, {"tag": tag, "legacy": legacy, "tvl": 0.0, "p7": 0.0, "p30": 0.0, "n": 0})
        a["tvl"] += tvl; a["n"] += 1
        c7, c30 = p.get("change_7d"), p.get("change_1m")
        a["p7"] += tvl / (1 + c7 / 100) if c7 is not None and c7 > -99 else tvl
        a["p30"] += tvl / (1 + c30 / 100) if c30 is not None and c30 > -99 else tvl
    gid_tag = {}
    for p in rows or []:
        if p.get("gecko_id"): gid_tag.setdefault(p["gecko_id"], sector_of(p.get("category"))[0])
    price = {}
    for c in universe or []:
        t = gid_tag.get(c["id"]); ch = c.get("price_change_percentage_7d_in_currency"); mc = c.get("market_cap") or 0
        if t and ch is not None and mc > 0:
            a = price.setdefault(t, [0.0, 0.0, 0]); a[0] += mc * ch; a[1] += mc; a[2] += 1
    cg_tag = {}
    for r in cg_cats or []:
        t = sector_of(None, [r.get("name", "")])[0]
        if t != "Tanpa sektor": cg_tag[t] = r
    out = []
    for tag, a in agg.items():
        if a["tvl"] < 150e6: continue          # sektor terlalu kecil: bising
        ch7 = (a["tvl"] / a["p7"] - 1) * 100 if a["p7"] else None
        ch30 = (a["tvl"] / a["p30"] - 1) * 100 if a["p30"] else None
        pr = price.get(tag); p7 = (pr[0] / pr[1]) if pr and pr[1] else None
        out.append({"tag": tag, "legacy": a["legacy"], "tvl": a["tvl"], "tvl_ch7": ch7, "tvl_ch30": ch30, "price_ch7": p7,
                    "divergence": (ch7 - p7) if (ch7 is not None and p7 is not None) else None, "protocols": a["n"],
                    "coins": pr[2] if pr else 0, "cg": ({"mc_ch24": cg_tag[tag].get("market_cap_change_24h")} if tag in cg_tag else None)})
    for t, r in cg_tag.items():            # sektor tanpa TVL (AI, DePIN, ZK, ...) hanya dari kategori CoinGecko
        if t not in agg:
            out.append({"tag": t, "legacy": False, "tvl": None, "tvl_ch7": None, "tvl_ch30": None, "price_ch7": None, "divergence": None, "protocols": 0, "coins": 0,
                        "cg": {"mc_ch24": r.get("market_cap_change_24h")}})
    for s in out: s["velocity"] = tvl_velocity(s)
    out.sort(key=lambda s: -(s["velocity"] if s["velocity"] is not None else -1))
    return out

def tvl_velocity(s):
    """0-100: >= +20% TVL sektor dalam 7 hari = penuh. None bila TVL sektor tidak tersedia."""
    if s is None or s.get("tvl_ch7") is None: return None
    return round(100 * max(0.0, min(1.0, s["tvl_ch7"] / 20.0)), 1)

def top_narratives(sectors, n=2):
    ok = [s for s in sectors if not s["legacy"] and s["velocity"] and s["velocity"] > 0 and s["protocols"] >= 3]
    return ok[:n]

# ---------------------------------------------------------------- per koin: komponen Narrative_Score
def volume_anomaly(vol, mc, ch7, buys=None, sells=None, dex=False):
    """0-100. Vol/MC >= 20% tanpa lonjakan harga = akumulasi tersembunyi. Data gabungan CEX+DEX dikurangi bobotnya."""
    if not mc: return None, "market cap tidak diketahui"
    r = vol / mc; ch = abs(ch7) if ch7 is not None else 0
    if ch7 is not None and ch7 > 25: s, note = 20, f"vol/MC {r*100:.0f}% tetapi harga sudah naik {ch7:.0f}% (tidak tersembunyi lagi)"
    elif r >= .20 and ch <= 15: s, note = 100, f"vol/MC {r*100:.0f}% dengan harga datar ({ch7:+.0f}% 7h): pola akumulasi"
    elif r >= .10 and ch <= 25: s, note = 60, f"vol/MC {r*100:.0f}%, harga relatif tenang"
    elif r < .03: s, note = 0, f"vol/MC {r*100:.1f}%: tidak ada anomali"
    else: s, note = 30, f"vol/MC {r*100:.0f}%"
    if buys is not None and sells is not None and buys + sells >= 50:
        share = buys / (buys + sells); note += f"; porsi beli DEX {share*100:.0f}%"
        if share >= .55 and s >= 60: s = min(100, s + 10)
        if share <= .42: s = max(0, s - 15)
    if not dex: s = round(s * 0.7); note += " (gabungan CEX+DEX, bobot x0,7)"
    return s, note

def dev_score(commits4w, prev_commits=None):
    """0-100 dari commit 4 minggu; bonus bila naik >= 50% dari pengukuran sebelumnya."""
    if commits4w is None: return None, "tidak ada repo GitHub di CoinGecko"
    s = 0 if commits4w == 0 else 40 if commits4w < 10 else 70 if commits4w < 40 else 100
    note = f"{commits4w} commit / 4 minggu"
    if prev_commits and commits4w >= prev_commits * 1.5 and commits4w >= 5:
        s = min(100, s + 15); note += f" (naik dari {prev_commits})"
    return s, note

def social_velocity(w_now, w_prev, saturated):
    """0-100 dari rate of change bobot buzz. Naratif jenuh (sudah ramai) mendapat skor rendah."""
    if saturated: return 10, "pembahasan sudah jenuh"
    if w_prev is None: return None, "belum ada pengukuran sebelumnya"
    roc = (w_now + 1) / (w_prev + 1)
    s = 100 if roc >= 3 else 60 if roc >= 1.5 else 30 if roc >= .8 else 10
    return s, f"kecepatan {roc:.1f}x vs pengukuran sebelumnya"

def narrative_score(sector, vol_a, dev, soc):
    """Narrative_Score 0-100. Komponen tak diketahui diberi nilai netral 30 dan menurunkan keyakinan."""
    comp = {"tvl_velocity": (tvl_velocity(sector) if sector else None, .40), "volume_anomaly": (vol_a, .30), "dev_activity": (dev, .20), "social_velocity": (soc, .10)}
    total, known = 0.0, 0.0
    for k, (v, w) in comp.items():
        total += (v if v is not None else 30) * w
        if v is not None: known += w
    return round(total), round(known, 2), {k: v for k, (v, w) in comp.items()}

# ---------------------------------------------------------------- pengambil data
def fetch_cg_categories():
    try: return scan.jget("https://api.coingecko.com/api/v3/coins/categories", 25)
    except Exception as e: print("narrative: kategori CoinGecko gagal:", e); return []

def fetch_cg_detail(cid):
    """Umur, repo/commit, kategori, alamat kontrak dari satu panggilan CoinGecko (tanpa kunci)."""
    try:
        d = scan.jget(f"https://api.coingecko.com/api/v3/coins/{cid}?localization=false&tickers=false&market_data=false&community_data=false&developer_data=true&sparkline=false", 25)
    except Exception as e:
        print(f"narrative: detail {cid} gagal:", e); return None
    age = None
    if d.get("genesis_date"):
        try: age = (time.time() - time.mktime(time.strptime(d["genesis_date"], "%Y-%m-%d"))) / DAY
        except Exception: pass
    dd = d.get("developer_data") or {}
    repos = (d.get("links") or {}).get("repos_url", {}).get("github") or []
    return {"age_days": age, "commits4w": dd.get("commit_count_4_weeks") if repos else None, "repos": [r for r in repos if r][:2],
            "contributors": dd.get("pull_request_contributors"), "categories": d.get("categories") or [],
            "platforms": {k: v for k, v in (d.get("platforms") or {}).items() if k and v}}

DS_CHAIN = {"ethereum": "ethereum", "binance-smart-chain": "bsc", "base": "base", "arbitrum-one": "arbitrum", "solana": "solana",
            "polygon-pos": "polygon", "avalanche": "avalanche", "optimistic-ethereum": "optimism"}

def fetch_dex(platforms, mc):
    """DexScreener: volume, likuiditas, beli/jual 24 jam, dan pool terbesar (untuk candle GeckoTerminal)."""
    best = None
    for plat, addr in list(platforms.items())[:3]:
        if plat not in DS_CHAIN: continue
        try: d = scan.jget("https://api.dexscreener.com/latest/dex/tokens/" + addr, 20)
        except Exception: continue
        pairs = [p for p in (d.get("pairs") or []) if p.get("chainId") == DS_CHAIN[plat] and (p.get("baseToken") or {}).get("address", "").lower() == addr.lower()]
        if not pairs: continue
        vol = sum((p.get("volume") or {}).get("h24") or 0 for p in pairs); liq = sum((p.get("liquidity") or {}).get("usd") or 0 for p in pairs)
        buys = sum(((p.get("txns") or {}).get("h24") or {}).get("buys") or 0 for p in pairs)
        sells = sum(((p.get("txns") or {}).get("h24") or {}).get("sells") or 0 for p in pairs)
        top = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)
        cand = {"chain": DS_CHAIN[plat], "vol24": vol, "liq": liq, "buys": buys, "sells": sells, "pool": top.get("pairAddress"), "pairs": len(pairs)}
        if not best or cand["liq"] > best["liq"]: best = cand
    return best

# ---------------------------------------------------------------- katalis
def catalysts_for(sym, now, news=()):
    """Katalis manual (catalysts.json) + berita radar positif <= 72 jam. -> (daftar, poin -10..+10)."""
    rows = [r for r in scan._load_json("catalysts.json", {}).get("events", []) if r.get("symbol", "").upper() == sym.upper()]
    out, pts = [], 0
    for r in rows:
        try: ts = time.mktime(time.strptime(r["date"], "%Y-%m-%d"))
        except Exception: continue
        days = (ts - now) / DAY
        if days < -1 or days > 45: continue
        pol = r.get("polarity", 1)
        out.append({"date": r["date"], "days": round(days), "type": r.get("type", ""), "note": r.get("note", ""), "polarity": pol, "source": r.get("source"), "manual": True})
        if pol < 0 and days <= 45: pts -= 10
        elif pol > 0 and days <= 14: pts = max(pts, 10)
        elif pol > 0 and days <= 30: pts = max(pts, 8)
    GOOD = {"Upgrade / Mainnet", "Listing Exchange Besar", "Airdrop / Snapshot", "Burn / Buyback", "Kemitraan / Adopsi / Investasi"}
    for it in news or []:
        if sym.upper() in [p.upper() for p in it.get("projects", [])] and it.get("event") in GOOD and now - it.get("published", 0) <= 72 * 3600:
            out.append({"date": time.strftime("%Y-%m-%d", time.gmtime(it["published"])), "days": 0, "type": it["event"], "note": it["title"][:120], "polarity": 1, "source": it.get("url"), "manual": False})
            pts = max(pts, 4) if pts >= 0 else pts
    return out, max(-10, min(10, pts))

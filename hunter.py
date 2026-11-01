#!/usr/bin/env python3
"""
Crypto Sastra - Hunter
Mencari altcoin kecil yang jarang dibahas tetapi valuasinya murah dibanding fundamentalnya.

Alur: universe CoinGecko (ranking menengah-bawah) -> data DefiLlama (TVL, pendapatan) -> radar sosial
(Reddit, X bila kunci ada, CoinGecko Trending sebagai penanda "sudah viral") -> skor undervalue 0-100
-> checklist tesis Kalimasada -> hunt.json.

Prinsip: angka yang tidak tersedia ditulis "tidak diketahui", tidak dikarang. Skor adalah alat penyaring riset,
bukan sinyal beli. Hanya butuh Python 3.9+ (tanpa dependensi).
"""
import json, math, os, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
import scan  # memakai jget, TIER1, BACKERS, _load_json
import narrative

MC_MIN = float(os.getenv("HUNT_MC_MIN", "15e6"))
MC_MAX = float(os.getenv("HUNT_MC_MAX", "400e6"))
VOL_MIN = float(os.getenv("HUNT_VOL_MIN", "300000"))
PAGES = int(os.getenv("HUNT_PAGES", "3"))
HUNT_EVERY = int(os.getenv("HUNT_EVERY_MIN", "55")) * 60
X_BEARER = os.getenv("X_BEARER_TOKEN", "")
X_ANALYSTS = [h.strip().lstrip("@") for h in os.getenv("X_ANALYSTS", "").split(",") if h.strip()]  # akun yang Anda percaya
UA = {"User-Agent": "Mozilla/5.0 (compatible; CryptoSastra/1.0)"}

SUBS = ["CryptoCurrency", "CryptoMarkets", "altcoin", "defi", "ethfinance", "solana", "SatoshiStreetBets", "CryptoMoonShots"]
LOW_QUALITY_SUBS = {"CryptoMoonShots", "SatoshiStreetBets"}   # bobot lebih kecil: banyak promosi dan pump
BULL = ("undervalued", "underrated", "accumulate", "accumulating", "hidden gem", "under the radar", "cheap", "buyback",
        "revenue", "bullish", "early", "asymmetric", "re-rating", "rerating", "fundamentals")
BEAR = ("scam", "rug", "rugpull", "dump", "dumping", "dead", "overvalued", "avoid", "exit liquidity", "pump and dump",
        "shitcoin", "honeypot", "insolvent", "hack", "exploit")
EXCLUDE_SYM = {"USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDD", "PYUSD", "USDS", "BUSD", "USDP", "GUSD", "FRAX", "LUSD", "CRVUSD",
               "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "CBBTC", "RETH", "CBETH", "BTCB", "XAUT", "PAXG"}
EXCLUDE_WORDS = ("usd", "wrapped", "staked", "bridged", "restaked", "liquid staking", "tether", "gold", "stablecoin")

def get(url, headers=None, timeout=20):
    h = dict(UA); h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read()

def jget(url, headers=None, timeout=20):
    return json.loads(get(url, headers, timeout))

# ---------------------------------------------------------------- data pasar & fundamental
def fetch_universe(pages=PAGES):
    out = []
    for p in range(1, pages + 1):
        try:
            out += jget("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=%d"
                        "&price_change_percentage=7d,30d" % p)
        except Exception as e:
            print(f"hunter: CoinGecko halaman {p} gagal: {e}")
            break
        time.sleep(2.5)
    return out

def fetch_trending():
    try:
        d = jget("https://api.coingecko.com/api/v3/search/trending")
        return {c["item"]["id"] for c in d.get("coins", [])}
    except Exception:
        return set()

def fetch_protocols():
    """gecko_id -> {tvl, slug, category, chains}. Kosong bila DefiLlama tidak terjangkau."""
    try:
        rows = jget("https://api.llama.fi/protocols", timeout=40)
    except Exception as e:
        print("hunter: DefiLlama protocols gagal:", e); return {}
    out = {}
    for r in rows:
        g = r.get("gecko_id")
        if g and (g not in out or (r.get("tvl") or 0) > (out[g].get("tvl") or 0)):
            out[g] = {"tvl": r.get("tvl") or 0, "slug": r.get("slug"), "category": r.get("category"),
                      "chains": (r.get("chains") or [])[:4], "ch7": r.get("change_7d"), "ch1m": r.get("change_1m")}
    return out

def fetch_fees(kind):
    """slug -> total30d untuk dataType dailyFees / dailyRevenue."""
    try:
        d = jget("https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=" + kind, timeout=40)
    except Exception as e:
        print(f"hunter: DefiLlama {kind} gagal:", e); return {}
    return {(p.get("slug") or p.get("name", "")).lower(): p.get("total30d") for p in d.get("protocols", []) if p.get("total30d") is not None}

# ---------------------------------------------------------------- radar sosial
def _rss_posts(sub):
    root = ET.fromstring(get(f"https://www.reddit.com/r/{sub}/top/.rss?t=week", timeout=20))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        title = e.findtext("a:title", "", ns); link = e.find("a:link", ns)
        out.append({"sub": sub, "title": title, "text": "", "score": 1, "comments": 0, "url": link.get("href") if link is not None else "", "created": time.time()})
    return out

def fetch_reddit(subs=SUBS):
    posts, ok, fail = [], 0, 0
    for sub in subs:
        got = None
        for host in ("www.reddit.com", "old.reddit.com"):
            try:
                d = jget(f"https://{host}/r/{sub}/top.json?t=week&limit=100"); got = d["data"]["children"]; break
            except Exception:
                continue
        if got is not None:
            for c in got:
                p = c["data"]
                posts.append({"sub": sub, "title": p.get("title", ""), "text": (p.get("selftext") or "")[:1500], "score": p.get("score", 0),
                              "comments": p.get("num_comments", 0), "url": "https://www.reddit.com" + p.get("permalink", ""), "created": p.get("created_utc", 0),
                              "flair": p.get("link_flair_text") or ""})
            ok += 1
        else:
            try: posts += _rss_posts(sub); ok += 1
            except Exception: fail += 1
        time.sleep(1.2)
    return posts, {"ok": ok, "fail": fail}

def fetch_x():
    """Tweet ber-cashtag dari pencarian 'undervalued' dan dari akun analis pilihan Anda. Perlu X_BEARER_TOKEN (X API v2)."""
    if not X_BEARER: return [], {"ok": 0, "fail": 0, "off": True}
    H = {"Authorization": "Bearer " + X_BEARER}
    queries = [('(undervalued OR underrated OR "hidden gem" OR "under the radar" OR accumulating) (altcoin OR crypto OR token) -is:retweet lang:en has:cashtags', False)]
    if X_ANALYSTS:
        queries.append(("(" + " OR ".join("from:" + h for h in X_ANALYSTS[:20]) + ") has:cashtags -is:retweet", True))
    tweets, ok, fail = [], 0, 0
    for q, analyst in queries:
        url = ("https://api.twitter.com/2/tweets/search/recent?max_results=100&expansions=author_id&tweet.fields=public_metrics,entities,created_at"
               "&user.fields=public_metrics,username&query=" + urllib.parse.quote(q))
        try:
            d = jget(url, H); users = {u["id"]: u for u in d.get("includes", {}).get("users", [])}
            for t in d.get("data", []):
                u = users.get(t.get("author_id"), {})
                tweets.append({"text": t.get("text", ""), "tags": [c["tag"].upper() for c in t.get("entities", {}).get("cashtags", [])],
                               "likes": t.get("public_metrics", {}).get("like_count", 0), "followers": u.get("public_metrics", {}).get("followers_count", 0),
                               "user": u.get("username", ""), "analyst": analyst, "url": f"https://x.com/{u.get('username','i')}/status/{t.get('id')}"})
            ok += 1
        except Exception as e:
            print("hunter: X gagal:", e); fail += 1
    return tweets, {"ok": ok, "fail": fail}

def sentiment(text):
    t = text.lower()
    b = sum(t.count(w) for w in BULL); s = sum(t.count(w) for w in BEAR)
    return (b - s) / (b + s + 1)

def extract_mentions(posts, tweets, universe):
    """-> {coin_id: {reddit, x, analyst, weight, sent, top:[...]}} Pencocokan: $CASHTAG, simbol huruf besar >=4, nama satu kata >=5."""
    by_sym, by_word = {}, {}
    for c in universe:
        sym = (c.get("symbol") or "").upper()
        by_sym.setdefault(sym, []).append(c["id"])
        for w in {c["id"].lower(), (c.get("name") or "").lower()}:
            if " " not in w and len(w) >= 5: by_word.setdefault(w, []).append(c["id"])
    res = {}
    def hit(cid, kind, weight, sent, ref):
        m = res.setdefault(cid, {"reddit": 0, "x": 0, "analyst": 0, "weight": 0.0, "sent_sum": 0.0, "n": 0, "top": []})
        m[kind] += 1; m["weight"] += weight; m["sent_sum"] += sent; m["n"] += 1; m["top"].append((weight, ref))
    for p in posts:
        txt = p["title"] + " " + p["text"]
        ids = set()
        for tag in re.findall(r"\$([A-Za-z0-9]{2,10})\b", txt):
            ids.update(by_sym.get(tag.upper(), [])[:1])          # hanya koin dengan market cap terbesar untuk simbol kembar
        for tok in re.findall(r"\b[A-Z][A-Z0-9]{3,9}\b", txt): ids.update(by_sym.get(tok, [])[:1])
        for tok in set(re.findall(r"[a-z]{5,20}", txt.lower())): ids.update(by_word.get(tok, [])[:1])
        if not ids: continue
        q = 0.4 if p["sub"] in LOW_QUALITY_SUBS else 1.0
        dd = 1.6 if re.search(r"\b(dd|analysis|thesis|deep dive|research)\b", (p["title"] + " " + p.get("flair", "")).lower()) else 1.0
        w = q * dd * (1 + math.log1p(max(p["score"], 0)) / 3 + math.log1p(p["comments"]) / 5)
        s = sentiment(txt)
        for cid in ids: hit(cid, "reddit", w, s, {"src": "r/" + p["sub"], "title": p["title"][:140], "url": p["url"], "score": p["score"]})
    for t in tweets:
        ids = set()
        for tag in t["tags"]: ids.update(by_sym.get(tag, [])[:1])
        if not ids: continue
        w = (math.log10(10 + t["followers"]) / 2) * (1 + math.log10(1 + t["likes"]) / 2) * (2.0 if t["analyst"] else 1.0)
        s = sentiment(t["text"])
        for cid in ids:
            hit(cid, "x", w, s, {"src": "X @" + t["user"], "title": t["text"][:140], "url": t["url"], "score": t["likes"]})
            if t["analyst"]: res[cid]["analyst"] += 1
    for m in res.values():
        m["sent"] = round(m["sent_sum"] / max(m["n"], 1), 2)
        m["top"] = [r for _, r in sorted(m["top"], key=lambda x: -x[0])[:3]]
        m["weight"] = round(m["weight"], 2); del m["sent_sum"]
    return res

# ---------------------------------------------------------------- skor
def _unlocks(sym, now):
    """Unlock <= 90 hari dari unlocks.json (diisi manual). None bila simbol tidak tercatat."""
    data = scan._load_json("unlocks.json", {})
    rows = data.get(sym)
    if rows is None: return None
    out = []
    for r in rows:
        try: ts = time.mktime(time.strptime(r["date"], "%Y-%m-%d"))
        except Exception: continue
        if 0 <= ts - now <= 90 * 86400: out.append(r)
    return out

BUZZ0 = 10.0   # bobot sosial ~ "sudah ramai"

def score_candidate(c, info, rev30, fees30, buzz, trending, social_ok, now=None, unlocks=None, extra=None):
    """Skor undervalue 0-100 + rincian + checklist. Murni (tanpa jaringan) agar mudah diuji."""
    now = now or time.time()
    mc = c.get("market_cap") or 0; fdv = c.get("fully_diluted_valuation") or 0; vol = c.get("total_volume") or 0
    price = c.get("current_price") or 0; ath = c.get("ath") or 0
    ch7 = c.get("price_change_percentage_7d_in_currency"); ch30 = c.get("price_change_percentage_30d_in_currency")
    tvl = (info or {}).get("tvl") or 0
    parts, notes, risks = {}, [], []
    ex = extra or {}; det = ex.get("detail"); dex = ex.get("dex"); sector = ex.get("sector")
    # 1 valuasi (30)
    ps = (mc / (rev30 * 12)) if (rev30 and rev30 > 0 and mc) else None
    mc_tvl = (mc / tvl) if tvl and mc else None
    if ps is not None:
        pts = 30 if ps <= 5 else 24 if ps <= 12 else 16 if ps <= 25 else 8 if ps <= 60 else 2
        parts["valuasi"] = (pts, 30, f"MC/pendapatan tahunan {ps:.1f}x")
        if ps <= 12: notes.append(f"Valuasi murah terhadap pendapatan protokol (MC {ps:.1f}x pendapatan tahunan)")
        if ps > 60: risks.append(f"Mahal terhadap pendapatan (MC {ps:.0f}x pendapatan tahunan)")
    elif mc_tvl is not None:
        pts = 22 if mc_tvl <= .15 else 14 if mc_tvl <= .4 else 8 if mc_tvl <= 1 else 3
        parts["valuasi"] = (pts, 30, f"MC/TVL {mc_tvl:.2f} (pendapatan tidak tersedia)")
        if mc_tvl <= .4: notes.append(f"MC hanya {mc_tvl:.2f}x TVL")
    else:
        parts["valuasi"] = (6, 30, "tanpa data pendapatan atau TVL")
        risks.append("Tidak ada data pendapatan/TVL untuk menilai valuasi")
    # 1b early-stage (< 1 tahun, belum ada pendapatan): valuasi = FDV vs rekan sektor + aktivitas developer
    age = det.get("age_days") if det else None
    dsc, dnote = narrative.dev_score(det.get("commits4w") if det else None, ex.get("prev_commits"))
    early = age is not None and age < 365 and ps is None
    if early:
        med = ex.get("peer_med_fdv"); fr = (fdv / med) if (fdv and med) else None
        peer = 16 if fr is None else 30 if fr <= .3 else 24 if fr <= .6 else 16 if fr <= 1 else 8 if fr <= 2 else 2
        pts = round(.5 * peer + .5 * 30 * ((dsc if dsc is not None else 30) / 100))
        parts["valuasi"] = (pts, 30, f"early-stage ({age:.0f} hari): FDV vs rekan sektor " + (f"{fr:.2f}x" if fr is not None else "tidak diketahui") + f"; dev: {dnote}")
        notes.append("Proyek <1 tahun: valuasi dinilai dari FDV vs rekan sektor dan aktivitas developer, bukan pendapatan")
    # 2 suplai (15)
    r = (fdv / mc) if (fdv and mc) else None
    if r is None: sp, st = 6, "FDV tidak diketahui"
    else: sp = 15 if r <= 1.15 else 12 if r <= 1.5 else 7 if r <= 2 else 3 if r <= 3 else 0; st = f"FDV/MC {r:.2f}"
    if r and r > 2: risks.append(f"FDV {r:.1f}x market cap: potensi dilusi besar")
    big = [u for u in (unlocks or []) if (u.get("pct_circ") or 0) >= 5]
    if big: sp = max(0, sp - 8); st += f"; unlock ≥5% dalam 90 hari ({big[0]['date']})"; risks.append("Ada unlock besar dalam 90 hari: " + big[0]["date"])
    tot_sup = c.get("max_supply") or c.get("total_supply"); circ = c.get("circulating_supply")
    circ_pct = (circ / tot_sup) if (circ and tot_sup) else None
    if circ_pct is not None and circ_pct < .25:
        sp = max(0, sp - 4); st += f"; hanya {circ_pct*100:.0f}% suplai beredar"; risks.append(f"Suplai beredar hanya {circ_pct*100:.0f}% dari total: risiko High FDV / Low Float")
    if unlocks is None and r and r > 1.5: risks.append("FDV > 1,5x MC dan jadwal unlock tidak tercatat: cek Tokenomist/TokenUnlocks sebelum bertindak")
    parts["suplai"] = (sp, 15, st)
    # 3 drawdown (10)
    dd = (1 - price / ath) if (ath and price) else None
    if dd is None: parts["drawdown"] = (3, 10, "ATH tidak diketahui")
    else:
        pts = 10 if .5 <= dd <= .9 else 6 if .3 <= dd < .5 else 4 if dd > .9 else 2
        parts["drawdown"] = (pts, 10, f"{dd*100:.0f}% di bawah ATH")
        if dd > .9: risks.append("Turun >90% dari ATH: bisa berarti proyek sekarat, bukan diskon")
    # 4 likuiditas (10)
    vm = (vol / mc) if mc else 0
    pts = 10 if .02 <= vm <= .4 else 6 if .01 <= vm < .02 else 5 if .4 < vm <= 1 else 1 if vm < .01 else 0
    parts["likuiditas"] = (pts, 10, f"volume/MC {vm*100:.1f}%")
    if vm < .01: risks.append("Likuiditas tipis: slippage tinggi saat masuk dan keluar")
    if vm > .6: risks.append("Volume sangat tinggi terhadap MC: tanda spekulasi/hype")
    # 5 fase harga (10)
    if ch30 is None: parts["fase"] = (4, 10, "perubahan 30h tidak diketahui")
    else:
        pts = 10 if -30 <= ch30 <= 30 else 6 if (30 < ch30 <= 80 or -60 <= ch30 < -30) else 1 if ch30 > 80 else 3
        if ch7 is not None and ch7 > 40: pts = max(0, pts - 3)
        parts["fase"] = (pts, 10, f"30h {ch30:+.0f}%" + (f", 7h {ch7:+.0f}%" if ch7 is not None else ""))
        if ch30 > 80: risks.append("Sudah naik tajam 30 hari: kemungkinan sudah di fase euforia")
    # 6 obscurity (25)
    b = (buzz or {}).get("weight", 0.0)
    viral = trending or b >= BUZZ0
    if not social_ok: parts["senyap"] = (12, 25, "radar sosial tidak terjangkau, netral")
    else:
        pts = 0 if trending else round(25 * (1 - min(1, b / BUZZ0)))
        parts["senyap"] = (pts, 25, "trending CoinGecko" if trending else f"bobot buzz {b:.1f} (ambang ramai {BUZZ0:.0f})")
    # insight analis (maks +8 / -8)
    bonus = 0
    if buzz and buzz.get("n"):
        s = buzz.get("sent", 0)
        if buzz.get("analyst") or buzz.get("x"): bonus = round(8 * max(-1, min(1, s * 3)))
        elif s < -0.2: bonus = -4
    base = max(0, min(100, sum(p[0] for p in parts.values()) + bonus))
    # Narrative engine: TVL_Velocity 40 + Volume_Anomaly 30 + Dev_Activity 20 + Social_Velocity 10
    dexok = bool(dex and dex.get("vol24") is not None)
    va, vnote = narrative.volume_anomaly(dex["vol24"] if dexok else vol, mc, ch7, dex.get("buys") if dexok else None, dex.get("sells") if dexok else None, dex=dexok)
    soc, snote = narrative.social_velocity(b, ex.get("w_prev"), viral)
    nscore, nconf, ncomp = narrative.narrative_score(sector, va, dsc, soc)
    legacy = bool(sector and sector.get("legacy")) or ex.get("legacy", False)
    ghost = False
    if det and det.get("commits4w") == 0 and age is not None and age > 365 and ps is None and (mc_tvl is None or mc_tvl > 1): ghost = True
    if dd is not None and dd > .9 and vm < .01: ghost = True
    cat, cat_pts = ex.get("catalysts", ([], 0))
    penalty = (10 if legacy else 0) + (15 if ghost else 0)
    if legacy: risks.append("Sektor usang (yield/farm/algo-stable): senyap di sini biasanya berarti ditinggalkan, bukan tersembunyi")
    if ghost: risks.append("Indikasi proyek mati: tanpa commit developer, tanpa pendapatan, dan likuiditas/harga runtuh")
    total = max(0, min(100, round(.7 * base + .3 * nscore) + cat_pts - penalty))
    for c_ in cat:
        if c_["polarity"] < 0: risks.append(f"Katalis negatif {c_['date']}: {c_['note']}")
        else: notes.append(f"Katalis {c_['date']} ({c_['type']}): {c_['note']}")
    # checklist Kalimasada
    tier1 = [v for v in scan.BACKERS.get((c.get("symbol") or "").upper(), ([], ""))[0] if v in scan.TIER1] if (c.get("symbol") or "").upper() in scan.BACKERS else None
    def chk(label, ok, detail): return {"label": label, "status": "unknown" if ok is None else ("pass" if ok else "fail"), "detail": detail}
    checklist = [
        chk("Kecil (market cap < $400 jt)", mc < 400e6, f"MC ${mc/1e6:.0f} jt"),
        chk("FDV/MC ≤ 1,5", None if r is None else r <= 1.5, st.split(";")[0]),
        chk("Tanpa unlock besar dalam 90 hari", None if unlocks is None else not big, "isi unlocks.json untuk memastikan" if unlocks is None else (f"{len(unlocks)} unlock tercatat" )),
        chk("Pendapatan nyata", None if (rev30 is None and fees30 is None) else bool(rev30 and rev30 > 0), "tidak ada data DefiLlama" if rev30 is None else f"${rev30/1e6:.2f} jt / 30 hari"),
        chk("Valuasi murah (MC ≤ 12x pendapatan tahunan atau ≤ 0,4x TVL)", None if (ps is None and mc_tvl is None) else ((ps is not None and ps <= 12) or (ps is None and mc_tvl <= .4)), parts["valuasi"][2]),
        chk("Belum viral", None if not social_ok else not viral, parts["senyap"][2]),
        chk("Fase 1-2 (belum euforia)", None if ch30 is None or dd is None else (ch30 < 40 and dd > .4), parts["fase"][2]),
        chk("Sektor naratif aktif (bukan usang, TVL tidak turun)", None if sector is None else (not legacy and (sector.get("tvl_ch7") is None or sector["tvl_ch7"] > 0)), "sektor tidak terdeteksi" if sector is None else f"{sector['tag']}" + (f", TVL 7h {sector['tvl_ch7']:+.0f}%" if sector.get("tvl_ch7") is not None else ", TVL sektor tidak tersedia")),
        chk("Developer aktif", None if dsc is None else dsc >= 40, dnote),
        chk("Anomali volume (akumulasi tersembunyi)", None if va is None else va >= 60, vnote),
        chk("Katalis dalam 30 hari", None if (det is None and not cat) else any(x["polarity"] > 0 and x["days"] <= 30 for x in cat), "; ".join(f"{x['type']} {x['date']}" for x in cat) or "tidak ada katalis tercatat (isi catalysts.json)"),
        chk("Backer Tier-1 ≥ 3", None if tier1 is None else len(tier1) >= 3, "data investor perlu verifikasi manual" if tier1 is None else ", ".join(tier1) or "tidak ada"),
    ]
    known = [x for x in checklist if x["status"] != "unknown"]
    return {"score": total, "hunter_score": base, "narrative_score": nscore, "narrative_conf": nconf, "narrative": ncomp, "narrative_notes": {"volume": vnote, "dev": dnote, "social": snote},
            "ghost": ghost, "legacy": legacy, "early": early, "catalysts": cat, "catalyst_pts": cat_pts, "penalty": penalty, "bonus": bonus, "parts": {k: {"pts": v[0], "max": v[1], "note": v[2]} for k, v in parts.items()},
            "checklist": checklist, "pass": sum(1 for x in known if x["status"] == "pass"), "known": len(known), "total": len(checklist),
            "viral": bool(viral), "notes": notes, "risks": risks, "ps": ps, "mc_tvl": mc_tvl, "fdv_mc": r, "dd": dd, "vol_mc": vm}

def tier_label(score, passed, known, ghost=False, legacy=False, conf=1.0):
    if ghost: return "lemah"
    if score >= 70 and known >= 5 and passed / max(known, 1) >= .7 and not legacy and conf >= .5: return "prioritas"
    if score >= 55 and not legacy: return "pantau"
    return "lemah"

# ---------------------------------------------------------------- orkestrasi
ENRICH_N = int(os.getenv("HUNT_ENRICH", "20"))     # jumlah kandidat teratas yang diperkaya (detail CoinGecko + DexScreener)

def is_excluded(c):
    sym = (c.get("symbol") or "").upper(); name = (c.get("name") or "").lower()
    return sym in EXCLUDE_SYM or any(w in name for w in EXCLUDE_WORDS)

def fetch_proto_rows():
    try: return jget("https://api.llama.fi/protocols", timeout=40)
    except Exception as e: print("hunter: DefiLlama protocols gagal:", e); return []

def index_protocols(rows):
    out = {}
    for r in rows:
        g = r.get("gecko_id")
        if g and (g not in out or (r.get("tvl") or 0) > (out[g].get("tvl") or 0)):
            out[g] = {"tvl": r.get("tvl") or 0, "slug": r.get("slug"), "category": r.get("category"), "chains": (r.get("chains") or [])[:4]}
    return out

def hunt(universe=None, protocols=None, rev=None, fees=None, trending=None, posts=None, tweets=None, now=None, top=40,
         proto_rows=None, cg_cats=None, details=None, dex=None, news=(), prev=None, enrich_n=ENRICH_N):
    now = now or time.time()
    universe = universe if universe is not None else fetch_universe()
    rows = proto_rows if proto_rows is not None else (fetch_proto_rows() if protocols is None else [])
    protocols = protocols if protocols is not None else index_protocols(rows)
    rev = rev if rev is not None else fetch_fees("dailyRevenue"); fees = fees if fees is not None else fetch_fees("dailyFees")
    trending = trending if trending is not None else fetch_trending()
    if posts is None: posts, rs = fetch_reddit()
    else: rs = {"ok": 1, "fail": 0}
    if tweets is None: tweets, xs = fetch_x()
    else: xs = {"ok": 1, "fail": 0}
    social_ok = rs["ok"] > 0 or xs.get("ok", 0) > 0
    mentions = extract_mentions(posts, tweets, universe) if social_ok else {}
    cats = cg_cats if cg_cats is not None else (narrative.fetch_cg_categories() if (rows or universe) else [])
    sectors = narrative.sector_table(rows, universe, cats)
    sec_by_tag = {s["tag"]: s for s in sectors}
    hot = [s["tag"] for s in narrative.top_narratives(sectors)]
    # median FDV rekan sektor (untuk valuasi early-stage)
    peers = {}
    for c in universe:
        info = protocols.get(c["id"])
        if info and c.get("fully_diluted_valuation"):
            peers.setdefault(narrative.sector_of(info.get("category"))[0], []).append(c["fully_diluted_valuation"])
    med = {t: sorted(v)[len(v) // 2] for t, v in peers.items() if len(v) >= 3}
    hist = (prev or {}).get("hist", {})
    seed = scan._load_json("hunt_seed.json", {}); manual = {m["symbol"]: m for m in seed.get("manual", [])}
    base_rows = []
    for c in universe:
        mc = c.get("market_cap") or 0
        if is_excluded(c) or not (MC_MIN <= mc <= MC_MAX) or (c.get("total_volume") or 0) < VOL_MIN: continue
        info = protocols.get(c["id"]); sym = c["symbol"].upper(); slug = ((info or {}).get("slug") or "")
        tag = narrative.sector_of((info or {}).get("category"))[0] if info else None
        base_rows.append({"c": c, "info": info, "sym": sym, "slug": slug, "tag": tag,
                          "rv": rev.get(slug.lower()) if info else None, "fe": fees.get(slug.lower()) if info else None,
                          "unl": _unlocks(sym, now), "cats": narrative.catalysts_for(sym, now, news)})
    def score(r, det=None, dx=None):
        c = r["c"]; tag = r["tag"]; legacy = False
        if det:
            t2, legacy, _ = narrative.sector_of((r["info"] or {}).get("category"), det.get("categories"))
            tag = t2 if t2 != "Tanpa sektor" else tag
        sector = sec_by_tag.get(tag) if tag else None
        if sector is None and tag and tag != "Tanpa sektor":
            sector = {"tag": tag, "legacy": narrative.sector_of(None, [tag])[1] or tag.endswith("(usang)"), "tvl_ch7": None}
        h = hist.get(c["id"], {})
        ex = {"detail": det, "dex": dx, "sector": sector, "peer_med_fdv": med.get(tag), "prev_commits": h.get("commits"), "w_prev": h.get("w"), "catalysts": r["cats"]}
        s = score_candidate(c, r["info"], r["rv"], r["fe"], mentions.get(c["id"]), c["id"] in trending, social_ok, now, r["unl"], ex)
        return s, tag, sector
    for r in base_rows: r["s"], r["tag_f"], r["sector"] = score(r)
    base_rows.sort(key=lambda r: -r["s"]["score"])
    n_det = 0
    for r in base_rows[:enrich_n]:
        cid = r["c"]["id"]
        if details is not None: det = details.get(cid)
        else:
            det = narrative.fetch_cg_detail(cid); time.sleep(2.5)
        if det is None: continue
        n_det += 1
        dx = (dex or {}).get(cid) if dex is not None else (narrative.fetch_dex(det["platforms"], r["c"].get("market_cap")) if det.get("platforms") else None)
        r["det"], r["dex"] = det, dx
        r["s"], r["tag_f"], r["sector"] = score(r, det, dx)
    cands, new_hist = [], {}
    for r in base_rows:
        c, s = r["c"], r["s"]; b = mentions.get(c["id"]) or {}; det = r.get("det") or {}; dx = r.get("dex")
        sec = r["sector"]
        new_hist[c["id"]] = {"w": b.get("weight", 0), "commits": det.get("commits4w") if det.get("commits4w") is not None else (hist.get(c["id"]) or {}).get("commits")}
        cands.append({
            "id": c["id"], "symbol": r["sym"], "name": c["name"], "rank": c.get("market_cap_rank"), "price": c.get("current_price"),
            "mc": c.get("market_cap"), "fdv": c.get("fully_diluted_valuation"), "vol": c.get("total_volume"),
            "chg7": c.get("price_change_percentage_7d_in_currency"), "chg30": c.get("price_change_percentage_30d_in_currency"),
            "ath_dd": s["dd"], "tvl": (r["info"] or {}).get("tvl"), "category": (r["info"] or {}).get("category"), "chains": (r["info"] or {}).get("chains"),
            "rev30": r["rv"], "fees30": r["fe"], "ps": s["ps"], "mc_tvl": s["mc_tvl"], "fdv_mc": s["fdv_mc"], "vol_mc": s["vol_mc"],
            "score": s["score"], "hunter_score": s["hunter_score"], "narrative_score": s["narrative_score"], "narrative_conf": s["narrative_conf"],
            "narrative": s["narrative"], "narrative_notes": s["narrative_notes"], "bonus": s["bonus"], "penalty": s["penalty"],
            "parts": s["parts"], "checklist": s["checklist"], "pass": s["pass"], "known": s["known"], "total": s["total"],
            "tier": tier_label(s["score"], s["pass"], s["known"], s["ghost"], s["legacy"], s["narrative_conf"]),
            "viral": s["viral"], "ghost": s["ghost"], "legacy": s["legacy"], "early": s["early"], "enriched": bool(det),
            "sector": ({"tag": sec["tag"], "tvl_ch7": sec.get("tvl_ch7"), "legacy": sec.get("legacy"), "hot": sec["tag"] in hot} if sec else None),
            "age_days": det.get("age_days"), "dev": ({"commits4w": det.get("commits4w"), "repos": det.get("repos")} if det else None),
            "dex": ({k: dx[k] for k in ("chain", "vol24", "liq", "buys", "sells", "pairs")} if dx else None),
            "scan_ref": ({"chain": dx["chain"], "pool": dx["pool"]} if dx and dx.get("pool") else None),
            "catalysts": s["catalysts"], "notes": s["notes"], "risks": s["risks"],
            "buzz": {"reddit": b.get("reddit", 0), "x": b.get("x", 0), "analyst": b.get("analyst", 0), "weight": b.get("weight", 0), "sent": b.get("sent"), "top": b.get("top", [])},
            "manual": manual.get(r["sym"]),
            "links": {"coingecko": "https://www.coingecko.com/en/coins/" + c["id"], "defillama": ("https://defillama.com/protocol/" + r["slug"]) if r["slug"] else None}})
    cands.sort(key=lambda x: -x["score"])
    gaps = ["Dompet segar / smart money tidak tersedia gratis: akumulasi diproksikan dari rasio beli/jual DEX 24 jam (DexScreener).",
            "Jadwal unlock dan backer Tier-1 tetap manual (unlocks.json, scan.py); isi sebelum mengambil keputusan.",
            "Katalis roadmap diisi manual di catatan catalysts.json atau terdeteksi dari berita radar 72 jam terakhir."]
    if not rows: gaps.append("DefiLlama tidak terjangkau: sektor dan TVL velocity tidak dihitung (nilai netral).")
    if not n_det and cands: gaps.append("Detail CoinGecko (umur, commit developer, alamat kontrak) tidak terjangkau: komponen dev dan DEX netral.")
    return {"generated_at": int(now), "mode": "live", "universe": len(universe), "filtered": len(cands), "enriched": n_det,
            "filters": {"mc_min": MC_MIN, "mc_max": MC_MAX, "vol_min": VOL_MIN},
            "sources": {"coingecko": bool(universe), "defillama": bool(rows or protocols), "reddit": rs, "x": xs, "trending": len(trending), "posts": len(posts), "tweets": len(tweets), "dexscreener": any(c["dex"] for c in cands)},
            "sectors": [{k: v for k, v in s.items()} for s in sectors[:16]], "top_narratives": hot,
            "candidates": cands[:top], "hist": new_hist, "data_gaps": gaps, "manual": seed.get("manual", []), "analyst_notes": seed.get("analyst_notes", []), "seed_asof": seed.get("asof")}

def handoff(res, n=3):
    """Kandidat teratas (prioritas/pantau, punya pool DEX) yang layak dioper ke Scan Institusional (SMC/FVG/OTE)."""
    out = [c for c in res.get("candidates", []) if c["tier"] in ("prioritas", "pantau") and c.get("scan_ref") and not c.get("viral")]
    return out[:n]

def empty():
    seed = scan._load_json("hunt_seed.json", {})
    return {"generated_at": 0, "mode": "kosong", "universe": 0, "filtered": 0, "candidates": [], "sources": {}, "sectors": [], "top_narratives": [], "data_gaps": [],
            "manual": seed.get("manual", []), "analyst_notes": seed.get("analyst_notes", []), "seed_asof": seed.get("asof")}

def run(load, dump, force=False, news=()):
    """Mode Actions: jalankan bila hasil terakhir lebih tua dari HUNT_EVERY. Riwayat buzz/commit ikut disimpan (untuk kecepatan sosial dan tren developer)."""
    prev = load("hunt.json", None)
    if prev and not force and time.time() - prev.get("generated_at", 0) < HUNT_EVERY: return prev
    res = hunt(news=news, prev=prev)
    if not res["candidates"] and prev and prev.get("candidates"):       # sumber gagal: pertahankan hasil lama, jangan menimpanya dengan kosong
        print("hunter: tanpa kandidat, hasil lama dipertahankan"); return prev
    if not res["candidates"]: print("hunter: tanpa kandidat; status sumber ditulis agar website menjelaskan penyebabnya:", res["sources"])
    dump("hunt.json", res)
    return res

if __name__ == "__main__":
    r = hunt()
    print(json.dumps({k: r[k] for k in ("universe", "filtered", "enriched", "sources", "top_narratives")}, indent=1))
    for c in r["candidates"][:15]:
        print(f"{c['score']:5.1f} {c['symbol']:8} MC ${(c['mc'] or 0)/1e6:6.0f}jt  {c['tier']:9} narasi {c['narrative_score']:3} lolos {c['pass']}/{c['known']}")

#!/usr/bin/env python3
"""
Crypto Sastra - Scan Institusional
Menerapkan doktrin "Kalimasada" (Barbell, Paradox of Choices, Lifecycle, Moonbag) lewat 6 modul:
  1 Narasi & Lifecycle  2 On-chain & Fundamental  3 Tokenomics & Supply  4 Smart Money
  5 Makro & Regulasi    6 Eksekusi SMC/ICT & Manajemen Risiko  -> skor akhir /10.

Prinsip data: setiap angka diberi label sumber & kualitas. Bila data gratis tidak tersedia, modul menulis
"N/A" dan menaruhnya di data_gaps, bukan mengarang. Hanya butuh Python 3.9+ (tanpa dependensi).
"""
import json, math, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 CryptoSastra/1.0"}

def _get(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()

def jget(url, timeout=15):
    return json.loads(_get(url, timeout))

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0

# ---------------------------------------------------------------- data statis (editable, verifikasi manual)
COINS = {  # symbol: cg id, narasi, nama chain/protokol DefiLlama bila ada, kode CoinMetrics bila ada
    "BTC": {"cg": "bitcoin", "name": "Bitcoin", "narr": "Store of value dan adopsi institusi (ETF, treasury perusahaan)", "cm": "btc"},
    "ETH": {"cg": "ethereum", "name": "Ethereum", "narr": "Institutional DeFi, RWA, dan lapisan settlement L2", "chain": "Ethereum", "cm": "eth"},
    "SOL": {"cg": "solana", "name": "Solana", "narr": "L1 throughput tinggi (PayFi, DEX, aplikasi konsumer)", "chain": "Solana"},
    "BNB": {"cg": "binancecoin", "name": "BNB", "narr": "Ekosistem exchange dan chain BNB", "chain": "BSC"},
    "XRP": {"cg": "ripple", "name": "XRP", "narr": "Stablecoin dan Payments lintas negara", "chain": "XRPL"},
    "ADA": {"cg": "cardano", "name": "Cardano", "narr": "L1 berbasis riset dengan ekosistem DeFi kecil", "chain": "Cardano"},
    "DOGE": {"cg": "dogecoin", "name": "Dogecoin", "narr": "Meme dan barometer sentimen ritel"},
    "AVAX": {"cg": "avalanche-2", "name": "Avalanche", "narr": "L1 institusional dan subnet (RWA)", "chain": "Avalanche"},
    "LINK": {"cg": "chainlink", "name": "Chainlink", "narr": "Oracle dan infrastruktur RWA/CCIP"},
    "TON": {"cg": "the-open-network", "name": "Toncoin", "narr": "Distribusi lewat Telegram (L1 konsumer)", "chain": "TON"},
    "ARB": {"cg": "arbitrum", "name": "Arbitrum", "narr": "L2 Ethereum", "chain": "Arbitrum"},
    "OP": {"cg": "optimism", "name": "Optimism", "narr": "L2 Ethereum dan Superchain", "chain": "OP Mainnet"},
    "AAVE": {"cg": "aave", "name": "Aave", "narr": "Institutional DeFi (lending)"},
    "UNI": {"cg": "uniswap", "name": "Uniswap", "narr": "Institutional DeFi (DEX)"},
    "SUI": {"cg": "sui", "name": "Sui", "narr": "L1 throughput tinggi (Move)", "chain": "Sui"},
    "PEPE": {"cg": "pepe", "name": "Pepe", "narr": "Meme (sentimen ritel murni)"},
}
TIER1 = {"a16z", "Paradigm", "Polychain", "Pantera", "Multicoin", "Sequoia", "Jump", "Binance Labs", "Coinbase Ventures",
         "Lightspeed", "Framework", "Dragonfly", "Galaxy", "USV"}
# Pengetahuan umum per Jun 2026, WAJIB diverifikasi di ChainBroker/Crunchbase sebelum bertindak.
BACKERS = {
    "BTC": ([], "Tidak berbasis VC (peluncuran adil, 2009)"), "ETH": ([], "ICO 2014, bukan model VC token"),
    "XRP": ([], "Dikendalikan korporasi (Ripple), bukan model VC token"), "BNB": ([], "Korporasi (Binance), bukan model VC token"),
    "ADA": ([], "ICO (IOHK), bukan model VC token"), "DOGE": ([], "Komunitas"), "LINK": ([], "ICO 2017"),
    "TON": ([], "TON Foundation / ekosistem Telegram"), "PEPE": ([], "Komunitas, tanpa VC"),
    "SOL": (["a16z", "Polychain", "Multicoin", "Jump"], "Riwayat eksposur FTX/Alameda"),
    "SUI": (["a16z", "Jump", "Coinbase Ventures", "Binance Labs"], "Unlock investor awal berjadwal panjang"),
    "AVAX": (["a16z", "Polychain"], "Ava Labs; investor lain di luar daftar Tier-1"),
    "ARB": (["Lightspeed", "Pantera", "Polychain"], "Offchain Labs"),
    "OP": (["a16z", "Paradigm"], "Optimism Foundation / OP Labs"),
    "UNI": (["a16z", "Paradigm", "USV", "Polychain"], "Uniswap Labs"),
    "AAVE": (["Framework"], "Informasi investor tidak lengkap, verifikasi manual"),
}
PLAYBOOK = {
    "a16z": "Playbook a16z: inkubasi dalam dan pembangunan ekosistem, horizon panjang.",
    "Pantera": "Playbook Pantera: pendanaan seed awal, rawan distribusi ke ritel saat listing exchange tier-1 (Greatest Fool).",
    "Animoca": "Playbook Animoca: dominasi ceruk (GameFi/NFT), ikan besar di kolam kecil.",
}
DEFL = {  # (status, catatan), pengetahuan umum, verifikasi sebelum bertindak
    "BNB": ("Ada", "Burn otomatis berkala (auto-burn) berbasis harga dan blok."),
    "ETH": ("Parsial", "EIP-1559 membakar fee dasar; net deflasi hanya saat aktivitas jaringan tinggi."),
    "SOL": ("Parsial", "Sebagian fee dasar dibakar; emisi staking masih lebih besar."),
    "AVAX": ("Parsial", "Fee transaksi dibakar; emisi staking tetap berjalan."),
    "XRP": ("Parsial", "Fee dibakar (kecil); suplai escrow dilepas berkala."),
    "TON": ("Parsial", "Sebagian fee dibakar."), "SUI": ("Parsial", "Sebagian fee dibakar; unlock investor jadi beban utama."),
    "AAVE": ("Perlu verifikasi", "Program buyback dari pendapatan protokol; cek status tata kelola terbaru."),
    "UNI": ("Perlu verifikasi", "Fee-switch/burn bergantung keputusan governance terbaru."),
    "LINK": ("Perlu verifikasi", "Tidak ada burn; ada akumulasi cadangan dari pendapatan, cek kebijakan terbaru."),
    "BTC": ("Tidak berlaku", "Suplai tetap 21 juta; halving memotong emisi."),
    "DOGE": ("Tidak ada", "Inflasi tetap sekitar 5 miliar koin per tahun."), "ADA": ("Tidak ada", "Suplai maksimum tetap; emisi dari cadangan."),
    "ARB": ("Tidak ada", "Pendapatan sequencer tidak otomatis dibeli-bakar, cek proposal governance."),
    "OP": ("Tidak ada", "Pendapatan sequencer tidak otomatis dibeli-bakar, cek proposal governance."),
    "PEPE": ("Tidak ada", "Suplai tetap, tanpa pendapatan protokol."),
}
SCAN_SYMBOLS = list(COINS)

def _load_json(name, default):
    try: return json.load(open(os.path.join(HERE, name), encoding="utf-8"))
    except Exception: return default

# ---------------------------------------------------------------- pengambil data (semua gratis, tanpa kunci)
def fetch_markets(symbols=None):
    ids = ",".join(COINS[s]["cg"] for s in (symbols or COINS))
    rows = jget("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=" + ids +
                "&price_change_percentage=7d,30d&per_page=100")
    by = {r["id"]: r for r in rows}
    return {s: by.get(COINS[s]["cg"]) for s in (symbols or COINS)}

def fetch_candles(sym, interval):
    """OHLCV tertutup+berjalan, urut lama ke baru. Binance (endpoint data publik) lalu OKX sebagai cadangan."""
    for base in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            arr = jget(f"{base}/api/v3/klines?symbol={sym}USDT&interval={interval}&limit=400")
            if arr: return [{"t": a[0], "o": float(a[1]), "h": float(a[2]), "l": float(a[3]), "c": float(a[4]), "v": float(a[5])} for a in arr]
        except Exception: pass
    try:
        bar = {"1d": "1D", "1w": "1W"}[interval]
        d = jget(f"https://www.okx.com/api/v5/market/candles?instId={sym}-USDT&bar={bar}&limit=300")["data"]
        return [{"t": int(a[0]), "o": float(a[1]), "h": float(a[2]), "l": float(a[3]), "c": float(a[4]), "v": float(a[5])} for a in reversed(d)]
    except Exception:
        return []

_LLAMA = {"t": 0, "chains": None, "protocols": None}
def llama():
    if time.time() - _LLAMA["t"] > 1800 or not _LLAMA["chains"]:
        try:
            _LLAMA["chains"] = jget("https://api.llama.fi/v2/chains", 20)
            _LLAMA["protocols"] = jget("https://api.llama.fi/protocols", 30)
            _LLAMA["t"] = time.time()
        except Exception:
            _LLAMA["chains"] = _LLAMA["chains"] or []; _LLAMA["protocols"] = _LLAMA["protocols"] or []
    return _LLAMA["chains"], _LLAMA["protocols"]

def fetch_tvl(sym):
    """TVL (USD) + perubahan 30 hari bila tersedia. Chain berdasarkan tokenSymbol, atau jumlah protokol bersimbol sama."""
    chains, protocols = llama()
    cfg = COINS[sym]
    if cfg.get("chain") or any(c.get("tokenSymbol") == sym for c in chains):
        c = next((c for c in chains if c.get("tokenSymbol") == sym), None) or next((c for c in chains if c.get("name") == cfg.get("chain")), None)
        if c:
            out = {"tvl": float(c.get("tvl") or 0), "kind": "chain", "name": c["name"], "ch30": None, "slug": c["name"]}
            try:
                h = jget("https://api.llama.fi/v2/historicalChainTvl/" + urllib_quote(c["name"]), 20)
                if len(h) > 31 and h[-31]["tvl"]: out["ch30"] = h[-1]["tvl"] / h[-31]["tvl"] - 1
            except Exception: pass
            return out
    ps = [p for p in protocols if (p.get("symbol") or "").upper() == sym and (p.get("tvl") or 0) > 0]
    if ps:
        tvl = sum(float(p["tvl"]) for p in ps); main = max(ps, key=lambda p: p["tvl"])
        return {"tvl": tvl, "kind": "protocol", "name": main["name"], "ch30": main.get("change_1m") and main["change_1m"] / 100, "slug": main.get("slug")}
    return None

def urllib_quote(s):
    import urllib.parse; return urllib.parse.quote(s)

def fetch_revenue(slug):
    """Pendapatan protokol (DefiLlama dailyRevenue): total 24j/7h/30h. None bila tidak tersedia."""
    if not slug: return None
    try:
        d = jget(f"https://api.llama.fi/summary/fees/{urllib_quote(slug)}?dataType=dailyRevenue", 20)
        if d.get("total30d") is None: return None
        return {"d24": d.get("total24h"), "d7": d.get("total7d"), "d30": d.get("total30d")}
    except Exception:
        return None

def fetch_coinmetrics(asset):
    """Hanya BTC/ETH (komunitas CoinMetrics, gratis): MVRV, nilai transfer adjusted (untuk NVT), alamat aktif."""
    out = {}
    start = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 110 * 86400))
    for m in ("CapMVRVCur", "TxTfrValAdjUSD", "CapMrktCurUSD", "AdrActCnt"):
        try:
            d = jget(f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={asset}&metrics={m}"
                     f"&frequency=1d&start_time={start}&page_size=200", 20)
            out[m] = [float(r[m]) for r in d["data"] if r.get(m) not in (None, "")]
        except Exception: pass
    return out

def fetch_macro():
    m = {"fng": None, "global": None}
    try:
        d = jget("https://api.alternative.me/fng/?limit=1")["data"][0]
        m["fng"] = {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception: pass
    try:
        g = jget("https://api.coingecko.com/api/v3/global")["data"]
        m["global"] = {"btc_dom": g["market_cap_percentage"]["btc"], "mcap_24h": g["market_cap_change_percentage_24h_usd"]}
    except Exception: pass
    return m

# ---------------------------------------------------------------- SMC / ICT (fungsi murni, mudah diuji)
def atr(c, n=14):
    trs = [max(c[i]["h"] - c[i]["l"], abs(c[i]["h"] - c[i - 1]["c"]), abs(c[i]["l"] - c[i - 1]["c"])) for i in range(1, len(c))]
    return mean(trs[-n:]) if trs else 0.0

def swings(c, k):
    out = []
    for i in range(k, len(c) - k):
        if all(c[i]["h"] > c[j]["h"] for j in range(i - k, i)) and all(c[i]["h"] >= c[j]["h"] for j in range(i + 1, i + k + 1)):
            out.append(("H", i, c[i]["h"]))
        if all(c[i]["l"] < c[j]["l"] for j in range(i - k, i)) and all(c[i]["l"] <= c[j]["l"] for j in range(i + 1, i + k + 1)):
            out.append(("L", i, c[i]["l"]))
    return out

def structure(c, k):
    sw = swings(c, k)
    hs = [s for s in sw if s[0] == "H"][-3:]; ls = [s for s in sw if s[0] == "L"][-3:]
    last = c[-1]["c"]; bias = "range"; note = "Swing belum cukup untuk menentukan struktur."
    if len(hs) >= 2 and len(ls) >= 2:
        hh, hl = hs[-1][2] > hs[-2][2], ls[-1][2] > ls[-2][2]
        bias = "bullish" if hh and hl else "bearish" if (not hh and not hl) else "range"
        note = {"bullish": "Higher High dan Higher Low.", "bearish": "Lower High dan Lower Low.", "range": "Swing campuran (konsolidasi)."}[bias]
        if bias == "bearish" and last > hs[-1][2]: note += " Harga menembus swing high terakhir (potensi CHoCH bullish)."
        if bias == "bullish" and last < ls[-1][2]: note += " Harga menembus swing low terakhir (potensi CHoCH bearish)."
    return {"bias": bias, "note": note, "swing_high": hs[-1][2] if hs else None, "swing_low": ls[-1][2] if ls else None,
            "swings": sw, "highs": hs, "lows": ls}

def fvgs(c, lookback=150, min_pct=0.003):
    out, n = [], len(c)
    for i in range(max(2, n - lookback), n):
        a, d = c[i - 2], c[i]
        ref = c[i - 1]["c"] or 1
        if d["l"] > a["h"] and (d["l"] - a["h"]) / ref >= min_pct:
            lo, hi = a["h"], d["l"]; later = c[i + 1:]
            st = "terisi" if any(x["l"] <= lo for x in later) else "sebagian" if any(x["l"] <= hi for x in later) else "belum tersentuh"
            out.append({"type": "bull", "lo": lo, "hi": hi, "i": i, "status": st})
        if d["h"] < a["l"] and (a["l"] - d["h"]) / ref >= min_pct:
            lo, hi = d["h"], a["l"]; later = c[i + 1:]
            st = "terisi" if any(x["h"] >= hi for x in later) else "sebagian" if any(x["h"] >= lo for x in later) else "belum tersentuh"
            out.append({"type": "bear", "lo": lo, "hi": hi, "i": i, "status": st})
    return out

def equal_levels(sw, kind, tol=0.004):
    pts = sorted(s[2] for s in sw if s[0] == kind); groups = []
    for p in pts:
        if groups and abs(p - groups[-1][-1]) / groups[-1][-1] <= tol: groups[-1].append(p)
        else: groups.append([p])
    return [round(mean(g), 8) for g in groups if len(g) >= 2]

def smc_setup(daily, weekly):
    last = daily[-1]["c"]; a = atr(daily)
    d, w = structure(daily, 5), structure(weekly, 3)
    all_f = fvgs(daily)
    bull_open = [f for f in all_f if f["type"] == "bull" and f["status"] != "terisi"]
    out = {"htf": {k: w[k] for k in ("bias", "note", "swing_high", "swing_low")}, "ltf": {k: d[k] for k in ("bias", "note", "swing_high", "swing_low")},
           "eqh": [x for x in equal_levels(d["swings"], "H") if x > last][:3], "eql": [x for x in equal_levels(d["swings"], "L") if x < last][-3:],
           "fvgs": sorted(bull_open, key=lambda f: abs(f["hi"] - last))[:4], "ote": None, "setup": None, "atr": a}
    # leg impuls: swing low terakhir sebelum swing high terakhir, puncak = max high sesudah swing low itu
    n = len(daily)
    all_h = [x for x in d["swings"] if x[0] == "H" and x[1] >= n - 180]; all_l = [x for x in d["swings"] if x[0] == "L"]
    leg = None
    if all_h:
        top_sw = max(all_h, key=lambda x: x[2])                          # puncak impuls = swing high tertinggi 180 candle terakhir
        prior = [x for x in all_l if top_sw[1] - 100 <= x[1] < top_sw[1]]   # awal leg = swing low terendah dalam 100 candle sebelum puncak
        if prior:
            lo = min(prior, key=lambda x: x[2]); top = max(x["h"] for x in daily[lo[1]:])
            if (top - lo[2]) / lo[2] >= 0.10: leg = {"low": lo[2], "high": top, "low_i": lo[1]}
    if not leg:
        out["setup"] = {"valid": False, "status": "tidak ada leg impuls", "reason": "Belum ada leg impuls bullish minimal 10% yang bersih."}; return out
    rng = leg["high"] - leg["low"]; lvl = lambda r: leg["high"] - r * rng
    ote = {"lo": lvl(0.79), "hi": lvl(0.62), "sweet": lvl(0.705), "eq": lvl(0.5), "leg_low": leg["low"], "leg_high": leg["high"]}
    out["ote"] = ote
    htf_ok = w["bias"] != "bearish"; ltf_ok = d["bias"] in ("bullish", "range") or "CHoCH bullish" in d["note"]   # retrace dalam ke OTE wajar terlihat sebagai range
    broken = last < leg["low"]
    if broken:
        out["setup"] = {"valid": False, "status": "invalid", "reason": "Harga berada di bawah swing low leg impuls: struktur bullish sudah patah."}; return out
    zone, label = (ote["lo"], ote["hi"]), "OTE (Fib 0,62 s/d 0,79)"
    for f in sorted(bull_open, key=lambda f: -f["i"]):
        lo, hi = max(f["lo"], ote["lo"]), min(f["hi"], ote["hi"])
        if lo < hi and f["lo"] >= leg["low"]:
            zone, label = (lo, hi), "Konfluensi FVG + OTE (setup A+)"; break
    entry = (zone[0] + zone[1]) / 2; stop = leg["low"] - 0.5 * a
    stop = min(stop, zone[0] - 0.25 * a)
    risk = entry - stop
    eqh = out["eqh"][0] if out["eqh"] else None
    t1 = leg["high"]; t2 = eqh if (eqh and eqh > t1) else leg["high"] + 0.272 * rng
    status = "di dalam zona" if zone[0] <= last <= zone[1] else "menunggu retrace ke zona" if last > zone[1] else "di bawah zona, awasi invalidasi"
    rr = (t1 - entry) / risk if risk > 0 else 0
    reasons = []
    if not htf_ok: reasons.append("Struktur weekly bearish")
    if not ltf_ok: reasons.append("Struktur daily bearish")
    if rr < 2: reasons.append(f"RR ke target 1 hanya {rr:.1f} (di bawah 2)")
    out["setup"] = {"valid": htf_ok and ltf_ok and rr >= 2, "label": label, "zone": [zone[0], zone[1]], "entry": entry, "stop": stop, "t1": t1, "t2": t2,
                    "moonbag": entry * 2, "rr": rr, "status": status, "stop_pct": risk / entry * 100 if entry else None,
                    "reason": "; ".join(reasons) if reasons else "Struktur HTF dan LTF selaras, RR memadai.", "confluence": label.startswith("Konfluensi")}
    return out

# ---------------------------------------------------------------- lifecycle (Modul 1)
def lifecycle(daily, mk, news48):
    cl = [x["c"] for x in daily]; last = cl[-1]
    sma200 = mean(cl[-200:]); ext = last / sma200 if sma200 else 1
    ch30 = last / cl[-31] - 1 if len(cl) > 31 else 0; ch90 = last / cl[-91] - 1 if len(cl) > 91 else 0
    hi, lo = max(x["h"] for x in daily), min(x["l"] for x in daily)
    dd = last / hi - 1; above_low = last / lo - 1 if lo else 0
    vol7, vol90 = mean(x["v"] for x in daily[-7:]), mean(x["v"] for x in daily[-90:]); vr = vol7 / vol90 if vol90 else 1
    s = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    if ch30 > 0.6: s[3] += 2
    if ext > 1.8: s[3] += 2
    if vr > 2: s[3] += 1.5
    if dd > -0.1: s[3] += 1
    if news48 >= 6: s[3] += 0.5
    if last < sma200: s[4] += 2
    if ch30 < -0.15: s[4] += 1.5
    if -0.7 < dd < -0.3: s[4] += 1
    if ch90 < -0.25: s[4] += 1.5
    if dd < -0.55: s[1] += 2
    if above_low < 0.35: s[1] += 1.5
    if abs(ch30) < 0.2: s[1] += 1
    if vr < 1.0: s[1] += 1
    if last > sma200 and 0 < ch30 <= 0.6: s[2] += 2
    if 1.0 <= vr <= 2.0: s[2] += 1.5
    if -0.6 < dd < -0.15: s[2] += 1.5
    if 1.0 < ext < 1.5: s[2] += 1
    phase = max([3, 4, 2, 1], key=lambda p: s[p])
    label = {1: "Akumulasi", 2: "Validasi", 3: "Euforia", 4: "Kelelahan"}[phase]
    entry_q = {1: "Entry optimal", 2: "Entry aman", 3: "Zona distribusi/exit, jangan mengejar", 4: "Hindari atau short"}[phase]
    why = [f"Jarak dari high 1 tahun: {dd*100:.0f}%; dari low 1 tahun: +{above_low*100:.0f}%.",
           f"Perubahan 30 hari {ch30*100:+.0f}%, 90 hari {ch90*100:+.0f}%.",
           f"Harga {ext:.2f}x SMA-200 ({'di atas' if last > sma200 else 'di bawah'}).",
           f"Volume 7 hari {vr:.2f}x rata-rata 90 hari; {news48} berita 48 jam di radar."]
    return {"phase": phase, "label": label, "entry_quality": entry_q, "why": why, "scores": s,
            "metrics": {"dd": dd, "ch30": ch30, "ch90": ch90, "ext": ext, "vr": vr}}

# ---------------------------------------------------------------- analisis penuh (fungsi murni)
def tone_score(t): return {"good": 8.0, "fair": 6.0, "poor": 3.0}.get(t)

def analyze(sym, mk, daily, weekly, tvl=None, revenue=None, cm=None, macro=None, news_items=(), now=None):
    now = now or time.time(); cfg = COINS[sym]; gaps = []
    last = daily[-1]["c"]
    news48 = sum(1 for i in news_items if sym in i.get("projects", []) and now - i.get("published", 0) < 48 * 3600)
    # --- Modul 1
    lc = lifecycle(daily, mk, news48)
    rank = (mk or {}).get("market_cap_rank")
    top_mind = bool(rank and rank <= 30)
    s1 = {1: 9.0, 2: 7.5, 3: 3.0, 4: 2.0}[lc["phase"]] + (0.5 if top_mind else -1.5)
    narrative = {"sector": cfg["narr"], "lifecycle": lc, "rank": rank, "top_of_mind": top_mind,
                 "thesis": f"{cfg['name']}: {cfg['narr']}.",
                 "filter": ("Lolos filter Paradox of Choices (market leader peringkat %s)." % rank) if top_mind else "Di luar 30 besar: likuiditas terfragmentasi, waspadai noise.",
                 "score": max(0, min(10, s1))}
    # --- Modul 2
    mcap = (mk or {}).get("market_cap"); vol24 = (mk or {}).get("total_volume")
    f = {"nvt": None, "mvrv": None, "tvl": None, "activity": []}
    if cm and cm.get("TxTfrValAdjUSD") and cm.get("CapMrktCurUSD"):
        tv90 = mean(cm["TxTfrValAdjUSD"][-90:]); v = cm["CapMrktCurUSD"][-1] / tv90 if tv90 else None
        if v: f["nvt"] = {"value": v, "kind": "on-chain (NVT 90 hari, nilai transfer adjusted)", "tone": "good" if v < 45 else "fair" if v <= 95 else "poor",
                          "verdict": "Undervalued (utilitas)" if v < 45 else "Wajar" if v <= 95 else "Overvalued (dorongan hype)", "note": "Ambang klasik 45 dan 95, bergeser antar era."}
    if not f["nvt"] and mcap and vol24:
        v = mcap / vol24
        f["nvt"] = {"value": v, "kind": "proxy: kapitalisasi / volume bursa 24 jam (BUKAN NVT on-chain murni)",
                    "tone": "poor" if v < 3 else "good" if v <= 30 else "fair",
                    "verdict": "Perputaran sangat tinggi, spekulasi berlebih" if v < 3 else "Perputaran sehat" if v <= 30 else "Perputaran rendah, minat sepi",
                    "note": "Proxy hanya menggambarkan perputaran bursa; NVT on-chain butuh data transfer (CoinMetrics/Glassnode)."}
        gaps.append("NVT on-chain tidak tersedia gratis untuk aset ini; memakai proxy volume bursa.")
    if cm and cm.get("CapMVRVCur"):
        v = cm["CapMVRVCur"][-1]
        f["mvrv"] = {"value": v, "kind": "on-chain (CoinMetrics)", "tone": "good" if v < 1.2 else "fair" if v < 2.5 else "poor",
                     "verdict": "Akumulasi dalam (< 1)" if v < 1 else "Normal" if v < 2.5 else "Pemegang untung besar, risiko jual" if v < 3.5 else "Euforia",
                     "note": ">1 pemegang untung (risiko distribusi); <1 pemegang rugi (akumulasi)."}
    else:
        cs = daily[-365:]; vw = sum(((x["h"] + x["l"] + x["c"]) / 3) * x["v"] for x in cs) / max(1e-12, sum(x["v"] for x in cs)); v = last / vw
        f["mvrv"] = {"value": v, "kind": "proxy: harga / VWAP 365 hari (BUKAN realized cap)", "tone": "good" if v < 1.0 else "fair" if v < 1.6 else "poor",
                     "verdict": "Di bawah biaya rata-rata pasar (akumulasi)" if v < 1 else "Sedikit di atas biaya rata-rata" if v < 1.6 else "Jauh di atas biaya rata-rata (risiko jual)",
                     "note": "Realized cap sejati butuh Glassnode/CoinMetrics berbayar untuk aset ini."}
        gaps.append("MVRV sejati tidak tersedia gratis; memakai proxy harga/VWAP 365 hari.")
    if tvl and mcap:
        r = mcap / tvl["tvl"] if tvl["tvl"] else None
        if r: f["tvl"] = {"value": r, "tvl_usd": tvl["tvl"], "source": f"DefiLlama ({tvl['kind']}: {tvl['name']})", "tone": "good" if r < 1 else "fair" if r < 3 else "poor",
                          "verdict": "Diskon terhadap modal terkunci" if r < 1 else "Premium wajar" if r < 3 else "Premium tinggi dibanding modal terkunci", "note": ">1: valuasi lebih besar daripada dana di dalam protokol.", "ch30": tvl.get("ch30")}
    else:
        gaps.append("Rasio TVL tidak berlaku atau data TVL tidak tersedia (mis. BTC, meme).")
    if tvl and tvl.get("ch30") is not None: f["activity"].append(f"TVL 30 hari: {tvl['ch30']*100:+.1f}%.")
    if revenue and revenue.get("d30") is not None:
        avg30 = revenue["d30"] / 30; d7 = (revenue.get("d7") or 0) / 7
        tr = (d7 / avg30 - 1) * 100 if avg30 else 0
        f["activity"].append(f"Pendapatan protokol 30 hari: ${revenue['d30']:,.0f}; rata-rata 7 hari {tr:+.0f}% vs rata-rata 30 hari.")
    else: gaps.append("Pendapatan protokol tidak tersedia dari sumber gratis untuk aset ini.")
    if cm and cm.get("AdrActCnt"):
        a = cm["AdrActCnt"]; ch = a[-1] / mean(a[-30:]) - 1 if len(a) > 30 else 0
        f["activity"].append(f"Alamat aktif harian {a[-1]:,.0f} ({ch*100:+.0f}% vs rata-rata 30 hari).")
    else: gaps.append("Alamat aktif tidak tersedia gratis; gunakan Token Terminal/Artemis untuk verifikasi.")
    sc = [tone_score(f[k]["tone"]) for k in ("nvt", "mvrv", "tvl") if f[k]]
    s2 = mean(sc) if sc else 5.0
    if tvl and tvl.get("ch30") is not None: s2 += 0.5 if tvl["ch30"] > 0.05 else -0.5 if tvl["ch30"] < -0.1 else 0
    f["score"] = max(0, min(10, s2))
    # --- Modul 3
    fdv = (mk or {}).get("fully_diluted_valuation"); circ = (mk or {}).get("circulating_supply")
    cap_supply = (mk or {}).get("max_supply") or (mk or {}).get("total_supply")
    ratio = fdv / mcap if (fdv and mcap) else None
    circ_pct = circ / cap_supply * 100 if (circ and cap_supply) else None
    risk = "N/A" if ratio is None else "Tinggi" if ratio >= 3 else "Sedang" if ratio >= 1.5 else "Rendah"
    unl = [u for u in _load_json("unlocks.json", {}).get(sym, []) if u.get("date", "") >= time.strftime("%Y-%m-%d", time.gmtime(now))]
    unl = [u for u in unl if u["date"] <= time.strftime("%Y-%m-%d", time.gmtime(now + 90 * 86400))]
    news_unl = [i for i in news_items if sym in i.get("projects", []) and i.get("event") == "Token Unlock" and now - i.get("published", 0) < 14 * 86400]
    defl = DEFL.get(sym, ("Perlu verifikasi", "Tidak ada data."))
    s3 = 8.0 - (4 if risk == "Tinggi" else 2 if risk == "Sedang" else 0) - (2 if (unl or news_unl) else 0)
    s3 += {"Ada": 1.5, "Parsial": 0.75}.get(defl[0], 0)
    if circ_pct is not None and circ_pct < 50: s3 -= 1
    if not unl: gaps.append("Jadwal unlock 7-90 hari tidak ada di sumber gratis; isi unlocks.json dari TokenUnlocks/Tokenomist.")
    tok = {"fdv_ratio": ratio, "circ_pct": circ_pct, "fdv_risk": risk, "fdv": fdv, "mcap": mcap, "unlocks": unl,
           "unlock_news": [{"title": i["title"], "source": i["source"], "url": i.get("url")} for i in news_unl][:3],
           "deflation": {"status": defl[0], "note": defl[1]}, "score": max(0, min(10, s3)),
           "fdv_note": ("FDV jauh di atas kapitalisasi: struktur 'legal rug pull' bila suplai beredar kecil." if risk == "Tinggi" else
                        "Sebagian suplai belum beredar; tekanan emisi tetap ada." if risk == "Sedang" else
                        "FDV mendekati kapitalisasi; risiko dilusi rendah." if risk == "Rendah" else "Suplai maksimum tidak ditetapkan atau data FDV tidak tersedia.")}
    # --- Modul 4
    vc, note = BACKERS.get(sym, ([], "Data investor tidak ada"))
    t1 = [v for v in vc if v in TIER1]
    if not vc: s4, rule = 6.0, None
    else: s4, rule = {0: 2.0, 1: 4.0, 2: 6.0}.get(len(t1), 8.0), len(t1) >= 3
    pb = [PLAYBOOK[v] for v in vc if v in PLAYBOOK]
    if "Pantera" in vc: s4 -= 1
    sm = {"backers": vc, "tier1": t1, "tier1_count": len(t1), "rule_met": rule, "playbook": pb, "note": note, "score": max(0, min(10, s4)),
          "verdict": ("Tidak berbasis VC: aturan 3 Tier-1 tidak berlaku, risikonya bergeser ke tata kelola/sentralisasi." if not vc else
                      "Memenuhi aturan minimal 3 entitas Tier-1." if rule else f"Belum memenuhi aturan 3 Tier-1 (terdata {len(t1)}).")}
    gaps.append("Daftar investor berasal dari pengetahuan umum; verifikasi di ChainBroker/Crunchbase.")
    # --- Modul 5
    pos = sum(1 for i in news_items if i.get("event") in ("Regulasi Positif", "ETF Disetujui") and now - i.get("published", 0) < 7 * 86400)
    neg = sum(1 for i in news_items if i.get("event") == "Hukum / Regulasi Negatif" and now - i.get("published", 0) < 7 * 86400)
    manual = _load_json("macro.json", {})
    mc = {"fng": (macro or {}).get("fng"), "global": (macro or {}).get("global"), "reg": {"pos": pos, "neg": neg},
          "fed": manual.get("fed_stance") or "Belum diisi (edit macro.json: sikap The Fed, suku bunga, likuiditas)", "tailwinds": [], "headwinds": []}
    s5 = 5.0 + max(-2, min(2, (pos - neg) * 0.5))
    if mc["fng"]:
        v = mc["fng"]["value"]
        if v <= 25: s5 += 1; mc["tailwinds"].append(f"Fear & Greed {v} (ketakutan ekstrem): kontrarian menguntungkan akumulasi.")
        elif v >= 75: s5 -= 1.5; mc["headwinds"].append(f"Fear & Greed {v} (keserakahan): risiko puncak jangka pendek.")
    else: gaps.append("Indeks Fear & Greed tidak terjangkau.")
    if pos > neg: mc["tailwinds"].append(f"Radar mencatat {pos} berita regulasi/ETF positif vs {neg} negatif dalam 7 hari.")
    elif neg > pos: mc["headwinds"].append(f"Radar mencatat {neg} berita regulasi negatif vs {pos} positif dalam 7 hari.")
    if mc["global"]: mc["tailwinds" if mc["global"]["mcap_24h"] > 0 else "headwinds"].append(f"Total kapitalisasi pasar {mc['global']['mcap_24h']:+.1f}% 24 jam; dominasi BTC {mc['global']['btc_dom']:.1f}%.")
    if not manual.get("fed_stance"): gaps.append("Sikap The Fed dan likuiditas global belum diisi di macro.json.")
    mc["score"] = max(0, min(10, s5))
    # --- Modul 6
    smc = smc_setup(daily, weekly); st = smc["setup"]
    if st and st.get("valid"): s6 = 8.0 if st.get("confluence") else 7.0
    elif st and st.get("status") in ("menunggu retrace ke zona", "di dalam zona") and smc["htf"]["bias"] != "bearish": s6 = 5.5
    else: s6 = 2.5
    smc["score"] = s6
    # --- skor akhir & verdict
    w = {"narrative": .20, "fundamentals": .20, "tokenomics": .15, "smart_money": .15, "macro": .10, "smc": .20}
    mods = {"narrative": narrative["score"], "fundamentals": f["score"], "tokenomics": tok["score"], "smart_money": sm["score"], "macro": mc["score"], "smc": s6}
    total = sum(mods[k] * w[k] for k in w)
    near = bool(st and st.get("zone") and last <= st["zone"][1] * 1.03 and st.get("status") != "invalid")
    ph = lc["phase"]
    if ph == 3: label, text = "DISTRIBUTE", "Fase Euforia: zona distribusi. Jangan mengejar harga; amankan profit sesuai aturan Moonbag."
    elif ph == 4: label, text = "AVOID", "Fase Kelelahan: hindari atau tunggu perubahan struktur. Tidak ada leverage."
    elif total >= 7.5 and st and st.get("valid") and near: label, text = "ACCUMULATE", "Skor tinggi dan harga di/dekat zona entry: pasang limit bertahap di zona, stop struktural wajib."
    elif total >= 6 and smc["htf"]["bias"] != "bearish":
        label = "WAIT"
        text = ("Tesis layak dan harga sudah di/dekat zona, tetapi skor belum mencapai 7,5: ukuran posisi kecil atau tunggu konfirmasi struktur."
                if near and st and st.get("valid") else "Tesis layak tetapi harga belum di zona: tunggu retrace ke FVG/OTE, jangan FOMO.")
    else: label, text = "AVOID", "Skor atau struktur belum mendukung; lewati dan simpan modal."
    # barbell + 1% risk
    alt_cap = 10 if total >= 8 else 7 if total >= 7 else 5 if total >= 6 else 0
    risk_alloc = (1.0 / st["stop_pct"] * 100) if st and st.get("stop_pct") else None
    final = min(alt_cap, risk_alloc) if risk_alloc is not None else alt_cap
    if sym == "BTC": bb = "BTC adalah basis barbell (bersama stablecoin 60-80% portofolio). Tambahan taktis tetap tunduk pada aturan risiko 1%."
    else: bb = "Altcoin maksimum 10-30% portofolio total, 3-5 posisi terkonsentrasi, tanpa leverage. Posisi ini dibatasi oleh skor dan aturan risiko 1%."
    barbell = {"alt_cap_pct": alt_cap, "risk_alloc_pct": risk_alloc, "final_pct": final if label in ("ACCUMULATE", "WAIT") else 0, "text": bb}
    coverage = sum(1 for k in ("nvt", "mvrv", "tvl") if f[k]) / 3
    return {"symbol": sym, "name": cfg["name"], "generated_at": int(now), "price": last, "demo": False,
            "narrative": narrative, "fundamentals": f, "tokenomics": tok, "smart_money": sm, "macro": mc, "smc": smc, "barbell": barbell,
            "verdict": {"score": round(total, 1), "label": label, "text": text, "modules": {k: round(v, 1) for k, v in mods.items()}, "weights": w},
            "data_gaps": gaps, "coverage": round(coverage, 2),
            "sources": ["CoinGecko", "Binance/OKX (OHLCV)", "DefiLlama", "CoinMetrics Community (BTC/ETH)", "alternative.me", "Radar berita Crypto Sastra"]}

def scan_symbol(sym, markets=None, news_items=(), macro=None):
    """Kumpulkan data lalu analisis. Melempar ValueError bila candle tidak cukup."""
    mk = (markets or fetch_markets([sym])).get(sym)
    daily, weekly = fetch_candles(sym, "1d"), fetch_candles(sym, "1w")
    if len(daily) < 120 or len(weekly) < 40: raise ValueError(f"Data candle {sym} tidak cukup (daily={len(daily)}, weekly={len(weekly)})")
    tvl = None; revenue = None; cm = None
    try:
        tvl = fetch_tvl(sym)
        if tvl: revenue = fetch_revenue(tvl.get("slug"))
    except Exception: pass
    if COINS[sym].get("cm"):
        try: cm = fetch_coinmetrics(COINS[sym]["cm"])
        except Exception: cm = None
    return analyze(sym, mk, daily, weekly, tvl, revenue, cm, macro or fetch_macro(), news_items)

def index_entry(r):
    return {"symbol": r["symbol"], "name": r["name"], "generated_at": r["generated_at"], "score": r["verdict"]["score"], "label": r["verdict"]["label"]}

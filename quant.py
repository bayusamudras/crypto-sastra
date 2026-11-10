#!/usr/bin/env python3
"""
Crypto Sastra - Modul Filter Kuantitatif (murni, tanpa jaringan kecuali fetcher di bawah)

  1. Valuasi relatif sektor : P/F = FDV / fee tahunan, dibanding median sektornya (bukan lintas sektor).
  2. Anomali pertumbuhan    : Capital Efficiency (volume harian / TVL) dan Price-Usage Divergence
                              (volume & fee 30 hari naik > +30% sementara harga 30 hari < +5%).
  3. Tokenomics & emission trap : MC/FDV < 0.25 dieliminasi kecuali tanpa unlock besar 12 bulan; Net Real Yield = pendapatan - nilai emisi.
  4. Akumulasi smart money & kedalaman DEX : net flow 100 dompet profit teratas (butuh sumber data), likuiditas DEX / market cap.

Aturan data: komponen tanpa data = None ("n/a"), tidak pernah ditebak. Skor tambahan dibatasi (+10 / -18).
"""
import json, os, statistics, time, urllib.request

UA = {"User-Agent": "CryptoSastra/1.0"}
DAY = 86400
PF_DISCOUNT = -0.5          # P/F >= 50% di bawah median sektor
GROWTH_MIN, PRICE_MAX = 0.30, 0.05
CAPEFF_HOT, CAPEFF_OK = 1.0, 0.8
MCFDV_MIN = 0.25
DEPTH_THICK, DEPTH_THIN = 0.10, 0.03
DUNE_KEY, DUNE_QUERY = os.getenv("DUNE_API_KEY", ""), os.getenv("DUNE_QUERY_ID", "")

def _j(url, headers=None, timeout=40):
    h = dict(UA); h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r: return json.loads(r.read())

# ---------------------------------------------------------------- pengambil data (gratis)
def fetch_overview(kind, data_type=None):
    """DefiLlama overview/<kind> (fees|dexs|derivatives) -> slug -> {d1,d7,d30,ch30}. ch30 = total30d vs 30 hari sebelumnya bila tersedia."""
    url = f"https://api.llama.fi/overview/{kind}?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true" + (f"&dataType={data_type}" if data_type else "")
    try: d = _j(url)
    except Exception as e:
        print(f"quant: DefiLlama {kind} gagal:", e); return {}
    out = {}
    for p in d.get("protocols", []):
        k = (p.get("slug") or p.get("name", "")).lower()
        if p.get("total30d") is None: continue
        ch = p.get("change_30dover30d")
        out[k] = {"d1": p.get("total24h"), "d7": p.get("total7d"), "d30": p.get("total30d"), "ch30": (ch / 100.0) if ch is not None else None}
    return out

SM_STATUS = {"dune": {"configured": False, "rows": 0, "error": None}, "manual": 0}

def fetch_smart_money():
    """Net flow dompet smart money per simbol. Sumber (urutan): Dune (DUNE_API_KEY + DUNE_QUERY_ID; kolom symbol, net_flow_usd_7d,
    net_flow_usd_14d, wallets_buying, wallets_selling), lalu smartmoney.json (ekspor manual dari Nansen/Arkham/Dune). Tanpa keduanya: {}."""
    out = {}
    d = os.getenv("DUNE_API_KEY", DUNE_KEY); qid = os.getenv("DUNE_QUERY_ID", DUNE_QUERY).strip()
    SM_STATUS["dune"] = {"configured": bool(d and qid), "key": bool(d), "query_id": bool(qid), "rows": 0, "error": None}
    if d and qid:
        try:
            rows = _j(f"https://api.dune.com/api/v1/query/{qid}/results", {"X-Dune-API-Key": d}).get("result", {}).get("rows", [])
            SM_STATUS["dune"]["rows"] = len(rows)
            if rows and not any("symbol" in r and "net_flow_usd_7d" in r for r in rows[:5]): SM_STATUS["dune"]["error"] = "kolom wajib tidak ada (symbol, net_flow_usd_7d)"
            for r in rows:
                if r.get("symbol"): out[str(r["symbol"]).upper()] = {k: r.get(k) for k in ("net_flow_usd_7d", "net_flow_usd_14d", "wallets_buying", "wallets_selling")}
        except Exception as e: SM_STATUS["dune"]["error"] = str(e)[:100]; print("quant: Dune gagal:", e)
    return out

# ---------------------------------------------------------------- 1. valuasi relatif sektor
def pf_ratio(fdv, fees30):
    return (fdv / (fees30 * 12)) if (fdv and fees30 and fees30 > 0) else None

def sector_medians(rows):
    """rows: [(tag, pf)] -> {tag: {"median", "n"}}; sektor dengan < 3 rekan tidak dipakai (median tak bermakna)."""
    g = {}
    for tag, pf in rows:
        if tag and pf and pf > 0: g.setdefault(tag, []).append(pf)
    return {t: {"median": statistics.median(v), "n": len(v)} for t, v in g.items() if len(v) >= 3}

def _growth(rec):
    """-> (growth, dasar). ch30 resmi bila ada; jika tidak, proksi: laju 7 hari disetahunkan ke 30 hari vs rata-rata 30 hari."""
    if not rec: return None, None
    if rec.get("ch30") is not None: return rec["ch30"], "30h vs 30h sebelumnya"
    if rec.get("d7") is not None and rec.get("d30"): return (rec["d7"] * 30 / 7) / rec["d30"] - 1, "proksi laju 7h vs rata-rata 30h"
    return None, None

def analyze(c, ctx):
    """c: kandidat; ctx: {tag, pf_med, fees, vol, tvl, unlocks12, circ_now, hist, now, sm}. -> dict hasil modul."""
    now = ctx.get("now") or time.time(); mc, fdv = c.get("mc") or 0, c.get("fdv") or 0
    notes, flags, pts = [], [], 0
    fees, vol = ctx.get("fees"), ctx.get("vol")
    gf, gf_b = _growth(fees); gv, gv_b = _growth(vol)
    # --- 1. P/F relatif
    pf = pf_ratio(fdv, (fees or {}).get("d30"))
    med = ctx.get("pf_med"); rel = (pf / med["median"] - 1) if (pf and med) else None
    growth_known = [g for g in (gv, gf) if g is not None]
    val = {"pf": pf, "median": med["median"] if med else None, "peers": med["n"] if med else 0, "rel": rel, "status": "n/a"}
    if pf is None: val["note"] = "Fee protokol tidak tersedia: P/F tidak dihitung."
    elif not med: val["note"] = f"P/F {pf:.1f}x; sektor {ctx.get('tag') or '?'} punya < 3 rekan berdata: tak ada median pembanding."
    else:
        rising = bool(growth_known) and max(growth_known) > 0
        if rel <= PF_DISCOUNT and rising: val["status"] = "undervalued_terkonfirmasi"; pts += 4; notes.append(f"P/F {pf:.1f}x = {abs(rel)*100:.0f}% di bawah median sektor {ctx['tag']} ({med['median']:.1f}x, n={med['n']}) dan penggunaan tumbuh")
        elif rel <= PF_DISCOUNT: val["status"] = "murah_belum_terkonfirmasi"; notes.append(f"P/F {abs(rel)*100:.0f}% di bawah median sektor tetapi pertumbuhan penggunaan belum terkonfirmasi")
        elif rel >= 0.5: val["status"] = "mahal"; flags.append(f"P/F {rel*100:.0f}% di atas median sektor")
        else: val["status"] = "wajar"
        val["note"] = f"P/F {pf:.1f}x vs median sektor {med['median']:.1f}x ({rel*100:+.0f}%, {med['n']} rekan)"
    # --- 2. anomali pertumbuhan
    tvl = ctx.get("tvl") or 0; d1 = (vol or {}).get("d1") if vol else None
    if d1 is None and vol and vol.get("d7") is not None: d1 = vol["d7"] / 7
    ce = (d1 / tvl) if (d1 is not None and tvl > 0) else None
    cap = {"ratio": ce, "status": "n/a"}
    if ce is not None:
        if ce >= CAPEFF_HOT: cap["status"] = "sangat_aktif"; pts += 2; notes.append(f"Volume harian {ce:.2f}x TVL: modal berputar aktif, bukan sekadar mengendap")
        elif ce >= CAPEFF_OK: cap["status"] = "aktif"; pts += 2
        elif ce >= 0.3: cap["status"] = "normal"
        else: cap["status"] = "rendah"
    ch30 = c.get("chg30"); div = {"price_ch30": ch30, "vol_growth": gv, "fee_growth": gf, "basis": gv_b or gf_b, "status": "n/a"}
    if growth_known and ch30 is not None:
        up = min(growth_known) > GROWTH_MIN
        if up and ch30 < PRICE_MAX * 100: div["status"] = "divergensi"; pts += 4; notes.append(f"Divergensi harga-penggunaan: " + ", ".join(x for x in (f"volume {gv*100:+.0f}%" if gv is not None else "", f"fee {gf*100:+.0f}%" if gf is not None else "") if x) + f" sementara harga 30h {ch30:+.1f}%")
        elif up: div["status"] = "sudah_naik"
        else: div["status"] = "tidak"
    # --- 3. tokenomics & emission trap
    ratio = (mc / fdv) if (mc and fdv) else None
    u12 = ctx.get("unlocks12")
    tok = {"mc_fdv": ratio, "unlocks12": None if u12 is None else len(u12), "elim": False, "status": "n/a"}
    if ratio is not None:
        if ratio < MCFDV_MIN:
            if u12 is not None and not u12: tok["status"] = "rendah_tanpa_unlock"; flags.append(f"MC/FDV {ratio:.2f}: rendah, tetapi tidak ada unlock 12 bulan tercatat")
            else:
                tok["elim"] = True; tok["status"] = "eliminasi"
                flags.append(f"ELIMINASI: MC/FDV {ratio:.2f} < 0,25 " + ("dan ada unlock 12 bulan" if u12 else "dan jadwal unlock tidak tercatat (isi unlocks.json bila memang tak ada)"))
        else: tok["status"] = "lolos"
    hist = ctx.get("hist") or {}; circ = ctx.get("circ_now")
    em = {"annual_usd": None, "net_real_yield": None, "status": "n/a", "days": None}
    if circ and hist.get("circ") and hist.get("ct") and mc:
        days = (now - hist["ct"]) / DAY
        if days >= 3 and hist["circ"] > 0:
            em["days"] = round(days, 1); em["annual_usd"] = ((circ / hist["circ"]) - 1) * (365 / days) * mc
    rev30 = c.get("rev30")
    if em["annual_usd"] is not None and rev30 is not None:
        net = rev30 * 12 - em["annual_usd"]; em["net_real_yield"] = net
        if net >= 0: em["status"] = "positif"; notes.append(f"Net real yield positif: pendapatan ${rev30*12/1e6:.1f} jt/th vs emisi ${em['annual_usd']/1e6:.1f} jt/th")
        elif em["annual_usd"] >= 2 * rev30 * 12: em["status"] = "jebakan_emisi"; pts -= 8; flags.append(f"Jebakan emisi: nilai emisi ${em['annual_usd']/1e6:.1f} jt/th >= 2x pendapatan ${rev30*12/1e6:.1f} jt/th")
        else: em["status"] = "negatif"; pts -= 3; flags.append(f"Emisi (${em['annual_usd']/1e6:.1f} jt/th) melebihi pendapatan (${rev30*12/1e6:.1f} jt/th)")
    # --- 4. smart money & kedalaman DEX
    sm = ctx.get("sm"); smv = {"status": "n/a"}
    if sm and sm.get("net_flow_usd_7d") is not None:
        n7, n14 = sm["net_flow_usd_7d"], sm.get("net_flow_usd_14d"); b, s = sm.get("wallets_buying"), sm.get("wallets_selling")
        smv.update(net7=n7, net14=n14, buying=b, selling=s)
        if n7 > 0 and (n14 is None or n14 > 0) and (b is None or s is None or b > s): smv["status"] = "akumulasi"; pts += 4; notes.append(f"Smart money net beli ${n7/1e3:.0f} rb (7h)" + (f", {b} dompet beli vs {s} jual" if b is not None and s is not None else ""))
        elif n7 < 0: smv["status"] = "distribusi"; pts -= 3; flags.append(f"Smart money net jual ${abs(n7)/1e3:.0f} rb (7h)")
        else: smv["status"] = "netral"
    dx = c.get("dex") or {}; depth = {"ratio": None, "status": "n/a"}
    if dx.get("liq") is not None and mc:
        r = dx["liq"] / mc; depth["ratio"] = r
        if r >= DEPTH_THICK: depth["status"] = "tebal"; notes.append(f"Likuiditas DEX {r*100:.1f}% market cap: tebal, sulit dimanipulasi")
        elif r >= DEPTH_THIN: depth["status"] = "sedang"
        else: depth["status"] = "tipis"; pts -= 3; flags.append(f"Likuiditas DEX hanya {r*100:.1f}% market cap: mudah dimanipulasi, slippage besar")
    adj = max(-18, min(10, pts - (10 if tok["elim"] else 0)))
    known = sum(1 for x in (val["status"], cap["status"], div["status"], tok["status"], em["status"], smv["status"], depth["status"]) if x != "n/a")
    return {"valuation": val, "capital_efficiency": cap, "divergence": div, "tokenomics": tok, "emission": em, "smart_money": smv, "depth": depth,
            "elim": tok["elim"], "adjust": adj, "notes": notes, "flags": flags, "coverage": round(known / 7, 2)}

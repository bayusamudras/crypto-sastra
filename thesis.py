#!/usr/bin/env python3
"""
Crypto Sastra - Mesin Tesis (murni, tanpa dependensi)

Dari informasi yang terkumpul (berita radar, momentum TVL sektor, pasokan stablecoin, catatan manual Anda di thesis_events.json)
mesin ini menyusun TESIS TEMA: apa yang mungkin terjadi, mengapa, apa yang akan mengonfirmasi, apa yang membatalkan,
lalu memeringkat proyek terbaik di sektor itu beserta alasannya (skala, penggunaan, pertumbuhan, fee, kepatuhan).

Ini hipotesis berbasis bukti yang tercatat, bukan ramalan. Keyakinan hanya naik bila ada bukti dari JENIS berbeda
(berita + data on-chain + catatan manual). Tanpa bukti sama sekali, tema tidak ditampilkan.
"""
import json, math, re, time, urllib.request

DAY = 86400
UA = {"User-Agent": "CryptoSastra/1.0"}

THEMES = [
 {"id": "stablecoin", "title": "Stablecoin & uang on-chain institusional", "horizon": "1-2 kuartal",
  "kw": ["stablecoin", "usdc", "usdt", "genius act", "tokenized deposit", "payment", "pembayaran", "circle", "paypal", "pyusd", "remittance", "bank ", "visa", "mastercard", "stripe"],
  "tags": ["Payments", "Lending", "RWA"], "cats": ["cdp", "stablecoin", "algo-stables", "basis trading", "rwa"],
  "mechanism": "Regulasi yang makin jelas dan masuknya bank/fintech membuat stablecoin menjadi rel pembayaran dan jaminan dolar on-chain. Permintaan institusional mengalir ke penerbit patuh regulasi dan ke protokol yang menjadi infrastruktur penyalurannya (likuiditas, kredit, imbal hasil).",
  "confirm": ["Total pasokan stablecoin naik berturut-turut (lihat bukti on-chain)", "Pengumuman bank/fintech baru yang menerbitkan atau menyalurkan stablecoin", "Fee protokol infrastruktur (lending, DEX stablecoin) ikut naik"],
  "invalidate": ["Pasokan stablecoin turun > 5% dalam 30 hari", "Aturan baru membatasi penerbit atau penyimpan", "Depeg stablecoin besar"]},
 {"id": "rwa", "title": "Tokenisasi aset dunia nyata (RWA)", "horizon": "2-4 kuartal",
  "kw": ["rwa", "tokeniz", "tokenis", "real world asset", "treasury", "blackrock", "buidl", "franklin", "private credit", "ondo", "securitize"],
  "tags": ["RWA"], "cats": ["rwa", "rwa lending", "treasury"],
  "mechanism": "Manajer aset besar menaruh produk tunai/obligasi di rantai publik. Nilai terkumpul di platform penerbit dan infrastruktur kredit on-chain, bukan di koin spekulatif.",
  "confirm": ["TVL kategori RWA naik", "Produk baru dari manajer aset besar", "Integrasi sebagai jaminan di protokol DeFi"],
  "invalidate": ["Larangan atau pembatasan investor ritel/non-akreditasi", "Gagal bayar pada kredit swasta on-chain"]},
 {"id": "derivatives", "title": "Perp DEX & derivatif on-chain", "horizon": "1-2 kuartal",
  "kw": ["perp", "perpetual", "derivative", "hyperliquid", "open interest", "dydx", "gmx", "aster", "lighter", "options"],
  "tags": ["Derivatives"], "cats": ["derivatives", "perps", "options"],
  "mechanism": "Volume derivatif berpindah dari bursa terpusat ke DEX yang memberi fee riil kepada pemegang token lewat buyback. Pemenang adalah yang punya likuiditas dan pendapatan tertinggi per FDV.",
  "confirm": ["Volume perp DEX dan open interest naik", "Fee/pendapatan protokol naik", "Buyback atau bagi hasil berlanjut"],
  "invalidate": ["Insiden likuidasi berantai atau eksploit", "Pangsa volume kembali ke bursa terpusat"]},
 {"id": "restaking", "title": "Staking likuid, restaking, dan BTCFi", "horizon": "2-3 kuartal",
  "kw": ["staking", "restaking", "eigenlayer", "lido", "liquid staking", "etf staking", "btcfi", "babylon", "lst"],
  "tags": ["Liquid Staking", "Restaking"], "cats": ["liquid staking", "restaking", "liquid restaking", "bridge"],
  "mechanism": "ETF dan institusi mulai mengizinkan staking sehingga imbal hasil native menjadi produk. Aliran masuk ke penyedia staking likuid dengan pangsa pasar dan kepatuhan terbaik.",
  "confirm": ["Persetujuan/peluncuran staking di ETF atau kustodian", "TVL staking likuid naik", "Pangsa pasar pemimpin stabil"],
  "invalidate": ["Insiden slashing besar", "Pembatasan staking oleh regulator"]},
 {"id": "lending", "title": "Kredit & pasar uang on-chain", "horizon": "1-3 kuartal",
  "kw": ["lending", "borrow", "aave", "morpho", "compound", "credit", "yield", "kredit", "interest rate"],
  "tags": ["Lending"], "cats": ["lending", "cdp", "yield aggregator", "basis trading"],
  "mechanism": "Bila likuiditas dolar on-chain bertambah (stablecoin naik, suku bunga turun), permintaan pinjam-meminjam naik dan pendapatan protokol kredit mengikuti.",
  "confirm": ["TVL dan pinjaman aktif naik", "Fee/pendapatan protokol kredit naik"],
  "invalidate": ["Utang macet besar", "Suku bunga stablecoin jatuh di bawah imbal hasil tradisional"]},
 {"id": "etf", "title": "Arus ETF & institusi ke aset besar", "horizon": "1-2 kuartal",
  "kw": ["etf", "inflow", "outflow", "institution", "institusi", "treasury company", "sec ", "spot etf", "13f", "grayscale"],
  "tags": [], "cats": [],
  "mechanism": "Produk ETF baru dan alokasi institusi menyalurkan permintaan lebih dulu ke aset likuid besar; altcoin kecil biasanya menyusul belakangan bila arus bertahan.",
  "confirm": ["Arus bersih ETF positif berturut-turut", "Produk baru disetujui"], "invalidate": ["Arus keluar berkelanjutan", "Penolakan atau penundaan persetujuan"]},
]

# ---------------------------------------------------------------- data stablecoin (gratis)
def fetch_stablecoins():
    try:
        req = urllib.request.Request("https://stablecoins.llama.fi/stablecoins?includePrices=true", headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read()).get("peggedAssets", [])
    except Exception as e:
        print("thesis: stablecoin gagal:", e); return []

def _usd(x, k="peggedUSD"): return ((x or {}).get(k)) if isinstance(x, dict) else None

def rank_stablecoins(rows, n=5, meta=None):
    """USD-pegged: skor = skala (35) + pertumbuhan 30h (25) + sebaran chain (15) + mekanisme (20) + stabilitas peg (5) + atribut manual (hingga 10 / -10)."""
    meta = meta or {}; out = []
    for p in rows:
        if p.get("pegType") != "peggedUSD": continue
        cur = _usd(p.get("circulating")); prev = _usd(p.get("circulatingPrevMonth"))
        if not cur or cur < 50e6: continue
        g = (cur / prev - 1) if prev else None; chains = len(p.get("chains") or [])
        mech = p.get("pegMechanism") or ""; price = p.get("price")
        s = 35 * min(1, math.log10(cur / 50e6) / 3) + (25 * max(0, min(1, (g + .05) / .25)) if g is not None else 10) + 15 * min(1, chains / 15)
        s += 20 if mech == "fiat-backed" else 12 if mech == "crypto-backed" else 4
        dev = abs(price - 1) if price else None
        s += 5 if (dev is not None and dev < .005) else 0 if dev is None else -5 if dev > .02 else 2
        m = meta.get((p.get("symbol") or "").upper(), {}); s += max(-10, min(10, m.get("bonus", 0)))
        why = [f"Pasokan ${cur/1e9:.2f} M" if cur >= 1e9 else f"Pasokan ${cur/1e6:.0f} jt"]
        if g is not None: why.append(f"{g*100:+.1f}% dalam 30 hari")
        if chains: why.append(f"beredar di {chains} chain")
        why.append({"fiat-backed": "dijamin aset fiat/tunai (paling mudah diterima institusi)", "crypto-backed": "dijamin kripto (desentralisasi lebih tinggi, risiko jaminan)"}.get(mech, "mekanisme: " + (mech or "tidak diketahui")))
        if dev is not None and dev > .02: why.append(f"harga menyimpang {dev*100:.1f}% dari $1 (risiko peg)")
        if m.get("note"): why.append(m["note"])
        out.append({"kind": "stablecoin", "symbol": p.get("symbol"), "name": p.get("name"), "score": round(s), "supply": cur, "growth30": g, "chains": chains, "mechanism": mech, "why": why})
    return sorted(out, key=lambda x: -x["score"])[:n]

# ---------------------------------------------------------------- peringkat protokol per tema
def rank_protocols(rows, cats, fees, universe_by_gecko, cand_by_id, n=5):
    """Protokol DefiLlama pada kategori tema: skala TVL (35) + fee 30h (30) + pertumbuhan TVL 30h (15) + sebaran chain (10) + punya token terukur (10)."""
    out = []
    for r in rows:
        cat = (r.get("category") or "").lower()
        if not any(c in cat for c in cats) or (r.get("tvl") or 0) < 20e6: continue
        slug = (r.get("slug") or "").lower(); f = (fees.get(slug) or {}).get("d30"); tvl = r["tvl"]
        g = r.get("change_1m"); chains = len(r.get("chains") or [])
        s = 35 * min(1, math.log10(tvl / 20e6) / 2.7) + (30 * min(1, math.log10(1 + f / 1e5) / 2.5) if f else 0) + (15 * max(0, min(1, ((g or 0) + 10) / 40)) if g is not None else 6) + 10 * min(1, chains / 10)
        gid = r.get("gecko_id"); u = universe_by_gecko.get(gid); cd = cand_by_id.get(gid)
        if u: s += 10
        why = [f"TVL ${tvl/1e6:.0f} jt" if tvl < 1e9 else f"TVL ${tvl/1e9:.2f} M"]
        if f: why.append(f"fee 30 hari ${f/1e6:.2f} jt (${f*12/1e6:.1f} jt/tahun)")
        else: why.append("fee tidak tercatat di DefiLlama")
        if g is not None: why.append(f"TVL {g:+.0f}% sebulan")
        if chains > 1: why.append(f"aktif di {chains} chain")
        if u and u.get("market_cap") and f and f > 0: why.append(f"MC/fee tahunan {u['market_cap']/(f*12):.1f}x")
        if cd: why.append(f"Hunter: {cd['tier']} (skor {cd['score']}), keyakinan agen {cd['conviction']['conviction']}" if cd.get("conviction") else f"Hunter: {cd['tier']} (skor {cd['score']})")
        out.append({"kind": "protocol", "symbol": (r.get("symbol") or "").upper() if r.get("symbol") not in (None, "-") else None, "name": r.get("name"), "category": r.get("category"),
                    "score": round(s), "tvl": tvl, "fees30": f, "mc": (u or {}).get("market_cap"), "has_token": bool(u), "why": why})
    return sorted(out, key=lambda x: -x["score"])[:n]

# ---------------------------------------------------------------- bukti & tesis
def _match(theme, text):
    t = " " + (text or "").lower() + " "; return sum(1 for k in theme["kw"] if k in t)

def evidence(theme, news, sectors, stable_trend, manual, now):
    ev = []; types = set()
    hits = [i for i in news if i.get("published", 0) >= now - 7 * DAY and _match(theme, i.get("title", "") + " " + i.get("summary", "")) > 0]
    hits.sort(key=lambda i: -(i.get("score") or 0))
    if len(hits) >= 2 or any((i.get("score") or 0) >= 55 for i in hits):
        types.add("berita"); ev.append({"type": "berita", "text": f"{len(hits)} berita 7 hari terakhir menyinggung tema ini", "items": [{"title": i["title"], "url": i.get("url"), "source": i.get("source"), "score": i.get("score")} for i in hits[:4]]})
    for s in sectors or []:
        if s.get("tag") in theme["tags"] and s.get("tvl_ch7") is not None:
            if s["tvl_ch7"] > 2: types.add("on-chain"); ev.append({"type": "on-chain", "text": f"TVL sektor {s['tag']} {s['tvl_ch7']:+.1f}% dalam 7 hari"})
            elif s["tvl_ch7"] < -2: ev.append({"type": "kontra", "text": f"TVL sektor {s['tag']} {s['tvl_ch7']:+.1f}% dalam 7 hari (melawan tesis)"})
    if theme["id"] == "stablecoin" and stable_trend:
        g = stable_trend["growth30"]
        if g > .01: types.add("on-chain"); ev.append({"type": "on-chain", "text": f"Total pasokan stablecoin USD ${stable_trend['total']/1e9:.0f} M, {g*100:+.1f}% dalam 30 hari"})
        elif g < -.01: ev.append({"type": "kontra", "text": f"Total pasokan stablecoin {g*100:+.1f}% dalam 30 hari (melawan tesis)"})
    for m in manual:
        if m.get("theme") == theme["id"]:
            types.add("catatan"); ev.append({"type": "catatan", "text": f"{m.get('date', '')}: {m.get('note', '')}", "source": m.get("source"), "horizon": m.get("horizon")})
    return ev, types

def stable_trend(rows):
    cur = prev = 0
    for p in rows:
        if p.get("pegType") != "peggedUSD": continue
        c, pm = _usd(p.get("circulating")), _usd(p.get("circulatingPrevMonth"))
        if c and pm: cur += c; prev += pm
    return {"total": cur, "growth30": cur / prev - 1} if prev else None

def build(news=(), sectors=(), proto_rows=(), universe=(), fees=None, stable_rows=(), cands=(), manual=(), meta=None, now=None):
    now = now or time.time(); fees = fees or {}
    ug = {c["id"]: c for c in universe}; cb = {c["id"]: c for c in cands}
    st = stable_trend(stable_rows); themes = []
    for th in THEMES:
        ev, types = evidence(th, list(news), sectors, st, list(manual), now)
        if not types: continue
        contra = [e for e in ev if e["type"] == "kontra"]
        conf = "kuat" if len(types) >= 3 and not contra else "sedang" if len(types) >= 2 else "lemah"
        leaders = []
        if th["id"] == "stablecoin": leaders = rank_stablecoins(stable_rows, 4, meta)
        leaders_p = rank_protocols(proto_rows, th["cats"], fees, ug, cb, 5) if th["cats"] else []
        hz = next((e.get("horizon") for e in ev if e.get("horizon")), None) or th["horizon"]
        themes.append({"id": th["id"], "title": th["title"], "confidence": conf, "types": sorted(types), "horizon": hz, "mechanism": th["mechanism"],
                       "evidence": ev, "confirm": th["confirm"], "invalidate": th["invalidate"], "leaders": leaders, "leaders_protocols": leaders_p,
                       "best": (leaders[0] if (leaders and th["id"] == "stablecoin") else (leaders_p[0] if leaders_p else None)),
                       "caveat": "Hipotesis dari bukti yang tercatat, bukan ramalan atau nasihat keuangan." + ("" if (leaders or leaders_p) else " Tidak ada data pemeringkat proyek untuk tema ini.")})
    order = {"kuat": 0, "sedang": 1, "lemah": 2}
    themes.sort(key=lambda t: (order[t["confidence"]], -len(t["evidence"])))
    return {"generated_at": int(now), "themes": themes, "stable_total": st, "sources": {"stablecoins": bool(stable_rows), "protocols": bool(proto_rows), "news": len(list(news)), "manual": len(list(manual))}}

def llm_synthesis(theme, llm):
    """Opsional: 3 kalimat sintesis dari bukti yang SUDAH ada (LLM tidak boleh menambah fakta)."""
    try:
        r = llm([{"role": "user", "content": "Tulis tesis 3 kalimat Bahasa Indonesia untuk tema berikut HANYA dari data ini, tanpa menambah fakta atau angka baru, akhiri dengan satu pembatal utama:\n"
                  + json.dumps({k: theme[k] for k in ("title", "mechanism", "evidence", "invalidate")}, ensure_ascii=False, default=str)[:5000]}], None, "Analis riset yang hati-hati. Jangan mengarang.", 300)
        return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text").strip()[:700] or None
    except Exception: return None

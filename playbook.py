#!/usr/bin/env python3
"""
Crypto Sastra - Papan Eksekusi (murni, tanpa jaringan)

Menyaring kandidat Hunter menjadi daftar pendek "layak dieksekusi" dengan gerbang berlapis dan rencana keluar.
Status:
  EKSEKUSI   : SEMUA gerbang lolos, termasuk konfirmasi smart money (akumulasi) DAN narasi on-chain (TVL sektor naik).
  MENUNGGU   : kandidat bagus tetapi ada gerbang yang belum lolos / tidak ada datanya. Tanpa data smart money tidak ada yang bisa berstatus EKSEKUSI.
Rencana keluar bersifat aturan baku (bukan level struktur pasar); bandingkan dengan Scan SMC sebelum memasang order. Bukan nasihat keuangan.
"""
import time

DAY = 86400
MIN_SCORE, MIN_CONV, MIN_COVER, MIN_LIQ = 65, 65, .6, 100e3
STOP, TP1, TP2, TRAIL, TIME_STOP, TIME_REVIEW = .20, .40, 1.00, .25, 30, 21
RISK_PCT, MAX_SIZE_PCT = 1.0, 5.0

def _g(name, ok, text):      # ok: True lolos, False gagal, None tidak ada data
    return {"gate": name, "ok": ok, "text": text}

def gates(c):
    q = c.get("quant") or {}; cv = c.get("conviction") or {}; ag = c.get("agents") or {}; sec = c.get("sector") or {}
    sm = q.get("smart_money") or {}; dp = q.get("depth") or {}; dx = c.get("dex") or {}
    reps = {r["agent"]: r for r in ag.get("reports", [])}; sr = reps.get("Keamanan & Tokenomics")
    out = []
    out.append(_g("Kualitas dasar", c.get("tier") in ("prioritas", "pantau") and not c.get("viral") and not c.get("ghost") and not c.get("legacy") and not q.get("elim") and c.get("score", 0) >= MIN_SCORE,
                  f"skor {c.get('score')} (min {MIN_SCORE}), tier {c.get('tier')}" + (", sudah viral" if c.get("viral") else "") + (", proyek hantu" if c.get("ghost") else "") + (", sektor usang" if c.get("legacy") else "") + (", ELIMINASI MC/FDV" if q.get("elim") else "")))
    if not cv: out.append(_g("Dewan agen", None, "belum diperiksa agen (hanya kandidat teratas yang diperiksa tiap siklus)"))
    else: out.append(_g("Dewan agen", cv.get("conviction", 0) >= MIN_CONV and not cv.get("veto") and (cv.get("coverage") or 0) >= MIN_COVER,
                        f"keyakinan {cv.get('conviction')} (min {MIN_CONV}), cakupan data {round((cv.get('coverage') or 0)*100)}%" + (f", VETO: {'; '.join(cv['veto'])}" if cv.get("veto") else "")))
    if sr is None: out.append(_g("Keamanan kontrak", None, "laporan keamanan tidak ada"))
    else:
        verified = bool(ag.get("security")); out.append(_g("Keamanan kontrak", (sr["verdict"] != "veto" and verified) if verified else None,
                                                          "GoPlus: tidak ada veto" if verified and sr["verdict"] != "veto" else "kontrak belum terverifikasi otomatis (non-EVM/tidak terjangkau): cek manual" if not verified else "veto keamanan"))
    out.append(_g("Likuiditas untuk keluar", (dx.get("liq") or 0) >= MIN_LIQ and dp.get("status") != "tipis" if dx else None,
                  f"likuiditas DEX ${(dx.get('liq') or 0)/1e3:.0f} rb, {((dp.get('ratio') or 0)*100):.1f}% market cap" if dx else "tidak ada pool DEX terdeteksi"))
    un = c.get("unlock_next")
    out.append(_g("Tanpa unlock dekat", None if (un is None and not c.get("unlock_known")) else not (un and un["days"] <= 30),
                  "jadwal unlock tidak tercatat (isi unlocks.json)" if (un is None and not c.get("unlock_known")) else (f"unlock {un['date']} ({un['days']} hari lagi)" if un else "tidak ada unlock tercatat 12 bulan")))
    # konfirmasi wajib
    sms = sm.get("status", "n/a")
    out.append(_g("Konfirmasi smart money", True if sms == "akumulasi" else False if sms in ("distribusi", "netral") else None,
                  {"akumulasi": f"net beli ${(sm.get('net7') or 0)/1e3:.0f} rb (7h) oleh dompet profit teratas", "distribusi": "smart money menjual bersih", "netral": "tidak ada akumulasi bersih"}.get(sms, "tanpa sumber data smart money (pasang DUNE_API_KEY atau smartmoney.json)")))
    ch7 = sec.get("tvl_ch7"); hot = bool(sec.get("hot")); nsc = c.get("narrative_score")
    nar = None if ch7 is None else (ch7 > 0 and (hot or (nsc or 0) >= 55))
    out.append(_g("Konfirmasi narasi on-chain", nar, "TVL sektor tidak tersedia" if ch7 is None else f"sektor {sec.get('tag')}: TVL 7h {ch7:+.1f}%" + (", narasi utama" if hot else "") + f", skor narasi {nsc}"))
    return out

def exit_plan(c, now):
    p = c.get("price"); un = c.get("unlock_next"); cats = [k for k in (c.get("catalysts") or []) if k.get("polarity", 0) > 0 and k.get("days") is not None and k["days"] >= 0]
    plan = {"entry": p, "stop": p * (1 - STOP) if p else None, "tp1": p * (1 + TP1) if p else None, "tp2": p * (1 + TP2) if p else None,
            "rules": [f"Stop keras {STOP*100:.0f}% di bawah entry: keluar semua, tanpa menunggu.",
                      f"Take profit 1 (+{TP1*100:.0f}%): jual 1/3, geser stop ke titik impas.",
                      f"Take profit 2 (+{TP2*100:.0f}%): jual 1/3 lagi; sisanya trailing stop {TRAIL*100:.0f}% dari puncak.",
                      f"Batas waktu: bila belum +10% pada hari {TIME_REVIEW}, tinjau; keluar penuh pada hari {TIME_STOP} bila tesis tidak bergerak."],
            "triggers": ["Smart money berbalik net jual (status distribusi) -> keluar sebagian besar.", "TVL sektor turun lebih dari 5% dalam 7 hari -> narasi pudar, keluar.",
                         "Keyakinan Master Agent turun di bawah 50 atau muncul VETO keamanan -> keluar segera.", "Koin menjadi viral/trending sementara penggunaan datar -> jual ke dalam kekuatan.",
                         "Harga naik >40% tetapi fee/volume tidak ikut naik (divergensi tertutup) -> ambil untung."],
            "deadline": None}
    if un and un["days"] <= 365:
        d = max(0, un["days"] - 7); plan["deadline"] = {"days": d, "text": f"Unlock {un['date']}" + (f" ({un['pct_circ']}% suplai)" if un.get("pct_circ") else "") + f": keluar paling lambat 7 hari sebelumnya (dalam {d} hari)."}
        plan["rules"].insert(0, plan["deadline"]["text"])
    if cats: plan["rules"].append(f"Katalis positif {cats[0]['date']} ({cats[0]['type']}): ambil sebagian 1 hari sebelumnya (sell the news).")
    st = (STOP * 100) or 1; plan["size_pct"] = round(min(MAX_SIZE_PCT, RISK_PCT / (STOP)), 1)
    plan["size_text"] = f"Risiko maksimum {RISK_PCT:.0f}% modal per posisi: dengan stop {STOP*100:.0f}% ukuran posisi ≈ {plan['size_pct']}% modal (batas {MAX_SIZE_PCT:.0f}%)."
    return plan

SWAP = {"ethereum": ("Uniswap", "https://app.uniswap.org/swap?chain=mainnet&outputCurrency={a}"), "base": ("Uniswap (Base)", "https://app.uniswap.org/swap?chain=base&outputCurrency={a}"),
        "arbitrum": ("Uniswap (Arbitrum)", "https://app.uniswap.org/swap?chain=arbitrum&outputCurrency={a}"), "optimism": ("Uniswap (Optimism)", "https://app.uniswap.org/swap?chain=optimism&outputCurrency={a}"),
        "polygon": ("Uniswap (Polygon)", "https://app.uniswap.org/swap?chain=polygon&outputCurrency={a}"), "avalanche": ("Uniswap (Avalanche)", "https://app.uniswap.org/swap?chain=avalanche&outputCurrency={a}"),
        "bsc": ("PancakeSwap", "https://pancakeswap.finance/swap?chain=bsc&outputCurrency={a}"), "solana": ("Jupiter", "https://jup.ag/swap/SOL-{a}")}

def buy_links(c):
    """Tautan pembuka (non-kustodian): Anda memeriksa alamat dan menekan konfirmasi sendiri di dompet/bursa. Tidak ada order otomatis."""
    dx = c.get("dex") or {}; links = []
    if dx.get("address") and dx.get("chain") in SWAP:
        n, u = SWAP[dx["chain"]]; links.append({"label": n, "url": u.format(a=dx["address"])})
    if dx.get("pool") and dx.get("chain"): links.append({"label": "DexScreener", "url": f"https://dexscreener.com/{dx['chain']}/{dx['pool']}"})
    if c.get("id"): links.append({"label": "CoinGecko (daftar bursa)", "url": f"https://www.coingecko.com/en/coins/{c['id']}"})
    if c.get("symbol"): links.append({"label": "Binance (bila terdaftar)", "url": f"https://www.binance.com/en/trade/{c['symbol']}_USDT?type=spot"})
    return {"links": links, "address": dx.get("address"), "chain": dx.get("chain"), "note": "Periksa alamat kontrak di explorer sebelum membeli; tautan hanya membuka aplikasi, bukan rekomendasi bursa."}

def why(c):
    r = []
    q = c.get("quant") or {}
    r += (q.get("notes") or [])[:3]; r += (c.get("notes") or [])[:3]
    cv = c.get("conviction")
    if cv and cv.get("thesis"): r.append(cv["thesis"])
    return r[:6]

def build(cands, thesis=None, now=None, n_exec=5, n_wait=5):
    now = now or time.time(); ex, wait = [], []
    themes = {t["id"]: t for t in (thesis or {}).get("themes", [])}
    for c in cands:
        if c.get("tier") == "lemah" and not (c.get("quant") or {}).get("elim") and c.get("score", 0) < 55: continue
        gs = gates(c); fails = [g for g in gs if g["ok"] is False]; unk = [g for g in gs if g["ok"] is None]
        item = {"symbol": c["symbol"], "name": c["name"], "id": c["id"], "price": c.get("price"), "mc": c.get("mc"), "score": c.get("score"), "tier": c.get("tier"),
                "conviction": (c.get("conviction") or {}).get("conviction"), "gates": gs, "why": why(c), "risks": (c.get("risks") or [])[:4], "plan": exit_plan(c, now), "buy": buy_links(c), "sector": (c.get("sector") or {}).get("tag")}
        if not fails and not unk: item["status"] = "EKSEKUSI"; ex.append(item)
        elif not fails and all(g["gate"] == "Konfirmasi smart money" for g in unk): item["status"] = "MENUNGGU SMART MONEY"; wait.append(item)
        elif len(fails) <= 1 and c.get("score", 0) >= 60: item["status"] = "MENUNGGU"; wait.append(item)
    ex.sort(key=lambda x: -(x["score"] + (x["conviction"] or 0))); wait.sort(key=lambda x: (x["status"] != "MENUNGGU SMART MONEY", -x["score"]))
    sm_on = any(((c.get("quant") or {}).get("smart_money") or {}).get("status", "n/a") != "n/a" for c in cands)
    return {"generated_at": int(now), "execute": ex[:n_exec], "waiting": wait[:n_wait], "smart_money_active": sm_on, "n_checked": len(cands),
            "rules": {"min_score": MIN_SCORE, "min_conviction": MIN_CONV, "stop": STOP, "tp1": TP1, "tp2": TP2}}

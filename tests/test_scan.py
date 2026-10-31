import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan, synth

def run(sym="SOL", seed=7, mk=None, cm=None, tvl=None):
    d = synth.make_daily(seed=seed); w = synth.to_weekly(d)
    last = d[-1]["c"]
    mk = mk or {"market_cap": last * 5e6, "fully_diluted_valuation": last * 6e6, "circulating_supply": 5e6, "total_supply": 6e6, "max_supply": None,
                "total_volume": last * 4e5, "market_cap_rank": 5}
    return scan.analyze(sym, mk, d, w, tvl, None, cm, {"fng": {"value": 40, "label": "Fear"}, "global": {"btc_dom": 58.0, "mcap_24h": 1.2}}, [])

def test_structure_and_fvg():
    d = synth.make_daily(); s = scan.structure(d, 5)
    assert s["bias"] in ("bullish", "bearish", "range") and s["swing_high"] and s["swing_low"]
    f = scan.fvgs(d); assert all(x["lo"] < x["hi"] for x in f)

def test_swings_known_pattern():
    c = [{"o": x, "h": x + 1, "l": x - 1, "c": x, "v": 1} for x in [1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4, 5, 6, 7]]
    sw = scan.swings(c, 2); assert ("H", 4, 6) in sw and ("L", 8, 0) in sw

def test_full_scan_shape_and_math():
    r = run()
    assert 0 <= r["verdict"]["score"] <= 10 and r["verdict"]["label"] in ("ACCUMULATE", "WAIT", "AVOID", "DISTRIBUTE")
    assert abs(sum(r["verdict"]["weights"].values()) - 1) < 1e-9
    st = r["smc"]["setup"]
    if st.get("zone"):
        assert st["stop"] < st["zone"][0] < st["zone"][1] and abs(st["moonbag"] - 2 * st["entry"]) < 1e-9
    if r["barbell"]["risk_alloc_pct"] and st.get("stop_pct"):
        assert abs(r["barbell"]["risk_alloc_pct"] * st["stop_pct"] / 100 - 1.0) < 1e-6   # risiko tepat 1% portofolio
    assert r["barbell"]["final_pct"] <= 10
    json.dumps(r)

def test_fdv_rules():
    last = synth.make_daily()[-1]["c"]
    hi = run(mk={"market_cap": 1e9, "fully_diluted_valuation": 5e9, "circulating_supply": 2e8, "total_supply": 1e9, "max_supply": 1e9, "total_volume": 5e7, "market_cap_rank": 20})
    assert hi["tokenomics"]["fdv_risk"] == "Tinggi" and hi["tokenomics"]["circ_pct"] == 20.0
    lo = run(mk={"market_cap": 1e9, "fully_diluted_valuation": 1.1e9, "circulating_supply": 9e8, "total_supply": 1e9, "max_supply": 1e9, "total_volume": 5e7, "market_cap_rank": 20})
    assert lo["tokenomics"]["fdv_risk"] == "Rendah" and lo["tokenomics"]["score"] > hi["tokenomics"]["score"]

def test_tvl_ratio_and_onchain_metrics():
    r = run(sym="ETH", tvl={"tvl": 2.5e7, "kind": "chain", "name": "Ethereum", "ch30": 0.12, "slug": "Ethereum"},
            cm={"CapMVRVCur": [1.8], "TxTfrValAdjUSD": [1e6] * 100, "CapMrktCurUSD": [8e7], "AdrActCnt": [5e5] * 40})
    f = r["fundamentals"]
    assert f["nvt"]["kind"].startswith("on-chain") and abs(f["nvt"]["value"] - 80) < 1e-6 and f["nvt"]["tone"] == "fair"
    assert f["mvrv"]["kind"].startswith("on-chain") and f["mvrv"]["tone"] == "fair"
    assert f["tvl"]["value"] > 0 and f["tvl"]["tone"] in ("good", "fair", "poor")

def test_smart_money_rules():
    assert run(sym="BTC")["smart_money"]["rule_met"] is None
    assert run(sym="UNI")["smart_money"]["rule_met"] is True and run(sym="OP")["smart_money"]["rule_met"] is False

def run_scn(frac):
    d = synth.make_scenario(frac); w = synth.to_weekly(d); last = d[-1]["c"]
    mk = {"market_cap": last * 5e6, "fully_diluted_valuation": last * 5.2e6, "circulating_supply": 5e6, "total_supply": 5.2e6, "max_supply": None, "total_volume": last * 4e5, "market_cap_rank": 5}
    return d, scan.analyze("UNI", mk, d, w, None, None, None, {"fng": {"value": 30, "label": "Fear"}, "global": {"btc_dom": 58.0, "mcap_24h": 1.0}}, [])

def test_ote_math_and_zone_status():
    d, r = run_scn(0.7); o = r["smc"]["ote"]; st = r["smc"]["setup"]
    rng = o["leg_high"] - o["leg_low"]
    assert abs(o["hi"] - (o["leg_high"] - 0.62 * rng)) < 1e-9 and abs(o["lo"] - (o["leg_high"] - 0.79 * rng)) < 1e-9 and abs(o["eq"] - (o["leg_high"] - 0.5 * rng)) < 1e-9
    assert 95 < o["leg_low"] < 105 and 155 < o["leg_high"] < 175           # leg skenario 100 -> 160
    assert st["stop"] < o["leg_low"] and st["t1"] == o["leg_high"] and abs(st["moonbag"] - 2 * st["entry"]) < 1e-9
    assert st["status"] == "di dalam zona" and st["valid"] and st["rr"] >= 2, st
    assert r["verdict"]["label"] in ("ACCUMULATE", "WAIT")

def test_waiting_when_price_above_zone():
    d, r = run_scn(0.2); st = r["smc"]["setup"]
    assert st["status"] == "menunggu retrace ke zona" and r["verdict"]["label"] != "ACCUMULATE" or r["narrative"]["lifecycle"]["phase"] in (3, 4)

def test_invalid_when_structure_broken():
    d, r = run_scn(1.1); assert r["smc"]["setup"]["status"] == "invalid" and r["barbell"]["final_pct"] == 0

def test_phase3_never_accumulates():
    r = run(seed=3)
    if r["narrative"]["lifecycle"]["phase"] == 3: assert r["verdict"]["label"] == "DISTRIBUTE"
    if r["narrative"]["lifecycle"]["phase"] == 4: assert r["verdict"]["label"] == "AVOID"

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
    r = run()
    print(json.dumps({k: r[k] for k in ("verdict", "barbell")}, indent=1)[:900])
    print("phase", r["narrative"]["lifecycle"]["phase"], r["narrative"]["lifecycle"]["label"], "| htf", r["smc"]["htf"]["bias"], "| ltf", r["smc"]["ltf"]["bias"])
    print("setup", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in (r["smc"]["setup"] or {}).items() if k != "zone"}, "zone", [round(x, 2) for x in (r["smc"]["setup"].get("zone") or [])])

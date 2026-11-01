import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hunter, narrative

def coin(i, sym, name, mc, fdv=None, vol=None, ath=None, price=1.0, c7=2.0, c30=5.0):
    return {"id": i, "symbol": sym.lower(), "name": name, "market_cap": mc, "fully_diluted_valuation": fdv or mc * 1.1,
            "total_volume": vol if vol is not None else mc * 0.08, "ath": ath or price * 4, "current_price": price,
            "price_change_percentage_7d_in_currency": c7, "price_change_percentage_30d_in_currency": c30, "market_cap_rank": 300}

U = [coin("goodcoin", "GOOD", "Goodcoin", 100e6), coin("hypecoin", "HYPE2", "Hypecoin", 100e6, c30=200, c7=60),
     coin("bigcoin", "BIG", "Bigcoin", 5e9), coin("usd-x", "USDX", "Stable USD", 100e6), coin("tinycoin", "TINY", "Tinycoin", 1e6),
     coin("illiq", "ILL", "Illiquid", 50e6, vol=1000), coin("dilute", "DIL", "Dilutecoin", 100e6, fdv=500e6)]
PROTO = {"goodcoin": {"tvl": 400e6, "slug": "goodcoin", "category": "Lending", "chains": ["Ethereum"]}}
REV = {"goodcoin": 2e6}   # 24 jt/tahun -> MC/PS = 4.2x
POSTS = [{"sub": "CryptoCurrency", "title": "$HYPE2 is going to the moon, Hypecoin " * 3, "text": "", "score": 3000, "comments": 800, "url": "u", "created": 0}] * 6

def test_filters_and_ranking():
    r = hunter.hunt(U, PROTO, REV, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    syms = [c["symbol"] for c in r["candidates"]]
    assert "BIG" not in syms and "USDX" not in syms and "TINY" not in syms and "ILL" not in syms
    assert syms[0] == "GOOD"

def test_valuation_and_checklist():
    r = hunter.hunt(U, PROTO, REV, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    g = r["candidates"][0]
    assert round(g["ps"], 1) == 4.2 and g["parts"]["valuasi"]["pts"] == 30
    st = {x["label"]: x["status"] for x in g["checklist"]}
    assert st["Pendapatan nyata"] == "pass" and st["Backer Tier-1 ≥ 3"] == "unknown" and st["Belum viral"] == "pass"

def test_buzz_penalizes_viral():
    quiet = hunter.hunt(U, {}, {}, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    loud = hunter.hunt(U, {}, {}, {}, set(), POSTS, [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    q = {c["symbol"]: c for c in quiet["candidates"]}; l = {c["symbol"]: c for c in loud["candidates"]}
    assert l["HYPE2"]["viral"] and l["HYPE2"]["parts"]["senyap"]["pts"] == 0 and l["HYPE2"]["buzz"]["reddit"] > 0
    assert not q["HYPE2"]["viral"] and q["HYPE2"]["parts"]["senyap"]["pts"] == 25
    assert l["GOOD"]["parts"]["senyap"]["pts"] == 25

def test_trending_means_viral():
    r = hunter.hunt(U, PROTO, REV, {}, {"goodcoin"}, [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    g = next(c for c in r["candidates"] if c["symbol"] == "GOOD")
    assert g["viral"] and g["parts"]["senyap"]["pts"] == 0

def test_dilution_and_late_phase_penalized():
    r = hunter.hunt(U, {}, {}, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    d = {c["symbol"]: c for c in r["candidates"]}
    assert d["DIL"]["parts"]["suplai"]["pts"] == 0 and d["DIL"]["risks"]
    assert d["HYPE2"]["parts"]["fase"]["pts"] <= 1

def test_social_down_is_neutral_not_zero():
    r = hunter.hunt(U, {}, {}, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    r2 = hunter.score_candidate(U[0], None, None, None, None, False, False)
    assert r2["parts"]["senyap"]["pts"] == 12 and next(x for x in r2["checklist"] if x["label"] == "Belum viral")["status"] == "unknown"

def test_mentions_and_sentiment():
    tw = [{"text": "$GOOD is undervalued, accumulating", "tags": ["GOOD"], "likes": 50, "followers": 100000, "user": "ana", "analyst": True, "url": "x"}]
    m = hunter.extract_mentions([], tw, U)
    assert m["goodcoin"]["x"] == 1 and m["goodcoin"]["analyst"] == 1 and m["goodcoin"]["sent"] > 0
    s = hunter.score_candidate(U[0], None, None, None, m["goodcoin"], False, True)
    assert s["bonus"] > 0

def test_tier_never_prioritas_without_evidence():
    assert hunter.tier_label(90, 2, 3) != "prioritas"
    assert hunter.tier_label(80, 6, 7) == "prioritas"

# ---------------------------------------------------------------- Narrative Engine
KW = dict(details={}, dex={}, cg_cats=[], proto_rows=[])

def test_sector_tagging_and_legacy():
    assert narrative.sector_of("RWA Lending")[0] == "RWA"
    assert narrative.sector_of("Yield Aggregator")[1] is True
    assert narrative.sector_of(None, ["Artificial Intelligence (AI)"])[0] == "AI"
    assert narrative.sector_of(None, [])[0] == "Tanpa sektor"

def test_sector_table_velocity_and_divergence():
    rows = [{"category": "RWA", "tvl": 150e6, "change_7d": 45, "change_1m": 60, "gecko_id": "r%d" % i} for i in range(4)] + \
           [{"category": "Dexs", "tvl": 300e6, "change_7d": -2, "change_1m": 1, "gecko_id": "d%d" % i} for i in range(3)]
    uni = [{"id": "r%d" % i, "market_cap": 1e8, "price_change_percentage_7d_in_currency": 5} for i in range(4)]
    t = {s["tag"]: s for s in narrative.sector_table(rows, uni)}
    assert t["RWA"]["velocity"] == 100 and abs(t["RWA"]["tvl_ch7"] - 45) < .01 and abs(t["RWA"]["divergence"] - 40) < .01
    assert t["DEX"]["velocity"] == 0
    assert [s["tag"] for s in narrative.top_narratives(list(t.values()))] == ["RWA"]

def test_components():
    assert narrative.volume_anomaly(30e6, 100e6, 2, dex=True)[0] == 100            # vol/MC 30% tanpa lonjakan harga
    assert narrative.volume_anomaly(30e6, 100e6, 60, dex=True)[0] == 20            # sudah pump: tidak tersembunyi
    assert narrative.volume_anomaly(30e6, 100e6, 2, dex=False)[0] == 70            # gabungan CEX+DEX dipotong
    assert narrative.volume_anomaly(1e6, 100e6, 0, dex=True)[0] == 0
    assert narrative.dev_score(0)[0] == 0 and narrative.dev_score(50)[0] == 100 and narrative.dev_score(None)[0] is None
    assert narrative.dev_score(12, prev_commits=6)[0] == 85
    assert narrative.social_velocity(8, 1, False)[0] == 100 and narrative.social_velocity(40, 30, True)[0] == 10
    n, conf, _ = narrative.narrative_score(None, None, None, None)
    assert n == 30 and conf == 0
    n, conf, _ = narrative.narrative_score({"tvl_ch7": 30}, 100, 100, 100)
    assert n == 100 and conf == 1.0

def test_early_stage_uses_peers_and_dev():
    pr = {"early": {"tvl": 0, "slug": "early", "category": "Lending"}}
    u = [coin("early", "ERLY", "Earlycoin", 60e6, fdv=60e6)]
    r = hunter.hunt(u, pr, {}, {}, set(), [], [], now=time.time(), details={"early": {"age_days": 120, "commits4w": 80, "categories": [], "platforms": {}, "repos": ["x"]}},
                    dex={"early": None}, cg_cats=[], proto_rows=[])
    c = r["candidates"][0]
    assert c["early"] and "early-stage" in c["parts"]["valuasi"]["note"] and c["parts"]["valuasi"]["pts"] >= 15
    assert c["dev"]["commits4w"] == 80

def test_ghost_and_legacy_penalties():
    pr = {"dead": {"tvl": 0, "slug": "dead", "category": "Yield"}}
    u = [coin("dead", "DEAD", "Deadcoin", 40e6)]
    det = {"dead": {"age_days": 900, "commits4w": 0, "categories": [], "platforms": {}, "repos": ["x"]}}
    r = hunter.hunt(u, pr, {}, {}, set(), [], [], now=time.time(), details=det, dex={"dead": None}, cg_cats=[], proto_rows=[])
    c = r["candidates"][0]
    assert c["ghost"] and c["legacy"] and c["tier"] == "lemah" and c["penalty"] == 25
    assert any("proyek mati" in x for x in c["risks"]) and any("usang" in x for x in c["risks"])

def test_unlock_and_float_penalty():
    c = coin("lowfloat", "LF", "Lowfloat", 100e6, fdv=900e6); c["circulating_supply"] = 10; c["total_supply"] = 100
    s = hunter.score_candidate(c, None, None, None, None, False, True, unlocks=[{"date": "2099-01-01", "pct_circ": 12}])
    assert s["parts"]["suplai"]["pts"] == 0 and any("Low Float" in x for x in s["risks"])
    s2 = hunter.score_candidate(c, None, None, None, None, False, True, unlocks=None)
    assert any("jadwal unlock tidak tercatat" in x for x in s2["risks"])

def test_catalysts(monkeypatch):
    now = time.time(); d = time.strftime("%Y-%m-%d", time.gmtime(now + 10 * 86400)); neg = time.strftime("%Y-%m-%d", time.gmtime(now + 20 * 86400))
    monkeypatch.setattr(narrative.scan, "_load_json", lambda n, dflt: {"events": [{"symbol": "AAA", "date": d, "type": "Mainnet", "note": "v2", "polarity": 1},
                                                                           {"symbol": "BBB", "date": neg, "type": "Unlock", "note": "cliff", "polarity": -1}]})
    assert narrative.catalysts_for("AAA", now)[1] == 10
    assert narrative.catalysts_for("BBB", now)[1] == -10
    news = [{"projects": ["CCC"], "event": "Listing Exchange Besar", "published": now - 3600, "title": "CCC listed", "url": "u"}]
    assert narrative.catalysts_for("CCC", now, news)[1] == 4
    assert narrative.catalysts_for("ZZZ", now)[1] == 0

def test_handoff_requires_pool_and_not_viral():
    res = {"candidates": [{"symbol": "A", "tier": "prioritas", "scan_ref": {"chain": "base", "pool": "0x1"}, "viral": False},
                          {"symbol": "B", "tier": "prioritas", "scan_ref": None, "viral": False},
                          {"symbol": "C", "tier": "pantau", "scan_ref": {"chain": "base", "pool": "0x2"}, "viral": True},
                          {"symbol": "D", "tier": "lemah", "scan_ref": {"chain": "base", "pool": "0x3"}, "viral": False}]}
    assert [c["symbol"] for c in hunter.handoff(res)] == ["A"]

def test_history_feeds_social_velocity():
    u = [coin("goodcoin", "GOOD", "Goodcoin", 100e6)]
    posts = [{"sub": "defi", "title": "$GOOD DD analysis", "text": "", "score": 40, "comments": 10, "url": "u", "created": 0}]
    prev = {"hist": {"goodcoin": {"w": 0.0, "commits": 5}}}
    r = hunter.hunt(u, {}, {}, {}, set(), posts, [], now=time.time(), prev=prev, **KW)
    assert r["candidates"][0]["narrative_notes"]["social"].startswith("kecepatan")
    assert "goodcoin" in r["hist"]

def test_dex_candles_feed_scan(monkeypatch):
    import scan, synth
    d = synth.make_scenario(0.7)
    lst = [[c["t"] // 1000, c["o"], c["h"], c["l"], c["c"], c["v"]] for c in reversed(d)]      # GeckoTerminal: terbaru dulu
    monkeypatch.setattr(scan, "jget", lambda url, timeout=15: {"data": {"attributes": {"ohlcv_list": lst}}})
    scan.COINS["DEXC"] = {"cg": "dexc", "name": "Dex Coin", "narr": "RWA (uji)"}; scan.DYN["DEXC"] = {"chain": "base", "pool": "0xpool"}
    try:
        day, wk = scan.fetch_candles("DEXC", "1d"), scan.fetch_candles("DEXC", "1w")
        assert len(day) == len(d) and day[0]["t"] < day[-1]["t"] and len(wk) >= len(d) // 7 - 1
        mk = {"market_cap": 5e7, "fully_diluted_valuation": 6e7, "circulating_supply": 1, "total_supply": 1, "max_supply": None, "total_volume": 4e6, "market_cap_rank": 400}
        monkeypatch.setattr(scan, "fetch_tvl", lambda s: None)
        r = scan.scan_symbol("DEXC", {"DEXC": mk}, [], {"fng": {"value": 50, "label": "Neutral"}, "global": {"btc_dom": 58, "mcap_24h": 0.5}})
        assert 0 <= r["verdict"]["score"] <= 10 and r["symbol"] == "DEXC"
    finally:
        scan.COINS.pop("DEXC", None); scan.DYN.pop("DEXC", None); scan._GT.clear()

def test_old_schema_is_recomputed(monkeypatch):
    calls = []
    monkeypatch.setattr(hunter, "hunt", lambda **kw: calls.append(1) or {"schema": hunter.SCHEMA, "candidates": [{"x": 1}], "sources": {}, "generated_at": 1})
    fresh_old = {"generated_at": time.time(), "candidates": [{"y": 1}]}        # baru dibuat tetapi tanpa skema
    out = hunter.run(lambda n, d: fresh_old, lambda n, o: None)
    assert calls and out["schema"] == hunter.SCHEMA
    calls.clear(); cur = {"schema": hunter.SCHEMA, "generated_at": time.time(), "candidates": [{"y": 1}]}
    assert hunter.run(lambda n, d: cur, lambda n, o: None) is cur and not calls

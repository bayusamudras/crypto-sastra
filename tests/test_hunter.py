import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hunter

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
    r = hunter.hunt(U, PROTO, REV, {}, set(), [], [], now=time.time())
    syms = [c["symbol"] for c in r["candidates"]]
    assert "BIG" not in syms and "USDX" not in syms and "TINY" not in syms and "ILL" not in syms
    assert syms[0] == "GOOD"

def test_valuation_and_checklist():
    r = hunter.hunt(U, PROTO, REV, {}, set(), [], [], now=time.time())
    g = r["candidates"][0]
    assert round(g["ps"], 1) == 4.2 and g["parts"]["valuasi"]["pts"] == 30
    st = {x["label"]: x["status"] for x in g["checklist"]}
    assert st["Pendapatan nyata"] == "pass" and st["Backer Tier-1 ≥ 3"] == "unknown" and st["Belum viral"] == "pass"

def test_buzz_penalizes_viral():
    quiet = hunter.hunt(U, {}, {}, {}, set(), [], [], now=time.time())
    loud = hunter.hunt(U, {}, {}, {}, set(), POSTS, [], now=time.time())
    q = {c["symbol"]: c for c in quiet["candidates"]}; l = {c["symbol"]: c for c in loud["candidates"]}
    assert l["HYPE2"]["viral"] and l["HYPE2"]["parts"]["senyap"]["pts"] == 0 and l["HYPE2"]["buzz"]["reddit"] > 0
    assert not q["HYPE2"]["viral"] and q["HYPE2"]["parts"]["senyap"]["pts"] == 25
    assert l["GOOD"]["parts"]["senyap"]["pts"] == 25

def test_trending_means_viral():
    r = hunter.hunt(U, PROTO, REV, {}, {"goodcoin"}, [], [], now=time.time())
    g = next(c for c in r["candidates"] if c["symbol"] == "GOOD")
    assert g["viral"] and g["parts"]["senyap"]["pts"] == 0

def test_dilution_and_late_phase_penalized():
    r = hunter.hunt(U, {}, {}, {}, set(), [], [], now=time.time())
    d = {c["symbol"]: c for c in r["candidates"]}
    assert d["DIL"]["parts"]["suplai"]["pts"] == 0 and d["DIL"]["risks"]
    assert d["HYPE2"]["parts"]["fase"]["pts"] <= 1

def test_social_down_is_neutral_not_zero():
    r = hunter.hunt(U, {}, {}, {}, set(), [], [], now=time.time())
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

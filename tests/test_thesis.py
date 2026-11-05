import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import thesis, hunter
NOW = 1_800_000_000
def sc(sym, cur, prev, mech="fiat-backed", chains=10, price=1.0, peg="peggedUSD"):
    return {"symbol": sym, "name": sym, "pegType": peg, "pegMechanism": mech, "circulating": {"peggedUSD": cur}, "circulatingPrevMonth": {"peggedUSD": prev}, "chains": ["c"] * chains, "price": price}
ST = [sc("AAA", 70e9, 65e9, chains=20), sc("BBB", 80e9, 79e9, chains=25), sc("CCC", 5e9, 2e9, "crypto-backed", 8), sc("DDD", 1e9, 1.1e9, "algorithmic", 2, .96), sc("EUR", 5e9, 4e9, peg="peggedEUR")]
NEWS = [{"id": "1", "title": "Major bank to issue stablecoin after GENIUS Act", "summary": "", "published": NOW - 3600, "score": 70, "source": "x", "url": "u"},
        {"id": "2", "title": "Visa expands stablecoin payment settlement", "published": NOW - 7200, "score": 40, "source": "x", "url": "u"}]

def test_stablecoin_rank_prefers_scale_growth_fiat_and_excludes_non_usd():
    r = thesis.rank_stablecoins(ST); syms = [x["symbol"] for x in r]
    assert "EUR" not in syms and syms[0] in ("AAA", "BBB") and syms.index("DDD") > syms.index("CCC")
    assert any("30 hari" in w for w in r[0]["why"]) and any("fiat" in w for w in r[0]["why"])
def test_theme_needs_evidence_and_confidence_grows_with_types():
    assert thesis.build([], [], [], [], {}, [], [], [], None, NOW)["themes"] == []
    t = thesis.build(NEWS, [], [], [], {}, ST, [], [], None, NOW)["themes"]
    s = [x for x in t if x["id"] == "stablecoin"][0]; assert s["confidence"] in ("sedang", "kuat") and set(s["types"]) >= {"berita", "on-chain"}
    assert s["best"]["symbol"] in ("AAA", "BBB") and s["invalidate"] and s["confirm"]
    t2 = thesis.build(NEWS, [], [], [], {}, [], [], [], None, NOW)["themes"]; assert [x for x in t2 if x["id"] == "stablecoin"][0]["confidence"] == "lemah"
def test_manual_note_and_contra_evidence():
    man = [{"theme": "stablecoin", "date": "2026-11-01", "note": "uji", "source": "s", "horizon": "Q1 2027"}]
    s = thesis.build(NEWS, [], [], [], {}, ST, [], man, None, NOW)["themes"][0]; assert s["horizon"] == "Q1 2027" and s["confidence"] == "kuat"
    shrink = [sc("AAA", 60e9, 70e9)]
    s2 = thesis.build(NEWS, [], [], [], {}, shrink, [], [], None, NOW)["themes"][0]; assert any(e["type"] == "kontra" for e in s2["evidence"])
def test_protocol_ranking():
    rows = [{"name": "Big", "slug": "big", "category": "Lending", "tvl": 5e9, "change_1m": 10, "chains": ["a"] * 6, "gecko_id": "big", "symbol": "BIG"},
            {"name": "Small", "slug": "small", "category": "Lending", "tvl": 30e6, "change_1m": -5, "chains": ["a"], "symbol": "SM"}, {"name": "Other", "slug": "o", "category": "Dexs", "tvl": 9e9}]
    r = thesis.rank_protocols(rows, ["lending"], {"big": {"d30": 4e6}}, {"big": {"market_cap": 1e9}}, {}); assert [x["name"] for x in r] == ["Big", "Small"] and any("MC/fee" in w for w in r[0]["why"])
def test_hunt_has_thesis():
    import test_hunter as T
    r = hunter.hunt(T.U, T.PROTO, T.REV, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[], news=[])
    assert "thesis" in r and r["schema"] == hunter.SCHEMA

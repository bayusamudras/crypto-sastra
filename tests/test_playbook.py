import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import playbook, hunter
NOW = 1_800_000_000
def cand(sm="akumulasi", ch7=6.0, **k):
    c = {"id": "x", "symbol": "XYZ", "name": "Xyz", "price": 2.0, "mc": 80e6, "score": 74, "tier": "prioritas", "narrative_score": 62, "viral": False, "ghost": False, "legacy": False,
         "sector": {"tag": "RWA", "tvl_ch7": ch7, "hot": True}, "dex": {"liq": 900e3}, "unlock_known": True, "unlock_next": None, "catalysts": [], "notes": ["n"], "risks": [],
         "quant": {"elim": False, "smart_money": {"status": sm, "net7": 3e5}, "depth": {"status": "tebal", "ratio": .1}, "notes": ["q"]},
         "conviction": {"conviction": 72, "coverage": .8, "veto": [], "thesis": "t"},
         "agents": {"security": {"honeypot": False}, "reports": [{"agent": "Keamanan & Tokenomics", "verdict": "ok", "score": 80}]}}
    c.update(k); return c
def test_execute_only_with_all_confirmations():
    r = playbook.build([cand()], None, NOW); assert [x["symbol"] for x in r["execute"]] == ["XYZ"] and r["execute"][0]["status"] == "EKSEKUSI"
def test_no_smart_money_data_never_executes():
    r = playbook.build([cand(sm="n/a")], None, NOW); assert not r["execute"] and r["waiting"][0]["status"] == "MENUNGGU SMART MONEY"
def test_distribution_or_falling_tvl_blocks():
    assert not playbook.build([cand(sm="distribusi")], None, NOW)["execute"]
    assert not playbook.build([cand(ch7=-3)], None, NOW)["execute"]
def test_veto_viral_unlock_block():
    assert not playbook.build([cand(viral=True)], None, NOW)["execute"]
    assert not playbook.build([cand(conviction={"conviction": 90, "coverage": .9, "veto": ["honeypot"]})], None, NOW)["execute"]
    assert not playbook.build([cand(unlock_next={"date": "2026-12-01", "days": 10, "pct_circ": 8})], None, NOW)["execute"]
def test_exit_plan_levels_and_unlock_deadline():
    p = playbook.build([cand(unlock_next={"date": "2027-03-01", "days": 100, "pct_circ": 5})], None, NOW)["execute"][0]["plan"]
    assert abs(p["stop"] - 1.6) < 1e-9 and abs(p["tp1"] - 2.8) < 1e-9 and p["deadline"]["days"] == 93 and p["size_pct"] == 5.0 and len(p["triggers"]) >= 4
def test_hunt_has_playbook_and_stale_smartmoney_ignored():
    import test_hunter as T
    r = hunter.hunt(T.U, T.PROTO, T.REV, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    assert "playbook" in r and r["playbook"]["execute"] == []
    assert hunter._fresh_sm(time.time()) == {}

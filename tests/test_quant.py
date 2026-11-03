import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import quant, hunter
NOW = 1_800_000_000
def c(**k):
    d = {"mc": 50e6, "fdv": 60e6, "rev30": 2e5, "chg30": 1.0, "dex": {"liq": 8e6}}; d.update(k); return d
def ctx(**k):
    d = {"tag": "Perp", "pf_med": {"median": 40.0, "n": 5}, "fees": {"d1": 1e5, "d7": 8e5, "d30": 3e6, "ch30": .5}, "vol": {"d1": 5e7, "d7": 3e8, "d30": 1e9, "ch30": .6},
         "tvl": 40e6, "unlocks12": [], "circ_now": None, "hist": None, "now": NOW, "sm": None}; d.update(k); return d

def test_sector_median_needs_peers():
    m = quant.sector_medians([("A", 10), ("A", 20), ("B", 5), ("A", 30), ("A", None)]); assert m["A"]["median"] == 20 and "B" not in m
def test_pf_undervalued_confirmed_and_divergence():
    q = quant.analyze(c(), ctx())           # pf = 60e6/36e6 = 1.67x vs 40x
    assert q["valuation"]["status"] == "undervalued_terkonfirmasi" and q["divergence"]["status"] == "divergensi"
    assert q["capital_efficiency"]["status"] == "sangat_aktif" and q["depth"]["status"] == "tebal" and q["adjust"] > 0 and q["adjust"] <= 10
def test_cheap_without_growth_not_confirmed():
    q = quant.analyze(c(), ctx(fees={"d30": 3e6, "ch30": -.2}, vol={"d1": 1e6, "d30": 3e7, "ch30": -.1}))
    assert q["valuation"]["status"] == "murah_belum_terkonfirmasi" and q["divergence"]["status"] == "tidak"
def test_divergence_not_when_price_already_up():
    assert quant.analyze(c(chg30=40), ctx())["divergence"]["status"] == "sudah_naik"
def test_mcfdv_elimination_rules():
    lo = c(mc=10e6, fdv=100e6)
    assert quant.analyze(lo, ctx(unlocks12=[{"date": "2027-01-01"}]))["elim"]
    assert quant.analyze(lo, ctx(unlocks12=None))["elim"]            # tak tercatat = dianggap berisiko
    assert not quant.analyze(lo, ctx(unlocks12=[]))["elim"]          # dipastikan tanpa unlock
def test_emission_trap():
    q = quant.analyze(c(mc=100e6, fdv=120e6, rev30=1e5), ctx(circ_now=110, hist={"circ": 100, "ct": NOW - 30 * 86400}))
    assert q["emission"]["status"] == "jebakan_emisi" and q["emission"]["net_real_yield"] < 0
def test_positive_real_yield_and_no_history_is_na():
    assert quant.analyze(c(rev30=5e6), ctx(circ_now=100.5, hist={"circ": 100, "ct": NOW - 30 * 86400}))["emission"]["status"] == "positif"
    assert quant.analyze(c(), ctx())["emission"]["status"] == "n/a"
def test_smart_money_and_missing():
    assert quant.analyze(c(), ctx(sm={"net_flow_usd_7d": 2e5, "net_flow_usd_14d": 3e5, "wallets_buying": 30, "wallets_selling": 10}))["smart_money"]["status"] == "akumulasi"
    assert quant.analyze(c(), ctx(sm={"net_flow_usd_7d": -2e5}))["smart_money"]["status"] == "distribusi"
    assert quant.analyze(c(), ctx())["smart_money"]["status"] == "n/a"
def test_thin_depth_flagged():
    q = quant.analyze(c(dex={"liq": 5e5}), ctx()); assert q["depth"]["status"] == "tipis"
def test_hunt_integration():
    import test_hunter as T
    r = hunter.hunt(T.U, T.PROTO, T.REV, {}, set(), [], [], now=time.time(), details={}, dex={}, cg_cats=[], proto_rows=[])
    assert all("quant" in x for x in r["candidates"]) and r["schema"] == hunter.SCHEMA

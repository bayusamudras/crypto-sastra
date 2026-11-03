import json, time, unittest
import agents, memory

NOW = 1_800_000_000
def cand(**k):
    c = {"id": "x", "symbol": "XYZ", "name": "Xyz", "mc": 50e6, "score": 70, "price": 1.0, "fdv_mc": 1.2, "tier": "prioritas", "rev30": 1e5,
         "dex": {"chain": "ethereum", "address": "0xabc", "liq": 800e3, "buys": 300, "sells": 200, "pool_age_days": 90, "vol24": 1e6},
         "dev": {"commits4w": 40, "repos": ["https://github.com/a/b"]}, "buzz": {}, "sector": {"tag": "RWA"}, "links": {}}
    c.update(k); return c

SAFE = {"honeypot": False, "cannot_sell_all": False, "mintable": False, "hidden_owner": False, "take_back_ownership": False, "pausable": False,
        "slippage_mod": False, "proxy": False, "open_source": True, "buy_tax": 0, "sell_tax": 0, "holder_count": 5000, "top1_pct": 5, "top10_pct": 25, "lp_locked_pct": 90, "owner_pct": 0}
GH = {"repo": "a/b", "fork": False, "parent": None, "commits90": 120, "capped": True, "authors90": 6, "top_author_share": .3, "trivial_share": .1,
      "pr_sample": [{"files": 6, "lines": 300, "comments": 2}], "archived": False, "pushed_days": 2, "stars": 10, "created_days": 400}
def tools(sec=SAFE, gh=GH, y=None):
    return {"security": lambda ch, ad: sec, "github": lambda r: gh, "yield": lambda s: y, "doc": lambda u: None}

class AgentTests(unittest.TestCase):
    def test_clean(self):
        o = agents.run_council(cand(), tools())
        self.assertGreaterEqual(o["conviction"], 60); self.assertFalse(o["veto"])
    def test_honeypot_veto_absolute(self):
        o = agents.run_council(cand(), tools(sec=dict(SAFE, honeypot=True)))
        self.assertEqual(o["verdict"], "HINDARI"); self.assertLessEqual(o["conviction"], 15)
    def test_llm_cannot_override_veto(self):
        llm = lambda m, t, s: {"stop_reason": "end_turn", "content": [{"type": "text", "text": '{"adjust": 99, "thesis": "beli", "red_flags": [], "verify": []}'}]}
        o = agents.run_council(cand(), tools(sec=dict(SAFE, honeypot=True)), llm=llm, use_llm=True)
        self.assertLessEqual(o["conviction"], 15)
    def test_llm_adjust_clamped_and_tool_loop(self):
        calls = []
        def llm(m, t, s):
            calls.append(1)
            if len(calls) == 1: return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "t1", "name": "real_yield", "input": {"slug": "a"}}]}
            return {"stop_reason": "end_turn", "content": [{"type": "text", "text": '{"adjust": 99, "thesis": "ok", "red_flags": ["x"], "verify": []}'}]}
        o = agents.run_council(cand(), tools(), llm=llm, use_llm=True)
        self.assertEqual(len(calls), 2); self.assertTrue(o["llm"]); self.assertEqual(o["thesis"], "ok")
    def test_no_data_caps_conviction(self):
        o = agents.run_council(cand(dex=None, dev=None), {"security": None, "github": None})
        self.assertLessEqual(o["conviction"], 74); self.assertIn("On-Chain & Likuiditas", o["no_data"])
    def test_fork_and_concentration_flagged(self):
        o = agents.run_council(cand(), tools(sec=dict(SAFE, top10_pct=80), gh=dict(GH, fork=True, parent="u/v")))
        fl = " ".join(x for r in o["reports"] for x in r["flags"]); self.assertIn("fork", fl); self.assertIn("Konsentrasi", fl)
    def test_llm_failure_falls_back(self):
        def bad(m, t, s): raise RuntimeError("x")
        o = agents.run_council(cand(), tools(), llm=bad, use_llm=True); self.assertFalse(o["llm"])

class MemoryTests(unittest.TestCase):
    def test_vector_similarity(self):
        a, b, c = memory.embed("fdv_tinggi sektor:RWA unlock_dekat"), memory.embed("fdv_tinggi sektor:RWA unlock_dekat likuiditas_tipis"), memory.embed("zzz qqq www")
        self.assertGreater(memory.cosine(a, b), .6); self.assertLess(memory.cosine(a, c), .3)
    def test_trend(self):
        m = memory.Memory()
        for i, v in enumerate((2, 8, 15)): m.record_sectors([{"tag": "RWA", "tvl_ch7": v}], NOW + i * 86400)
        self.assertEqual(m.trend_for("RWA")["label"], "akselerasi")
    def test_evaluate_lesson_and_learned_rule(self):
        m = memory.Memory()
        for i in range(6):
            m.log_picks([cand(id=f"c{i}", symbol=f"C{i}", fdv_mc=3, price=1.0)], NOW + i * 4 * 86400, btc=100)
        for i in range(6):
            m.log_picks([cand(id=f"g{i}", symbol=f"G{i}", fdv_mc=1.0, price=1.0)], NOW + i * 4 * 86400 + 60, btc=100)
        px = lambda ids: {k: (0.4 if k.startswith("c") else 1.2 if k.startswith("g") else 100) for k in ids}
        n = m.evaluate(px, NOW + 60 * 86400)
        self.assertGreater(n, 0); self.assertTrue(m.lessons)
        self.assertIn("fdv_tinggi", m.rules); self.assertLessEqual(m.rules["fdv_tinggi"]["penalty"], 12)
        pen, why = m.penalty_for(cand(fdv_mc=3)); self.assertGreater(pen, 0)
        self.assertEqual(m.penalty_for(cand(fdv_mc=1))[0], 0)
        self.assertTrue(m.similar_lessons(cand(symbol="NEW", fdv_mc=3)))
    def test_roundtrip(self):
        m = memory.Memory(); m.log_picks([cand()], NOW, 100)
        m2 = memory.Memory(json.loads(json.dumps(m.to_dict()))); self.assertEqual(len(m2.picks), 1)
if __name__ == "__main__": unittest.main()

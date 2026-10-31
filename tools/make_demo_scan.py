#!/usr/bin/env python3
"""Buat data contoh Scan (SINTETIS, bukan data pasar) dan sisipkan ke site/crypto-sastra.src.html untuk mode pratinjau."""
import json, os, re, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [root, os.path.join(root, "tests")]
import scan, synth
d = synth.make_scenario(0.7); w = synth.to_weekly(d); k = 1.45
for c in d + w:
    for f in ("o", "h", "l", "c"): c[f] *= k
last = d[-1]["c"]
mk = {"market_cap": last * 5.2e8, "fully_diluted_valuation": last * 6.1e8, "circulating_supply": 5.2e8, "total_supply": 6.1e8, "max_supply": None,
      "total_volume": last * 9e6, "market_cap_rank": 5}
r = scan.analyze("SOL", mk, d, w, {"tvl": last * 5.2e8 * 0.19, "kind": "chain", "name": "Solana", "ch30": 0.08, "slug": "Solana"},
                 {"d24": 1.2e6, "d7": 8.8e6, "d30": 35e6}, None,
                 {"fng": {"value": 41, "label": "Fear"}, "global": {"btc_dom": 58.2, "mcap_24h": 0.9}}, [])
r["demo"] = True
txt = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
p = os.path.join(root, "site", "crypto-sastra.src.html"); s = open(p, encoding="utf-8").read()
s = re.sub(r"/\*DEMO_SCAN_START\*/.*?/\*DEMO_SCAN_END\*/", lambda m: "/*DEMO_SCAN_START*/const DEMO_SCAN=" + txt + ";/*DEMO_SCAN_END*/", s, flags=re.S)
open(p, "w", encoding="utf-8").write(s); print("demo scan:", r["verdict"]["score"], r["verdict"]["label"], "| fase", r["narrative"]["lifecycle"]["phase"], "| setup", r["smc"]["setup"]["status"], "| bytes", len(txt))

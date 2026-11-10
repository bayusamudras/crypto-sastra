#!/usr/bin/env python3
"""
Crypto Sastra - Memori & Pembelajaran Diri (tanpa dependensi)

  * Memori vektor     : teks diubah menjadi vektor bag-of-words ber-hash (ruang 512 dimensi), kemiripan = cosine.
                        Setara fungsi ChromaDB/Pinecone untuk skala kecil (ratusan catatan), tanpa server dan gratis.
  * Riwayat narasi    : snapshot TVL/momentum per sektor tiap siklus -> label akselerasi/jenuh/netral.
  * Rekam jejak founder: founders.json (manual): proyek sebelumnya, hasil (sukses/rug/gagal).
  * Catatan pilihan   : setiap kandidat teratas dicatat (harga, BTC, fitur risikonya).
  * Evaluasi          : pada hari 7/14/30 dibandingkan dengan BTC. Gagal = turun >35% atau kalah dari BTC >30 poin.
  * Pelajaran         : kegagalan jadi catatan teks (vektor) yang dicari saat kandidat mirip muncul.
  * Aturan terpelajar : fitur dengan tingkat gagal jauh di atas rata-rata (n>=5) mendapat penalti skor, maksimal 12.
Penyimpanan: memory.json lewat fungsi load/dump yang sama dengan data lain.
"""
import hashlib, json, math, re, time

DIM = 512
DAY = 86400
HORIZONS = (7, 14, 30)
FAIL_ABS, FAIL_REL = -35.0, -30.0
MAX_PICKS, MAX_LESSONS, MAX_TREND = 600, 120, 60
MAX_PENALTY = 12
MIN_N = 5

def embed(text):
    v = {}
    toks = re.findall(r"[a-z0-9_]{2,}", (text or "").lower())
    for t in toks:
        h = int(hashlib.md5(t.encode()).hexdigest()[:8], 16)
        i = h % DIM; v[i] = v.get(i, 0) + (1 if (h >> 9) & 1 else -1)
    return {i: x for i, x in v.items() if x}

def cosine(a, b):
    if not a or not b: return 0.0
    dot = sum(x * b.get(i, 0) for i, x in a.items())
    na = math.sqrt(sum(x * x for x in a.values())); nb = math.sqrt(sum(x * x for x in b.values()))
    return dot / (na * nb) if na and nb else 0.0

def features_of(c):
    """Fitur risiko yang bisa dipelajari dari kegagalan masa lalu."""
    f = []
    if (c.get("fdv_mc") or 0) > 2: f.append("fdv_tinggi")
    if c.get("ghost"): f.append("proyek_hantu")
    if c.get("viral"): f.append("sudah_viral")
    if c.get("legacy"): f.append("sektor_usang")
    if c.get("rev30") in (None, 0): f.append("tanpa_pendapatan")
    dx = c.get("dex") or {}
    if dx and (dx.get("liq") or 0) < 100e3: f.append("likuiditas_tipis")
    if dx.get("pool_age_days") is not None and dx["pool_age_days"] < 14: f.append("pool_baru")
    if (c.get("buzz") or {}).get("bot_ratio") and c["buzz"]["bot_ratio"] > .5: f.append("sosial_bot")
    if any("Unlock" in x for x in (c.get("risks") or [])): f.append("unlock_dekat")
    q = c.get("quant") or {}
    if (q.get("emission") or {}).get("status") == "jebakan_emisi": f.append("jebakan_emisi")
    if (q.get("depth") or {}).get("status") == "tipis": f.append("depth_tipis")
    sec = (c.get("sector") or {}).get("tag")
    if sec: f.append("sektor:" + sec)
    ag = c.get("agents") or {}
    for r in ag.get("reports", []):
        for fl in r.get("flags", []):
            if "holder" in fl.lower() and "konsentrasi" in fl.lower(): f.append("holder_terkonsentrasi")
            if "mint" in fl.lower(): f.append("bisa_mint")
            if "lp" in fl.lower() and "terkunci" in fl.lower(): f.append("lp_tidak_terkunci")
    return sorted(set(f))

def pick_text(c):
    return " ".join([c.get("symbol", ""), c.get("name", ""), (c.get("sector") or {}).get("tag") or "", c.get("category") or ""] + features_of(c) + [x for x in (c.get("risks") or [])][:4])

class Memory:
    def __init__(self, data=None):
        d = data or {}
        self.picks = d.get("picks", []); self.lessons = d.get("lessons", []); self.trends = d.get("trends", {}); self.rules = d.get("rules", {})
        self.stats = d.get("stats", {})
        self.founders = {}

    @classmethod
    def load(cls, load, founders=None):
        m = cls(load("memory.json", None)); m.founders = founders or {}; return m

    def to_dict(self):
        return {"picks": self.picks[-MAX_PICKS:], "lessons": self.lessons[-MAX_LESSONS:], "trends": self.trends, "rules": self.rules, "stats": self.stats}

    # ---- riwayat narasi
    def record_sectors(self, sectors, now=None):
        now = int(now or time.time())
        for s in sectors or []:
            if s.get("tvl_ch7") is None: continue
            h = self.trends.setdefault(s["tag"], [])
            if h and now - h[-1]["t"] < 6 * 3600: continue
            h.append({"t": now, "ch7": s["tvl_ch7"], "n": s.get("n")})
            del h[:-MAX_TREND]

    def trend_for(self, tag):
        """akselerasi: momentum TVL naik dan makin cepat; jenuh: sempat tinggi lalu melambat."""
        h = self.trends.get(tag) or []
        if len(h) < 3: return None
        a, b, c = h[-3]["ch7"], h[-2]["ch7"], h[-1]["ch7"]
        if c > 5 and c > b > a: label = "akselerasi"
        elif max(a, b) > 15 and c < max(a, b) * .5: label = "jenuh"
        elif c < -5 and c < b: label = "memudar"
        else: label = "netral"
        return {"tag": tag, "label": label, "series": [x["ch7"] for x in h[-6:]]}

    def founder_note(self, sym):
        f = self.founders.get((sym or "").upper())
        if not f: return None
        bad = [p for p in f.get("projects", []) if p.get("outcome") in ("rug", "gagal")]
        return {"name": f.get("founder"), "projects": f.get("projects", []), "bad": len(bad), "note": f.get("note")}

    # ---- catatan pilihan + evaluasi
    def log_picks(self, cands, now=None, btc=None, n=10):
        now = int(now or time.time()); have = {(p["id"], p["t"] // (3 * DAY)) for p in self.picks}
        added = 0
        for c in cands[:n]:
            if not c.get("price") or (c["id"], now // (3 * DAY)) in have: continue       # satu catatan per koin per 3 hari
            self.picks.append({"id": c["id"], "sym": c["symbol"], "t": now, "price": c["price"], "btc": btc, "score": c.get("score"),
                               "conv": (c.get("conviction") or {}).get("conviction"), "tier": c.get("tier"), "feat": features_of(c),
                               "text": pick_text(c), "ev": {}}); added += 1
        del self.picks[:-MAX_PICKS]
        return added

    def evaluate(self, price_fn, now=None):
        """price_fn(list_of_ids) -> {id: price}; harus menyertakan 'bitcoin'. Mengembalikan jumlah evaluasi baru."""
        now = int(now or time.time()); due = []
        for p in self.picks:
            for h in HORIZONS:
                if str(h) not in p["ev"] and now - p["t"] >= h * DAY: due.append((p, h))
        if not due: return 0
        try: prices = price_fn(sorted({p["id"] for p, _ in due} | {"bitcoin"})) or {}
        except Exception as e: print("memori: harga gagal:", e); return 0
        btc_now, new = prices.get("bitcoin"), 0
        for p, h in due:
            cur = prices.get(p["id"])
            if cur is None or not p.get("price"): continue
            ret = (cur / p["price"] - 1) * 100
            br = ((btc_now / p["btc"] - 1) * 100) if (btc_now and p.get("btc")) else None
            rel = ret - br if br is not None else None
            fail = ret <= FAIL_ABS or (rel is not None and rel <= FAIL_REL)
            p["ev"][str(h)] = {"ret": round(ret, 1), "rel": None if rel is None else round(rel, 1), "fail": fail}; new += 1
            if fail and h >= 14 and not p.get("lessoned"):
                p["lessoned"] = True
                self.lessons.append({"sym": p["sym"], "t": now, "ret": round(ret, 1), "feat": p["feat"], "vec": embed(p["text"]), "text": p["text"],
                                     "msg": f"{p['sym']} turun {ret:.0f}% dalam {h} hari setelah dipilih (skor {p.get('score')}). Fitur risiko saat itu: {', '.join(p['feat']) or 'tidak ada'}."})
        del self.lessons[:-MAX_LESSONS]
        self.learn(); return new

    def learn(self):
        """Fitur dengan tingkat gagal jauh di atas rata-rata (evaluasi 14 hari atau paling akhir tersedia) -> penalti."""
        rows = []
        for p in self.picks:
            e = p["ev"].get("14") or p["ev"].get("30") or p["ev"].get("7")
            if e: rows.append((p["feat"], e["fail"]))
        if len(rows) < MIN_N * 2: self.rules = {}; self.stats = {"evaluated": len(rows), "fail_rate": None}; return
        base = sum(f for _, f in rows) / len(rows); rules = {}
        feats = {x for ft, _ in rows for x in ft}
        for x in feats:
            w = [f for ft, f in rows if x in ft]
            if len(w) < MIN_N: continue
            rate = sum(w) / len(w); lift = rate - base
            if lift >= .2: rules[x] = {"penalty": min(MAX_PENALTY, round(lift * 25)), "n": len(w), "rate": round(rate, 2), "base": round(base, 2)}
        self.rules = rules; self.stats = {"evaluated": len(rows), "fail_rate": round(base, 2)}

    def penalty_for(self, c):
        fs = features_of(c); hit = [(f, self.rules[f]) for f in fs if f in self.rules]
        if not hit: return 0, []
        pen = min(MAX_PENALTY, sum(r["penalty"] for _, r in hit))
        return pen, [f"{f}: {r['rate']*100:.0f}% pilihan serupa gagal (n={r['n']}), penalti {r['penalty']}" for f, r in hit]

    def similar_lessons(self, c, k=2, thr=.45):
        v = embed(pick_text(c)); sc = sorted(((cosine(v, l["vec"]), l) for l in self.lessons), key=lambda x: -x[0])
        return [{"sim": round(s, 2), "msg": l["msg"]} for s, l in sc[:k] if s >= thr and l["sym"] != c.get("symbol")]

    def summary(self):
        ev = sum(1 for p in self.picks if p["ev"])
        return {"picks": len(self.picks), "evaluated": self.stats.get("evaluated", 0), "with_eval": ev, "fail_rate": self.stats.get("fail_rate"),
                "rules": [{"feature": k, **v} for k, v in sorted(self.rules.items(), key=lambda kv: -kv[1]["penalty"])],
                "lessons": [{"sym": l["sym"], "msg": l["msg"], "t": l["t"]} for l in self.lessons[-8:]][::-1],
                "trends": {k: self.trend_for(k) for k in self.trends if self.trend_for(k)}}

def cg_prices(ids):
    import urllib.request
    url = "https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&ids=" + ",".join(ids[:200])
    import os
    hd = {"User-Agent": "CryptoSastra/1.0"}
    if os.getenv("CG_API_KEY"): hd["x-cg-demo-api-key"] = os.getenv("CG_API_KEY")
    with urllib.request.urlopen(urllib.request.Request(url, headers=hd), timeout=20) as r:
        d = json.loads(r.read())
    return {k: v.get("usd") for k, v in d.items()}

#!/usr/bin/env python3
"""
Crypto Sastra - Dewan Agen
Sub-agent spesifik + Master Agent, memanggil alat (tool) data mentah secara dinamis.

  Agen On-Chain & Likuiditas   : umur pool DEX, kedalaman likuiditas, rasio beli/jual, konsentrasi holder
  Agen Keamanan & Tokenomics   : honeypot, fungsi mint, kepemilikan tersembunyi, pajak, kunci LP (GoPlus, gratis), unlock, real yield vs emisi (DefiLlama)
  Agen Narasi & Sosial         : intensitas diskusi, bot vs komunitas asli, sentimen, tren sektor dari memori
  Agen Developer & Kode        : GitHub REST API (aktivitas, fork vs orisinal, kompleksitas PR, bus factor)
  Master Agent                 : menggabungkan laporan menjadi skor keyakinan + verdict. Mode deterministik selalu jalan (gratis);
                                 bila ANTHROPIC_API_KEY ada, LLM memberi penalaran, boleh memanggil alat, dan menyetel keyakinan paling banyak +-15.

Tanpa dependensi (urllib). Semua alat tidak pernah melempar galat: gagal = None dan dicatat sebagai keterbatasan data.
Aturan keras: temuan keamanan berstatus VETO tidak bisa dibatalkan oleh LLM maupun skor lain.
"""
import json, math, os, re, time, urllib.parse, urllib.request

UA = {"User-Agent": "CryptoSastra/1.0"}
GH_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
AGENT_N = int(os.getenv("AGENT_N", "8"))            # kandidat teratas yang diperiksa dewan agen per siklus
LLM_N = int(os.getenv("MASTER_LLM_N", "5"))         # dari itu, berapa yang juga dinalar LLM (hemat biaya)
CHAIN_IDS = {"ethereum": 1, "bsc": 56, "base": 8453, "arbitrum": 42161, "polygon": 137, "avalanche": 43114, "optimism": 10}
DAY = 86400

def _j(url, headers=None, timeout=20):
    h = dict(UA); h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return json.loads(r.read())

def _f(x, d=None):
    try: return float(x)
    except Exception: return d

# ---------------------------------------------------------------- ALAT (tool) data mentah
def tool_security(chain, address):
    """GoPlus Security API (gratis, tanpa kunci): honeypot, mint, kepemilikan, pajak, holder, kunci LP. Hanya EVM; None bila tidak tersedia."""
    cid = CHAIN_IDS.get(chain)
    if not cid or not address: return None
    try: d = _j(f"https://api.gopluslabs.io/api/v1/token_security/{cid}?contract_addresses={address.lower()}", timeout=25)
    except Exception: return None
    r = ((d or {}).get("result") or {}).get(address.lower())
    if not r: return None
    b = lambda k: str(r.get(k, "")).strip() == "1"
    holders = r.get("holders") or []
    pct = lambda h: _f(h.get("percent"), 0.0) * 100
    nonc = [h for h in holders if not (str(h.get("is_contract")) == "1" and str(h.get("is_locked")) == "1")]
    lp = r.get("lp_holders") or []
    lp_locked = sum(_f(x.get("percent"), 0.0) for x in lp if str(x.get("is_locked")) == "1") * 100 if lp else None
    return {"honeypot": b("is_honeypot"), "cannot_sell_all": b("cannot_sell_all"), "mintable": b("is_mintable"), "hidden_owner": b("hidden_owner"),
            "take_back_ownership": b("can_take_back_ownership"), "pausable": b("transfer_pausable"), "slippage_mod": b("slippage_modifiable"),
            "proxy": b("is_proxy"), "open_source": str(r.get("is_open_source", "1")) == "1",
            "buy_tax": _f(r.get("buy_tax"), 0.0) * 100, "sell_tax": _f(r.get("sell_tax"), 0.0) * 100,
            "holder_count": int(_f(r.get("holder_count"), 0) or 0), "top1_pct": pct(holders[0]) if holders else None,
            "top10_pct": sum(pct(h) for h in nonc[:10]) if nonc else None, "lp_locked_pct": lp_locked, "owner_pct": _f(r.get("owner_percent"), 0.0) * 100}

def tool_github(repos):
    """GitHub REST: aktivitas 90 hari, penulis unik, bus factor, fork vs orisinal, pesan commit sepele, kompleksitas PR. Pakai token bila ada (1000 panggilan/jam)."""
    if not repos: return None
    m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", repos[0])
    if not m: return None
    owner, name = m.group(1), re.sub(r"\.git$", "", m.group(2))
    H = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN: H["Authorization"] = "Bearer " + GH_TOKEN
    base = f"https://api.github.com/repos/{owner}/{name}"
    try:
        info = _j(base, H)
        since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 90 * DAY))
        commits = _j(f"{base}/commits?per_page=100&since={since}", H)
    except Exception: return None
    authors = {}
    trivial = 0
    for c in commits:
        a = ((c.get("author") or {}).get("login")) or ((c.get("commit") or {}).get("author") or {}).get("name") or "?"
        authors[a] = authors.get(a, 0) + 1
        msg = ((c.get("commit") or {}).get("message") or "").split("\n")[0].strip().lower()
        if len(msg) < 12 or msg in ("update", "fix", "wip", "test", "commit", "merge") or msg.startswith("update readme"): trivial += 1
    n = len(commits)
    prs = []
    try:
        for p in [x for x in _j(f"{base}/pulls?state=closed&per_page=15", H) if x.get("merged_at")][:5]:
            d = _j(f"{base}/pulls/{p['number']}", H)
            prs.append({"files": d.get("changed_files", 0), "lines": (d.get("additions", 0) or 0) + (d.get("deletions", 0) or 0), "comments": (d.get("review_comments", 0) or 0)})
    except Exception: pass
    return {"repo": f"{owner}/{name}", "fork": bool(info.get("fork")), "parent": (info.get("parent") or {}).get("full_name"), "stars": info.get("stargazers_count"),
            "created_days": (time.time() - time.mktime(time.strptime(info["created_at"], "%Y-%m-%dT%H:%M:%SZ"))) / DAY if info.get("created_at") else None,
            "pushed_days": (time.time() - time.mktime(time.strptime(info["pushed_at"], "%Y-%m-%dT%H:%M:%SZ"))) / DAY if info.get("pushed_at") else None,
            "commits90": n, "capped": n >= 100, "authors90": len(authors), "top_author_share": (max(authors.values()) / n) if n else None,
            "trivial_share": (trivial / n) if n else None, "pr_sample": prs, "archived": bool(info.get("archived"))}

_YIELDS = {"t": 0, "rows": None}
def tool_yield(slug):
    """DefiLlama Yields: pisahkan real yield (apyBase dari fee) dan yield inflasioner (apyReward dari emisi token) untuk pool milik protokol."""
    if not slug: return None
    if time.time() - _YIELDS["t"] > 1800 or _YIELDS["rows"] is None:
        try: _YIELDS["rows"] = _j("https://yields.llama.fi/pools", timeout=60).get("data", []); _YIELDS["t"] = time.time()
        except Exception: _YIELDS["rows"] = _YIELDS["rows"] or []
    rows = [p for p in _YIELDS["rows"] if (p.get("project") or "").lower() == slug.lower() or (p.get("project") or "").lower().startswith(slug.lower() + "-")]
    rows = [p for p in rows if (p.get("tvlUsd") or 0) > 100000]
    if not rows: return None
    tvl = sum(p["tvlUsd"] for p in rows)
    base = sum((p.get("apyBase") or 0) * p["tvlUsd"] for p in rows) / tvl
    rew = sum((p.get("apyReward") or 0) * p["tvlUsd"] for p in rows) / tvl
    return {"pools": len(rows), "tvl": tvl, "apy_base": base, "apy_reward": rew, "real_share": (base / (base + rew)) if (base + rew) > 0 else None}

def tool_doc(url, maxlen=6000):
    """Ambil teks halaman (whitepaper/dokumentasi) untuk dianalisis LLM. HTML dibersihkan; PDF tidak dibaca."""
    if not url or not url.startswith("http"): return None
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            if "pdf" in (r.headers.get("Content-Type") or "").lower(): return None
            raw = r.read(400000).decode("utf-8", "ignore")
    except Exception: return None
    raw = re.sub(r"(?is)<(script|style|nav|footer)[^>]*>.*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()[:maxlen]

def default_tools():
    return {"security": tool_security, "github": tool_github, "yield": tool_yield, "doc": tool_doc}

# ---------------------------------------------------------------- LLM (opsional): Anthropic Messages API dengan tool use
def anthropic_call(messages, tools=None, system=None, max_tokens=900):
    body = {"model": MODEL, "max_tokens": max_tokens, "messages": messages}
    if system: body["system"] = system
    if tools: body["tools"] = tools
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())

LLM_TOOLS = [
    {"name": "security_report", "description": "Laporan keamanan kontrak token (honeypot, mint, pajak, holder, kunci LP) dari GoPlus.",
     "input_schema": {"type": "object", "properties": {"chain": {"type": "string"}, "address": {"type": "string"}}, "required": ["chain", "address"]}},
    {"name": "github_analysis", "description": "Analisis repo GitHub: aktivitas, penulis unik, fork atau orisinal, kompleksitas PR.",
     "input_schema": {"type": "object", "properties": {"repo_url": {"type": "string"}}, "required": ["repo_url"]}},
    {"name": "real_yield", "description": "Pisahkan real yield (fee) dan yield inflasioner (emisi) untuk protokol DefiLlama (slug).",
     "input_schema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "fetch_doc", "description": "Ambil teks whitepaper/dokumentasi dari URL untuk menilai utilitas dan model bisnis.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}]

def _run_llm_tool(name, args, tools):
    try:
        if name == "security_report": return tools["security"](args.get("chain"), args.get("address"))
        if name == "github_analysis": return tools["github"]([args.get("repo_url", "")])
        if name == "real_yield": return tools["yield"](args.get("slug"))
        if name == "fetch_doc": return tools["doc"](args.get("url"))
    except Exception as e: return {"error": str(e)[:100]}
    return {"error": "alat tidak dikenal"}

SYSTEM = ("Kamu Master Agent riset altcoin kecil. Kamu menerima laporan sub-agent (JSON). Aturan: (1) VETO keamanan tidak boleh dibatalkan; (2) jangan mengarang angka, "
          "gunakan alat bila perlu data tambahan; (3) jawab HANYA JSON: {\"adjust\": -15..15, \"thesis\": \"<=3 kalimat Bahasa Indonesia\", \"red_flags\": [..], \"verify\": [..]}. "
          "Ini bahan riset, bukan nasihat keuangan.")

def master_llm(cand, reports, lessons, tools, llm=None, max_turns=4):
    """Penalaran LLM atas laporan sub-agent; boleh memanggil alat. -> {"adjust","thesis","red_flags","verify"} atau None."""
    llm = llm or (anthropic_call if ANTHROPIC_KEY else None)
    if not llm: return None
    brief = {"symbol": cand["symbol"], "name": cand["name"], "mc": cand.get("mc"), "score": cand.get("score"), "sector": (cand.get("sector") or {}).get("tag"),
             "pe": cand.get("ps"), "fdv_mc": cand.get("fdv_mc"), "chain": (cand.get("dex") or {}).get("chain"), "address": (cand.get("dex") or {}).get("address"),
             "repos": (cand.get("dev") or {}).get("repos"), "protocol_slug": ((cand.get("links") or {}).get("defillama") or "").rsplit("/", 1)[-1] or None,
             "agent_reports": reports, "lessons_similar": lessons}
    msgs = [{"role": "user", "content": json.dumps(brief, ensure_ascii=False, default=str)[:9000]}]
    try:
        for _ in range(max_turns):
            r = llm(msgs, LLM_TOOLS, SYSTEM)
            blocks = r.get("content", [])
            uses = [b for b in blocks if b.get("type") == "tool_use"]
            if uses and r.get("stop_reason") == "tool_use":
                msgs.append({"role": "assistant", "content": blocks})
                msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": u["id"],
                                                        "content": json.dumps(_run_llm_tool(u["name"], u.get("input", {}), tools), ensure_ascii=False, default=str)[:4000]} for u in uses]})
                continue
            txt = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            m = re.search(r"\{.*\}", txt, re.S)
            if not m: return None
            out = json.loads(m.group(0))
            return {"adjust": max(-15, min(15, int(out.get("adjust", 0) or 0))), "thesis": str(out.get("thesis", ""))[:600],
                    "red_flags": [str(x)[:160] for x in (out.get("red_flags") or [])][:6], "verify": [str(x)[:160] for x in (out.get("verify") or [])][:6]}
    except Exception as e:
        print("master LLM gagal:", e)
    return None

def doc_summary(url, tools, llm=None):
    """Whitepaper/model bisnis lewat LLM: utilitas token, skema bagi hasil, product-market fit. None bila LLM/dokumen tidak tersedia."""
    llm = llm or (anthropic_call if ANTHROPIC_KEY else None)
    if not llm: return None
    text = tools.get("doc", lambda u: None)(url)
    if not text: return None
    try:
        r = llm([{"role": "user", "content": "Dari teks dokumentasi proyek crypto ini, ekstrak JSON {\"utility\":\"\",\"revenue_model\":\"\",\"revenue_share\":\"\",\"pmf\":\"\",\"red_flags\":[]} "
                  "(Bahasa Indonesia, singkat, tulis 'tidak disebutkan' bila tidak ada, jangan mengarang):\n\n" + text}], None, "Jawab hanya JSON.", 500)
        m = re.search(r"\{.*\}", "".join(b.get("text", "") for b in r.get("content", [])), re.S)
        return json.loads(m.group(0)) if m else None
    except Exception: return None

# ---------------------------------------------------------------- SUB-AGEN (murni: laporan dari data)
def _rep(agent, score, verdict, findings, flags, conf, data=None):
    return {"agent": agent, "score": None if score is None else max(0, min(100, round(score))), "verdict": verdict, "findings": findings, "flags": flags, "confidence": round(conf, 2), "data": data or {}}

def onchain_agent(c, sec):
    dx = c.get("dex"); f, fl, s, conf = [], [], 50.0, 0.0
    if not dx:
        return _rep("On-Chain & Likuiditas", None, "unknown", ["Tidak ada pool DEX terdeteksi atau data DexScreener tidak terjangkau."], [], 0.0)
    conf = .6; liq, mc = dx.get("liq") or 0, c.get("mc") or 0
    s = 40
    if liq >= 500e3: s += 25; f.append(f"Likuiditas DEX ${liq/1e3:.0f} rb: cukup dalam")
    elif liq >= 100e3: s += 12; f.append(f"Likuiditas DEX ${liq/1e3:.0f} rb: terbatas")
    else: s -= 15; fl.append(f"Likuiditas DEX hanya ${liq/1e3:.0f} rb: slippage dan risiko exit tinggi")
    if mc and liq / mc < .01: s -= 8; fl.append("Likuiditas < 1% market cap")
    tot = (dx.get("buys") or 0) + (dx.get("sells") or 0)
    if tot >= 50:
        share = dx["buys"] / tot; f.append(f"Porsi transaksi beli {share*100:.0f}% ({tot} transaksi 24 jam)")
        s += 12 if share >= .55 else -10 if share <= .42 else 0
    age = dx.get("pool_age_days")
    if age is not None:
        if age < 7: s -= 10; fl.append(f"Pool baru ({age:.0f} hari): fase paling berisiko, likuiditas bisa ditarik")
        elif age < 30: f.append(f"Pool berumur {age:.0f} hari")
        else: s += 5; f.append(f"Pool berumur {age:.0f} hari")
    if sec:
        conf = .85
        if sec.get("top10_pct") is not None:
            t = sec["top10_pct"]; f.append(f"10 holder terbesar (di luar kontrak terkunci) memegang {t:.0f}%")
            if t > 70: s -= 20; fl.append(f"Konsentrasi holder ekstrem: top-10 memegang {t:.0f}%")
            elif t > 50: s -= 10; fl.append(f"Konsentrasi holder tinggi: top-10 memegang {t:.0f}%")
            elif t < 30: s += 8
        if sec.get("top1_pct") and sec["top1_pct"] > 20: s -= 8; fl.append(f"Satu dompet memegang {sec['top1_pct']:.0f}%")
        if sec.get("holder_count"): f.append(f"{sec['holder_count']:,} holder")
    else: fl.append("Data holder tidak tersedia (GoPlus tidak mendukung chain ini atau tidak terjangkau); smart money tidak dilacak (Arkham berbayar).")
    s = max(0, min(100, s))
    return _rep("On-Chain & Likuiditas", s, "caution" if (fl and s < 55) else "ok", f, fl, conf)

def security_agent(c, sec, yld, unlocks):
    f, fl, veto = [], [], []
    if sec:
        if sec["honeypot"] or sec["cannot_sell_all"]: veto.append("Honeypot/tidak bisa dijual penuh")
        if sec["sell_tax"] > 10 or sec["buy_tax"] > 10: veto.append(f"Pajak transaksi ekstrem (beli {sec['buy_tax']:.0f}%, jual {sec['sell_tax']:.0f}%)")
        if sec["take_back_ownership"] and sec["hidden_owner"]: veto.append("Kepemilikan tersembunyi yang bisa diambil kembali")
        for k, msg in (("mintable", "Kontrak masih bisa mencetak token baru (mint)"), ("hidden_owner", "Pemilik tersembunyi"), ("pausable", "Transfer bisa dijeda pemilik"),
                       ("slippage_mod", "Pajak bisa diubah pemilik"), ("take_back_ownership", "Pemilik bisa mengambil kembali kepemilikan"), ("proxy", "Kontrak proxy (logika bisa diganti)")):
            if sec.get(k): fl.append(msg)
        if not sec.get("open_source"): fl.append("Kode kontrak tidak open source / tidak terverifikasi")
        lp = sec.get("lp_locked_pct")
        if lp is None: fl.append("Status kunci likuiditas (LP) tidak diketahui")
        elif lp < 50: fl.append(f"Hanya {lp:.0f}% LP terkunci: likuiditas bisa ditarik")
        else: f.append(f"{lp:.0f}% LP terkunci")
        if not fl and not veto: f.append("Tidak ada bendera merah kontrak yang terdeteksi GoPlus")
    else:
        fl.append("Audit kontrak otomatis tidak tersedia (bukan EVM, kontrak tidak ditemukan, atau GoPlus tidak terjangkau): verifikasi manual di explorer.")
    fr, circ = c.get("fdv_mc"), None
    if fr: f.append(f"FDV/MC {fr:.2f}");
    if fr and fr > 2: fl.append(f"FDV {fr:.1f}x market cap: dilusi besar di depan")
    soon = [u for u in (unlocks or []) if (u.get("days") is None or u.get("days") <= 45)]
    if unlocks is None and fr and fr > 1.5: fl.append("Jadwal unlock tidak tercatat padahal FDV tinggi (cek Tokenomist)")
    for u in unlocks or []: fl.append(f"Unlock {u['date']}" + (f" ({u['pct_circ']}% suplai beredar)" if u.get("pct_circ") is not None else ""))
    if yld and yld.get("real_share") is not None:
        rs = yld["real_share"]; f.append(f"Yield pool: {rs*100:.0f}% berasal dari fee riil, sisanya emisi token (APY fee {yld['apy_base']:.1f}% vs emisi {yld['apy_reward']:.1f}%)")
        if rs < .3 and yld["apy_reward"] > 5: fl.append("Yield didominasi emisi token (inflasioner): rawan tekanan jual")
    s = 70 - 12 * len([x for x in fl if not x.startswith("Unlock")]) - 8 * len([x for x in fl if x.startswith("Unlock")])
    if yld and yld.get("real_share") is not None: s += 10 if yld["real_share"] >= .6 else 0
    if sec: s += 10
    conf = .85 if sec else .35
    if veto: return _rep("Keamanan & Tokenomics", 5, "veto", f, veto + fl, conf, {"veto": veto})
    return _rep("Keamanan & Tokenomics", s, "caution" if len(fl) >= 2 else "ok", f, fl, conf)

def social_agent(c, trend=None):
    b = c.get("buzz") or {}; f, fl = [], []
    tot = (b.get("reddit") or 0) + (b.get("x") or 0) + (b.get("tg") or 0)
    s = 55
    if c.get("viral"): s -= 30; fl.append("Sudah ramai dibahas: keunggulan 'belum terlihat' hilang")
    elif tot == 0: s += 10; f.append("Belum ada pembahasan terdeteksi minggu ini")
    else: f.append(f"Pembahasan: Reddit {b.get('reddit',0)}, X {b.get('x',0)}, Telegram {b.get('tg',0)}")
    br = b.get("bot_ratio")
    if br is not None and (b.get("x") or 0) >= 3:
        if br > .5: s -= 20; fl.append(f"Banyak engagement tampak bot/terkoordinasi ({br*100:.0f}% duplikat atau akun baru berpengikut sedikit)")
        else: f.append(f"Rasio bot di X ≈ {br*100:.0f}%")
    if b.get("analyst"): s += 12; f.append(f"{b['analyst']} sebutan dari akun analis pilihan Anda")
    if b.get("sent") is not None and tot:
        if b["sent"] > .2: s += 8
        elif b["sent"] < -.2: s -= 10; fl.append("Sentimen pembahasan negatif")
    if trend:
        f.append(f"Tren sektor {trend['tag']}: {trend['label']}")
        s += 8 if trend["label"] == "akselerasi" else -8 if trend["label"] == "jenuh" else 0
    conf = .35 if tot == 0 and not trend else .6
    return _rep("Narasi & Sosial", s, "caution" if (fl and s < 50) else "ok", f, fl, conf)

def code_agent(c, gh):
    if not gh:
        det = c.get("dev")
        if det and det.get("commits4w") is not None:
            n = det["commits4w"]; s = 20 if n == 0 else 45 if n < 10 else 65 if n < 40 else 80
            return _rep("Developer & Kode", s, "caution" if n == 0 else "ok", [f"{n} commit / 4 minggu (CoinGecko); analisis GitHub mendalam tidak tersedia"], ["Tidak ada commit 4 minggu"] if n == 0 else [], .35)
        return _rep("Developer & Kode", None, "unknown", ["Repo GitHub tidak ditemukan di CoinGecko."], ["Tanpa repo publik, keaslian kode tidak bisa dinilai"], 0.0)
    f, fl, s = [], [], 50
    f.append(f"{gh['commits90']}{'+' if gh['capped'] else ''} commit dalam 90 hari oleh {gh['authors90']} penulis")
    if gh["fork"]: s -= 25; fl.append(f"Repo adalah fork dari {gh.get('parent') or 'repo lain'}: orisinalitas belum terbukti")
    if gh["archived"]: s -= 30; fl.append("Repo diarsipkan")
    if gh["commits90"] == 0: s -= 30; fl.append("Tidak ada commit 90 hari")
    elif gh["commits90"] >= 100: s += 20
    elif gh["commits90"] >= 30: s += 12
    elif gh["commits90"] >= 8: s += 4
    if gh["authors90"] >= 4: s += 12
    elif gh["authors90"] == 1 and gh["commits90"] > 0: s -= 8; fl.append("Satu kontributor saja (bus factor 1)")
    if gh["top_author_share"] and gh["top_author_share"] > .8 and gh["authors90"] > 1: fl.append(f"{gh['top_author_share']*100:.0f}% commit dari satu orang")
    if gh["trivial_share"] and gh["trivial_share"] > .5: s -= 10; fl.append(f"{gh['trivial_share']*100:.0f}% pesan commit sepele (update/fix)")
    prs = gh.get("pr_sample") or []
    if prs:
        avg = sum(p["files"] for p in prs) / len(prs); f.append(f"PR gabungan terakhir rata-rata {avg:.0f} berkas, {sum(p['lines'] for p in prs)//len(prs)} baris")
        if avg >= 4: s += 8
    if gh.get("pushed_days") is not None and gh["pushed_days"] > 60: s -= 12; fl.append(f"Push terakhir {gh['pushed_days']:.0f} hari lalu")
    return _rep("Developer & Kode", s, "caution" if (fl and s < 50) else "ok", f, fl, .85, {"repo": gh["repo"]})

# ---------------------------------------------------------------- MASTER AGENT
WEIGHTS = {"Kuantitatif": .30, "Keamanan & Tokenomics": .25, "On-Chain & Likuiditas": .15, "Developer & Kode": .15, "Narasi & Sosial": .15}

def master(c, reports, lessons=(), llm_out=None):
    """Gabungkan laporan -> skor keyakinan 0-100, verdict, tesis. Veto keamanan mutlak."""
    quant = _rep("Kuantitatif", c.get("score"), "ok", [f"Skor formula {c.get('score')}/100 (dasar {c.get('hunter_score')}, fundamental {c.get('fundamental_score')}, narasi {c.get('narrative_score')})"], [], .9)
    allr = [quant] + list(reports)
    known = [r for r in allr if r["score"] is not None]
    tw = sum(WEIGHTS[r["agent"]] * max(.2, r["confidence"]) for r in known)
    conv = sum(r["score"] * WEIGHTS[r["agent"]] * max(.2, r["confidence"]) for r in known) / tw if tw else 0
    coverage = sum(WEIGHTS[r["agent"]] for r in known) / sum(WEIGHTS.values())
    vetoes = [x for r in allr if r["verdict"] == "veto" for x in r["data"].get("veto", [])]
    cautions = [r for r in allr if r["verdict"] == "caution"]
    adj = (llm_out or {}).get("adjust", 0) or 0
    conv = conv + adj
    if len(cautions) >= 2: conv = min(conv, 69)
    if coverage < .6: conv = min(conv, 74)         # data kurang: jangan beri keyakinan tinggi
    if lessons: conv -= 5
    if vetoes: conv = min(conv, 15)
    conv = max(0, min(100, round(conv)))
    verdict = "HINDARI" if (vetoes or conv < 40) else "RISET LANJUT" if conv >= 75 and coverage >= .6 else "PANTAU"
    flags = [x for r in allr for x in r["flags"]]
    gaps = [r["agent"] for r in allr if r["score"] is None]
    thesis = (llm_out or {}).get("thesis") or (
        f"{'VETO: ' + '; '.join(vetoes) + '. ' if vetoes else ''}Keyakinan {conv}/100 dari {len(known)} dari {len(allr)} agen (cakupan data {round(coverage*100)}%). "
        + (f"Perhatian: {'; '.join(flags[:3])}." if flags else "Tidak ada bendera merah menonjol dari agen yang punya data."))
    return {"conviction": conv, "verdict": verdict, "veto": vetoes, "coverage": round(coverage, 2), "thesis": thesis, "reports": allr, "no_data": gaps,
            "red_flags": ((llm_out or {}).get("red_flags") or []), "verify": ((llm_out or {}).get("verify") or []), "llm": bool(llm_out), "lessons": list(lessons)}

def run_council(c, tools, mem=None, gh_fn=None, llm=None, use_llm=False, trend=None, unlocks=None, now=None):
    """Satu kandidat melewati semua sub-agen lalu Master. `tools` = dict alat (kosong = tanpa panggilan jaringan)."""
    dx = c.get("dex") or {}
    sec = tools["security"](dx.get("chain"), dx.get("address")) if (tools.get("security") and dx.get("address")) else None
    gh = tools["github"]((c.get("dev") or {}).get("repos") or []) if tools.get("github") else None
    slug = ((c.get("links") or {}).get("defillama") or "").rsplit("/", 1)[-1] or None
    yld = tools["yield"](slug) if (tools.get("yield") and slug) else None
    reports = [onchain_agent(c, sec), security_agent(c, sec, yld, unlocks), social_agent(c, trend), code_agent(c, gh)]
    lessons = mem.similar_lessons(c) if mem else []
    out = master(c, reports, lessons)
    if use_llm:
        lo = master_llm(c, [{k: r[k] for k in ("agent", "score", "verdict", "findings", "flags")} for r in out["reports"]], lessons, tools, llm)
        if lo: out = master(c, reports, lessons, lo)
    out["security"] = sec; out["github"] = gh; out["real_yield"] = yld
    return out

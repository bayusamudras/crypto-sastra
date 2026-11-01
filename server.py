#!/usr/bin/env python3
"""
Crypto Sastra - Crypto News Intelligence
- Mengumpulkan berita dari banyak sumber (RSS, Reddit, CryptoPanic, X/Twitter API, CoinGecko)
- Menilai (score 0-100), menentukan dampak, alasan, aksi, estimasi exit, proyek terdampak
- Push realtime ke dashboard lewat Server-Sent Events (SSE)
- Hanya butuh Python 3.9+ (tanpa dependensi wajib)

Jalankan:  python3 server.py   -> buka http://localhost:8000
Mode GitHub Actions: python3 server.py --once  -> satu siklus, hasil ditulis ke DATA_DIR/*.json
"""
import json, os, re, sys, time, threading, hashlib, math, queue, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
try:
    import scan
except Exception as _e:      # scan.py opsional; fitur Scan Institusional mati bila tidak ada
    scan = None
    print('scan.py tidak dimuat:', _e)
try:
    import hunter
except Exception as _e:      # hunter.py opsional
    hunter = None
    print('hunter.py tidak dimuat:', _e)
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from email.utils import parsedate_to_datetime

PORT = int(os.getenv("PORT", "8000"))
POLL = int(os.getenv("POLL_SECONDS", "20"))           # makin kecil makin cepat (hati-hati rate limit)
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")    # opsional: analisis mendalam oleh Claude
CRYPTOPANIC_KEY = os.getenv("CRYPTOPANIC_KEY", "")    # opsional
X_BEARER = os.getenv("X_BEARER_TOKEN", "")            # opsional: X/Twitter API v2
X_ACCOUNTS = os.getenv("X_ACCOUNTS", "binance,coinbase,SECGov,whale_alert,tier10k,WatcherGuru").split(",")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")        # opsional: alert Telegram
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")           # ID chat/grup/channel tujuan (bisa beberapa, pisah koma)
ALERT_MIN = int(os.getenv("ALERT_MIN_SCORE", "70"))   # skor minimum untuk dikirim
ALERT_MAX_PER_HOUR = int(os.getenv("ALERT_MAX_PER_HOUR", "20"))
UA = {"User-Agent": "Mozilla/5.0 CryptoNewsAgent/1.0"}

# ---------------------------------------------------------------- sumber
RSS = {
    "CoinDesk": ("https://www.coindesk.com/arc/outboundfeeds/rss/", 0.90),
    "Cointelegraph": ("https://cointelegraph.com/rss", 0.85),
    "Decrypt": ("https://decrypt.co/feed", 0.85),
    "The Block": ("https://www.theblock.co/rss.xml", 0.90),
    "Bitcoin Magazine": ("https://bitcoinmagazine.com/.rss/full/", 0.80),
    "CryptoSlate": ("https://cryptoslate.com/feed/", 0.75),
    "Binance Announcements": ("https://www.binance.com/en/support/announcement/rss", 0.98),
    "Coinbase Blog": ("https://www.coinbase.com/blog/rss.xml", 0.95),
    "Ethereum Blog": ("https://blog.ethereum.org/feed.xml", 0.95),
    "SEC Press": ("https://www.sec.gov/news/pressreleases.rss", 0.98),
}
REDDIT = {"r/CryptoCurrency": "CryptoCurrency", "r/ethfinance": "ethfinance", "r/solana": "solana"}

# ---------------------------------------------------------------- proyek & hubungan
PROJECTS = {
    "BTC": {"names": ["bitcoin", "btc"], "sector": "L1", "rank": 1, "related": ["MSTR", "MARA", "RIOT", "STX", "ORDI"]},
    "ETH": {"names": ["ethereum", "ether", "eth"], "sector": "L1", "rank": 2, "related": ["LDO", "ARB", "OP", "AAVE", "UNI"]},
    "SOL": {"names": ["solana", "sol"], "sector": "L1", "rank": 5, "related": ["JUP", "RAY", "JTO", "BONK", "PYTH"]},
    "BNB": {"names": ["bnb", "binance coin", "bnb chain"], "sector": "L1", "rank": 4, "related": ["CAKE", "XVS"]},
    "XRP": {"names": ["xrp", "ripple"], "sector": "Payments", "rank": 3, "related": ["XLM", "HBAR", "ALGO"]},
    "ADA": {"names": ["cardano", "ada"], "sector": "L1", "rank": 9, "related": ["DOT", "ATOM"]},
    "DOGE": {"names": ["dogecoin", "doge"], "sector": "Meme", "rank": 8, "related": ["SHIB", "PEPE", "BONK", "WIF"]},
    "AVAX": {"names": ["avalanche", "avax"], "sector": "L1", "rank": 12, "related": ["JOE", "GMX"]},
    "LINK": {"names": ["chainlink", "link"], "sector": "Oracle", "rank": 14, "related": ["PYTH", "BAND", "API3"]},
    "TON": {"names": ["toncoin", "ton ", "telegram"], "sector": "L1", "rank": 10, "related": ["NOT", "DOGS"]},
    "ARB": {"names": ["arbitrum", "arb"], "sector": "L2", "rank": 40, "related": ["OP", "GMX", "ETH"]},
    "OP": {"names": ["optimism", "op mainnet", "superchain"], "sector": "L2", "rank": 45, "related": ["ARB", "BASE", "ETH"]},
    "AAVE": {"names": ["aave"], "sector": "DeFi", "rank": 35, "related": ["COMP", "MKR", "UNI"]},
    "UNI": {"names": ["uniswap", "uni "], "sector": "DeFi", "rank": 30, "related": ["AAVE", "SUSHI", "CRV"]},
    "SUI": {"names": ["sui "], "sector": "L1", "rank": 20, "related": ["APT", "SEI"]},
    "PEPE": {"names": ["pepe"], "sector": "Meme", "rank": 25, "related": ["DOGE", "SHIB", "WIF"]},
    "USDT": {"names": ["tether", "usdt"], "sector": "Stablecoin", "rank": 3, "related": ["USDC", "BTC", "ETH"]},
    "USDC": {"names": ["usdc", "circle"], "sector": "Stablecoin", "rank": 6, "related": ["USDT", "COIN"]},
    "COIN": {"names": ["coinbase"], "sector": "Exchange", "rank": 0, "related": ["BTC", "ETH", "SOL"]},
}
ALIAS = [(a, s) for s, p in PROJECTS.items() for a in p["names"]]

# ---------------------------------------------------------------- jenis event
# (regex, label, arah, bobot dampak 0-1, jendela_exit_jam (min,max), strategi, prediksi lanjutan)
EVENTS = [
    (r"\b(hack|exploit|drain|stolen|breach|rug ?pull|depeg)\b", "Hack / Exploit", -1, 0.95, (0, 6),
     "Jual/kurangi eksposur segera; jangan 'tangkap pisau jatuh'. Cek status withdraw & audit.",
     ["Delisting/suspend deposit-withdraw", "Dana dibekukan / bounty", "Kontagion ke proyek yang sama (fork/bridge)"]),
    (r"\b(delist|delisting|removal of trading|suspend(s|ed)? (trading|withdraw))", "Delisting", -1, 0.85, (0, 12),
     "Keluar sebelum tanggal delisting; likuiditas biasanya tipis mendekati hari-H.",
     ["Penurunan volume permanen", "Exchange lain ikut delist"]),
    (r"\b(lawsuit|sues?|charged|indict|investigation|enforcement|ban(s|ned)?)\b", "Hukum / Regulasi Negatif", -1, 0.75, (0, 24),
     "Kurangi posisi, tunggu kepastian hukum. Pantau pernyataan resmi tim.",
     ["Exchange AS membatasi aset", "Settlement / denda dalam 1-6 bulan"]),
    (r"\b(etf)\b.*\b(approv|launch|go(es)? live)|\bapprov\w* .*\betf\b", "ETF Disetujui", 1, 0.90, (24, 168),
     "Pola 'buy the rumor, sell the news': ambil profit bertahap pada lonjakan awal, sisakan sedikit.",
     ["Inflow ETF hari 1-5", "ETF aset sejenis diajukan/disetujui", "Altcoin sektor sama ikut naik"]),
    (r"\b(etf)\b.*\b(fil(e|ing|ed)|appl(y|ies|ication))", "ETF Pengajuan", 1, 0.60, (48, 336),
     "Posisi spekulatif kecil; catat tenggat keputusan SEC sebagai katalis berikutnya.",
     ["Tenggat keputusan SEC", "Pengajuan serupa dari issuer lain"]),
    (r"\b(will list|to list|lists?|listing|listed on|now available on)\b.*\b(binance|coinbase|upbit|bybit|okx|robinhood|kraken)|\b(binance|coinbase|upbit|bybit|okx|robinhood|kraken)\b.*\b(will list|to list|listing|lists)\b",
     "Listing Exchange Besar", 1, 0.85, (1, 48),
     "Masuk awal sebelum/saat pengumuman, JUAL di spike 1-24 jam; listing sering 'sell the news' setelahnya.",
     ["Pump 20-100% pada hari listing", "Dump setelah 2-5 hari", "Listing di exchange lain menyusul"]),
    (r"\b(token unlock|unlock(s|ing)?|vesting cliff|cliff)\b", "Token Unlock", -1, 0.60, (24, 120),
     "Kurangi sebelum tanggal unlock; beli ulang setelah tekanan jual reda.",
     ["Tekanan jual di hari unlock", "Pembelian ulang setelah +3-7 hari"]),
    (r"\b(mainnet|upgrade|hard ?fork|launch(es|ed)?|v\d+(\.\d+)?)\b", "Upgrade / Mainnet", 1, 0.55, (24, 240),
     "Akumulasi sebelum tanggal upgrade, ambil profit sekitar hari-H.",
     ["Sell-the-news pada hari-H", "Sektor sejenis ikut bergerak"]),
    (r"\b(partner(ship)?|integrat(e|es|ion)|collaborat|adopt(s|ion)?|acquir|invest(s|ment|ed)? )", "Kemitraan / Adopsi / Investasi", 1, 0.55, (6, 96),
     "Cek apakah kemitraan nyata (pengumuman resmi kedua pihak). Masuk bertahap, bukan all-in.",
     ["Pengumuman lanjutan dari mitra", "Kenaikan aktivitas on-chain"]),
    (r"\b(burn|buyback|halving|staking reward)\b", "Burn / Buyback", 1, 0.50, (12, 120),
     "Efek biasanya moderat dan cepat habis; manfaatkan sebagai momentum jangka pendek.", ["Efek suplai berkurang bertahap"]),
    (r"\b(airdrop|snapshot|points)\b", "Airdrop / Snapshot", 1, 0.45, (12, 120),
     "Farming sebelum snapshot, jual saat TGE biasanya turun; waspadai scam link.", ["Dump setelah airdrop", "Naik tipis sebelum snapshot"]),
    (r"\b(approve|approval|legaliz|regulat(ion|ory) clarity|framework|bill passes?|license)\b", "Regulasi Positif", 1, 0.70, (12, 168),
     "Ikuti tren, ambil profit bertahap. Katalis berlaku luas ke aset terkait.", ["Exchange memperluas layanan", "Institusi masuk"]),
    (r"\b(record|all[- ]time high|ath|surge[sd]?|soar|rall(y|ies|ied))\b", "Rally / Momentum", 1, 0.50, (2, 48),
     "Trend following dengan stop-loss ketat; jangan FOMO di puncak.", ["Koreksi sehat setelah ATH", "Funding rate tinggi → risiko long squeeze"]),
    (r"\b(crash|plunge[sd]?|tumble[sd]?|liquidation|sell-?off|dump)\b", "Crash / Likuidasi", -1, 0.70, (0, 12),
     "Hindari leverage; tunggu stabilisasi. Pantau level support & funding rate.", ["Likuidasi berantai", "Rebound teknikal setelah kapitulasi"]),
]
EVENTS = [(re.compile(r, re.I), *rest) for r, *rest in EVENTS]
POS = re.compile(r"\b(bullish|surge|growth|partnership|adopt|record|approval|win|breakthrough|upgrade|inflow|buy)\b", re.I)
NEG = re.compile(r"\b(bearish|crash|hack|ban|lawsuit|outflow|loss|decline|fraud|scam|fear|delay|reject)\b", re.I)
URGENT = re.compile(r"\b(breaking|just in|urgent|confirmed|official|announces?)\b", re.I)

# ---------------------------------------------------------------- state
LOCK = threading.Lock()
NEWS = {}                 # id -> item
SEEN = set()
SUBS = []                 # SSE subscribers
HUNT = {}                 # hasil Hunter terakhir (mode server)
SCANS = {}                # symbol -> hasil Scan Institusional (mode server)
SCAN_PER_RUN = int(os.getenv("SCAN_PER_RUN", "3"))   # jumlah koin yang dipindai per siklus (mode Actions)
STARTED = time.time()

# ---------------------------------------------------------------- harga live & kalibrasi
CG_IDS = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
          "DOGE": "dogecoin", "AVAX": "avalanche-2", "LINK": "chainlink", "TON": "the-open-network", "ARB": "arbitrum",
          "OP": "optimism", "AAVE": "aave", "UNI": "uniswap", "SUI": "sui", "PEPE": "pepe", "USDT": "tether", "USDC": "usd-coin"}
PRICES = {}                                   # symbol -> (harga_usd, timestamp)
HORIZONS = {"1j": 3600, "6j": 6 * 3600, "24j": 24 * 3600}
STATS_FILE = os.getenv("STATS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json"))
STATS = {}                                    # event -> {"hits": n, "n": n, "sum_ret": float}
SIM_PRICES = os.getenv("SIM_PRICES", "") == "1"   # simulasi harga (untuk uji offline)
MIN_SAMPLES = 8                               # minimum sampel sebelum bobot event dikalibrasi

try:
    STATS = json.load(open(STATS_FILE))
except Exception:
    STATS = {}

def event_multiplier(label):
    """Bobot event dikalibrasi dari hasil nyata: hit-rate tinggi -> bobot naik, rendah -> turun (0.7-1.3)."""
    s = STATS.get(label)
    if not s or s["n"] < MIN_SAMPLES: return 1.0
    return round(0.7 + 0.6 * (s["hits"] / s["n"]), 3)

def save_stats():
    try: json.dump(STATS, open(STATS_FILE, "w"))
    except Exception as e: print("simpan stats gagal:", e)

def http_get(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()

# ---------------------------------------------------------------- analisis
def detect_projects(text):
    low = " " + text.lower() + " "
    found = {}
    for alias, sym in ALIAS:
        a = alias if alias.endswith(" ") else alias
        if re.search(r"(?<![a-z0-9])" + re.escape(a.strip()) + r"(?![a-z0-9])", low):
            found[sym] = found.get(sym, 0) + 1
    # tangkap $TICKER
    for t in re.findall(r"\$([A-Za-z]{2,10})\b", text):
        found[t.upper()] = found.get(t.upper(), 0) + 2
    return [s for s, _ in sorted(found.items(), key=lambda x: -x[1])][:4]

def analyze(item):
    text = f"{item['title']} {item['summary']}"
    projects = detect_projects(text)
    ev = None
    for e in EVENTS:
        if e[0].search(text):
            ev = e; break
    pos, neg = len(POS.findall(text)), len(NEG.findall(text))
    if ev:
        _, label, direction, weight, (h0, h1), strategy, follow = ev
    else:
        label, direction, weight, (h0, h1), strategy, follow = "Berita Umum", (1 if pos > neg else -1 if neg > pos else 0), 0.25, (6, 48), \
            "Pantau saja; belum ada katalis jelas.", ["Tunggu konfirmasi dari sumber kedua"]
    if ev and pos != neg:  # sentimen kata bisa membalik arah kalau kuat
        if (pos - neg) * direction < -2:
            direction = -direction
    # skor
    cred = item["credibility"]
    cap = 1.0
    if projects:
        r = PROJECTS.get(projects[0], {}).get("rank", 60)
        cap = 1.0 if r <= 5 else 0.9 if r <= 20 else 0.8 if r <= 50 else 0.7
    else:
        cap = 0.5
    urgency = 1.15 if URGENT.search(text) else 1.0
    age_min = max(0, (time.time() - item["published"]) / 60)
    fresh = math.exp(-age_min / 360)           # setengah hidup ± 4 jam
    weight = min(1.0, weight * event_multiplier(label))     # kalibrasi dari hasil historis
    score = round(min(100, 100 * weight * cred * cap * urgency * (0.55 + 0.45 * fresh)))
    conf = round(min(0.95, 0.35 + 0.4 * cred + (0.1 if ev else 0) + (0.1 if projects else 0)), 2)
    # proyek terdampak (efek riak)
    ripple = []
    for p in projects[:2]:
        for rel in PROJECTS.get(p, {}).get("related", [])[:4]:
            if rel not in projects and rel not in [r["symbol"] for r in ripple]:
                ripple.append({"symbol": rel, "reason": f"Terkait {p} (sektor/ekosistem/korelasi), dampak {'positif' if direction>0 else 'negatif' if direction<0 else 'netral'} tidak langsung"})
    # estimasi exit (heuristik)
    t0 = item["published"]
    if direction > 0:
        exit_txt = f"Jendela jual ideal: {h0}-{h1} jam setelah berita (± {time.strftime('%d %b %H:%M', time.localtime(t0 + h0*3600))} s/d {time.strftime('%d %b %H:%M', time.localtime(t0 + h1*3600))})."
    elif direction < 0:
        exit_txt = f"Keluar secepatnya, paling lambat {h1} jam ({time.strftime('%d %b %H:%M', time.localtime(t0 + h1*3600))}). Pertimbangkan re-entry setelah harga stabil."
    else:
        exit_txt = "Tidak ada sinyal exit jelas; tunggu konfirmasi."
    action = [
        f"Verifikasi: cari konfirmasi di sumber resmi (website/X proyek, pengumuman exchange) sebelum bertindak.",
        strategy,
        "Risiko: maksimum 1% modal per trade dengan stop struktural; tanpa leverage pada altcoin; total altcoin 10-30% portofolio (3-5 posisi).",
        "Moonbag: bila posisi naik 100%, jual 50% sehingga sisanya bebas risiko. Altcoin jarang layak ditahan lebih dari 2-4 bulan.",
    ]
    reasons = []
    if ev: reasons.append(f"Terdeteksi jenis kejadian '{label}' (bobot dampak {int(weight*100)}/100).")
    reasons.append(f"Kredibilitas sumber {item['source']}: {int(cred*100)}%.")
    if projects: reasons.append(f"Proyek utama {projects[0]} (peringkat ±{PROJECTS.get(projects[0],{}).get('rank','?')}) → skala dampak {int(cap*100)}%.")
    if urgency > 1: reasons.append("Ada kata kunci urgensi (breaking/confirmed/official).")
    reasons.append(f"Kesegaran berita: {int(age_min)} menit lalu.")
    item.update({
        "projects": projects, "event": label, "direction": "bullish" if direction > 0 else "bearish" if direction < 0 else "netral",
        "score": score, "confidence": conf, "impact": f"{label}: {'positif' if direction>0 else 'negatif' if direction<0 else 'netral'} untuk {', '.join(projects) or 'pasar umum'}.",
        "reasons": reasons, "action": action, "exit": exit_txt, "ripple": ripple, "predictions": follow,
        "ai": None,
    })
    return item

def ai_enrich(item):
    """Opsional: minta Claude untuk analisis lebih dalam (jalan di background)."""
    if not ANTHROPIC_KEY or item["score"] < 55: return
    try:
        body = json.dumps({"model": "claude-sonnet-5-5", "max_tokens": 600, "messages": [{"role": "user", "content":
            "Kamu analis crypto. Dari berita ini, beri JSON ringkas dengan kunci: ringkasan, dampak_jangka_pendek, risiko, "
            "skenario_bull, skenario_bear, yang_perlu_dipantau (list). Bahasa Indonesia, tanpa teks lain.\n\n"
            f"Judul: {item['title']}\nIsi: {item['summary']}\nSumber: {item['source']}\nEvent: {item['event']}"}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
            "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=40).read())
        item["ai"] = out["content"][0]["text"]
        push(item, "update")
    except Exception as e:
        print("ai_enrich gagal:", e)

ALERT_LOG = []   # timestamp alert terkirim (pembatas laju)
ONCE = False       # True saat dijalankan sebagai siklus tunggal (GitHub Actions)
BOOTSTRAP = False  # run pertama tanpa data sebelumnya: tidak kirim alert untuk backlog
AI_LEFT = 5        # batas analisis AI per siklus pada mode ONCE

def tg_send(text):
    """Kirim pesan HTML ke Telegram. Dipisah supaya mudah diuji/di-mock."""
    for chat in [c.strip() for c in TG_CHAT.split(",") if c.strip()]:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data), timeout=15)

def format_alert(item):
    import html as H
    icon = {"bullish": "🟢", "bearish": "🔴"}.get(item["direction"], "🟡")
    lead = max(0, int((item["first_seen"] - item["published"]) / 60))
    return (f"{icon} <b>[{item['score']}] {item['direction'].upper()} · {H.escape(item['event'])}</b>\n"
            f"<b>{H.escape(' '.join('$' + p for p in item['projects']) or 'Pasar umum')}</b>\n\n"
            f"{H.escape(item['title'])}\n"
            f"Sumber: <a href=\"{H.escape(item['url'] or '#')}\">{H.escape(item['source'])}</a> · terdeteksi {lead} mnt setelah publikasi\n\n"
            f"<b>Aksi:</b> {H.escape(item['action'][1])}\n"
            f"<b>Exit:</b> {H.escape(item['exit'])}\n"
            + (f"<b>Ikut terdampak:</b> {H.escape(', '.join(r['symbol'] for r in item['ripple']))}\n" if item["ripple"] else "")
            + "\n<i>Bukan nasihat keuangan. Verifikasi sebelum bertindak.</i>")

def maybe_alert(item):
    if not (TG_TOKEN and TG_CHAT) or item["score"] < ALERT_MIN or item.get("demo"): return
    if (time.time() - item["published"]) > 6 * 3600: return          # berita lama tidak perlu alert
    now = time.time()
    ALERT_LOG[:] = [t for t in ALERT_LOG if now - t < 3600]
    if len(ALERT_LOG) >= ALERT_MAX_PER_HOUR: return                   # cegah spam
    ALERT_LOG.append(now)
    try: tg_send(format_alert(item))
    except Exception as e: print("telegram gagal:", e)

def push(item, kind="news"):
    msg = f"event: {kind}\ndata: {json.dumps(item)}\n\n".encode()
    for q in list(SUBS):
        try: q.put_nowait(msg)
        except Exception: pass

def ingest(source, title, summary, url, published, cred):
    title, summary = clean(title), clean(summary)[:500]
    if not title: return
    _id = hashlib.sha1((url or title).encode()).hexdigest()[:12]
    if ONCE and published < time.time() - 72 * 3600: return   # abaikan berita > 72 jam pada mode siklus
    with LOCK:
        if _id in SEEN: return
        SEEN.add(_id)
    item = {"id": _id, "source": source, "title": title, "summary": summary, "url": url,
            "published": published, "first_seen": time.time(), "credibility": cred, "demo": False}
    item = analyze(item)
    if item["score"] < 12 and not item["projects"]: return   # buang noise
    # catat harga saat berita pertama terlihat, untuk mengukur hasil nyata nanti
    sym = next((p for p in item["projects"] if p in PRICES), None)
    item["track"] = {"symbol": sym, "price0": PRICES[sym][0], "btc0": PRICES["BTC"][0] if "BTC" in PRICES else None,
                     "t0": time.time(), "outcomes": {}} if sym else None
    with LOCK: NEWS[_id] = item
    push(item)
    if ONCE:                                   # mode siklus: kerjakan berurutan agar selesai sebelum proses berhenti
        global AI_LEFT
        if not BOOTSTRAP: maybe_alert(item)
        if ANTHROPIC_KEY and item["score"] >= 55 and AI_LEFT > 0:
            AI_LEFT -= 1; ai_enrich(item)
    else:
        threading.Thread(target=maybe_alert, args=(item,), daemon=True).start()
        threading.Thread(target=ai_enrich, args=(item,), daemon=True).start()

# ---------------------------------------------------------------- pengumpul
def parse_time(s):
    try: return parsedate_to_datetime(s).timestamp()
    except Exception:
        try: return time.mktime(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception: return time.time()

def pull_rss(name, url, cred):
    root = ET.fromstring(http_get(url))
    for it in root.iter():
        if it.tag.endswith("item") or it.tag.endswith("entry"):
            g = lambda t: next((c for c in it if c.tag.endswith(t)), None)
            title = g("title"); link = g("link"); desc = g("description") or g("summary") or g("content")
            date = g("pubDate") or g("published") or g("updated")
            href = (link.get("href") if link is not None and link.get("href") else (link.text if link is not None else ""))
            ingest(name, title.text if title is not None else "", desc.text if desc is not None else "", href,
                   parse_time(date.text) if date is not None and date.text else time.time(), cred)

def pull_reddit(label, sub):
    d = json.loads(http_get(f"https://www.reddit.com/r/{sub}/new.json?limit=25"))
    for c in d["data"]["children"]:
        p = c["data"]
        if p.get("score", 0) < 25 and p.get("num_comments", 0) < 15: continue
        ingest(f"Reddit {label}", p["title"], p.get("selftext", ""), "https://reddit.com" + p["permalink"], p["created_utc"], 0.50)

def pull_cryptopanic():
    d = json.loads(http_get(f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_KEY}&public=true&filter=hot"))
    for p in d["results"]:
        ingest("CryptoPanic/" + p["source"]["title"], p["title"], "", p["url"], parse_time(p["published_at"]), 0.70)

def pull_x():
    q = " OR ".join(f"from:{a}" for a in X_ACCOUNTS) + " -is:retweet"
    url = "https://api.twitter.com/2/tweets/search/recent?max_results=50&tweet.fields=created_at&query=" + urllib.parse.quote(q)
    d = json.loads(http_get(url, {"Authorization": f"Bearer {X_BEARER}"}))
    for t in d.get("data", []):
        ingest("X (Twitter)", t["text"][:140], t["text"], f"https://x.com/i/web/status/{t['id']}", parse_time(t["created_at"]), 0.65)

def pull_gecko_trending():
    d = json.loads(http_get("https://api.coingecko.com/api/v3/search/trending"))
    for c in d.get("coins", [])[:7]:
        i = c["item"]
        ingest("CoinGecko Trending", f"{i['name']} (${i['symbol']}) masuk trending pencarian #{i['score']+1}",
               "Lonjakan minat pencarian sering mendahului pergerakan harga.", f"https://www.coingecko.com/en/coins/{i['id']}",
               time.time(), 0.60)

def pull_prices():
    if SIM_PRICES:
        import random
        for s in CG_IDS:
            p = PRICES.get(s, (random.uniform(0.5, 500), 0))[0]
            PRICES[s] = (p * (1 + random.gauss(0, 0.004)), time.time())
        return
    ids = ",".join(CG_IDS.values())
    d = json.loads(http_get(f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"))
    for s, cid in CG_IDS.items():
        if cid in d: PRICES[s] = (d[cid]["usd"], time.time(), d[cid].get("usd_24h_change"))

def evaluate_outcomes():
    """Bandingkan harga sekarang dengan harga saat berita terlihat; catat hasil di 1j/6j/24j dan perbarui statistik."""
    now = time.time(); changed = []
    with LOCK: items = list(NEWS.values())
    for it in items:
        tr = it.get("track")
        if not tr or it["direction"] == "netral" or it.get("demo"): continue
        cur = PRICES.get(tr["symbol"])
        if not cur: continue
        for name, secs in HORIZONS.items():
            if name in tr["outcomes"] or now - tr["t0"] < secs: continue
            ret = (cur[0] / tr["price0"] - 1) * 100
            sign = 1 if it["direction"] == "bullish" else -1
            # alpha = return di atas/bawah BTC, supaya tren pasar umum tidak dianggap keberhasilan sinyal
            btc_now = PRICES.get("BTC")
            btc_ret = (btc_now[0] / tr["btc0"] - 1) * 100 if btc_now and tr.get("btc0") and tr["symbol"] != "BTC" else 0.0
            alpha = ret - btc_ret
            raw_hit, hit = ret * sign > 0, alpha * sign > 0   # hit = berdasarkan alpha (lebih jujur)
            tr["outcomes"][name] = {"ret_pct": round(ret, 2), "btc_pct": round(btc_ret, 2), "alpha_pct": round(alpha, 2),
                                    "hit": hit, "raw_hit": raw_hit}
            if name == "6j":                      # horizon 6 jam dipakai untuk kalibrasi bobot event
                s = STATS.setdefault(it["event"], {"hits": 0, "n": 0, "sum_ret": 0.0})
                s["n"] += 1; s["hits"] += int(hit); s["sum_ret"] += ret * sign
                s["raw_hits"] = s.get("raw_hits", 0) + int(raw_hit); s["sum_alpha"] = s.get("sum_alpha", 0.0) + alpha * sign
                save_stats()
            changed.append(it)
    for it in changed: push(it, "update")

def scan_loop():
    """Mode server: pindai semua koin bergiliran (hemat rate limit), lalu ulangi tiap ~30 menit."""
    while True:
        try: mk = scan.fetch_markets()
        except Exception as e: mk = {}; print("scan markets gagal:", e)
        try: macro = scan.fetch_macro()
        except Exception: macro = None
        for sym in scan.SCAN_SYMBOLS:
            try: SCANS[sym] = scan.scan_symbol(sym, {sym: mk.get(sym)}, list(NEWS.values()), macro)
            except Exception as e: print(f"scan {sym} gagal: {e}")
            time.sleep(40)
        time.sleep(1800)

def runner(fn, *a):
    def loop():
        while True:
            try: fn(*a)
            except Exception as e: print(f"[{fn.__name__}{a[:1]}] gagal: {e}")
            time.sleep(300 if fn is pull_gecko_trending else 30 if fn in (pull_prices, evaluate_outcomes) else POLL)
    threading.Thread(target=loop, daemon=True).start()

def start_collectors():
    for n, (u, c) in RSS.items(): runner(pull_rss, n, u, c)
    for l, s in REDDIT.items(): runner(pull_reddit, l, s)
    if CRYPTOPANIC_KEY: runner(pull_cryptopanic)
    if X_BEARER: runner(pull_x)
    runner(pull_gecko_trending)
    runner(pull_prices)
    runner(evaluate_outcomes)
    if scan: threading.Thread(target=scan_loop, daemon=True).start()
    if hunter: threading.Thread(target=hunt_loop, daemon=True).start()

# ---------------------------------------------------------------- demo (kalau offline)
def seed_demo():
    now = time.time()
    demo = [
        ("Binance Announcements", "Binance Will List Sui (SUI) with Seed Tag Applied", "Official: trading opens tomorrow, deposits open now.", 0.98, 8),
        ("The Block", "SEC approves spot Solana ETF, trading to go live next week", "Breaking: approval confirmed, issuers prepare launch.", 0.90, 25),
        ("CoinDesk", "Ethereum Pectra-style upgrade scheduled for mainnet next month", "Core devs confirmed mainnet date.", 0.90, 55),
        ("Cointelegraph", "Cross-chain bridge exploit drains $40M, DeFi protocol Aave suspends markets", "Hackers drained funds; exchanges halt deposits.", 0.85, 90),
        ("Reddit r/CryptoCurrency", "Large token unlock for Arbitrum (ARB) this week, 90M tokens cliff", "Vesting cliff hits Thursday.", 0.5, 130),
        ("Coinbase Blog", "Coinbase to list PEPE and expand Base partnership", "Coinbase adds roadmap entry.", 0.95, 200),
    ]
    for s, t, d, c, mins in demo:
        ingest(s, t, d, "https://example.com/" + hashlib.md5(t.encode()).hexdigest()[:6], now - mins * 60, c)
        NEWS[hashlib.sha1(("https://example.com/" + hashlib.md5(t.encode()).hexdigest()[:6]).encode()).hexdigest()[:12]]["demo"] = True

# ---------------------------------------------------------------- top 5 & prediksi
def top5():
    now = time.time(); agg = {}
    with LOCK: items = list(NEWS.values())
    for it in items:
        age_h = (now - it["published"]) / 3600
        if age_h > 48: continue
        decay = math.exp(-age_h / 12)
        sign = 1 if it["direction"] == "bullish" else -1 if it["direction"] == "bearish" else 0
        for i, p in enumerate(it["projects"]):
            a = agg.setdefault(p, {"symbol": p, "impact": 0.0, "net": 0.0, "n": 0, "news": []})
            w = it["score"] * decay * (1 if i == 0 else 0.5)
            a["impact"] += w; a["net"] += sign * w; a["n"] += 1; a["news"].append(it)
        for r in it["ripple"][:3]:
            a = agg.setdefault(r["symbol"], {"symbol": r["symbol"], "impact": 0.0, "net": 0.0, "n": 0, "news": []})
            w = it["score"] * decay * 0.3
            a["impact"] += w; a["net"] += sign * w * 0.8; a["n"] += 1; a["news"].append(it)
    ranked = sorted(agg.values(), key=lambda x: -x["impact"])[:5]
    out = []
    for i, a in enumerate(ranked, 1):
        best = max(a["news"], key=lambda n: n["score"])
        d = "bullish" if a["net"] > 0.25 * a["impact"] else "bearish" if a["net"] < -0.25 * a["impact"] else "campuran"
        out.append({"rank": i, "symbol": a["symbol"], "impact": round(a["impact"], 1), "direction": d, "news_count": a["n"],
                    "why": f"Peringkat #{i} karena akumulasi skor dampak {round(a['impact'],1)} dari {a['n']} berita 48 jam terakhir "
                           f"(bobot menurun seiring waktu). Pendorong terbesar: \"{best['title'][:90]}\" [{best['event']}, skor {best['score']}, {best['source']}]. "
                           f"Arah bersih: {d}." + ("" if a['symbol'] in best['projects'] else " Dampak bersifat tidak langsung (efek riak dari proyek terkait)."),
                    "best_action": best["action"][1], "exit": best["exit"]})
    return out

def predictions():
    with LOCK: items = sorted(NEWS.values(), key=lambda x: -x["score"])[:8]
    out = []
    for it in items:
        if it["score"] < 40: continue
        out.append({"based_on": it["title"], "source": it["source"], "url": it["url"], "event": it["event"],
                    "potential": it["predictions"], "affected": [r["symbol"] for r in it["ripple"]], "confidence": it["confidence"]})
    return out[:6]

def stats_api():
    return [{"event": e, "n": s["n"], "hit_rate": round(s["hits"] / s["n"], 3) if s["n"] else None,
             "raw_hit_rate": round(s.get("raw_hits", s["hits"]) / s["n"], 3) if s["n"] else None,
             "avg_ret_pct": round(s["sum_ret"] / s["n"], 2) if s["n"] else None,
             "avg_alpha_pct": round(s.get("sum_alpha", s["sum_ret"]) / s["n"], 2) if s["n"] else None,
             "weight_multiplier": event_multiplier(e), "calibrated": s["n"] >= MIN_SAMPLES} for e, s in STATS.items()]

HUNT_SCAN = int(os.getenv("HUNT_SCAN", "2"))     # kandidat Hunter yang dioper ke Scan SMC per siklus

def hunt_handoff(res, load=None, dump=None):
    """Serah-terima: kandidat Hunter teratas (belum viral, punya pool DEX) dipindai SMC/FVG/OTE dengan candle dari pool DEX-nya."""
    if not (scan and hunter and res and res.get("candidates")): return
    idx = {e["symbol"]: e for e in (load("scan/index.json", []) if load else [])}
    macro = None; done = 0
    for c in hunter.handoff(res, 8):
        if done >= HUNT_SCAN: break
        sym = c["symbol"]
        if sym in scan.COINS and sym not in scan.DYN: continue          # koin tetap Scan sudah punya jalurnya sendiri
        last = idx.get(sym, {}).get("generated_at") or (SCANS.get(sym) or {}).get("generated_at", 0)
        if time.time() - last < 6 * 3600: continue
        tag = (c.get("sector") or {}).get("tag") or "sektor tidak diketahui"
        scan.COINS[sym] = {"cg": c["id"], "name": c["name"], "narr": f"{tag} (ditemukan Hunter, skor {c['score']:.0f}/100, narasi {c['narrative_score']}/100)"}
        scan.DYN[sym] = c["scan_ref"]; done += 1
        try:
            macro = macro or scan.fetch_macro()
            r = scan.scan_symbol(sym, None, list(NEWS.values()), macro)
            if dump:
                os.makedirs(os.path.join(os.getenv("DATA_DIR", "data"), "scan"), exist_ok=True)
                dump(f"scan/{sym}.json", r); idx[sym] = scan.index_entry(r)
            else: SCANS[sym] = r
        except Exception as e: print(f"handoff scan {sym} gagal: {e}")
    if dump and idx: dump("scan/index.json", sorted(idx.values(), key=lambda e: e["symbol"]))

def hunt_loop():
    """Mode server: jalankan Hunter berulang tiap HUNT_EVERY_MIN menit (default 55)."""
    while True:
        try:
            r = hunter.hunt(news=list(NEWS.values()), prev=HUNT or None)
            if r["candidates"]: HUNT.clear(); HUNT.update(r); hunt_handoff(r)
        except Exception as e: print("hunter gagal:", e)
        time.sleep(hunter.HUNT_EVERY)

def scan_rotation(d, load, dump):
    """Mode Actions: pindai SCAN_PER_RUN koin dengan hasil paling lama, tulis data/scan/*.json."""
    os.makedirs(os.path.join(d, "scan"), exist_ok=True)
    idx = {e["symbol"]: e for e in load("scan/index.json", [])}
    order = sorted(scan.SCAN_SYMBOLS, key=lambda x: idx.get(x, {}).get("generated_at", 0))[:SCAN_PER_RUN]
    mk = scan.fetch_markets(); macro = None
    try: macro = scan.fetch_macro()
    except Exception: pass
    for sym in order:
        try:
            r = scan.scan_symbol(sym, {sym: mk.get(sym)}, list(NEWS.values()), macro)
            dump(f"scan/{sym}.json", r); idx[sym] = scan.index_entry(r)
        except Exception as e: print(f"scan {sym} gagal: {e}")
    dump("scan/index.json", sorted(idx.values(), key=lambda e: e["symbol"]))

def prices_api():
    return {s: {"usd": v[0], "chg24h": v[2] if len(v) > 2 else None} for s, v in PRICES.items()}

# ---------------------------------------------------------------- mode siklus tunggal (GitHub Actions)
def once():
    """Satu siklus: muat data sebelumnya -> kumpulkan -> nilai -> ukur hasil -> tulis JSON statis -> selesai."""
    global ONCE, BOOTSTRAP, STATS_FILE
    from concurrent.futures import ThreadPoolExecutor
    ONCE = True
    d = os.getenv("DATA_DIR", "data"); os.makedirs(d, exist_ok=True)
    STATS_FILE = os.path.join(d, "stats_raw.json")
    def load(name, default):
        try: return json.load(open(os.path.join(d, name), encoding="utf-8"))
        except Exception: return default
    def dump(name, obj):
        tmp = os.path.join(d, name + ".tmp")
        json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, os.path.join(d, name))
    STATS.clear(); STATS.update(load("stats_raw.json", {}))
    prev = load("news.json", None)
    BOOTSTRAP = prev is None
    cutoff = time.time() - 72 * 3600
    for it in (prev or {}).get("items", []):
        if it.get("published", 0) >= cutoff: NEWS[it["id"]] = it
    SEEN.update(NEWS.keys())
    ALERT_LOG[:] = load("state.json", {}).get("alerts", [])
    try: pull_prices()
    except Exception as e: print("harga gagal:", e)
    jobs = [(pull_rss, (n, u, c)) for n, (u, c) in RSS.items()] + [(pull_reddit, (l, sub)) for l, sub in REDDIT.items()] + [(pull_gecko_trending, ())]
    if CRYPTOPANIC_KEY: jobs.append((pull_cryptopanic, ()))
    if X_BEARER: jobs.append((pull_x, ()))
    def run(job):
        fn, a = job
        try: fn(*a)
        except Exception as e: print(f"[{fn.__name__}{a[:1]}] gagal: {e}")
    with ThreadPoolExecutor(8) as ex: list(ex.map(run, jobs))
    evaluate_outcomes()
    items = sorted(NEWS.values(), key=lambda x: -x["first_seen"])[:300]
    now = time.time()
    dump("news.json", {"items": items, "uptime": 0, "generated_at": int(now), "mode": "static",
                       "sources": len(RSS) + len(REDDIT) + bool(CRYPTOPANIC_KEY) + bool(X_BEARER) + 1})
    dump("top5.json", top5()); dump("predictions.json", predictions()); dump("stats.json", stats_api()); dump("prices.json", prices_api())
    dump("state.json", {"alerts": [t for t in ALERT_LOG if now - t < 3600], "last_run": int(now)})
    save_stats()
    if scan:
        try: scan_rotation(d, load, dump)
        except Exception as e: print("scan rotasi gagal:", e)
    if hunter:
        try:
            res = hunter.run(load, dump, news=list(NEWS.values()))
            hunt_handoff(res, load, dump)
        except Exception as e: print("hunter gagal:", e)
    print(f"siklus selesai: {len(items)} berita, {len(PRICES)} harga, bootstrap={BOOTSTRAP}, alert_terkirim={len(ALERT_LOG)}")

# ---------------------------------------------------------------- HTTP
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/news":
            with LOCK: items = sorted(NEWS.values(), key=lambda x: -x["first_seen"])[:200]
            self._json({"items": items, "uptime": int(time.time() - STARTED), "sources": len(RSS) + len(REDDIT) + bool(CRYPTOPANIC_KEY) + bool(X_BEARER) + 1})
        elif path == "/health": self._json({"ok": True, "items": len(NEWS), "uptime": int(time.time() - STARTED)})
        elif path == "/api/prices": self._json(prices_api())
        elif path == "/api/stats": self._json(stats_api())
        elif path == "/api/hunt": self._json(HUNT or hunter.empty())
        elif path == "/api/scan/index": self._json(sorted([scan.index_entry(r) for r in SCANS.values()], key=lambda e: e["symbol"]) if scan else [])
        elif path == "/api/scan":
            sym = (urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("symbol", [""])[0] or "").upper()
            if not scan or sym not in scan.COINS: return self._json({"error": "simbol tidak didukung", "supported": list(scan.COINS) if scan else []})
            if sym not in SCANS:
                try: SCANS[sym] = scan.scan_symbol(sym, None, list(NEWS.values()))
                except Exception as e: return self._json({"error": f"scan gagal: {e}"})
            self._json(SCANS[sym])
        elif path == "/api/top5": self._json(top5())
        elif path == "/api/predictions": self._json(predictions())
        elif path == "/events":
            q = queue.Queue(maxsize=200); SUBS.append(q)
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
            try:
                while True:
                    try: self.wfile.write(q.get(timeout=15))
                    except queue.Empty: self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except Exception: pass
            finally:
                if q in SUBS: SUBS.remove(q)
        else:
            f = os.path.join(os.path.dirname(__file__), "static", "index.html")
            b = open(f, "rb").read()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)

if __name__ == "__main__":
    if "--once" in sys.argv:
        once(); sys.exit(0)
    start_collectors()
    time.sleep(8)
    if not NEWS:
        print("Tidak ada berita live (offline/jaringan diblokir) -> memuat DATA DEMO.")
        seed_demo()
    print(f"Dashboard: http://localhost:{PORT}  | poll tiap {POLL}s | AI={'on' if ANTHROPIC_KEY else 'off'} | X={'on' if X_BEARER else 'off'} | Telegram={'on (>=' + str(ALERT_MIN) + ')' if TG_TOKEN and TG_CHAT else 'off'}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()

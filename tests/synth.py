"""Candle sintetis untuk uji & data contoh (BUKAN data pasar)."""
import random

def make_daily(n=400, seed=7):
    rnd = random.Random(seed); price = 100.0; out = []; t = 1_700_000_000_000
    # fase: konsolidasi -> impuls naik dengan gap -> retrace dalam ke ~65%
    plan = [("range", 220), ("up", 90), ("down", 60), ("chop", n - 370)]
    for kind, days in plan:
        for _ in range(days):
            drift = {"range": 0.0, "up": 0.011, "down": -0.011, "chop": 0.0005}[kind]
            vol = {"range": 0.012, "up": 0.014, "down": 0.012, "chop": 0.01}[kind]
            o = price * (1 + (0.012 if kind == "up" and rnd.random() < 0.08 else 0))  # gap naik acak saat impuls
            c = o * (1 + drift + rnd.gauss(0, vol))
            h = max(o, c) * (1 + abs(rnd.gauss(0, vol / 2))); l = min(o, c) * (1 - abs(rnd.gauss(0, vol / 2)))
            out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": 1000 * (2 if kind == "up" else 1) * (1 + rnd.random())}); price = c; t += 86_400_000
    return out

def to_weekly(d):
    w = []
    for i in range(0, len(d) - 6, 7):
        g = d[i:i + 7]
        w.append({"t": g[0]["t"], "o": g[0]["o"], "h": max(x["h"] for x in g), "l": min(x["l"] for x in g), "c": g[-1]["c"], "v": sum(x["v"] for x in g)})
    return w


def make_scenario(final_price_frac, seed=11):
    """Skenario terkontrol: range 100 (220 hari) -> impuls ke 160 dengan gap (70 hari) -> retrace -> tahan.
    final_price_frac = posisi harga akhir sebagai fraksi retracement leg (0.7 = di dalam OTE, 0.2 = baru turun sedikit)."""
    rnd = random.Random(seed); out = []; t = 1_700_000_000_000
    pts = [(0, 100), (220, 100), (290, 160), (315, 160 - 60 * final_price_frac), (400, 160 - 60 * final_price_frac)]
    prev = 100.0
    for d in range(400):
        for (d0, p0), (d1, p1) in zip(pts, pts[1:]):
            if d0 <= d <= d1: base = p0 + (p1 - p0) * ((d - d0) / max(1, d1 - d0)); break
        gap = 0.012 if 220 < d < 290 and d % 6 == 0 else 0.0           # gap naik periodik saat impuls (FVG)
        o = prev * (1 + gap); c = base * (1 + rnd.gauss(0, 0.004))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.003))); l = min(o, c) * (1 - abs(rnd.gauss(0, 0.003)))
        out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": 1000 * (2 if 220 < d < 290 else 1)}); prev = c; t += 86_400_000
    return out

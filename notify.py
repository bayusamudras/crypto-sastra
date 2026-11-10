#!/usr/bin/env python3
"""
Crypto Sastra - Notifikasi sinyal eksekusi (cepat, tanpa dependensi)

Dijalankan TIAP siklus pengumpul (~3 menit), terpisah dari Hunter yang lebih lambat. Siklus hidup sinyal:
  ENTRY   koin baru berstatus EKSEKUSI (membawa tiket order + tautan beli)
  TP1/TP2 target harga tercapai (stop digeser ke impas setelah TP1; trailing aktif setelah TP2)
  STOP    harga menyentuh stop, TRAIL trailing stop kena, UNLOCK batas keluar sebelum unlock, REVIEW/TIME batas waktu
  EXIT    sinyal melemah (VETO, smart money berbalik, keyakinan turun, narasi pudar, atau hilang dari EKSEKUSI >= 2 hasil Hunter berturut-turut)
Kanal: Telegram, ntfy.sh (push gratis ke HP), webhook (Discord/Slack). Notifikasi web ada di halaman (membaca alerts.json).
Tidak ada eksekusi order otomatis: tautan beli hanya membuka bursa/dompet Anda, dan Anda yang menekan konfirmasi.
"""
import html, json, os, time, urllib.parse, urllib.request
import playbook

DAY = 86400
MAX_EVENTS, MAX_PER_RUN = 60, 10
EMOJI = {"ENTRY": "🟢", "TP1": "💰", "TP2": "💰💰", "STOP": "🔴", "TRAIL": "🟠", "UNLOCK": "⏰", "REVIEW": "🔎", "TIME": "⌛", "EXIT": "🚪"}
PRIO = {"ENTRY": "high", "STOP": "urgent", "EXIT": "urgent", "UNLOCK": "high", "TRAIL": "high", "TP1": "default", "TP2": "default", "REVIEW": "low", "TIME": "default"}

def _px(v): return "-" if v is None else (f"${v:.3f}" if v >= 1 else f"${v:.4g}")

def format_event(e):
    lines = [f"{EMOJI.get(e['type'], '•')} <b>{e['type']} ${html.escape(e['symbol'])}</b>", html.escape(e["text"])]
    if e.get("ticket"): lines.append(html.escape(e["ticket"]))
    if e.get("links"): lines.append("Beli (Anda konfirmasi sendiri): " + " · ".join(f'<a href="{html.escape(l["url"])}">{html.escape(l["label"])}</a>' for l in e["links"][:4]))
    lines.append("<i>Bahan riset, bukan nasihat keuangan.</i>")
    return "\n".join(lines)

def _post(url, data, headers=None, timeout=15):
    req = urllib.request.Request(url, data=data, method="POST", headers={"User-Agent": "CryptoSastra/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.status

def send_all(e, env=None):
    """Kirim ke semua kanal yang dikonfigurasi. Mengembalikan daftar kanal sukses. Kegagalan satu kanal tidak menghentikan yang lain."""
    env = env if env is not None else os.environ; ok = []; text = format_event(e); plain = f"{e['type']} ${e['symbol']}: {e['text']}" + (f"\n{e['ticket']}" if e.get("ticket") else "")
    tok, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", "")
    if tok and chat:
        for c in [x.strip() for x in chat.split(",") if x.strip()]:
            try:
                _post(f"https://api.telegram.org/bot{tok}/sendMessage", urllib.parse.urlencode({"chat_id": c, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode()); ok.append("telegram")
            except Exception as ex: print("notif telegram gagal:", str(ex)[:80])
    topic = env.get("NTFY_TOPIC", "").strip()
    if topic:
        try:
            h = {"Title": f"{e['type']} ${e['symbol']}", "Priority": PRIO.get(e["type"], "default"), "Tags": "chart_with_upwards_trend" if e["type"] in ("ENTRY", "TP1", "TP2") else "warning"}
            if e.get("links"): h["Click"] = e["links"][0]["url"]
            _post("https://ntfy.sh/" + urllib.parse.quote(topic), plain.encode("utf-8"), h); ok.append("ntfy")
        except Exception as ex: print("notif ntfy gagal:", str(ex)[:80])
    hook = env.get("ALERT_WEBHOOK_URL", "").strip()
    if hook:
        try: _post(hook, json.dumps({"content": plain, "text": plain}).encode(), {"content-type": "application/json"}); ok.append("webhook")
        except Exception as ex: print("notif webhook gagal:", str(ex)[:80])
    return ok

def _ticket(it, p, size_pct):
    pl = it["plan"]
    return f"Tiket: entry {_px(p)} · stop {_px(pl['stop'])} · TP1 {_px(pl['tp1'])} · TP2 {_px(pl['tp2'])} · ukuran ≈ {size_pct}% modal (risiko {playbook.RISK_PCT:.0f}%)"

def fast_tick(load, dump, price_fn, send=send_all, now=None, hunt=None):
    now = now or time.time(); hunt = hunt if hunt is not None else load("hunt.json", None)
    st = load("alerts.json", None) or {}; st.setdefault("events", []); st.setdefault("active", {}); st.setdefault("seq", 0); st.setdefault("cool", {})
    if not hunt or not hunt.get("playbook"): return st
    pb = hunt["playbook"]; ex = {x["symbol"]: x for x in pb.get("execute", [])}; wt = {x["symbol"]: x for x in pb.get("waiting", [])}
    hgen = hunt.get("generated_at", 0); act = st["active"]
    ids = sorted({a["id"] for a in act.values()} | {x["id"] for x in ex.values()})
    try: prices = price_fn(ids) if (price_fn and ids) else {}
    except Exception as e: print("notif harga gagal:", e); prices = {}
    new = []
    def ev(typ, sym, text, it=None, ticket=None, a=None):
        st["seq"] += 1; e = {"id": st["seq"], "t": int(now), "type": typ, "symbol": sym, "text": text}
        if ticket: e["ticket"] = ticket
        src = it or (wt.get(sym) or {})
        if (it or {}).get("buy") and typ == "ENTRY": e["links"] = it["buy"].get("links", [])
        elif a and a.get("links") and typ in ("TP1", "TP2", "STOP", "TRAIL", "EXIT", "UNLOCK", "TIME", "REVIEW"): e["links"] = a["links"]
        new.append(e)
    # --- sinyal baru
    for sym, it in ex.items():
        if sym in act: act[sym]["miss"] = 0; continue
        if now - st["cool"].get(sym, 0) < 7 * DAY: continue          # jeda 7 hari setelah sinyal ditutup: hindari masuk-keluar berulang
        p = prices.get(it["id"]) or it.get("price")
        if not p: continue
        pl = it["plan"]; k = p / (pl["entry"] or p)
        a = {"id": it["id"], "entry": p, "stop": pl["stop"] * k, "tp1": pl["tp1"] * k, "tp2": pl["tp2"] * k, "peak": p, "t0": int(now), "hunt_seen": hgen, "miss": 0,
             "tp1_hit": False, "tp2_hit": False, "review": False, "deadline_days": (pl.get("deadline") or {}).get("days"), "links": (it.get("buy") or {}).get("links", [])}
        act[sym] = a
        it2 = dict(it); it2["plan"] = dict(pl, stop=a["stop"], tp1=a["tp1"], tp2=a["tp2"])
        why = "; ".join((it.get("why") or [])[:2])
        ev("ENTRY", sym, f"Lolos semua gerbang (skor {round(it.get('score') or 0)}, keyakinan {it.get('conviction')}). {why}", it, _ticket(it2, p, pl.get("size_pct")))
    # --- pelacakan sinyal aktif
    for sym in list(act):
        a = act[sym]; p = prices.get(a["id"]); closed = None
        if p:
            a["peak"] = max(a["peak"], p)
            if p <= a["stop"]: closed = ("STOP", f"Harga {_px(p)} menyentuh stop {_px(a['stop'])}. Keluar sesuai rencana.")
            elif a["tp2_hit"] and p <= a["peak"] * (1 - playbook.TRAIL): closed = ("TRAIL", f"Harga {_px(p)} turun {playbook.TRAIL*100:.0f}% dari puncak {_px(a['peak'])}. Keluar sisa posisi.")
            else:
                if not a["tp1_hit"] and p >= a["tp1"]: a["tp1_hit"] = True; a["stop"] = max(a["stop"], a["entry"]); ev("TP1", sym, f"Harga {_px(p)} mencapai TP1: jual 1/3 dan geser stop ke impas {_px(a['entry'])}.", a=a)
                if not a["tp2_hit"] and p >= a["tp2"]: a["tp2_hit"] = True; ev("TP2", sym, f"Harga {_px(p)} mencapai TP2: jual 1/3 lagi; sisanya trailing {playbook.TRAIL*100:.0f}% dari puncak.", a=a)
        age = (now - a["t0"]) / DAY
        if not closed:
            dd = a.get("deadline_days")
            if dd is not None and age >= dd: closed = ("UNLOCK", "Batas keluar sebelum unlock tiba: tutup posisi.")
            elif age >= playbook.TIME_STOP: closed = ("TIME", f"Batas waktu {playbook.TIME_STOP} hari tercapai: keluar penuh bila tesis belum bergerak.")
            elif age >= playbook.TIME_REVIEW and not a["review"] and p and p < a["entry"] * 1.10: a["review"] = True; ev("REVIEW", sym, f"Hari ke-{int(age)} dan belum +10% dari entry: tinjau tesis.", a=a)
        if not closed and hgen > a["hunt_seen"]:                  # evaluasi sinyal hanya saat ada hasil Hunter baru
            a["hunt_seen"] = hgen
            if sym in ex: a["miss"] = 0
            else:
                w = wt.get(sym); hard = []
                if w:
                    for g in w["gates"]:
                        if g["ok"] is False and g["gate"] in ("Dewan agen", "Keamanan kontrak", "Konfirmasi smart money", "Konfirmasi narasi on-chain", "Kualitas dasar"): hard.append(f"{g['gate']}: {g['text']}")
                a["miss"] = a.get("miss", 0) + 1
                if hard: closed = ("EXIT", "Sinyal melemah: " + "; ".join(hard[:3]))
                elif a["miss"] >= 2: closed = ("EXIT", "Tidak lagi memenuhi semua gerbang dalam 2 hasil Hunter berturut-turut.")
        if closed:
            ev(closed[0], sym, closed[1], a=a); del act[sym]; st["cool"][sym] = int(now)
    # --- kirim dan catat
    for e in new[:MAX_PER_RUN]:
        try: e["sent"] = send(e) if send else []
        except Exception as ex: e["sent"] = []; print("notif gagal:", ex)
    st["events"] = (st["events"] + new)[-MAX_EVENTS:]; st["updated"] = int(now)
    dump("alerts.json", st); return st

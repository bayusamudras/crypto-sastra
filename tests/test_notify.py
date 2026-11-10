import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import notify, playbook, test_playbook as TP
NOW = 1_800_000_000; DAY = 86400
def hunt(execute=(), waiting=(), gen=NOW):
    return {"generated_at": gen, "playbook": {"execute": list(execute), "waiting": list(waiting)}}
def item(price=2.0, **k):
    c = TP.cand(); c["dex"] = {"liq": 900e3, "chain": "ethereum", "address": "0xabc", "pool": "0xpool"}; c["price"] = price
    it = playbook.build([c], None, NOW)["execute"][0]; it.update(k); return it
class Env:
    def __init__(s): s.files = {}; s.sent = []
    def load(s, n, d): return copy.deepcopy(s.files.get(n, d))
    def dump(s, n, o): s.files[n] = copy.deepcopy(o)
    def send(s, e): s.sent.append(e); return ["test"]
def tick(env, h, prices, now, **kw):
    return notify.fast_tick(env.load, env.dump, lambda ids: prices, env.send, now, hunt=h)
def types(env): return [e["type"] for e in env.sent]

def test_entry_once_with_ticket_and_buy_links():
    env = Env(); h = hunt([item()]); tick(env, h, {"x": 2.0}, NOW); tick(env, h, {"x": 2.0}, NOW + 180)
    assert types(env) == ["ENTRY"]; e = env.sent[0]
    assert "stop" in e["ticket"] and any("uniswap" in l["url"] and "0xabc" in l["url"] for l in e["links"]) and any("dexscreener.com/ethereum/0xpool" in l["url"] for l in e["links"])
def test_price_lifecycle_tp1_tp2_trail():
    env = Env(); h = hunt([item()]); tick(env, h, {"x": 2.0}, NOW)
    tick(env, h, {"x": 2.9}, NOW + 600); tick(env, h, {"x": 4.1}, NOW + 1200); tick(env, h, {"x": 4.0}, NOW + 1800); tick(env, h, {"x": 3.0}, NOW + 2400)
    assert types(env) == ["ENTRY", "TP1", "TP2", "TRAIL"]
def test_stop_closes_and_no_repeat():
    env = Env(); h = hunt([item()]); tick(env, h, {"x": 2.0}, NOW); tick(env, h, {"x": 1.5}, NOW + 300); tick(env, h, {"x": 1.4}, NOW + 600)
    assert types(env) == ["ENTRY", "STOP"]
def test_breakeven_stop_after_tp1():
    env = Env(); h = hunt([item()]); tick(env, h, {"x": 2.0}, NOW); tick(env, h, {"x": 2.9}, NOW + 60); tick(env, h, {"x": 1.95}, NOW + 120)
    assert types(env) == ["ENTRY", "TP1", "STOP"]
def test_exit_on_hard_gate_failure_only_with_new_hunt():
    env = Env(); tick(env, hunt([item()]), {"x": 2.0}, NOW)
    w = {"symbol": "XYZ", "gates": [{"gate": "Konfirmasi smart money", "ok": False, "text": "smart money menjual bersih"}]}
    tick(env, hunt([], [w], gen=NOW), {"x": 2.0}, NOW + 60); assert types(env) == ["ENTRY"]          # hasil Hunter sama: belum dievaluasi
    tick(env, hunt([], [w], gen=NOW + 1800), {"x": 2.0}, NOW + 1800); assert types(env)[-1] == "EXIT" and "smart money" in env.sent[-1]["text"]
def test_exit_after_two_misses_without_hard_reason():
    env = Env(); tick(env, hunt([item()]), {"x": 2.0}, NOW)
    tick(env, hunt([], [], gen=NOW + 1800), {"x": 2.0}, NOW + 1800); assert types(env) == ["ENTRY"]
    tick(env, hunt([], [], gen=NOW + 3600), {"x": 2.0}, NOW + 3600); assert types(env)[-1] == "EXIT"
def test_time_stop_and_unlock_deadline():
    env = Env(); tick(env, hunt([item()]), {"x": 2.0}, NOW); tick(env, hunt([item()]), {"x": 2.0}, NOW + 22 * DAY); tick(env, hunt([item()]), {"x": 2.0}, NOW + 31 * DAY)
    assert types(env) == ["ENTRY", "REVIEW", "TIME"]
    env = Env(); it = item(); it["plan"]["deadline"] = {"days": 5, "text": "x"}; tick(env, hunt([it]), {"x": 2.0}, NOW); tick(env, hunt([it]), {"x": 2.0}, NOW + 6 * DAY); assert types(env) == ["ENTRY", "UNLOCK"]
def test_no_playbook_is_noop_and_price_failure_safe():
    env = Env(); notify.fast_tick(env.load, env.dump, None, env.send, NOW, hunt={}); assert env.sent == []
    def boom(ids): raise RuntimeError("x")
    notify.fast_tick(env.load, env.dump, boom, env.send, NOW, hunt=hunt([item()])); assert types(env) == ["ENTRY"]
def test_channels_and_format():
    calls = []; orig = notify._post; notify._post = lambda url, data, headers=None, timeout=15: calls.append((url, headers)) or 200
    try:
        e = {"type": "ENTRY", "symbol": "XYZ", "text": "<b>x</b>", "ticket": "t", "links": [{"label": "Uni", "url": "https://u?a=1&b=2"}]}
        ok = notify.send_all(e, {"TELEGRAM_BOT_TOKEN": "T", "TELEGRAM_CHAT_ID": "1,2", "NTFY_TOPIC": "topik", "ALERT_WEBHOOK_URL": "https://hook"})
        assert ok == ["telegram", "telegram", "ntfy", "webhook"] and any("ntfy.sh/topik" in c[0] and c[1]["Click"].startswith("https://u") for c in calls)
        assert "&lt;b&gt;" in notify.format_event(e) and notify.send_all(e, {}) == []
    finally: notify._post = orig

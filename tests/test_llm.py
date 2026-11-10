import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import llm, agents
KEYS = ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER", "LLM_MODELS"]
def clean():
    for k in KEYS: os.environ.pop(k, None)
    llm.STATS["used"].clear(); llm.STATS["errors"].clear(); llm.LAST["provider"] = None

def test_availability_and_order():
    clean(); assert llm.available() == [] and llm.default() is None
    os.environ.update(GROQ_API_KEY="g", GEMINI_API_KEY="m", ANTHROPIC_API_KEY="a"); assert llm.available() == ["gemini", "groq", "anthropic"]
    os.environ["LLM_PROVIDER"] = "anthropic,groq"; assert llm.available() == ["anthropic", "groq", "gemini"]; clean()
def test_model_override():
    clean(); os.environ["LLM_MODELS"] = "groq=abc, gemini=xyz"; assert llm.model_for("groq") == "abc" and llm.model_for("gemini") == "xyz" and llm.model_for("openai") == "gpt-4o-mini"; clean()
def test_translation_roundtrip():
    msgs = [{"role": "user", "content": "hai"}, {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "real_yield", "input": {"slug": "a"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{\"x\":1}"}]}]
    out, tools = llm.to_openai(msgs, agents.LLM_TOOLS, "sis")
    assert out[0] == {"role": "system", "content": "sis"} and out[2]["tool_calls"][0]["function"]["arguments"] == '{"slug": "a"}' and out[3] == {"role": "tool", "tool_call_id": "t1", "content": "{\"x\":1}"}
    assert tools[0]["function"]["parameters"]["type"] == "object"
    r = llm.from_openai({"choices": [{"message": {"content": None, "tool_calls": [{"id": "c1", "function": {"name": "real_yield", "arguments": "{\"slug\": \"b\"}"}}]}}]})
    assert r["stop_reason"] == "tool_use" and r["content"][0]["input"] == {"slug": "b"}
    assert llm.from_openai({"choices": [{"message": {"content": "ok"}}]}) == {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
def test_fallback_and_stats(monkeypatch=None):
    clean(); os.environ.update(GEMINI_API_KEY="m", GROQ_API_KEY="g"); seen = []
    def fake(url, body, headers, timeout=60):
        seen.append((url, body["model"], headers.get("Authorization")))
        if "generativelanguage" in url: raise RuntimeError("HTTP 429")
        return {"choices": [{"message": {"content": "jawab"}}]}
    orig = llm._post; llm._post = fake
    try:
        r = llm.call([{"role": "user", "content": "x"}])
        assert r["content"][0]["text"] == "jawab" and llm.LAST["provider"] == "groq" and "gemini" in llm.STATS["errors"] and seen[1][2] == "Bearer g"
        os.environ.pop("GROQ_API_KEY")
        try: llm.call([{"role": "user", "content": "x"}]); assert False
        except RuntimeError: pass
    finally: llm._post = orig; clean()
def test_anthropic_native_path():
    clean(); os.environ["ANTHROPIC_API_KEY"] = "a"; got = {}
    def fake(url, body, headers, timeout=60): got.update(url=url, h=headers, b=body); return {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    orig = llm._post; llm._post = fake
    try: llm.call([{"role": "user", "content": "x"}], None, "s"); assert got["h"]["x-api-key"] == "a" and got["b"]["system"] == "s" and "anthropic.com" in got["url"]
    finally: llm._post = orig; clean()

def test_gemini_model_discovery_on_404():
    import urllib.error, io
    clean(); os.environ["GEMINI_API_KEY"] = "m"; llm._PICKED.clear(); seen = []
    def fake(url, body, headers, timeout=60):
        seen.append(body["model"])
        if body["model"] == "gemini-2.5-flash": raise urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO(b""))
        return {"choices": [{"message": {"content": "ok"}}]}
    class R:
        def __init__(s, d): s.d = d
        def read(s): return s.d
        def __enter__(s): return s
        def __exit__(s, *a): pass
    orig, ou = llm._post, llm.urllib.request.urlopen; llm._post = fake
    llm.urllib.request.urlopen = lambda req, timeout=20: R(json.dumps({"data": [{"id": "models/gemini-3.0-flash"}, {"id": "models/gemini-3.0-flash-lite"}, {"id": "models/gemini-2.9-flash"}, {"id": "models/gemini-3.0-pro"}, {"id": "models/gemini-3.0-flash-image"}]}).encode())
    try:
        r = llm.call([{"role": "user", "content": "x"}]); assert r["content"][0]["text"] == "ok" and seen[-1] == "gemini-3.0-flash"
        llm.call([{"role": "user", "content": "x"}]); assert seen[-1] == "gemini-3.0-flash" and seen.count("gemini-2.5-flash") == 1   # dipakai ulang tanpa menebak lagi
    finally: llm._post = orig; llm.urllib.request.urlopen = ou; llm._PICKED.clear(); clean()

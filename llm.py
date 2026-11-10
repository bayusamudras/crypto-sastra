#!/usr/bin/env python3
"""
Crypto Sastra - Penyedia LLM serba bisa (tanpa dependensi)

Satu antarmuka berbentuk Anthropic (messages + tool_use) untuk banyak penyedia. Semua selain Anthropic dipanggil lewat
API kompatibel-OpenAI (chat/completions + tools), diterjemahkan bolak-balik di sini.

  gemini      GEMINI_API_KEY      (tingkat gratis tersedia)
  groq        GROQ_API_KEY        (tingkat gratis tersedia)
  openrouter  OPENROUTER_API_KEY  (ada model gratis berakhiran :free)
  deepseek    DEEPSEEK_API_KEY
  mistral     MISTRAL_API_KEY
  openai      OPENAI_API_KEY
  anthropic   ANTHROPIC_API_KEY

LLM_PROVIDER : urutan prioritas, dipisah koma (default: yang gratis dulu). Bila satu gagal (batas laju, galat), mencoba berikutnya.
LLM_MODELS   : override model, contoh "groq=llama-3.3-70b-versatile,gemini=gemini-2.5-flash".
Nama model bawaan bisa usang: ganti lewat LLM_MODELS bila penyedia menolaknya.
"""
import json, os, urllib.request

UA = "CryptoSastra/1.0"
REG = {  # nama: (env kunci, endpoint, model bawaan)
 "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "gemini-2.5-flash"),
 "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
 "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.3-70b-instruct:free"),
 "deepseek": ("DEEPSEEK_API_KEY", "https://api.deepseek.com/chat/completions", "deepseek-chat"),
 "mistral": ("MISTRAL_API_KEY", "https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
 "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
 "anthropic": ("ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/messages", os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")),
}
DEFAULT_ORDER = ["gemini", "groq", "openrouter", "deepseek", "mistral", "openai", "anthropic"]
LAST = {"provider": None}
STATS = {"used": {}, "errors": {}}

def order():
    pref = [x.strip().lower() for x in os.getenv("LLM_PROVIDER", "").split(",") if x.strip() in REG]
    return pref + [p for p in DEFAULT_ORDER if p not in pref]

def available():
    return [p for p in order() if os.getenv(REG[p][0], "").strip()]

def model_for(p):
    for kv in os.getenv("LLM_MODELS", "").split(","):
        if "=" in kv and kv.split("=", 1)[0].strip().lower() == p: return kv.split("=", 1)[1].strip()
    return REG[p][2]

def status():
    return {"configured": available(), "used": dict(STATS["used"]), "errors": dict(STATS["errors"])}

# ---- terjemahan Anthropic <-> OpenAI
def to_openai(messages, tools, system):
    out = [{"role": "system", "content": system}] if system else []
    for m in messages:
        c = m["content"]
        if isinstance(c, str): out.append({"role": m["role"], "content": c}); continue
        if m["role"] == "assistant":
            txt = "".join(b.get("text", "") for b in c if b.get("type") == "text")
            calls = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b.get("input", {}), ensure_ascii=False)}} for b in c if b.get("type") == "tool_use"]
            msg = {"role": "assistant", "content": txt or None}
            if calls: msg["tool_calls"] = calls
            out.append(msg)
        else:
            for b in c:
                if b.get("type") == "tool_result": out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b.get("content") if isinstance(b.get("content"), str) else json.dumps(b.get("content"), ensure_ascii=False)})
                elif b.get("type") == "text": out.append({"role": "user", "content": b["text"]})
    body_tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t["input_schema"]}} for t in (tools or [])]
    return out, body_tools

def from_openai(resp):
    msg = ((resp.get("choices") or [{}])[0]).get("message") or {}
    blocks = []
    if msg.get("content"): blocks.append({"type": "text", "text": msg["content"]})
    for tc in msg.get("tool_calls") or []:
        try: args = json.loads(tc["function"].get("arguments") or "{}")
        except Exception: args = {}
        blocks.append({"type": "tool_use", "id": tc.get("id") or tc["function"]["name"], "name": tc["function"]["name"], "input": args})
    return {"content": blocks, "stop_reason": "tool_use" if msg.get("tool_calls") else "end_turn"}

def _post(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={"content-type": "application/json", "User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def call_provider(p, messages, tools=None, system=None, max_tokens=900):
    env, url, _ = REG[p]; key = os.getenv(env, "").strip(); model = model_for(p)
    if p == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system: body["system"] = system
        if tools: body["tools"] = tools
        return _post(url, body, {"x-api-key": key, "anthropic-version": "2023-06-01"})
    msgs, ot = to_openai(messages, tools, system)
    body = {"model": model, "messages": msgs, "max_tokens": max_tokens}
    if ot: body["tools"] = ot
    hdr = {"Authorization": "Bearer " + key}
    if p == "openrouter": hdr["X-Title"] = "Crypto Sastra"
    return from_openai(_post(url, body, hdr))

def call(messages, tools=None, system=None, max_tokens=900):
    """Coba penyedia terkonfigurasi sesuai urutan; yang pertama berhasil dipakai. Gagal semua -> galat terakhir dilempar."""
    last = None
    for p in available():
        try:
            r = call_provider(p, messages, tools, system, max_tokens)
            LAST["provider"] = p; STATS["used"][p] = STATS["used"].get(p, 0) + 1; STATS["errors"].pop(p, None); return r
        except Exception as e:
            STATS["errors"][p] = str(e)[:120]; last = e; print(f"llm {p} gagal:", str(e)[:120])
    if last: raise last
    raise RuntimeError("tidak ada penyedia LLM terkonfigurasi")

def default():
    return call if available() else None

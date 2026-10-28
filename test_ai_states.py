#!/usr/bin/env python3
"""Offline tests for the AI availability states + raised caps.

Run: python3 test_ai_states.py   (needs requirements installed: httpx)

Covers the Oct 28 fix:
- the AI key is accepted under AI_API_KEY, OPENAI_API_KEY or GROQ_API_KEY;
- caps: 5 answered questions per group per UTC day, 3 per user in DMs;
- MAX_TOKENS is 600;
- the three failure states stay DISTINCT — 'unconfigured' only when the
  key is genuinely absent, 'pot' when the daily pot is spent, 'error'
  when the API call fails — and host_logic.ai_failure_note maps them to
  the honest user-facing note. A local stub server proves the success
  path still returns the reply and clears the failure state.
"""
import asyncio, json, os, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The store must point at a throwaway file BEFORE bot/store are imported.
os.environ["STORE_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="tghost-ai-states-"), "store.json")

# Some sandboxes export proxy env (incl. bracketed IPv6 no_proxy entries)
# that httpx cannot parse; production (Railway) has none. Drop them for
# this test process only.
for _k in ("http_proxy", "https_proxy", "all_proxy", "no_proxy",
           "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
    os.environ.pop(_k, None)

import ai_client, budget, host_logic

passed = 0


def check(cond, label):
    global passed
    assert cond, f"FAILED: {label}"
    passed += 1
    print(f"  ok: {label}")


KEY_VARS = ("AI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY")
_saved_env = {k: os.environ.get(k) for k in KEY_VARS}
_saved_base = ai_client.AI_BASE_URL


def set_keys(**kw):
    for k in KEY_VARS:
        os.environ.pop(k, None)
    for k, v in kw.items():
        if v is not None:
            os.environ[k] = v


MSGS = [{"role": "user", "content": "what is staking?"}]

print("== env-name fallback ==")
try:
    set_keys()
    check(ai_client.configured() is False, "no key anywhere = not configured")
    check(ai_client.api_key() == "", "no key anywhere = empty key")
    set_keys(GROQ_API_KEY="gsk-test")
    check(ai_client.configured() is True, "GROQ_API_KEY alone configures the bot")
    check(ai_client.api_key() == "gsk-test", "GROQ_API_KEY is picked up")
    set_keys(OPENAI_API_KEY="sk-test")
    check(ai_client.api_key() == "sk-test", "OPENAI_API_KEY is picked up")
    set_keys(AI_API_KEY="primary", GROQ_API_KEY="secondary")
    check(ai_client.api_key() == "primary", "AI_API_KEY wins when several are set")
    set_keys(AI_API_KEY="", GROQ_API_KEY="fallback")
    check(ai_client.api_key() == "fallback", "empty AI_API_KEY falls through to GROQ_API_KEY")
finally:
    set_keys(**{k: v for k, v in _saved_env.items() if v is not None})

print("== raised caps ==")
check(host_logic.DAILY_QA_LIMIT == 5, "group cap is 5 answered questions/day")
check(host_logic.DM_DAILY_QA_LIMIT == 3, "DM cap is 3 answered questions/user/day")
check(host_logic.daily_qa_ok("2026-10-28", 4, "2026-10-28") is True, "4 answered today: one more allowed")
check(host_logic.daily_qa_ok("2026-10-28", 5, "2026-10-28") is False, "5 answered today: cap reached")
check(host_logic.daily_qa_ok("2026-10-27", 5, "2026-10-28") is True, "new UTC day resets the count")
check(ai_client.MAX_TOKENS == 600, "answer MAX_TOKENS is 600")
check(budget.DAILY_TOKEN_BUDGET == 200_000, "daily pot unchanged at 200,000")

print("== note mapping ==")
check(host_logic.ai_failure_note(False, None) == "unconfigured", "no key -> unconfigured note")
check(host_logic.ai_failure_note(False, "pot") == "unconfigured", "no key trumps other states")
check(host_logic.ai_failure_note(True, "unconfigured") == "unconfigured", "key vanished -> unconfigured note")
check(host_logic.ai_failure_note(True, "pot") == "daily_limit", "pot empty -> daily-limit note, NOT 'isn't configured'")
check(host_logic.ai_failure_note(True, "error") == "error", "API error -> hiccup note, NOT 'isn't configured'")
check(host_logic.ai_failure_note(True, None) == "error", "unknown failure -> hiccup note (never cries 'unconfigured')")

print("== state: unconfigured ==")
try:
    set_keys()
    budget.reset()
    out = asyncio.run(ai_client.chat(MSGS))
    check(out is None, "unconfigured: chat returns None")
    check(ai_client.last_failure() == "unconfigured", "unconfigured: failure state recorded")
    check(host_logic.ai_failure_note(ai_client.configured(), ai_client.last_failure()) == "unconfigured",
          "unconfigured: maps to the limited-mode note")
finally:
    set_keys(**{k: v for k, v in _saved_env.items() if v is not None})

print("== state: pot empty ==")
try:
    set_keys(AI_API_KEY="test-key")
    budget.reset()
    check(budget.reserve(budget.DAILY_TOKEN_BUDGET) is True, "pot filled for the test")
    out = asyncio.run(ai_client.chat(MSGS))
    check(out is None, "pot empty: chat returns None")
    check(ai_client.last_failure() == "pot", "pot empty: failure state recorded")
    check(host_logic.ai_failure_note(ai_client.configured(), ai_client.last_failure()) == "daily_limit",
          "pot empty: maps to the daily-limit note")
finally:
    budget.reset()
    set_keys(**{k: v for k, v in _saved_env.items() if v is not None})

print("== state: API error ==")
try:
    set_keys(AI_API_KEY="test-key")
    budget.reset()
    ai_client.AI_BASE_URL = "http://127.0.0.1:9"  # discard port: refused at once
    out = asyncio.run(ai_client.chat(MSGS))
    check(out is None, "API error: chat returns None")
    check(ai_client.last_failure() == "error", "API error: failure state recorded")
    check(host_logic.ai_failure_note(ai_client.configured(), ai_client.last_failure()) == "error",
          "API error: maps to the hiccup note")
    check(budget.spent() == 0, "API error: reservation refunded, pot untouched")
finally:
    ai_client.AI_BASE_URL = _saved_base
    budget.reset()
    set_keys(**{k: v for k, v in _saved_env.items() if v is not None})

print("== state: success clears the failure ==")


class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.dumps({"choices": [{"message": {"content": " staking is locking tokens "}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    set_keys(AI_API_KEY="test-key")
    budget.reset()
    ai_client.AI_BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
    out = asyncio.run(ai_client.chat(MSGS))
    check(out == "staking is locking tokens", "success: reply text returned (stripped)")
    check(ai_client.last_failure() is None, "success: failure state cleared")
finally:
    ai_client.AI_BASE_URL = _saved_base
    budget.reset()
    set_keys(**{k: v for k, v in _saved_env.items() if v is not None})
    server.shutdown()

print("== bot level: on_message delivers the honest note ==")
try:
    import bot, store
    _bot_level = True
except Exception as _e:  # telegram not installed in this env
    print(f"  skipped: bot-level checks need requirements installed ({_e})")
    _bot_level = False

if _bot_level:
    import datetime as _dt

    class _U:
        def __init__(self, uid, name="Garigo"):
            self.id, self.first_name, self.is_bot = uid, name, False

    class _Msg:
        def __init__(self, text, user, reply_from=None):
            self.text, self.from_user = text, user
            self.reply_to_message = None
            if reply_from is not None:
                self.reply_to_message = type("R", (), {"from_user": reply_from})()
            self.replies = []

        async def reply_text(self, text, **kw):
            self.replies.append(text)

    class _Chat:
        def __init__(self, cid, ctype):
            self.id, self.type, self.title = cid, ctype, "FRG"

    class _Upd:
        def __init__(self, chat, msg):
            self.effective_chat, self.message = chat, msg

    class _Ctx:
        class application:
            bot_data = {"bot_id": 999000, "bot_username": "Professorcryptohostbot"}

    BOT_USER = _U(999000, "Professor")
    MEMBER = _U(424242)
    _today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")

    def group_ask(cid, text="keeping it for the dip — thoughts?"):
        msg = _Msg(text, MEMBER, reply_from=BOT_USER)
        asyncio.run(bot.on_message(_Upd(_Chat(cid, "supergroup"), msg), _Ctx()))
        return msg

    try:
        # 1) genuinely unconfigured -> limited-mode note, not counted
        set_keys()
        m = group_ask(9701)
        check(m.replies == [bot.LIMITED_NOTE], "group, no key: limited-mode note")
        check(store.get_group(9701).get("qa_count") in (None, 0),
              "group, no key: question NOT counted as answered")

        # 2) pot spent -> daily-limit note (never 'isn't configured')
        set_keys(AI_API_KEY="test-key")
        budget.reset()
        budget.reserve(budget.DAILY_TOKEN_BUDGET)
        m = group_ask(9702)
        check(m.replies == [bot.DAILY_LIMIT_NOTE], "group, pot empty: daily-limit note")
        check("AI_API_KEY" not in m.replies[0], "group, pot empty: no config talk")
        budget.reset()

        # 3) API error -> hiccup note (never 'isn't configured')
        ai_client.AI_BASE_URL = "http://127.0.0.1:9"
        m = group_ask(9703)
        check(m.replies == [bot.ERROR_NOTE], "group, API error: hiccup note")
        ai_client.AI_BASE_URL = _saved_base

        # 4) success -> real answer, counted once
        srv = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        ai_client.AI_BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}"
        m = group_ask(9704)
        check(m.replies == ["staking is locking tokens"], "group, AI up: real answer")
        check(store.get_group(9704).get("qa_count") == 1, "group, AI up: answer counted")
        srv.shutdown()
        ai_client.AI_BASE_URL = _saved_base

        # 5) group cap of 5: at cap -> daily-limit note, once per day only
        store.update_group(9705, qa_day=_today, qa_count=5)
        m = group_ask(9705)
        check(m.replies == [bot.DAILY_LIMIT_NOTE], "group at cap 5: daily-limit note")
        store.update_group(9705, last_reply_ts=0, reply_window=[])  # clear cooldown
        m = group_ask(9705)
        check(m.replies == [], "group at cap 5: limit note sent only once per day")

        # 6) DM: cap of 3 users get the daily-limit note
        bot.DM_DAILY[555001] = (_today, 3, False)
        msg = _Msg("what is staking?", _U(555001))
        asyncio.run(bot.on_message(_Upd(_Chat(555001, "private"), msg), _Ctx()))
        check(msg.replies == [bot.DAILY_LIMIT_NOTE], "DM at cap 3: daily-limit note")

        # 7) DM: unconfigured -> limited-mode note
        set_keys()
        msg = _Msg("what is staking?", _U(555002))
        asyncio.run(bot.on_message(_Upd(_Chat(555002, "private"), msg), _Ctx()))
        check(msg.replies == [bot.LIMITED_NOTE], "DM, no key: limited-mode note")
    finally:
        budget.reset()
        ai_client.AI_BASE_URL = _saved_base
        set_keys(**{k: v for k, v in _saved_env.items() if v is not None})
        bot.DM_DAILY.pop(555001, None)
        bot.DM_DAILY.pop(555002, None)

print(f"\nALL {passed} CHECKS PASSED")

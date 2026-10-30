#!/usr/bin/env python3
"""Offline unit tests for TG Host — plain asserts, no network, no Telegram.

Run: python3 tests.py
Covers: store CRUD per group, cooldown/cap logic, starter due + quiet-hours
math, trigger decisions, admin gate, starter-theme weighting (~60/40),
built-in KB facts, welcome rendering.
"""
import importlib, os, sys, tempfile, time

# Point the store at a throwaway file BEFORE importing it.
_tmp = tempfile.mkdtemp(prefix="tghost-test-")
os.environ["STORE_PATH"] = os.path.join(_tmp, "store.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import host_logic, kb, store
importlib.reload(store)

passed = 0

def check(cond, label):
    global passed
    assert cond, f"FAILED: {label}"
    passed += 1
    print(f"  ok: {label}")

NOW = 1_760_000_000  # fixed epoch for deterministic math

print("== store: defaults & CRUD ==")
g = store.get_group(111)
check(g["enabled"] is True, "default enabled")
check(g["persona_name"] == "Professor Crypto", "default persona name")
check(g["starter_mins"] == 240, "default starter_mins 240")
check(g["quiet_start"] == 4 and g["quiet_end"] == 11, "default quiet 4-11 UTC")
check(g["cooldown_s"] == 20 and g["hourly_cap"] == 30, "default cooldown/cap")
check(g["questions_on"] is False, "questions mode default off")
check(g["custom_starters"] == [] and g["reply_window"] == [], "list defaults are lists")

store.update_group(111, persona_name="Luna", starter_mins=60)
g = store.get_group(111)
check(g["persona_name"] == "Luna" and g["starter_mins"] == 60, "update persists")
g2 = store.get_group(222)
check(g2["persona_name"] == "Professor Crypto", "other group unaffected (per-group isolation)")
check(set(store.all_group_ids()) == {111}, "only touched group is registered (111 read-created? no: reads don't create)" if False else "group id list sane")

store.learn(111, "Our site is example.com")
store.learn(111, "We meet Fridays")
check("example.com" in store.get_group(111)["knowledge"], "learn appends")
check("Fridays" in store.get_group(111)["knowledge"], "learn appends second fact")
store.clear_knowledge(111)
check(store.get_group(111)["knowledge"] == "", "forget clears")

store.add_custom_starter(111, "GM! What are we watching today?")
store.add_custom_starter(111, "Poll time: stake or stay liquid?")
check(len(store.get_group(111)["custom_starters"]) == 2, "custom starters accumulate")

store.touch_activity(111, ts=NOW)
check(store.get_group(111)["last_activity_ts"] == NOW, "touch_activity records ts")

print("== cooldown / cap ==")
check(host_logic.cooldown_ok(0, NOW, 20), "cooldown ok with no prior reply")
check(host_logic.cooldown_ok(NOW - 20, NOW, 20), "cooldown ok at boundary")
check(not host_logic.cooldown_ok(NOW - 5, NOW, 20), "cooldown blocks inside window")
check(host_logic.cap_ok([NOW - 60] * 29, NOW, 30), "cap ok at 29 in window")
check(not host_logic.cap_ok([NOW - 60] * 30, NOW, 30), "cap blocks at 30 in window")
check(host_logic.cap_ok([NOW - 7200] * 30, NOW, 30), "old replies fall out of window")
check(host_logic.prune_reply_window([NOW - 7200, NOW - 10], NOW) == [NOW - 10], "prune keeps only recent")

print("== daily question cap ==")
check(host_logic.DAILY_QA_LIMIT == 5, "daily question limit is 5 per group")
check(host_logic.DM_DAILY_QA_LIMIT == 3, "DM question limit is 3 per user")
check(host_logic.daily_qa_ok("", 0, "2026-10-24"), "daily cap ok with no prior day")
check(host_logic.daily_qa_ok("2026-10-23", 1, "2026-10-24"), "new UTC day resets daily count")
check(host_logic.daily_qa_ok("2026-10-24", 1, "2026-10-24"), "daily cap allows second question same day (cap 5)")
check(not host_logic.daily_qa_ok("2026-10-24", 5, "2026-10-24"), "daily cap blocks sixth question same day")
check(host_logic.daily_qa_count("2026-10-23", 1, "2026-10-24") == 0, "daily count resets on new day")
check(host_logic.daily_qa_count("2026-10-24", 1, "2026-10-24") == 1, "daily count keeps same-day total")

print("== quiet hours ==")
check(host_logic.in_quiet_hours(4, 4, 11), "quiet start inclusive")
check(host_logic.in_quiet_hours(10, 4, 11), "quiet mid-window")
check(not host_logic.in_quiet_hours(11, 4, 11), "quiet end exclusive")
check(not host_logic.in_quiet_hours(15, 4, 11), "daytime not quiet")
check(host_logic.in_quiet_hours(23, 22, 6), "wrap window: late night quiet")
check(host_logic.in_quiet_hours(3, 22, 6), "wrap window: early morning quiet")
check(not host_logic.in_quiet_hours(12, 22, 6), "wrap window: midday not quiet")
check(not host_logic.in_quiet_hours(5, 5, 5), "start == end = no quiet hours")

print("== starter due math ==")
base = dict(last_activity_ts=NOW - 300 * 60, last_starter_ts=0, starter_mins=240,
            quiet_start=4, quiet_end=11)
check(host_logic.starter_due(NOW, hour_utc=15, **base), "due after 300 quiet mins at 15:00 UTC")
check(not host_logic.starter_due(NOW, hour_utc=15, **{**base, "last_activity_ts": NOW - 100 * 60}),
      "not due before silence threshold")
check(not host_logic.starter_due(NOW, hour_utc=5, **base), "not due inside quiet hours")
check(not host_logic.starter_due(NOW, hour_utc=15, **{**base, "last_starter_ts": NOW - 60 * 60}),
      "not due when bot started a topic an hour ago (even if group silent longer)")
check(not host_logic.starter_due(NOW, hour_utc=15, **{**base, "last_activity_ts": 0}),
      "never-seen group is not cold-started")
check(host_logic.starter_due(NOW, hour_utc=15, **{**base, "last_activity_ts": NOW - 240 * 60}),
      "due exactly at threshold")

print("== triggers ==")
check(host_logic.decide_trigger("hey @HostBot what is staking?", bot_username="HostBot",
                                is_reply_to_bot=False, questions_on=False) == "mention", "mention triggers")
check(host_logic.decide_trigger("GM everyone", bot_username="HostBot",
                                is_reply_to_bot=False, questions_on=False) is None, "plain chat does not trigger")
check(host_logic.decide_trigger("thanks!", bot_username="HostBot",
                                is_reply_to_bot=True, questions_on=False) == "reply", "reply to bot triggers")
check(host_logic.decide_trigger("how does the LUNC burn work?", bot_username="HostBot",
                                is_reply_to_bot=False, questions_on=True) == "question", "questions mode catches crypto ?")
check(host_logic.decide_trigger("how does the LUNC burn work?", bot_username="HostBot",
                                is_reply_to_bot=False, questions_on=False) is None, "questions mode off = no catch")
check(host_logic.decide_trigger("what's for lunch today?", bot_username="HostBot",
                                is_reply_to_bot=False, questions_on=True) is None, "non-crypto ? ignored")
check(host_logic.decide_trigger("what is bitcoin.", bot_username="HostBot",
                                is_reply_to_bot=False, questions_on=True) is None, "no '?' = no question trigger")
check(host_logic.looks_crypto_question("?") is False, "tiny message rejected")
check(host_logic.looks_crypto_question("is staking safe?") is True, "keyword question passes")

print("== admin gate ==")
class FakeMember:
    def __init__(self, status): self.status = status
check(host_logic.is_admin_status(FakeMember("administrator").status), "administrator is admin")
check(host_logic.is_admin_status(FakeMember("creator").status), "creator is admin")
check(not host_logic.is_admin_status(FakeMember("member").status), "member is not admin")
check(not host_logic.is_admin_status(FakeMember("restricted").status), "restricted is not admin")
check(not host_logic.is_admin_status(None), "None status is not admin")

print("== welcome rendering ==")
check(host_logic.render_welcome("Hi {name}!", "Steve") == "Hi Steve!", "{name} replaced")
check(host_logic.render_welcome("Hi {name}!", "") == "Hi friend!", "empty name falls back")
check(host_logic.render_welcome("No placeholder", "X") == "No placeholder", "no placeholder untouched")

print("== starter themes & weighting ==")
totals = kb.theme_weight_totals()
share = totals["lunc"] / (totals["lunc"] + totals["market"])
check(0.55 <= share <= 0.65, f"LUNC weight share ~60% (got {share:.0%})")
check(all(t["fallback"] and t["theme"] for t in kb.STARTER_THEMES), "every theme has theme + fallback")
import random
rng = random.Random(7)
picks = [host_logic.pick_theme(rng)["category"] for _ in range(2000)]
lunc_share = picks.count("lunc") / len(picks)
check(0.54 <= lunc_share <= 0.66, f"empirical pick share ~60% (got {lunc_share:.0%})")
custom_rng_theme = host_logic.pick_theme(random.Random(1))
check(custom_rng_theme in kb.STARTER_THEMES, "pick returns a real theme")

print("== built-in KB facts ==")
K = kb.DEFAULT_KB
for needle in ["columbus-5", "21 days", "1.5%", "1.2%", "12223", "CW20",
               "Galaxy Station", "Keplr", "seed phrase", "LuncScan", "LUNCDash",
               "finder.terraclassic.community", "Transparent Validator Chat"]:
    check(needle in K, f"KB contains '{needle}'")
check("terra1" not in K, "KB contains no contract addresses")

print("== upgraded KB: deep LUNC + dated governance + general crypto ==")
for needle in ["May 2022", "Terra 2.0", "40%", "33.4%", "12233", "12234",
               "31010600", "v14_4", "October 24, 2026", "October 26, 2026",
               "validator.info", "NO WITH VETO", "Impermanent loss",
               "halving", "copycat tickers",
               "t.me/transparentvalidatorchat", "send back double", "Market cap",
               "/terra/tax/v1beta1/params"]:
    check(needle in K, f"upgraded KB contains '{needle}'")
check("12234" in K and "NO sunset" in K, "12234 no-sunset caveat present")
check("turnout" in K.lower() and "26.9%" in K, "12234 quorum snapshot present")
for banned in ["FUN", "ROTTI", "COFFEE", "DO Chain", "do-chain"]:
    check(banned not in K, f"KB excludes separate project '{banned}'")
check("LUNC Kickback" not in K and "lunckickback" not in K.lower(),
      "KB promotes no specific validator")
check(len(kb.STARTER_THEMES) == 24, "starter pool grew to 24 themes (12 LUNC + 12 market)")
check(sum(1 for t in kb.STARTER_THEMES if t["category"] == "lunc") == 12,
      "12 LUNC starter themes")
check(any("Finder" in t["fallback"] for t in kb.STARTER_THEMES),
      "new verification starter present")
check(any("Impermanent loss" in t["theme"] for t in kb.STARTER_THEMES),
      "new impermanent-loss starter present")

print("== topic pin ==")
check(store.get_group(111).get("topic_id") is None, "topic_id default None")
store.update_group(111, topic_id=1)
check(store.get_group(111)["topic_id"] == 1, "topic_id set to 1 (General)")
store.update_group(111, topic_id=None)
check(store.get_group(111).get("topic_id") is None, "topic_id cleared")
check(host_logic.thread_kw(1) == {"message_thread_id": 1}, "thread_kw(1) pins General")
check(host_logic.thread_kw(None) == {}, "thread_kw(None) = group root")
check(host_logic.thread_kw(0) == {} and host_logic.thread_kw("x") == {}, "thread_kw rejects bad ids")
check(host_logic.topic_here(1) == 1, "topic_here captures General (thread id 1)")
check(host_logic.topic_here(4242) == 4242, "topic_here captures a named topic's thread id")
check(host_logic.topic_here(None) is None, "topic_here(None) = no topic (root) — capture nothing")
check(host_logic.topic_here(0) is None, "topic_here(0) = no topic")
check(host_logic.topic_here("x") is None, "topic_here rejects garbage")

print("== stale topic pin self-heal (bot level) ==")
# These checks import bot.py, which needs the runtime deps from
# requirements.txt (python-telegram-bot, httpx). Without them the pure-logic
# checks above still run and this section reports itself skipped.
try:
    import asyncio
    import bot
    from telegram.error import BadRequest
    _bot_ok = True
except ImportError as _imp_err:
    _bot_ok = False
    print(f"  skipped: bot-level checks need requirements installed ({_imp_err})")

if _bot_ok:
    class FakeBot:
        """Records successful sends; raises BadRequest('Message thread not
        found') for (chat_id, thread_id) pairs marked stale, like Telegram
        does when a pinned forum topic was deleted."""
        def __init__(self, stale=(), fail_all=False):
            self.sent = []
            self.stale = set(stale)
            self.fail_all = fail_all
        async def send_message(self, chat_id=None, text=None, **kw):
            if self.fail_all:
                raise BadRequest("Chat not found")
            tid = kw.get("message_thread_id")
            if tid is not None and (chat_id, tid) in self.stale:
                raise BadRequest("Message thread not found")
            self.sent.append((chat_id, text, kw))

    class FakeApp:
        def __init__(self, fakebot): self.bot = fakebot

    # (c) a valid pin still sends with message_thread_id set, pin kept
    store.update_group(9001, topic_id=5)
    fb = FakeBot()
    asyncio.run(bot.send_pinned_message(fb, 9001, store.get_group(9001), "hello"))
    check(fb.sent == [(9001, "hello", {"message_thread_id": 5})],
          "valid pin sends into the pinned topic")
    check(store.get_group(9001)["topic_id"] == 5, "valid pin is kept")

    # (a) stale pin: cleared in the store + retry lands at the group root
    store.update_group(9002, topic_id=99)
    fb = FakeBot(stale={(9002, 99)})
    asyncio.run(bot.send_pinned_message(fb, 9002, store.get_group(9002), "starter!"))
    check(store.get_group(9002)["topic_id"] is None, "stale pin cleared from store")
    check(fb.sent == [(9002, "starter!", {})], "retry lands at group root (no thread id)")

    # an unrelated BadRequest must NOT clear the pin, and must propagate
    store.update_group(9003, topic_id=7)
    fb = FakeBot(fail_all=True)
    try:
        asyncio.run(bot.send_pinned_message(fb, 9003, store.get_group(9003), "x"))
        _raised = False
    except BadRequest:
        _raised = True
    check(_raised, "unrelated BadRequest still propagates")
    check(store.get_group(9003)["topic_id"] == 7, "unrelated failure keeps the pin")

    # (b) one bad group never blocks a later group in the same starter tick
    async def _fake_starter_text(cfg):
        return "STARTER"
    _orig_starter_text = bot.make_starter_text
    bot.make_starter_text = _fake_starter_text
    # Since 2026-10-29 starters are gated by the owner's STARTERS_ENABLED
    # switch (default off) and default off per group — this section tests
    # the tick mechanics, so it explicitly turns both on.
    os.environ["STARTERS_ENABLED"] = "1"
    try:
        store.update_group(9101, topic_id=99, last_activity_ts=NOW - 20000,
                           last_starter_ts=0, starters_on=True)
        store.update_group(9102, last_activity_ts=NOW - 20000, last_starter_ts=0,
                           starters_on=True)
        fb = FakeBot(stale={(9101, 99)})
        asyncio.run(bot.starter_tick(FakeApp(fb), NOW, 15))
    finally:
        bot.make_starter_text = _orig_starter_text
    check((9101, "STARTER", {}) in fb.sent, "bad-pin group still gets its starter (root retry)")
    check((9102, "STARTER", {}) in fb.sent, "later group in same tick still gets its starter")
    check(store.get_group(9101)["topic_id"] is None, "tick cleared the bad group's pin")
    check(store.get_group(9102)["last_starter_ts"] == NOW, "healthy group's starter ts recorded")

    # welcome path (on_new_member) self-heals the same way
    class _NewMember:
        is_bot = False
        first_name = "Newbie"
        username = None
    class _Chat:
        id = 9201
    class _MembersMsg:
        new_chat_members = [_NewMember()]
    class _JoinUpdate:
        effective_chat = _Chat()
        message = _MembersMsg()
    class _Ctx:
        def __init__(self, b): self.bot = b
    store.update_group(9201, topic_id=77)
    fb = FakeBot(stale={(9201, 77)})
    asyncio.run(bot.on_new_member(_JoinUpdate(), _Ctx(fb)))
    check(store.get_group(9201)["topic_id"] is None, "welcome: stale pin cleared")
    check(len(fb.sent) == 1 and fb.sent[0][0] == 9201 and fb.sent[0][2] == {}
          and "Newbie" in fb.sent[0][1], "welcome lands at group root after heal")

    print("== pinned-send log line (bot level) ==")
    import contextlib, io

    # pinned success: one log line naming the chat + thread actually used
    store.update_group(9001, topic_id=5)
    fb = FakeBot()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        asyncio.run(bot.send_pinned_message(fb, 9001, store.get_group(9001), "hello"))
    check("tg-host: sent to chat 9001 thread 5" in buf.getvalue(),
          "pinned send logs 'sent to chat <id> thread <tid>'")

    # unpinned success: logged as thread root
    store.update_group(9004, topic_id=None)
    fb = FakeBot()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        asyncio.run(bot.send_pinned_message(fb, 9004, store.get_group(9004), "root hi"))
    check("tg-host: sent to chat 9004 thread root" in buf.getvalue(),
          "root send logs 'thread root'")

    # failure: the exception still propagates and NO sent line is logged
    store.update_group(9003, topic_id=7)
    fb = FakeBot(fail_all=True)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            asyncio.run(bot.send_pinned_message(fb, 9003, store.get_group(9003), "x"))
        _raised = False
    except BadRequest:
        _raised = True
    check(_raised, "failed send still propagates (log section)")
    check("sent to chat" not in buf.getvalue(), "failed send logs no 'sent' line")

    # stale-pin heal retry: the root retry is logged as a root send
    store.update_group(9002, topic_id=99)
    fb = FakeBot(stale={(9002, 99)})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        asyncio.run(bot.send_pinned_message(fb, 9002, store.get_group(9002), "starter!"))
    check("tg-host: sent to chat 9002 thread root" in buf.getvalue(),
          "healed root retry logs 'thread root'")

    print("== /host topic here (bot level) ==")

    class _HostMsg:
        def __init__(self, thread_id=None):
            self.message_thread_id = thread_id
            self.replies = []
        async def reply_text(self, text, **kw):
            self.replies.append(text)

    class _HostChat:
        def __init__(self, cid):
            self.id = cid
            self.type = "supergroup"
            self.title = "FRG"

    class _HostUser:
        def __init__(self, uid): self.id = uid

    class _HostUpdate:
        def __init__(self, cid, uid, thread_id=None):
            self.effective_chat = _HostChat(cid)
            self.effective_user = _HostUser(uid)
            self.message = _HostMsg(thread_id)

    class _HostMember:
        def __init__(self, status): self.status = status

    class _HostBot:
        def __init__(self, member): self._member = member
        async def get_chat_member(self, chat_id, user_id): return self._member

    class _HostCtx:
        def __init__(self, args, member):
            self.args = args
            self.bot = _HostBot(member)

    ADMIN = _HostMember("administrator")

    # 'here' captures the thread id of the topic the admin is standing in
    upd = _HostUpdate(9301, 501, thread_id=4242)
    asyncio.run(bot.on_host(upd, _HostCtx(["topic", "here"], ADMIN)))
    check(store.get_group(9301)["topic_id"] == 4242,
          "'here' stores the command message's own thread id")
    check(any("4242" in r for r in upd.message.replies),
          "'here' reply echoes the captured topic id")

    # 'here' in General captures 1 and says so
    upd = _HostUpdate(9302, 501, thread_id=1)
    asyncio.run(bot.on_host(upd, _HostCtx(["topic", "here"], ADMIN)))
    check(store.get_group(9302)["topic_id"] == 1, "'here' in General stores 1")
    check(any("General" in r for r in upd.message.replies),
          "'here' reply notes id 1 is General")

    # 'here' at the group root: nothing changes, admin is told to stand in a topic
    store.update_group(9303, topic_id=7)
    upd = _HostUpdate(9303, 501, thread_id=None)
    asyncio.run(bot.on_host(upd, _HostCtx(["topic", "here"], ADMIN)))
    check(store.get_group(9303)["topic_id"] == 7,
          "'here' with no thread id changes nothing (old pin kept)")
    check(any("inside a topic" in r for r in upd.message.replies),
          "'here' at root explains: run it from inside the topic")

    # numeric + off paths unchanged
    upd = _HostUpdate(9304, 501)
    asyncio.run(bot.on_host(upd, _HostCtx(["topic", "5"], ADMIN)))
    check(store.get_group(9304)["topic_id"] == 5, "numeric /host topic <id> still works")
    upd = _HostUpdate(9304, 501)
    asyncio.run(bot.on_host(upd, _HostCtx(["topic", "off"], ADMIN)))
    check(store.get_group(9304)["topic_id"] is None, "/host topic off still clears the pin")

    # non-admins can't pin with 'here' either (existing admin gate covers it)
    upd = _HostUpdate(9305, 502, thread_id=9)
    asyncio.run(bot.on_host(upd, _HostCtx(["topic", "here"], _HostMember("member"))))
    check(store.get_group(9305)["topic_id"] is None, "non-admin 'here' is refused, nothing stored")
    check(any("Only group admins" in r for r in upd.message.replies),
          "non-admin 'here' gets the admin-gate reply")

    print("== /botstats (bot level) ==")
    import datetime as _dtmod

    # store figures on a deterministic future day, so reruns never flake
    _c = store.usage_counts(today="2030-01-01")
    check(_c["group_questions_today"] == 0, "usage_counts: nothing answered on a future day")
    store.update_group(9601, qa_day="2030-01-01", qa_count=1)
    store.update_group(9602, qa_day="2030-01-02", qa_count=7)
    _c = store.usage_counts(today="2030-01-01")
    check(_c["group_questions_today"] == 1, "usage_counts counts only today's group questions")
    check(_c["groups"] == len(store.all_group_ids()), "usage_counts groups = groups in store")

    class _StatsMsg:
        def __init__(self):
            self.replies = []
        async def reply_text(self, text, **kw):
            self.replies.append(text)

    class _StatsUser:
        def __init__(self, uid): self.id = uid

    class _StatsUpdate:
        def __init__(self, uid):
            self.effective_user = _StatsUser(uid)
            self.effective_message = _StatsMsg()
            self.message = self.effective_message

    class _StatsCtx:
        args = []

    _today = _dtmod.datetime.now(_dtmod.timezone.utc).strftime("%Y-%m-%d")
    _saved_owner = bot.OWNER_ID
    _saved_dm = dict(bot.DM_DAILY)
    try:
        bot.OWNER_ID = 606060
        bot.DM_DAILY.clear()
        bot.DM_DAILY[111001] = (_today, 1, False)        # asked today
        bot.DM_DAILY[111002] = ("1999-01-01", 1, False)  # stale day, must not count
        upd = _StatsUpdate(606060)
        asyncio.run(bot.on_botstats(upd, _StatsCtx()))
        check(len(upd.effective_message.replies) == 1, "owner gets the /botstats card")
        _txt = upd.effective_message.replies[0]
        check(f"Groups I'm serving: {len(store.all_group_ids())}" in _txt,
              "card shows the live group count")
        check("Group questions answered today (UTC):" in _txt,
              "card shows today's group question count")
        check("People who've asked me in DM today (UTC, since my last restart): 1" in _txt,
              "card counts only today's DM question users")

        upd = _StatsUpdate(606061)
        asyncio.run(bot.on_botstats(upd, _StatsCtx()))
        check(upd.effective_message.replies == [], "non-owner gets silence")

        bot.OWNER_ID = 0
        upd = _StatsUpdate(606060)
        asyncio.run(bot.on_botstats(upd, _StatsCtx()))
        check(upd.effective_message.replies == [], "no owner configured = silence for everyone")
    finally:
        bot.OWNER_ID = _saved_owner
        bot.DM_DAILY.clear()
        bot.DM_DAILY.update(_saved_dm)

print(f"\nALL {passed} CHECKS PASSED")

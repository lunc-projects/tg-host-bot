#!/usr/bin/env python3
"""Offline tests for the owner directive of 2026-10-29: "Turn off the
professor unless he is asked a question."

Run: python3 test_starters_off.py   (needs requirements installed)

Proves:
- the STARTERS_ENABLED owner switch parses strictly (default OFF);
- starter_tick posts NOTHING while the switch is off — even for a group
  whose stored per-group setting is starters_on=True and whose starter
  is long overdue — and posts again only when the owner switch is on
  AND the group setting is on;
- new groups default to starters_on=False;
- the asked-a-question paths are untouched: a member who mentions the
  bot or replies to it still gets an answer, counted as before.
"""
import asyncio, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Throwaway store BEFORE bot/store are imported.
os.environ["STORE_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="tghost-starters-off-"), "store.json")
os.environ.pop("STARTERS_ENABLED", None)

import bot, host_logic, store

passed = 0


def check(cond, label):
    global passed
    assert cond, f"FAILED: {label}"
    passed += 1
    print(f"  ok: {label}")


NOW = 1_760_000_000  # fixed epoch, same convention as tests.py

print("== owner switch parsing (default OFF) ==")
for v in (None, "", "0", "false", "off", "no", "enabled-ish"):
    check(host_logic.starters_globally_enabled(v) is False,
          f"STARTERS_ENABLED={v!r} -> starters OFF")
for v in ("1", "true", "yes", "on", "TRUE", " On "):
    check(host_logic.starters_globally_enabled(v) is True,
          f"STARTERS_ENABLED={v!r} -> starters ON")

print("== both switches must agree ==")
check(host_logic.starters_allowed(None, True) is False, "owner off + group on -> NO starter")
check(host_logic.starters_allowed("1", False) is False, "owner on + group off -> NO starter")
check(host_logic.starters_allowed("1", True) is True, "owner on + group on -> starter allowed")

print("== new groups start quiet ==")
check(store.get_group(4242)["starters_on"] is False, "default starters_on is False")


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **kw):
        self.sent.append((chat_id, text, kw))


class FakeApp:
    def __init__(self, fakebot):
        self.bot = fakebot


async def _fake_starter_text(cfg):
    return "STARTER"


_orig_starter_text = bot.make_starter_text
bot.make_starter_text = _fake_starter_text
try:
    # A group that would fire immediately if anything let it: enabled,
    # per-group starters ON, silent for ~5.5 hours, outside quiet hours.
    store.update_group(9101, starters_on=True, last_activity_ts=NOW - 20000,
                       last_starter_ts=0)

    print("== switch OFF: the scheduler is silent ==")
    os.environ.pop("STARTERS_ENABLED", None)
    fb = FakeBot()
    asyncio.run(bot.starter_tick(FakeApp(fb), NOW, 15))
    check(fb.sent == [], "switch off: starter_tick sent nothing")
    check(store.get_group(9101)["last_starter_ts"] == 0,
          "switch off: no starter timestamp recorded")

    print("== switch ON: the same group fires again ==")
    os.environ["STARTERS_ENABLED"] = "1"
    fb = FakeBot()
    asyncio.run(bot.starter_tick(FakeApp(fb), NOW, 15))
    check(fb.sent == [(9101, "STARTER", {})], "switch on + group on: starter posted")
    check(store.get_group(9101)["last_starter_ts"] == NOW, "switch on: starter ts recorded")

    print("== switch ON but group OFF: still silent ==")
    store.update_group(9102, starters_on=False, last_activity_ts=NOW - 20000,
                       last_starter_ts=0)
    fb = FakeBot()
    asyncio.run(bot.starter_tick(FakeApp(fb), NOW, 15))
    check(all(chat_id != 9102 for chat_id, _, _ in fb.sent),
          "group starters_on=False: no starter even with owner switch on")
finally:
    bot.make_starter_text = _orig_starter_text
    os.environ.pop("STARTERS_ENABLED", None)

print("== asked a question: still answered ==")


class _User:
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
        self.id, self.type, self.title = cid, ctype, "Test Group"


class _Upd:
    def __init__(self, chat, msg):
        self.effective_chat, self.message = chat, msg


class _Ctx:
    class application:
        bot_data = {"bot_id": 999000, "bot_username": "Professorcryptohostbot"}


BOT_USER = _User(999000, "Professor")
MEMBER = _User(424242)


async def _fake_ai(cfg, text, speaker=""):
    return "Staking locks your LUNC for about 21 days.", True


_orig_ai = bot.ai_reply_or_note
bot.ai_reply_or_note = _fake_ai
try:
    # Mention path: a member asks the bot directly.
    msg = _Msg("@Professorcryptohostbot what is staking?", MEMBER)
    asyncio.run(bot.on_message(_Upd(_Chat(9201, "supergroup"), msg), _Ctx()))
    check(msg.replies == ["Staking locks your LUNC for about 21 days."],
          "mention: member still gets an answer")
    check(store.get_group(9201)["qa_count"] == 1, "mention: answer counted as before")

    # Reply path: a member replies to one of the bot's messages.
    store.update_group(9202, last_reply_ts=0, reply_window=[])
    msg = _Msg("and how long is unbonding?", MEMBER, reply_from=BOT_USER)
    asyncio.run(bot.on_message(_Upd(_Chat(9202, "supergroup"), msg), _Ctx()))
    check(msg.replies == ["Staking locks your LUNC for about 21 days."],
          "reply-to-bot: member still gets an answer")

    # Unaddressed chatter is NOT answered (it never was, questions mode off).
    store.update_group(9203, last_reply_ts=0, reply_window=[])
    msg = _Msg("nice weather today", MEMBER)
    asyncio.run(bot.on_message(_Upd(_Chat(9203, "supergroup"), msg), _Ctx()))
    check(msg.replies == [], "unaddressed message: no reply (unchanged behaviour)")
finally:
    bot.ai_reply_or_note = _orig_ai

print(f"\nALL {passed} CHECKS PASSED")

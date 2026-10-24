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
check(host_logic.DAILY_QA_LIMIT == 1, "daily question limit is 1")
check(host_logic.daily_qa_ok("", 0, "2026-10-24"), "daily cap ok with no prior day")
check(host_logic.daily_qa_ok("2026-10-23", 1, "2026-10-24"), "new UTC day resets daily count")
check(not host_logic.daily_qa_ok("2026-10-24", 1, "2026-10-24"), "daily cap blocks second question same day")
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

print(f"\nALL {passed} CHECKS PASSED")

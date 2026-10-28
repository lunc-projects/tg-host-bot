"""Cross-bot daily usage stats — publish side (Professor Crypto).

Steve's ruling (2026-10-27): the four assistant bots' usage counts
come together as ONE daily report from the LUNC Assistant bot. This
bot only publishes its own counts to a shared Upstash DB under
``botstats:professor``; the LUNC bot reads them back at report time.

Counts ONLY — no names, titles, usernames or message text ever leave
the bot; payloads are plain numbers plus a unix timestamp.

This bot keeps no message log, so the honest counts are the ones its
/botstats shows: groups serving + group questions answered today
(store.usage_counts) and DM askers today. The DM figure lives in
bot.py's in-memory DM_DAILY, so bot.py computes it and passes the
full counts dict to publish(); current_counts() covers the
store-based fields for callers that have nothing to add.

Config is env-only: UPSTASH_STATS_URL + UPSTASH_STATS_TOKEN. When
either is unset, publish() is a silent no-op so the bot runs exactly
as before until the shared DB is wired up. All failures are swallowed:
stats must never break the bot.
"""
import json
import os
import time
from urllib.parse import quote

import httpx

BOT_NAME = "professor"
KEY = "botstats:" + BOT_NAME
TTL_SECONDS = 3 * 24 * 3600          # a report key lives 3 days


def configured():
    return bool(os.getenv("UPSTASH_STATS_URL") and os.getenv("UPSTASH_STATS_TOKEN"))


def current_counts():
    """Store-based counts (the DM askers figure is added by bot.py,
    which owns the in-memory DM_DAILY counter)."""
    import store
    u = store.usage_counts()
    return {
        "groups_serving": u["groups"],
        "group_questions_today": u["group_questions_today"],
    }


def build_payload(counts, ts=None):
    payload = {"bot": BOT_NAME, "ts": int(ts if ts is not None else time.time())}
    payload.update(counts)
    return payload


async def publish(counts=None, client_factory=None):
    """Write this bot's counts to the shared DB. Returns True on
    success; False (silently) when unconfigured or on any failure."""
    try:
        if not configured():
            return False
        if counts is None:
            counts = current_counts()
        base = (os.getenv("UPSTASH_STATS_URL") or "").rstrip("/")
        headers = {"Authorization": f"Bearer {os.getenv('UPSTASH_STATS_TOKEN') or ''}"}
        factory = client_factory or (lambda: httpx.AsyncClient(timeout=15))
        async with factory() as client:
            r = await client.post(
                f"{base}/set/{quote(KEY, safe='')}?EX={TTL_SECONDS}",
                headers=headers, content=json.dumps(build_payload(counts)))
            r.raise_for_status()
        return True
    except Exception:
        return False

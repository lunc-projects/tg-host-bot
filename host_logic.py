"""Pure, testable logic for TG Host: triggers, rate limits, scheduling.

No Telegram / network imports here — bot.py feeds it plain values and fake
member objects in tests mimic the Telegram ones.
"""
import random
import re

import kb

ADMIN_STATUSES = ("administrator", "creator")

# Conservative keyword set for "questions mode" (unaddressed '?' messages).
CRYPTO_KEYWORDS = [
    "lunc", "luna classic", "terra classic", "ustc", "columbus",
    "bitcoin", "btc", "ethereum", "eth", "crypto", "altcoin", "memecoin",
    "staking", "stake", "unstake", "unbonding", "restake", "redelegate",
    "validator", "commission", "governance", "proposal", "vote",
    "burn", "burning", "wallet", "keplr", "galaxy station", "seed phrase",
    "cw20", "token", "coin", "dex", "swap", "airdrop", "nft",
    "market cap", "dominance", "halving", "bull", "bear", "yield", "apy", "apr",
]


def is_admin_status(status) -> bool:
    """True for Telegram chat-member statuses that count as group admin."""
    return status in ADMIN_STATUSES


def looks_crypto_question(text: str) -> bool:
    """Questions-mode heuristic: ends in '?', reasonable length, crypto keyword."""
    if not text:
        return False
    t = text.strip()
    if not t.endswith("?"):
        return False
    if len(t) < 8 or len(t) > 300:
        return False
    low = t.lower()
    # Word boundaries matter: "lunc" must not match "lunch", "eth" not "whether".
    return any(re.search(r"\b" + re.escape(word) + r"\b", low) for word in CRYPTO_KEYWORDS)


def decide_trigger(text, *, bot_username, is_reply_to_bot, questions_on):
    """Return a trigger reason ('mention' | 'reply' | 'question') or None."""
    if is_reply_to_bot:
        return "reply"
    if bot_username and text and f"@{bot_username}".lower() in text.lower():
        return "mention"
    if questions_on and looks_crypto_question(text or ""):
        return "question"
    return None


def cooldown_ok(last_reply_ts, now, cooldown_s) -> bool:
    if not last_reply_ts:
        return True
    return (now - last_reply_ts) >= cooldown_s


def cap_ok(reply_timestamps, now, cap, window_s=3600) -> bool:
    """reply_timestamps: iterable of epoch seconds of recent bot replies."""
    recent = [t for t in reply_timestamps if now - t < window_s]
    return len(recent) < cap


def prune_reply_window(reply_timestamps, now, window_s=3600):
    return [t for t in reply_timestamps if now - t < window_s]


DAILY_QA_LIMIT = 1  # answered member questions per group per UTC day


def daily_qa_count(qa_day, qa_count, today) -> int:
    """Questions already answered today (UTC); a new day resets to 0."""
    return 0 if qa_day != today else int(qa_count or 0)


def daily_qa_ok(qa_day, qa_count, today) -> bool:
    return daily_qa_count(qa_day, qa_count, today) < DAILY_QA_LIMIT


def in_quiet_hours(hour_utc, quiet_start, quiet_end) -> bool:
    """Quiet window [start, end) in UTC hours; wraps past midnight if start > end.
    start == end means 'no quiet hours'."""
    if quiet_start == quiet_end:
        return False
    if quiet_start < quiet_end:
        return quiet_start <= hour_utc < quiet_end
    return hour_utc >= quiet_start or hour_utc < quiet_end


def starter_due(now, *, last_activity_ts, last_starter_ts, starter_mins,
                hour_utc, quiet_start, quiet_end):
    """A starter is due when the group has been silent for starter_mins,
    the bot hasn't posted a starter within that same window either, and
    we're outside quiet hours. Anchor = latest of (last activity, last starter)."""
    if not last_activity_ts:
        return False  # bot has never seen this group speak; don't cold-start it
    if in_quiet_hours(hour_utc, quiet_start, quiet_end):
        return False
    anchor = max(last_activity_ts or 0, last_starter_ts or 0)
    return (now - anchor) >= starter_mins * 60


def pick_theme(rng=None):
    """Weighted starter theme pick (~60% LUNC / 40% market by kb weights)."""
    rng = rng or random
    themes = kb.STARTER_THEMES
    return rng.choices(themes, weights=[t["weight"] for t in themes], k=1)[0]


def thread_kw(topic_id):
    """send_message kwargs pinning a post to a forum topic (1 = General)."""
    try:
        tid = int(topic_id) if topic_id is not None else 0
    except (TypeError, ValueError):
        tid = 0
    return {"message_thread_id": tid} if tid >= 1 else {}


def topic_here(message_thread_id):
    """Topic id captured from a message sent inside a forum topic (the
    `/host topic here` path): the message's own message_thread_id, which
    Telegram sets on posts inside a topic (1 = General). Returns None when
    the message carries no thread id — sent at the group root / outside any
    topic — so the caller can ask the admin to re-run it inside a topic."""
    try:
        tid = int(message_thread_id)
    except (TypeError, ValueError):
        return None
    return tid if tid >= 1 else None


def render_welcome(template: str, name: str) -> str:
    return template.replace("{name}", name or "friend")

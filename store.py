"""Per-group config + runtime state for TG Host, in one JSON file.

Layout: {"groups": {"<chat_id>": {config..., state...}}}
Config keys come from DEFAULTS; state keys are runtime (last activity /
reply / starter timestamps, reply window) and live in the same record.
"""
import datetime, json, os, time

STORE_PATH = os.getenv("STORE_PATH", "data/host_store.json")

DEFAULT_WELCOME = ("👋 Welcome, {name}! Great to have you with us. "
                   "Jump in and say hi — and feel free to ask me anything crypto, especially LUNC. 🟢")

DEFAULTS = {
    # config
    "enabled": True,
    "persona_name": "Professor Crypto",
    "knowledge": "",
    "welcome_on": True,
    "welcome_text": DEFAULT_WELCOME,
    # Default OFF since 2026-10-29 (owner: the Professor speaks only when
    # asked). Even a stored True cannot fire while the STARTERS_ENABLED
    # owner switch is off — see host_logic.starters_allowed.
    "starters_on": False,
    "starter_mins": 240,
    "custom_starters": [],
    "questions_on": False,
    "topic_id": None,  # forum topic id for starters/welcomes (1 = General); None = group root
    "quiet_start": 4,
    "quiet_end": 11,
    "cooldown_s": 20,
    "hourly_cap": 30,
    # runtime state
    "last_activity_ts": 0,
    "last_reply_ts": 0,
    "last_starter_ts": 0,
    "reply_window": [],
    "starter_rotation": 0,
    "qa_day": "",
    "qa_count": 0,
    "qa_limited_day": "",
}


def _load():
    try:
        with open(STORE_PATH) as f:
            data = json.load(f)
        if isinstance(data, dict) and "groups" in data:
            return data
    except Exception:
        pass
    return {"groups": {}}


def _save(data):
    folder = os.path.dirname(STORE_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp = STORE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, STORE_PATH)


def get_group(chat_id) -> dict:
    """Full record for a group: DEFAULTS overlaid with stored values."""
    data = _load()
    stored = data["groups"].get(str(chat_id), {})
    rec = dict(DEFAULTS)
    rec.update(stored)
    rec["custom_starters"] = list(rec.get("custom_starters") or [])
    rec["reply_window"] = list(rec.get("reply_window") or [])
    return rec


def update_group(chat_id, **fields):
    data = _load()
    key = str(chat_id)
    rec = dict(DEFAULTS)
    rec.update(data["groups"].get(key, {}))
    rec.update(fields)
    data["groups"][key] = rec
    _save(data)
    return rec


def all_group_ids():
    return [int(k) for k in _load()["groups"].keys()]


def usage_counts(today=None):
    """Owner-only usage snapshot, from what this bot actually records.

    The host bot keeps no message log (unlike the assistant bots), so the
    honest figures are: groups present in the store, and group questions
    answered today (qa_day/qa_count are the bot's own daily counters).
    DM question users live in bot.py's in-memory DM_DAILY and are counted
    by the /botstats handler, not here."""
    if today is None:
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    groups = _load().get("groups", {})
    answered = 0
    for rec in groups.values():
        if isinstance(rec, dict) and rec.get("qa_day") == today:
            try:
                answered += int(rec.get("qa_count") or 0)
            except (TypeError, ValueError):
                pass
    return {"groups": len(groups), "group_questions_today": answered}


def touch_activity(chat_id, ts=None):
    return update_group(chat_id, last_activity_ts=int(ts or time.time()))


def learn(chat_id, text):
    rec = get_group(chat_id)
    existing = rec.get("knowledge") or ""
    joined = (existing + "\n" + text.strip()).strip() if existing else text.strip()
    return update_group(chat_id, knowledge=joined)


def clear_knowledge(chat_id):
    return update_group(chat_id, knowledge="")


def add_custom_starter(chat_id, text):
    rec = get_group(chat_id)
    starters = list(rec.get("custom_starters") or [])
    starters.append(text.strip())
    return update_group(chat_id, custom_starters=starters)

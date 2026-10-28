#!/usr/bin/env python3
"""TG Host — a general-purpose AI host for crypto Telegram groups.

An openly-a-bot host with a LUNC (Terra Classic) heart: welcomes newcomers,
answers crypto questions from built-in evergreen knowledge + the group's own
facts (/host learn), and posts conversation starters when a group goes quiet.
Works in ANY group; every setting is per-group via /host commands.

Run: TELEGRAM_BOT_TOKEN=... AI_API_KEY=... python bot.py
"""
import asyncio, datetime, os, random, time

from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import ai_client, host_logic, kb, store, stats_report

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_TELEGRAM_ID", "0") or 0)
STARTER_TICK_S = 60  # scheduler wake-up interval

HELP = """🎙 *TG Host — your group's AI host*

I'm a bot (openly!) who helps keep this community active: I welcome new members, answer crypto questions, and start conversations when things go quiet. My home turf is *LUNC / Terra Classic*, plus the wider market (BTC, ETH, the majors).

*For everyone*
• @mention me or reply to one of my messages to chat
• Ask crypto questions — staking, burns, governance, validators, wallet safety, market basics
• I don't have a live price feed, so for current prices check CoinGecko or your exchange

*For group admins — /host commands*
/host on | off — master switch
/host status — current settings
/host name <name> — my persona name
/host learn <fact> — teach me about this community (links, project facts)
/host knowledge — show what I've learned here
/host forget — clear learned facts
/host welcome <text> — set welcome message ({name} = new member)
/host welcometoggle — welcome messages on/off
/host starters on | off — conversation starters
/host startermins <30–1440> — how quiet before I start a topic
/host addstarter <text> — add a custom starter line
/host questions on | off — also answer unaddressed crypto questions ending in ?
/host quiet <start>-<end> — my quiet hours in UTC (e.g. 4-11)
/host topic here | <id> | off — pin my starters & welcomes to a forum topic (send "here" from inside the topic you want; 1 = General)"""

DM_START = """🎙 Hi, I'm a *TG Host* bot — an AI host for crypto groups, with a LUNC / Terra Classic heart.

*To use me in your group:*
1. Add me to the group
2. Make me an *admin* (or turn off my BotFather privacy mode) so I can see messages, spot questions, welcome people and time the quiet spells
3. An admin can then shape me with /host commands — teach me the community's facts with /host learn, set my name, welcome text, starter pace and quiet hours

In a group I welcome newcomers, chat when mentioned or replied to, and start a conversation when the room's been quiet a while. I never pretend to be human — I'm a bot and I say so. 🤖"""

LIMITED_NOTE = ("🤖 I'm running in limited mode right now (my AI brain isn't configured), "
                "so I can welcome people but can't really chat yet. An admin/owner needs to set AI_API_KEY.")

DAILY_LIMIT_NOTE = ("🎙 I've reached my daily limit for answered questions — "
                    "I'll be back answering tomorrow. Keep the chat going though! 🙂")

ERROR_NOTE = ("🎙 My brain hiccuped on that one — give me a moment and try again. 🙏")

# DM daily counts, in-memory only (like all Professor state, a redeploy resets
# them): user_id -> (utc_date_str, answered_count, limit_note_sent)
DM_DAILY = {}


def build_system_prompt(cfg) -> str:
    name = cfg.get("persona_name") or "Professor Crypto"
    parts = [
        f"You are {name}, the AI host of a crypto Telegram group. You are a BOT — openly an AI host, "
        "never claim to be human; if asked, say you're an AI host bot. Friendly, warm, community-native "
        "tone: you speak the LUNC / Terra Classic community's language (burns, staking, governance, validators, "
        "classic pride) and also know the wider market (BTC, ETH, the majors, market sentiment).",
        "Keep replies SHORT and conversational: 1–3 lines mostly. An occasional emoji is fine. "
        "Ask follow-up questions to keep conversation going. Don't lecture, don't spam.",
        "HARD RULES: No financial advice. No price predictions, no 'will it pump/moon' promises, no shilling any "
        "token. Never ask for seed phrases or private keys — warn that anyone who does is a scammer. "
        "Do not invent contract addresses, links, or project facts: for this group, use only the group facts below "
        "plus the built-in knowledge; for other projects, stick to well-known general knowledge or say you're not sure.",
        "NO LIVE DATA: you have NO live price feed and NO live chain data. Never quote a specific current price, "
        "market cap, percentage move, block height or supply figure as fact. If asked for live prices or stats, "
        "say you don't have a live feed and suggest CoinGecko, an exchange, Finder or LuncScan — then happily "
        "discuss the asset/topic in general terms.",
        "HONEST DATING: your built-in knowledge is current as of October 24, 2026, and time-sensitive facts in it "
        "(proposal votes, upgrade timing, parameters) are marked with their dates. If someone asks about anything "
        "that could have changed since then, say plainly that your knowledge is dated to October 24, 2026, give "
        "the dated fact if you have one, and point them to Finder, LuncScan or validator.info to verify the live "
        "state. Never guess at an outcome that may already have happened, and never present a dated snapshot "
        "(for example a proposal's turnout) as the current result.",
        "BUILT-IN KNOWLEDGE (evergreen facts you can rely on):\n" + kb.DEFAULT_KB,
    ]
    group_kb = (cfg.get("knowledge") or "").strip()
    if group_kb:
        parts.append("FACTS ABOUT THIS GROUP / COMMUNITY (taught by its admins — trust these for this group):\n" + group_kb)
    return "\n\n".join(parts)


async def ai_reply(cfg, user_text, speaker=""):
    out = await ai_client.chat([
        {"role": "system", "content": build_system_prompt(cfg)},
        {"role": "user", "content": (f"{speaker}: {user_text}" if speaker else user_text)},
    ])
    return out


async def ai_reply_or_note(cfg, user_text, speaker=""):
    """(text, answered): the AI reply, or the HONEST note for why not.

    The 'isn't configured' note is reserved for a genuinely missing AI
    key. A spent daily pot reads as the daily limit, and an API error as
    a momentary hiccup — the real reason is logged server-side by
    ai_client either way."""
    out = await ai_reply(cfg, user_text, speaker)
    if out is not None:
        return out, True
    kind = host_logic.ai_failure_note(ai_client.configured(), ai_client.last_failure())
    note = {"unconfigured": LIMITED_NOTE,
            "daily_limit": DAILY_LIMIT_NOTE,
            "error": ERROR_NOTE}[kind]
    return note, False


async def is_group_admin(ctx, chat_id, user_id) -> bool:
    try:
        member = await ctx.bot.get_chat_member(chat_id, user_id)
        return host_logic.is_admin_status(member.status)
    except Exception:
        return False


# ---------------------------------------------------------------- handlers

async def on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text(DM_START, parse_mode=ParseMode.MARKDOWN)
    else:
        cfg = store.get_group(chat.id)
        await update.message.reply_text(
            f"🎙 {cfg.get('persona_name') or 'Host'} is here! Mention me or reply to me to chat. "
            "Admins: /host status shows my settings, /help lists everything.")


async def on_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode=ParseMode.MARKDOWN)


async def on_botstats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Owner-only usage counter (not in the public command list). This bot
    # keeps no message log and no token counter, so the card reports only
    # what it actually records: groups served, today's answered group
    # questions (store), and today's DM question users (in-memory).
    if not OWNER_ID or update.effective_user.id != OWNER_ID:
        return
    u = store.usage_counts()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dm_users = sum(1 for rec in DM_DAILY.values() if rec[0] == today)
    await update.effective_message.reply_text(
        "*Bot usage* (only what I actually record — I don't keep a message log)\n"
        f"Groups I'm serving: {u['groups']}\n"
        f"Group questions answered today (UTC): {u['group_questions_today']}\n"
        f"People who've asked me in DM today (UTC, since my last restart): {dm_users}",
        parse_mode=ParseMode.MARKDOWN)


def professor_counts():
    """The counts this bot publishes for the combined daily report —
    exactly what /botstats shows: groups serving, group questions
    answered today (store), DM askers today (in-memory DM_DAILY)."""
    u = store.usage_counts()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dm_users = sum(1 for rec in DM_DAILY.values() if rec[0] == today)
    return {"groups_serving": u["groups"],
            "group_questions_today": u["group_questions_today"],
            "dm_askers_today": dm_users}


async def stats_loop(app: Application):
    """Publish counts to the shared stats DB every ~30 min (silent
    no-op until UPSTASH_STATS_* is configured)."""
    while True:
        try:
            await stats_report.publish(professor_counts())
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(1800)


async def on_host(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    msg = update.message
    if chat.type == "private":
        await msg.reply_text("The /host settings live in a group — add me to one and run /host there. 🙂")
        return
    cfg = store.get_group(chat.id)
    args = ctx.args or []
    if not args or args[0].lower() == "status":
        lines = [
            f"🎙 *Host status — {chat.title or 'this group'}*",
            f"• Host: {'ON' if cfg['enabled'] else 'OFF'} · name: {cfg.get('persona_name')}",
            f"• Welcome: {'on' if cfg['welcome_on'] else 'off'}",
            f"• Starters: {'on' if cfg['starters_on'] else 'off'}"
            f" (after {cfg['starter_mins']} quiet mins, {len(cfg.get('custom_starters') or [])} custom)",
            f"• Questions mode: {'on' if cfg['questions_on'] else 'off'}",
            f"• Daily question limit: {host_logic.DAILY_QA_LIMIT} answered question(s) per day (UTC)",
            f"• Topic pin: {('General (1)' if cfg.get('topic_id') == 1 else cfg.get('topic_id')) if cfg.get('topic_id') else 'none — group root (pin with /host topic here)'}",
            f"• Quiet hours (UTC): {cfg['quiet_start']:02d}:00–{cfg['quiet_end']:02d}:00",
            f"• Learned facts: {len((cfg.get('knowledge') or '').splitlines()) if cfg.get('knowledge') else 0} line(s)",
            f"• AI brain: {'connected' if ai_client.configured() else 'NOT configured (limited mode)'}",
        ]
        await msg.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        return

    # Everything below changes config -> group admins only.
    if not await is_group_admin(ctx, chat.id, user.id):
        await msg.reply_text("🔒 Only group admins can change my settings.")
        return

    sub = args[0].lower()
    rest = " ".join(args[1:]).strip()

    if sub in ("on", "off"):
        store.update_group(chat.id, enabled=(sub == "on"))
        await msg.reply_text(f"🎙 Host is now {'ON' if sub == 'on' else 'OFF'} for this group.")
    elif sub == "name":
        if not rest:
            await msg.reply_text("Usage: /host name <display name>")
            return
        store.update_group(chat.id, persona_name=rest[:40])
        await msg.reply_text(f"✅ I'll go by “{rest[:40]}” here.")
    elif sub == "learn":
        if not rest:
            await msg.reply_text("Usage: /host learn <fact or link about this community>")
            return
        store.learn(chat.id, rest)
        await msg.reply_text("🧠 Learned. I'll use that in this group.")
    elif sub == "knowledge":
        k = (cfg.get("knowledge") or "").strip()
        await msg.reply_text(("📚 *What I know about this group:*\n" + k) if k else "📚 Nothing learned yet — /host learn <fact>.",
                              parse_mode=ParseMode.MARKDOWN)
    elif sub == "forget":
        store.clear_knowledge(chat.id)
        await msg.reply_text("🗑 Cleared everything I learned about this group.")
    elif sub == "welcome":
        if not rest:
            await msg.reply_text("Usage: /host welcome <text> — use {name} for the new member's name.")
            return
        store.update_group(chat.id, welcome_text=rest[:500])
        await msg.reply_text("✅ Welcome message set.")
    elif sub == "welcometoggle":
        new = not cfg["welcome_on"]
        store.update_group(chat.id, welcome_on=new)
        await msg.reply_text(f"👋 Welcomes are now {'on' if new else 'off'}.")
    elif sub == "starters":
        if rest.lower() not in ("on", "off"):
            await msg.reply_text("Usage: /host starters on | off")
            return
        store.update_group(chat.id, starters_on=(rest.lower() == "on"))
        await msg.reply_text(f"💬 Conversation starters {'enabled' if rest.lower() == 'on' else 'disabled'}.")
    elif sub == "startermins":
        try:
            n = int(rest)
            if not (30 <= n <= 1440):
                raise ValueError
        except ValueError:
            await msg.reply_text("Usage: /host startermins <30–1440>")
            return
        store.update_group(chat.id, starter_mins=n)
        await msg.reply_text(f"✅ I'll start a conversation after {n} quiet minutes (outside quiet hours).")
    elif sub == "addstarter":
        if not rest:
            await msg.reply_text("Usage: /host addstarter <a starter line>")
            return
        store.add_custom_starter(chat.id, rest[:300])
        await msg.reply_text("✅ Starter added to this group's rotation.")
    elif sub == "questions":
        if rest.lower() not in ("on", "off"):
            await msg.reply_text("Usage: /host questions on | off")
            return
        store.update_group(chat.id, questions_on=(rest.lower() == "on"))
        await msg.reply_text(f"❓ Questions mode {'on — I’ll also answer unaddressed crypto questions ending in ?' if rest.lower() == 'on' else 'off'}.")
    elif sub == "topic":
        if rest.lower() == "here":
            # Pin to the topic the admin is standing in: Telegram stamps the
            # command message itself with that topic's message_thread_id.
            tid = host_logic.topic_here(getattr(msg, "message_thread_id", None))
            if tid is None:
                await msg.reply_text("📌 That only works from inside a topic — open the topic you "
                                     "want me to post in and send /host topic here from there. "
                                     "Nothing changed.")
                return
            store.update_group(chat.id, topic_id=tid)
            await msg.reply_text(f"📌 Pinned — my starters & welcomes will post to this topic (id {tid})"
                                 + (" — that's General." if tid == 1 else "."))
        elif rest.lower() in ("off", "none", "clear"):
            store.update_group(chat.id, topic_id=None)
            await msg.reply_text("📌 Topic pin cleared — my starters & welcomes go to the group root.")
        else:
            try:
                tid = int(rest)
                if tid < 1:
                    raise ValueError
            except ValueError:
                await msg.reply_text("Usage: /host topic <topic id | here | off> — General is topic 1, "
                                     "and 'here' pins the topic you're standing in.")
                return
            store.update_group(chat.id, topic_id=tid)
            await msg.reply_text(f"📌 Pinned — my starters & welcomes will post to topic {tid}"
                                 + (" (General)." if tid == 1 else "."))
    elif sub == "quiet":
        try:
            a, b = rest.split("-")
            s, e = int(a), int(b)
            if not (0 <= s <= 23 and 0 <= e <= 23):
                raise ValueError
        except ValueError:
            await msg.reply_text("Usage: /host quiet <start>-<end> in UTC hours, e.g. /host quiet 4-11")
            return
        store.update_group(chat.id, quiet_start=s, quiet_end=e)
        await msg.reply_text(f"🌙 Quiet hours set to {s:02d}:00–{e:02d}:00 UTC.")
    else:
        await msg.reply_text("Unknown /host option — /help lists them all.")


def _is_stale_pin_error(err) -> bool:
    """True when Telegram rejected a send because the pinned forum topic is
    gone (deleted / renumbered): the group's stored topic_id is stale."""
    if not isinstance(err, BadRequest):
        return False
    low = str(err).lower()
    if "thread not found" in low:
        return True
    return "message_thread_id" in low and ("invalid" in low or "not found" in low)


async def send_pinned_message(bot, chat_id, cfg, text):
    """Send to a group honoring its topic pin (starters & welcomes).

    Self-heal: if Telegram says the pinned topic no longer exists, clear the
    pin in the store and retry ONCE at the group root, so a dead pin can
    never mute the group forever. Any other failure propagates unchanged."""
    kw = host_logic.thread_kw(cfg.get("topic_id"))
    try:
        await bot.send_message(chat_id=chat_id, text=text, **kw)
    except BadRequest as e:
        if not kw or not _is_stale_pin_error(e):
            raise
        print(f"tg-host: stale topic pin {cfg.get('topic_id')} for chat {chat_id} — "
              f"clearing pin, retrying at group root ({e})")
        store.update_group(chat_id, topic_id=None)
        await bot.send_message(chat_id=chat_id, text=text)
        print(f"tg-host: sent to chat {chat_id} thread root")
        return
    tid = kw.get("message_thread_id")
    print(f"tg-host: sent to chat {chat_id} thread {tid if tid else 'root'}")


async def on_new_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    cfg = store.get_group(chat.id)
    store.touch_activity(chat.id)
    if not cfg["enabled"] or not cfg["welcome_on"]:
        return
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or (f"@{member.username}" if member.username else "friend")
        text = host_logic.render_welcome(cfg.get("welcome_text") or store.DEFAULT_WELCOME, name)
        await send_pinned_message(ctx.bot, chat.id, cfg, text)


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text or not msg.from_user or msg.from_user.is_bot:
        return
    chat = update.effective_chat
    bot_id = ctx.application.bot_data.get("bot_id")
    bot_username = ctx.application.bot_data.get("bot_username", "")

    if chat.type != "private":
        cfg = store.get_group(chat.id)
        store.touch_activity(chat.id)
        if not cfg["enabled"]:
            return
        is_reply_to_bot = bool(msg.reply_to_message and msg.reply_to_message.from_user
                               and msg.reply_to_message.from_user.id == bot_id)
        reason = host_logic.decide_trigger(msg.text, bot_username=bot_username,
                                           is_reply_to_bot=is_reply_to_bot,
                                           questions_on=cfg["questions_on"])
        if not reason:
            return
        now = time.time()
        cfg = store.get_group(chat.id)  # re-read after activity touch
        if not host_logic.cooldown_ok(cfg["last_reply_ts"], now, cfg["cooldown_s"]):
            return
        if not host_logic.cap_ok(cfg["reply_window"], now, cfg["hourly_cap"]):
            return
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        qa_count = host_logic.daily_qa_count(cfg.get("qa_day"), cfg.get("qa_count"), today)
        if qa_count >= host_logic.DAILY_QA_LIMIT:
            if cfg.get("qa_limited_day") != today:
                await msg.reply_text(DAILY_LIMIT_NOTE)
                store.update_group(chat.id, qa_limited_day=today)
            return
        speaker = msg.from_user.first_name or "someone"
        out, answered = await ai_reply_or_note(cfg, msg.text, speaker)
        window = host_logic.prune_reply_window(cfg["reply_window"], now)
        window.append(int(now))
        fields = dict(last_reply_ts=int(now), reply_window=window,
                      last_activity_ts=int(now))
        if answered:
            fields["qa_day"] = today
            fields["qa_count"] = qa_count + 1
        store.update_group(chat.id, **fields)
        await msg.reply_text(out[:4000])
    else:
        # DM: chat like a mention, with its own per-user daily cap.
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        uid = msg.from_user.id
        rec = DM_DAILY.get(uid)
        if rec and rec[0] == today and rec[1] >= host_logic.DM_DAILY_QA_LIMIT:
            if not rec[2]:
                await msg.reply_text(DAILY_LIMIT_NOTE)
                DM_DAILY[uid] = (today, rec[1], True)
            return
        cfg = dict(store.DEFAULTS)
        out, answered = await ai_reply_or_note(cfg, msg.text, msg.from_user.first_name or "")
        if answered:
            n = rec[1] + 1 if (rec and rec[0] == today) else 1
            DM_DAILY[uid] = (today, n, False)
        await msg.reply_text(out[:4000])


# ---------------------------------------------------------------- starters

async def make_starter_text(cfg) -> str:
    """One starter: rotate custom lines half the time; else AI from a weighted
    built-in theme; fall back to the theme's ready-made question."""
    customs = cfg.get("custom_starters") or []
    if customs and random.random() < 0.5:
        idx = int(cfg.get("starter_rotation") or 0) % len(customs)
        return customs[idx]
    theme = host_logic.pick_theme()
    if ai_client.configured():
        out = await ai_client.chat([
            {"role": "system", "content": build_system_prompt(cfg)},
            {"role": "user", "content":
                f"The group has been quiet. Write ONE short conversation starter (1–2 lines) "
                f"for the group on this theme: {theme['theme']}. Ask a question that invites replies. "
                f"No financial advice, no price predictions, no quoting live prices."},
        ], temperature=0.8)
        if out:
            return out[:500]
    return theme["fallback"]


async def starter_tick(app: Application, now, hour_utc):
    """One scheduler pass over all groups. Each group is isolated in its own
    try/except: a failure in one group (e.g. a stale topic pin) is logged with
    its chat id and never aborts the tick for the remaining groups."""
    for chat_id in store.all_group_ids():
        try:
            cfg = store.get_group(chat_id)
            if not cfg["enabled"] or not cfg["starters_on"]:
                continue
            if not host_logic.starter_due(
                    now, last_activity_ts=cfg["last_activity_ts"],
                    last_starter_ts=cfg["last_starter_ts"],
                    starter_mins=cfg["starter_mins"], hour_utc=hour_utc,
                    quiet_start=cfg["quiet_start"], quiet_end=cfg["quiet_end"]):
                continue
            text = await make_starter_text(cfg)
            await send_pinned_message(app.bot, chat_id, cfg, text)
            store.update_group(chat_id, last_starter_ts=int(now),
                               last_activity_ts=int(now),
                               starter_rotation=int(cfg.get("starter_rotation") or 0) + 1)
        except Exception as e:
            print(f"starter_loop error for chat {chat_id}: {e}")


async def starter_loop(app: Application):
    while True:
        try:
            await asyncio.sleep(STARTER_TICK_S)
            now = time.time()
            hour_utc = datetime.datetime.now(datetime.timezone.utc).hour
            await starter_tick(app, now, hour_utc)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"starter_loop error: {e}")


async def post_init(app: Application):
    try:
        me = await app.bot.get_me()
        app.bot_data["bot_id"] = me.id
        app.bot_data["bot_username"] = me.username or ""
        await app.bot.set_my_commands([
            BotCommand("host", "Host settings (admins) & status"),
            BotCommand("start", "What I do / add me to a group"),
            BotCommand("help", "Usage for members & admins"),
        ])
    except Exception as e:
        print(f"post_init: {e}")
    asyncio.create_task(starter_loop(app))
    asyncio.create_task(stats_loop(app))


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help", on_help))
    app.add_handler(CommandHandler("botstats", on_botstats))
    app.add_handler(CommandHandler("host", on_host))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    print("TG Host polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

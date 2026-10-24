# TG Host 🎙

A general-purpose **AI host bot for crypto Telegram groups** — with a strong
**LUNC (Terra Classic)** heart plus the wider market (BTC, ETH, the majors).

It is *openly a bot*: it never claims to be human. Its job is to keep a
community active — welcome newcomers, answer crypto questions, and start
conversations when the room goes quiet. It works in **any** Telegram group;
nothing about any specific community is built in. Everything it knows about
*your* group is taught by your admins with `/host learn`, and every setting
is per-group.

## What it does

- **Welcomes** new members with a configurable message
- **Chats** when @mentioned or replied to — short, conversational, community-native
- **Questions mode** (optional, off by default): also answers unaddressed
  crypto questions that end in "?"
- **Conversation starters**: when a group is silent longer than a set time
  (default 4 h, outside quiet hours), it posts one starter. Themes are
  ~60% LUNC (governance, staking, the burn, validators, ecosystem, community)
  and ~40% big-market (BTC dominance, sectors, risk-on/off, cycles) —
  AI-written, or the group's own custom lines (`/host addstarter`)
- **Built-in knowledge**: evergreen Terra Classic facts (staking & 21-day
  unbonding, validators/commission, governance, the 1.5% burn tax of which
  1.2% is burned, CW20 tokens, wallet safety, Finder / LuncScan / LUNCDash)
  plus general crypto knowledge
- **Honesty guardrails**: the bot has **no live price feed** and never quotes
  a "current" price, market cap or chain stat — it points people to
  CoinGecko / an exchange / Finder instead. No financial advice, no price
  predictions, no shilling, never asks for seed phrases
- **Anti-flood**: per-group reply cooldown (20 s) and hourly reply cap (30);
  answered member questions capped at 1 per group per UTC day (DMs: 1 per user per day)

## Set up the bot (BotFather)

1. Open [@BotFather](https://t.me/BotFather) → `/newbot` → pick a name and a
   username ending in `bot`. Save the token it gives you (that's your
   `TELEGRAM_BOT_TOKEN` — keep it secret, never commit it).
2. **Privacy mode — important.** By default Telegram bots in groups only see
   commands and mentions, so the host can't spot questions or notice quiet
   spells. Fix *one* of these:
   - In BotFather: `/mybots` → your bot → *Bot Settings* → *Group Privacy* →
     **Turn off**, **or**
   - simply make the bot an **admin** in each group (admins see all messages
     regardless of privacy mode). Making it admin is the recommended route.
3. (Optional) `/setdescription` / `/setuserpic` in BotFather for polish.

## Deploy (Railway)

1. Create a new Railway project from this repo/folder.
2. Set environment variables:
   | Variable | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | the BotFather token |
   | `AI_API_KEY` | your Groq (or OpenAI-compatible) API key |
   | `AI_BASE_URL` | `https://api.groq.com/openai/v1` (default) |
   | `AI_MODEL` | `openai/gpt-oss-120b` (default) |
3. Start command is the Procfile: `worker: python bot.py`. Railway picks it up
   automatically.
4. Add the bot to a group, make it admin, and run `/host status` to confirm
   it's alive and the AI brain shows "connected".

> Without `AI_API_KEY` the bot still welcomes members and explains it's in
> limited mode, but it can't chat or write starters (it falls back to
> ready-made starter questions).
>
> Note: group settings are kept in a JSON file (`data/host_store.json`,
> override with `STORE_PATH`). On Railway's ephemeral filesystem that file
> resets on redeploy unless you attach a volume — same behaviour as the
> owner's other bots; a shared volume mounted at `data/` makes it durable.

## Using it in a group

Members: @mention the bot or reply to it. Admins shape it with `/host`:

| Command | Effect |
|---|---|
| `/host on` / `/host off` | master switch for this group |
| `/host status` | show all settings (anyone can run this) |
| `/host name <name>` | the persona name the host uses |
| `/host learn <fact>` | teach it a fact/link about this community |
| `/host knowledge` | show what it has learned here |
| `/host forget` | clear learned facts |
| `/host welcome <text>` | set the welcome message (`{name}` = new member) |
| `/host welcometoggle` | welcomes on/off |
| `/host starters on/off` | conversation starters on/off |
| `/host startermins <30–1440>` | quiet minutes before a starter |
| `/host addstarter <text>` | add a custom starter line |
| `/host questions on/off` | answer unaddressed crypto "?" messages too |
| `/host topic <id \| off>` | pin starters & welcomes to a forum topic (1 = General) |
| `/host quiet <start>-<end>` | quiet hours in UTC (default 4–11) |

All config commands are group-admin only; the bot politely refuses everyone
else.

## Files

- `bot.py` — Telegram handlers, persona prompt, starter scheduler
- `host_logic.py` — pure trigger / cooldown / cap / quiet-hours / scheduling logic
- `kb.py` — built-in evergreen LUNC + market knowledge and starter themes
- `store.py` — per-group JSON config/state store
- `ai_client.py` — OpenAI-compatible (Groq) chat wrapper
- `tests.py` — offline unit tests: `python3 tests.py`

"""Built-in knowledge + starter themes for TG Host.

The KB is EVERGREEN general knowledge shipped with the bot and used by every
group, underneath the per-group facts admins add with /host learn.
Strong LUNC (Terra Classic) focus plus the wider crypto market.

Rules baked in here:
- No project-specific promotion, no contract addresses, no live statistics
  (block heights, supplies, prices) — those go stale and the bot has no feed.
- Facts are phrased so they stay true over time.
"""

DEFAULT_KB = """TERRA CLASSIC (LUNC) — CORE FACTS
- Terra Classic is a Cosmos SDK proof-of-stake blockchain (chain-id columbus-5), run by its community and validators since 2022. It is the original Terra chain. Terra 2.0 and its LUNA token are a SEPARATE, newer chain — don't confuse LUNC with LUNA.
- LUNC is Terra Classic's native token: used for staking, governance voting, and paying transaction fees/gas.
- USTC is the chain's original stablecoin counterpart. It lost its dollar peg in May 2022 and now trades as a regular volatile token — it is NOT reliably worth $1.
- Staking: LUNC holders delegate to validators and earn staking rewards. Validators charge a commission (a % of your rewards) — when choosing one, people weigh commission, uptime, and how the validator votes on governance.
- Unbonding: undelegating takes 21 days. During unbonding the LUNC is locked and earns no rewards. Redelegating to a different validator is instant, but that amount then can't be redelegated or unbonded again for 21 days.
- Governance: stakers vote on proposals (parameter changes, software upgrades, community pool spends). Proposals need a deposit to reach a vote, and your voting power follows the validator you delegate to unless you vote yourself — your own vote overrides your validator's.
- Burn tax: Terra Classic charges a 1.5% on-chain tax on LUNC/USTC transfers (set by governance proposal 12223). 80% of that tax is burned — so 1.2% of every taxed transfer is destroyed forever — and the remainder supports the community pool and network/oracle rewards. That's the famous LUNC burn: supply shrinks a little with every taxed transaction, on top of periodic big burns by exchanges and the community.
- Tokens & ecosystem: beyond LUNC/USTC there is a community ecosystem of CW20 tokens (the Cosmos token standard), DEXs, NFT projects and tools built by independent teams. Always verify a token's real contract address on an explorer before buying — copycat tickers are common.
- Wallets: popular wallets for Terra Classic include Galaxy Station and Keplr (and others). Wallet safety rules never change: NEVER share your seed phrase or private key with anyone — no admin, validator, support agent or bot will ever ask for it. Anyone who does is a scammer. Admins never DM first with airdrops or "wallet fixes".
- Resources people in the community use: the Finder block explorer (finder.terraclassic.community), LuncScan (explorer + staking guides), LUNCDash (dashboards), and the Transparent Validator Chat on Telegram, where validators discuss governance and operations.

WIDER MARKET — GENERAL KNOWLEDGE ONLY
- BTC is the largest crypto asset and its share of total market value ("BTC dominance") is a common sentiment gauge. ETH and the other majors (large, long-lived layer-1 and exchange tokens) are the usual reference points for market mood: "risk-on" (people chasing growth/memecoins) vs "risk-off" (rotating to BTC/stablecoins).
- You know general crypto concepts cold: market cycles, halving, staking/yield basics, stablecoins, DEXs vs CEXs, bridges/IBC, memecoins as high-risk speculation, and the universal rule — never invest more than you can afford to lose, and do your own research.
"""

# --- Conversation starter themes -------------------------------------------
# Each theme: category ("lunc" | "market"), weight, theme (prompt seed for the
# AI), fallback (a ready-to-post question if AI is unavailable).
# Weights are tuned so LUNC ≈ 60% and the big market ≈ 40% of picks:
# 10 LUNC themes x weight 3 = 30, 10 market themes x weight 2 = 20.

STARTER_THEMES = [
    # --- LUNC / Terra Classic (60%) ---
    {"category": "lunc", "weight": 3,
     "theme": "Terra Classic governance — reading proposals and voting",
     "fallback": "🗳 Governance check-in: do you actually read proposals before they pass, or follow your validator's lead? What makes a proposal worth a YES for you?"},
    {"category": "lunc", "weight": 3,
     "theme": "Staking routines — claiming and re-staking rewards vs set-and-forget",
     "fallback": "🥩 Staking talk: are you a claim-and-restake regular, or set-and-forget? How often do you compound your LUNC rewards?"},
    {"category": "lunc", "weight": 3,
     "theme": "The LUNC burn — the 1.5% tax / 1.2% burn and what it means long term",
     "fallback": "🔥 Burn talk: every taxed LUNC transfer burns 1.2% of itself. Do you think the burn is still the chain's strongest story — or is utility catching up?"},
    {"category": "lunc", "weight": 3,
     "theme": "The 21-day unbonding wait — patience vs keeping funds liquid",
     "fallback": "⏳ 21 days unbonding — who's actually waited it out, and who keeps a liquid stack instead of staking it all?"},
    {"category": "lunc", "weight": 3,
     "theme": "What's building on Terra Classic — dApps, CW20 tokens, tools people have tried",
     "fallback": "🛠 Ecosystem roll call: tried any Terra Classic dApps or community tokens lately? What's actually worth a look (DYOR, as always)?"},
    {"category": "lunc", "weight": 3,
     "theme": "Choosing a validator — commission, uptime, voting record",
     "fallback": "🛡 Validator question: when you picked yours, what mattered most — commission, uptime, or how they vote?"},
    {"category": "lunc", "weight": 3,
     "theme": "Community memories — how long people have been in the LUNC community",
     "fallback": "💬 Community time: how long have you been around LUNC, and what's kept you here through the quiet stretches?"},
    {"category": "lunc", "weight": 3,
     "theme": "USTC — the other half of the classic pair and its role today",
     "fallback": "💵 USTC chat: do you hold any, and how do you see its role in the classic ecosystem these days?"},
    {"category": "lunc", "weight": 3,
     "theme": "Wallet security hygiene — dApp connections, approvals, seed safety",
     "fallback": "🔐 Security tip of the day: when did you last check which dApps your wallet is still connected to? Five-minute cleanup, real peace of mind. (And as always: nobody legit will EVER ask for your seed phrase.)"},
    {"category": "lunc", "weight": 3,
     "theme": "Terra Classic history and community pride — a chain kept alive by its people",
     "fallback": "📖 Classic pride: this chain is still here because its community refused to let it die. What's your favorite chapter of the LUNC story so far?"},

    # --- Big market (40%) ---
    {"category": "market", "weight": 2,
     "theme": "BTC dominance and what it says about market sentiment",
     "fallback": "₿ BTC dominance: when the king takes market share, alts usually feel it. Are you watching dominance right now, or ignoring it?"},
    {"category": "market", "weight": 2,
     "theme": "Which crypto sector people are watching this week — L1s, memecoins, RWA, AI tokens",
     "fallback": "👀 Sector watch: L1s, memecoins, RWA, AI tokens… which corner of the market has your attention this week, and why?"},
    {"category": "market", "weight": 2,
     "theme": "Macro mood — risk-on vs risk-off and how it changes behaviour",
     "fallback": "🌦 Market mood check: does it feel risk-on or risk-off out there to you right now? What's giving it away?"},
    {"category": "market", "weight": 2,
     "theme": "ETH and the majors — which large-cap has people's attention besides BTC",
     "fallback": "💠 Beyond BTC: which major has your attention these days — ETH, or another big name — and what's the story with it?"},
    {"category": "market", "weight": 2,
     "theme": "Market cycles — where in the cycle are we, and what are the tells",
     "fallback": "🔄 Cycle talk: where do you think we are in the market cycle right now — and what are the signs you're reading?"},
    {"category": "market", "weight": 2,
     "theme": "Trading/staking habits and rules people wish they'd learned earlier",
     "fallback": "📏 Hard-earned rules: what's one habit or rule you wish you'd followed from day one in crypto?"},
    {"category": "market", "weight": 2,
     "theme": "Underrated narratives — sectors or ideas the crowd is sleeping on",
     "fallback": "💤 Sleeper narratives: what's one corner of crypto you think the crowd is underrating right now?"},
    {"category": "market", "weight": 2,
     "theme": "Stablecoins — parking value, earning yield, staying flexible",
     "fallback": "🏦 Stablecoin habits: do you keep a stables stack for dips and flexibility, or stay fully deployed?"},
    {"category": "market", "weight": 2,
     "theme": "The week's biggest crypto headline and whether it actually matters",
     "fallback": "📰 Headline check: what's the biggest crypto story you've seen this week — and does it actually change anything, or is it noise?"},
    {"category": "market", "weight": 2,
     "theme": "Learning curve — a crypto concept that finally clicked for you",
     "fallback": "🧠 Level-up moment: what's one crypto concept that took you ages to understand — and finally clicked?"},
]


def theme_weight_totals() -> dict:
    """Total picker weight per category (used by tests to assert ~60/40)."""
    totals = {}
    for t in STARTER_THEMES:
        totals[t["category"]] = totals.get(t["category"], 0) + t["weight"]
    return totals

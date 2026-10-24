"""Built-in knowledge + starter themes for TG Host.

The KB is EVERGREEN general knowledge shipped with the bot and used by every
group, underneath the per-group facts admins add with /host learn.
Strong LUNC (Terra Classic) focus plus the wider crypto market.

Rules baked in here:
- No project-specific promotion, no contract addresses, no live statistics
  (supplies, prices) — those go stale and the bot has no feed.
- Facts are phrased so they stay true over time, EXCEPT the explicitly dated
  governance section below: those facts carry their as-of date, and the
  system prompt teaches the bot to treat them as stale once their dates pass
  and to point users at Finder / LuncScan / validator.info to verify live state.
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

TERRA CLASSIC — HISTORY (FACTUAL, NEUTRAL)
- May 2022: the original Terra stablecoin UST lost its dollar peg and the original LUNA token hyperinflated in the collapse that followed. The ecosystem then forked: a brand-new chain, Terra 2.0, launched with a new LUNA token, while the ORIGINAL chain kept running as Terra Classic (chain-id columbus-5) with LUNC and USTC. So: LUNC = the original chain's token, LUNA = the newer chain's token. They are not the same asset and their prices have nothing to do with each other.
- Terra Classic today is run by its community and validators through on-chain governance — there is no company in charge. Upgrades, parameter changes and community-pool spends all go through governance proposals.

TERRA CLASSIC — GOVERNANCE MECHANICS
- How a proposal works: it needs a deposit to enter the voting period; then stakers vote YES, NO, ABSTAIN, or NO WITH VETO. Your own vote always overrides your validator's vote — if you don't vote, your stake follows your validator.
- Quorum: at least 40% of bonded (staked) LUNC must vote, or the proposal fails regardless of the YES share.
- Pass: a majority of non-abstain votes must be YES. Veto: if more than 33.4% of non-abstain votes are NO WITH VETO, the proposal is vetoed and rejected (and its deposit can be burned).
- ABSTAIN counts toward quorum but not toward the pass/veto result — so a proposal can have a huge YES share and still fail if turnout is too low.

TERRA CLASSIC — DATED STATE (AS OF OCTOBER 24, 2026 — TREAT AS STALE AFTER ITS DATES)
- Proposal 12233 PASSED: the v4.1.1 software upgrade (plan name v14_4) at block height 31010600, expected around midday ET on Monday, October 26, 2026. Nodes that have not upgraded by that height will halt — that is why validators stage the new binary in advance. After that date, check Finder or validator.info for whether the upgrade completed.
- Proposal 12234 IN VOTING until Monday, October 26, 2026, 6:52 PM ET: it would restrict CosmWasm code uploads from Everybody to Nobody (an empty allow-list). Instantiating code that is ALREADY stored would stay open to everybody — only new uploads would need a governance proposal. The on-chain text has NO sunset or expiry date, so "temporary" is only an intention: restoring open uploads would itself need a new governance proposal.
- 12234's status as of the evening of October 23, 2026: roughly 26.9% turnout against the 40% quorum, with YES at about 99% of non-abstain votes. So the binding constraint is TURNOUT, not YES support — if quorum is not reached it fails even though almost everyone who voted said yes. Do not describe it as sure to pass; after October 26, 2026, verify the actual outcome on Finder or validator.info instead of repeating this snapshot.
- Verifying live chain state: Finder (finder.terraclassic.community) for transactions, proposals and contract code; LuncScan (luncscan.com) for explorer data and staking guides; validator.info for validators and governance; the chain's own tax parameters live at the LCD endpoint /terra/tax/v1beta1/params. Never quote the old treasury tax_rate endpoint — it is dead.

TERRA CLASSIC — ECOSYSTEM & TOOLS
- CW20 tokens are Terra Classic's Cosmos token standard — community tokens built as smart contracts, distinct from native LUNC (which lives at the chain level, not in a contract). A CW20's real identity is its contract address: always verify it on Finder before buying, because copycat tickers with the same name/symbol are common.
- Swaps and DEXs: community-built decentralised exchanges let you trade LUNC, USTC and CW20 tokens peer-to-contract, with prices set by liquidity pools rather than an order book. Thin pools mean high slippage — a small trade can move the price a lot.
- IBC (Inter-Blockchain Communication) is the Cosmos standard that lets tokens move between independent chains. An IBC transfer leaves one chain and arrives on another; each hop has its own fees, timing and risks, and the token's origin chain matters for what it is actually worth.
- Wallets and explorers people use: Galaxy Station, Keplr, Finder, LuncScan, validator.info, and the Transparent Validator Chat on Telegram (t.me/transparentvalidatorchat), where validators discuss governance and operations.

SAFETY — SCAM PATTERNS TO NAME PLAINLY
- Fake airdrops: random "you won / claim now" messages with a link. Real projects do not airdrop to strangers who connect a wallet to an unknown site.
- Impersonator admins: scammers copy admin names/photos and DM first offering help, airdrops or "wallet fixes". Real admins never DM first about your wallet.
- "Send to double it": anyone promising to send back double what you send is stealing, every time.
- Fake support: nobody legitimate — no admin, validator, support agent or bot — will ever ask for your seed phrase, private key, or remote access to your device. Anyone who does is a scammer, full stop.
- Before interacting with any token, dApp or contract: verify the contract address on Finder, check the project's own official channels (not a forwarded screenshot), and be extra suspicious of urgency ("claim in 1 hour or lose it").

WIDER MARKET — DEEPER GENERAL KNOWLEDGE
- BTC basics: the first and largest crypto asset, with a fixed issuance schedule — new supply is cut roughly every four years at the "halving". It is the market's usual bellwether: when BTC moves, most of the market follows, and BTC dominance (its share of total crypto market value) is a common sentiment gauge.
- ETH basics: the largest smart-contract platform; ETH pays for gas on its network. The "majors" are the large, long-lived layer-1 and exchange tokens people use as reference points for market mood.
- Reading a market properly: price is just the last trade. Market cap = price x circulating supply — a coin priced at a fraction of a cent is not "cheap" if its supply is enormous. Volume = how much value actually traded — thin volume means a few trades can swing the price. Liquidity = how much can trade without moving the price. Low liquidity plus large holders equals high volatility.
- Market cycles and volatility: crypto moves in cycles of enthusiasm and retrenchment; sharp rises and sharp drawdowns are both normal. Volatility is not a bug in this market — position sizing and never investing more than you can afford to lose are how people survive it.
- Stablecoins: tokens meant to track a fiat currency (usually USD). But a peg is a promise, not a law of physics — USTC itself broke its peg in May 2022. Before trusting a stablecoin, ask what backs it and how the peg is defended; never assume $1.
- DeFi in plain language: a DEX trades without a central company, using liquidity pools. Liquidity providers (LPs) deposit pairs of tokens into a pool and earn trading fees. Impermanent loss: if the two pooled tokens move apart in price, withdrawing can leave you with less value than if you had simply held both tokens — the fees you earned may or may not make up for it.
- DYOR with primary sources: prefer the explorer (Finder), the chain's own parameters and governance pages, and a project's docs and code over influencers, screenshots and forwarded claims. If a claim cannot be checked on a primary source, say so.

KNOWLEDGE DATE — READ THIS FIRST WHEN ANSWERING DATED QUESTIONS
- This built-in knowledge is current as of October 24, 2026. Anything time-sensitive in it — proposal outcomes, upgrade timing, tax parameters, ecosystem facts — may have changed since then. When asked about live or recent state, give the dated fact if you have one, say plainly that your knowledge is dated to October 24, 2026, and point the user to Finder, LuncScan or validator.info to verify the live state. Never guess at an outcome that may already have happened.
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
    {"category": "lunc", "weight": 3,
     "theme": "Verifying before you trust — checking token contracts on Finder, copycat tickers",
     "fallback": "🔍 Trust-but-verify: before you buy any community token, do you check its real contract address on Finder? Copycat tickers are everywhere — what's your verification habit?"},
    {"category": "lunc", "weight": 3,
     "theme": "Terra Classic utility beyond the burn — what would bring outsiders to the chain",
     "fallback": "🌱 Beyond the burn: the burn gets attention, but what would actually make outsiders USE Terra Classic? What utility would you most want to see built here?"},

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
    {"category": "market", "weight": 2,
     "theme": "Reading a market properly — price vs market cap vs volume vs liquidity",
     "fallback": "📊 Reading the market: price is just the last trade — market cap, volume and liquidity tell the real story. Which of those do you check first before touching a token?"},
    {"category": "market", "weight": 2,
     "theme": "Impermanent loss in plain language — LP lessons learned the hard way",
     "fallback": "💧 Impermanent loss, plainly: pooled tokens drifting apart can leave you worse off than just holding. Ever been LP-bitten — did the fees make up for it?"},
]


def theme_weight_totals() -> dict:
    """Total picker weight per category (used by tests to assert ~60/40)."""
    totals = {}
    for t in STARTER_THEMES:
        totals[t["category"]] = totals.get(t["category"], 0) + t["weight"]
    return totals

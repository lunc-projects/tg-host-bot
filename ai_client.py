import os
import httpx

import budget


def api_key() -> str:
    """The AI key from whichever env name the deployment uses.

    Deployments have used different names over time, so accept them all:
    AI_API_KEY first, then OPENAI_API_KEY, then GROQ_API_KEY. Resolved on
    every call (not frozen at import) so the answer is never stale."""
    return (os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
            or os.getenv("GROQ_API_KEY") or "")


AI_API_KEY = api_key()  # import-time snapshot; api_key() above is the live check
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
# Groq quick-start: AI_BASE_URL=https://api.groq.com/openai/v1 (the default above),
# AI_MODEL=openai/gpt-oss-120b (default) — an OpenAI-compatible key also works.

# Raised to 600 (owner, Oct 28): a little more room per answer while the
# daily pot still bounds the total.
MAX_TOKENS = 600

# Why the most recent chat() call produced no reply:
# None (success / not called yet) | "unconfigured" | "pot" | "error".
# Callers MUST use this to pick an honest user-facing note — a pot-empty
# or API-error failure is NOT "isn't configured".
_last_failure = None


def last_failure():
    return _last_failure


def configured() -> bool:
    return bool(api_key())


async def chat(messages, temperature=0.6) -> str | None:
    global _last_failure
    key = api_key()
    if not key:
        _last_failure = "unconfigured"
        print("AI skipped: no API key in env "
              "(AI_API_KEY / OPENAI_API_KEY / GROQ_API_KEY all unset)")
        return None
    # Daily pot: reserve the call's estimated cost first. A blocked call
    # returns None without spending anything; callers check last_failure()
    # (or budget.exhausted()) to tell the pot-empty case apart from errors.
    estimate = budget.estimate_input(messages) + MAX_TOKENS
    if not budget.reserve(estimate):
        _last_failure = "pot"
        print(f"AI skipped: daily pot exhausted "
              f"(spent {budget.spent()} of {budget.DAILY_TOKEN_BUDGET})")
        return None
    try:
        async with httpx.AsyncClient(timeout=60, proxy=os.getenv('OUTBOUND_PROXY') or None) as c:
            r = await c.post(f"{AI_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": AI_MODEL, "messages": messages, "temperature": temperature, "max_tokens": MAX_TOKENS})
            r.raise_for_status()
            out = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        budget.refund(estimate)
        _last_failure = "error"
        print(f"AI error: {type(e).__name__}: {e}")
        return None
    # Settle: give back the unused part of the output reservation.
    budget.refund(max(0, MAX_TOKENS - len(out) // 4))
    _last_failure = None
    return out

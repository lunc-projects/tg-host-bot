import os
import httpx

import budget

AI_API_KEY = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or ""
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
# Groq quick-start: AI_BASE_URL=https://api.groq.com/openai/v1 (the default above),
# AI_MODEL=openai/gpt-oss-120b (default) — an OpenAI-compatible key also works.

# Minimized so the daily pot lasts: short answers.
MAX_TOKENS = 500

def configured() -> bool:
    return bool(AI_API_KEY)

async def chat(messages, temperature=0.6) -> str | None:
    if not AI_API_KEY:
        return None
    # Daily pot: reserve the call's estimated cost first. A blocked call
    # returns None without spending anything; callers check
    # budget.exhausted() to tell the pot-empty case apart from other errors.
    estimate = budget.estimate_input(messages) + MAX_TOKENS
    if not budget.reserve(estimate):
        return None
    try:
        async with httpx.AsyncClient(timeout=60, proxy=os.getenv('OUTBOUND_PROXY') or None) as c:
            r = await c.post(f"{AI_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {AI_API_KEY}"},
                json={"model": AI_MODEL, "messages": messages, "temperature": temperature, "max_tokens": MAX_TOKENS})
            r.raise_for_status()
            out = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        budget.refund(estimate)
        print(f"AI error: {e}")
        return None
    # Settle: give back the unused part of the output reservation.
    budget.refund(max(0, MAX_TOKENS - len(out) // 4))
    return out

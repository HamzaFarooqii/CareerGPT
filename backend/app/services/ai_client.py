# ============================================================
# AI Client — Multi-Provider LLM Abstraction Layer
# ============================================================
# This module provides a single function `ai_generate(prompt)`
# that works with Groq, Gemini, or OpenRouter transparently.
# Routes will call this instead of directly using any SDK.
# ============================================================

import os
from app.config.settings import settings


def _call_groq(prompt: str, system: str = "") -> str:
    """Call Groq API (OpenAI-compatible). Free: 14,400 req/day."""
    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str, system: str = "") -> str:
    """Call Google Gemini API. Free: 1,500 req/day."""
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.LLM_MODEL)
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = model.generate_content(full_prompt)
    return response.text


def _call_openrouter(prompt: str, system: str = "") -> str:
    """Call OpenRouter API (OpenAI-compatible). Many free models."""
    import httpx
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://careerpilot.ai",
            "X-Title": "CareerPilot AI",
        },
        json={
            "model": settings.OPENROUTER_MODEL,
            "messages": messages,
            "max_tokens": 4096,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


async def ai_generate(prompt: str, system: str = "") -> str:
    """
    Generate text using the configured AI provider.
    Automatically falls back to other providers on failure.

    Args:
        prompt: The user prompt
        system: Optional system/instruction context

    Returns:
        Generated text string
    """
    provider = settings.AI_PROVIDER
    errors = []

    # Try primary provider
    try:
        if provider == "groq":
            return _call_groq(prompt, system)
        elif provider == "gemini":
            return _call_gemini(prompt, system)
        elif provider == "openrouter":
            return _call_openrouter(prompt, system)
    except Exception as e:
        errors.append(f"{provider}: {e}")
        print(f"⚠️ Primary AI provider '{provider}' failed: {e}")

    # Auto-fallback chain: groq → gemini → openrouter
    fallbacks = [
        ("groq", _call_groq),
        ("gemini", _call_gemini),
        ("openrouter", _call_openrouter),
    ]

    for name, fn in fallbacks:
        if name == provider:
            continue  # Already tried
        try:
            print(f"🔄 Trying fallback provider: {name}")
            return fn(prompt, system)
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"⚠️ Fallback '{name}' also failed: {e}")

    raise RuntimeError(
        f"All AI providers failed. Errors: {'; '.join(errors)}\n"
        f"Please check your API keys in backend/.env"
    )

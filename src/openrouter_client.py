"""Quota-aware HTTP client for OpenRouter chat completions.

Tries each configured model in order until one returns a usable response.
Mutates the supplied QuotaState in place so callers can persist usage after
a wake cycle. Raises QuotaExhausted when no calls remain locally or when
every model returns HTTP 429.
"""

from __future__ import annotations

import httpx

from src.memory import QuotaState


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 30.0


class QuotaExhausted(Exception):
    """Raised when the local quota counter is spent or the server returns 429."""


class OpenRouterClient:
    """Wraps OpenRouter chat completions with a local quota counter and model fallback."""

    def __init__(
        self,
        api_key: str,
        models: list[str],
        quota_state: QuotaState,
    ) -> None:
        self.api_key = api_key
        self.models = list(models)
        self.quota_state = quota_state

    def complete(self, prompt: str, max_tokens: int = 1000) -> str:
        """Run a chat completion against the configured models in order.

        Decrements quota_state.calls_made before each attempt. Raises
        QuotaExhausted if the local counter is already at the limit, or if
        every configured model returns HTTP 429 or an empty success body.
        Returns the assistant's text content on first success.
        """
        if not self.models:
            raise QuotaExhausted("no models configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_rate_limited = True

        for model in self.models:
            if self.quota_state.calls_made >= self.quota_state.calls_limit:
                raise QuotaExhausted("local quota counter exhausted")

            self.quota_state.calls_made += 1

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }

            try:
                response = httpx.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                )
            except httpx.HTTPError:
                all_rate_limited = False
                continue

            if response.status_code == 429:
                continue

            if response.status_code >= 400:
                all_rate_limited = False
                continue

            text = _extract_text(response)
            if text:
                return text

            all_rate_limited = False

        if all_rate_limited:
            raise QuotaExhausted("all configured models returned 429")
        raise QuotaExhausted("no model returned usable content")


def _extract_text(response: httpx.Response) -> str:
    """Pull the assistant message text out of an OpenRouter response body."""
    try:
        data = response.json()
    except ValueError:
        return ""

    choices = data.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""

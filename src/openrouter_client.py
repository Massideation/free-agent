"""Quota-aware HTTP client for OpenRouter chat completions.

Tries each configured model in order until one returns a usable response.
When every configured model fails and the dynamic free fallback is enabled
(config/settings.yaml, openrouter.models_dynamic_free_fallback), fetches
the live OpenRouter model list and tries up to three currently-free models
before giving up. Mutates the supplied QuotaState in place so callers can
persist usage after a wake cycle. Raises QuotaExhausted when no calls
remain locally or when every model returns HTTP 429.
"""

from __future__ import annotations

import logging

import httpx

from src.memory import QuotaState


logger = logging.getLogger(__name__)


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEFAULT_TIMEOUT_SECONDS = 30.0

# Hard cap on dynamic-fallback attempts within one logical call, on top of
# the configured list. Keeps a fully rotted free pool from turning one wake
# into a long walk of the entire public model catalog.
DYNAMIC_FALLBACK_MAX_MODELS = 3


class QuotaExhausted(Exception):
    """Raised when the local quota counter is spent or the server returns 429."""


class OpenRouterClient:
    """Wraps OpenRouter chat completions with a local quota counter and model fallback."""

    def __init__(
        self,
        api_key: str,
        models: list[str],
        quota_state: QuotaState,
        dynamic_free_fallback: bool = True,
    ) -> None:
        self.api_key = api_key
        self.models = list(models)
        self.quota_state = quota_state
        self.dynamic_free_fallback = bool(dynamic_free_fallback)
        # Outcome counters for this client's lifetime (one wake). The health
        # module reads these after the task runs: successful_calls counts
        # logical calls that returned usable text (from any model, configured
        # or dynamic); exhausted_calls counts logical calls where every model
        # failed. Local quota exhaustion and an empty models list are not
        # model failures and touch neither counter.
        self.successful_calls = 0
        self.exhausted_calls = 0

    def complete(self, prompt: str, max_tokens: int = 1000) -> str:
        """Run a chat completion against the configured models in order.

        Tries every configured model in turn, moving to the next on ANY
        failure: a transport error (timeout, connection drop), HTTP 429, any
        other non-200 status, or a 200 with an empty/unparseable body. The
        first model that returns usable text wins. When every configured
        model has failed and dynamic_free_fallback is on, up to
        DYNAMIC_FALLBACK_MAX_MODELS currently-free models from the live
        OpenRouter list are tried the same way. Only when all of that has
        failed does this raise QuotaExhausted, with a message summarising the
        real per-model failures so the private log shows true diagnostics.

        Increments quota_state.calls_made once per logical call. Raises
        QuotaExhausted immediately if the local counter is already spent.
        """
        if not self.models:
            raise QuotaExhausted("no models configured")

        # The daily budget counts one unit per logical call (one wake's
        # thinking), NOT per model attempt. Trying several fallback models
        # within a single call must not multiply the count, otherwise one
        # failing wake that walks the whole fallback list would exhaust the
        # daily budget by itself.
        if self.quota_state.calls_made >= self.quota_state.calls_limit:
            raise QuotaExhausted(
                "local quota counter exhausted (daily call limit reached)"
            )
        self.quota_state.calls_made += 1

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # One human-readable diagnostic per attempted model, e.g.
        # "meta-llama/...:free -> HTTP 429". Surfaced on total failure.
        failures: list[str] = []

        for model in self.models:
            text = self._try_model(model, prompt, max_tokens, headers, failures)
            if text:
                if failures:
                    logger.info(
                        "openrouter model %s succeeded after %d failure(s)",
                        model,
                        len(failures),
                    )
                self.successful_calls += 1
                return text

        # Every configured model failed. With the fallback enabled, fetch the
        # live model list and try up to DYNAMIC_FALLBACK_MAX_MODELS currently
        # free models that were not already tried this call. With the flag
        # off this block is skipped entirely and behavior matches today's.
        if self.dynamic_free_fallback:
            for model in self._fetch_free_models(exclude=set(self.models)):
                text = self._try_model(
                    model, prompt, max_tokens, headers, failures
                )
                if text:
                    logger.warning(
                        "openrouter dynamic free-model fallback engaged: all "
                        "configured models failed; %s answered",
                        model,
                    )
                    self.successful_calls += 1
                    return text

        self.exhausted_calls += 1
        summary = "; ".join(failures) if failures else "no models attempted"
        raise QuotaExhausted(f"all models failed: {summary}")

    def _try_model(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        headers: dict,
        failures: list[str],
    ) -> str:
        """Attempt one model. Returns its text, or "" after recording the failure.

        Exactly today's per-model behavior, factored out so the dynamic
        fallback walk reuses the same request, timeout, diagnostics, and
        logging idioms as the configured-list walk.
        """
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
        except httpx.HTTPError as exc:
            reason = f"transport error: {type(exc).__name__}: {exc}"
            failures.append(f"{model} -> {reason}")
            logger.warning("openrouter model %s failed: %s", model, reason)
            return ""

        if response.status_code != 200:
            reason = f"HTTP {response.status_code}"
            body = _error_snippet(response)
            if body:
                reason = f"{reason}: {body}"
            failures.append(f"{model} -> {reason}")
            logger.warning("openrouter model %s failed: %s", model, reason)
            return ""

        text = _extract_text(response)
        if text:
            return text

        reason = "empty or unparseable response body"
        failures.append(f"{model} -> {reason}")
        logger.warning("openrouter model %s failed: %s", model, reason)
        return ""

    def _fetch_free_models(self, exclude: set[str]) -> list[str]:
        """Fetch the live model list; return up to 3 free, untried model ids.

        Free means pricing.prompt == "0" AND pricing.completion == "0" AND
        every other pricing field (request, image, web_search,
        internal_reasoning, anything OpenRouter adds later) is also the
        string "0", compared as strings per the OpenRouter schema. A missing
        or malformed pricing block is treated as NOT free: never guess a
        model is free.
        Order follows the listing. Never raises; any transport, HTTP, or
        payload problem degrades to an empty list so the caller falls through
        to the normal all-models-failed error.
        """
        try:
            response = httpx.get(
                OPENROUTER_MODELS_URL, timeout=DEFAULT_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "openrouter model list fetch failed: transport error: %s",
                type(exc).__name__,
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "openrouter model list fetch failed: HTTP %d",
                response.status_code,
            )
            return []

        try:
            data = response.json()
        except ValueError:
            logger.warning("openrouter model list fetch failed: not JSON")
            return []

        entries = data.get("data") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            logger.warning(
                "openrouter model list fetch failed: unexpected payload shape"
            )
            return []

        free: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            model_id = entry.get("id")
            if not isinstance(model_id, str) or not model_id.strip():
                continue
            if model_id in exclude:
                continue
            pricing = entry.get("pricing")
            if not isinstance(pricing, dict):
                continue
            if pricing.get("prompt") != "0" or pricing.get("completion") != "0":
                continue
            # The pricing object also carries per-request, image, web search,
            # and reasoning rates. Any nonzero value anywhere means the model
            # can bill; only an all-zero pricing block counts as free.
            if any(value != "0" for value in pricing.values()):
                continue
            free.append(model_id)
            if len(free) >= DYNAMIC_FALLBACK_MAX_MODELS:
                break
        return free


def _error_snippet(response: httpx.Response, max_len: int = 200) -> str:
    """Best-effort short description of a non-200 body for diagnostics.

    Prefers OpenRouter's JSON {"error": {"message": ...}} shape, falls back
    to raw text. Always returns a trimmed, length-capped string and never
    raises, so it is safe to call on any failed response.
    """
    try:
        data = response.json()
    except ValueError:
        snippet = (response.text or "").strip()
        return snippet[:max_len]

    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            message = err.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:max_len]
        if isinstance(err, str) and err.strip():
            return err.strip()[:max_len]
    return str(data)[:max_len]


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

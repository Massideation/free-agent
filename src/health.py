"""Quiet-Evo guard: notices when the Evo cannot think and tells the operator.

Tracks consecutive all-models-failed wakes in state/health.json:

    {"consecutive_model_failures": int, "last_nudge_at": "<ISO 8601 UTC>" or null}

written with the same atomic helper as the other state files. After two
such wakes in a row the operator gets one short plain-language nudge over a
channel that is already configured: email is tried first, and Telegram is a
true fallback, used when email is not configured or when the email send
fails, else nothing. While the failures continue, the nudge repeats only
after RENUDGE_AFTER_DAYS so the operator is reminded, not spammed.

Unlike the fail-stop state files, health.json is deliberately forgiving: it
is a monitoring counter, not agent history. A corrupt file resets to
defaults (logged privately) rather than raising, because failing the wake
over its own health counter would deepen the exact outage this module
exists to surface.

observe_wake never raises. wake.py calls it only on a live wake, after the
task has run; --dry-run exits long before this module is touched, so a
dry-run never reads, writes, or sends anything here.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from src import logger, memory
from src.memory import State, StateFileCorrupt


HEALTH_FILE = memory.STATE_DIR / "health.json"

# Nudge the operator once the Evo has produced no model output for this many
# consecutive live wakes.
NUDGE_AFTER_FAILURES = 2
# While the failures continue, nudge again only after this many days.
RENUDGE_AFTER_DAYS = 7

_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _default_health() -> dict:
    return {"consecutive_model_failures": 0, "last_nudge_at": None}


def _load_health(today: str) -> dict:
    """Read state/health.json, degrading to defaults on any problem.

    Catches the StateFileCorrupt that memory._read_json raises so a corrupt
    counter file can never stop a wake; at worst one nudge arrives a couple
    of wakes later than it should have.
    """
    try:
        raw = memory._read_json(HEALTH_FILE)
    except StateFileCorrupt:
        logger.write_private(
            today,
            "health.json is corrupt; resetting the failure counter "
            "(monitoring data only, no agent history lost)",
        )
        return _default_health()
    except Exception as exc:
        logger.write_private(
            today, f"health.json read failed: {type(exc).__name__}"
        )
        return _default_health()

    data = _default_health()
    if isinstance(raw, dict):
        try:
            data["consecutive_model_failures"] = max(
                0, int(raw.get("consecutive_model_failures") or 0)
            )
        except (TypeError, ValueError):
            pass
        last = raw.get("last_nudge_at")
        if isinstance(last, str) and last.strip():
            data["last_nudge_at"] = last.strip()
    return data


def _save_health(data: dict, today: str) -> None:
    """Write state/health.json atomically. A failed write is logged, never raised."""
    try:
        memory._atomic_write_json(HEALTH_FILE, data)
    except Exception as exc:
        logger.write_private(
            today, f"health.json write failed: {type(exc).__name__}"
        )


def _nudge_message(count: int) -> str:
    """Short plain-language operator nudge. Hand-authored, no em dashes."""
    return (
        f"Your Evo could not think for {count} wakes in a row: every model "
        "call failed. Most likely the free model list rotated. Check the "
        "Actions log, or update the models list in config/settings.yaml."
    )


def _renudge_due(last_nudge_at: Optional[str]) -> bool:
    """True when no nudge was ever sent or the last one is over 7 days old.

    An unparseable timestamp counts as due: one extra nudge beats a silent
    Evo the operator never hears about.
    """
    if not last_nudge_at:
        return True
    try:
        last = datetime.strptime(str(last_nudge_at), _TS_FMT).replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        return True
    return datetime.now(timezone.utc) - last > timedelta(days=RENUDGE_AFTER_DAYS)


def _send_nudge(state: State, message: str, today: str) -> bool:
    """Send one nudge through an already-configured private channel.

    Reuses the existing helpers: send_operator_email when email is
    configured, then the Telegram sendMessage helper as a fallback when a
    bot token and a known operator chat exist, else nothing. Telegram is a
    real fallback: a failed or errored email send falls through to it
    instead of giving up, so a broken Resend key cannot silence an operator
    with a working bot. The Telegram body carries the same AI-agent
    disclosure footer as every other outbound Telegram message. Returns True
    only when a send actually went out, so a failed attempt does not stamp
    last_nudge_at and the next failing wake retries. Never raises; every
    miss is logged privately.
    """
    try:
        if os.environ.get("RESEND_API_KEY") and os.environ.get("OPERATOR_EMAIL"):
            try:
                from src.emailer import send_operator_email

                outcome = send_operator_email(
                    "Your Evo could not think this week", message
                )
                if outcome.get("sent"):
                    return True
                logger.write_private(
                    today,
                    f"health nudge email not sent: {outcome.get('reason', 'unknown')}",
                )
            except Exception as exc:
                logger.write_private(
                    today, f"health nudge email failed: {type(exc).__name__}"
                )

        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = getattr(getattr(state, "telegram", None), "last_chat_id", None)
        if token and chat_id is not None:
            from src.logger import DISCLOSURE_FOOTER
            from src.tasks.respond_to_telegram import _send_message

            _send_message(token, chat_id, f"{message}\n\n{DISCLOSURE_FOOTER}")
            return True

        logger.write_private(
            today,
            "health nudge skipped: no email or telegram channel available",
        )
        return False
    except Exception as exc:
        logger.write_private(
            today, f"health nudge failed: {type(exc).__name__}"
        )
        return False


def observe_wake(state: State, client, today: str) -> None:
    """Record this live wake's model outcome; nudge the operator if quiet.

    Reads the outcome counters OpenRouterClient tracked during this wake:
    successful_calls (logical calls that returned usable text) and
    exhausted_calls (logical calls where every model failed). A wake with
    no client, or with no model calls at all (a rest wake), changes
    nothing, including the file's mtime. The first successful call resets
    the counter and the nudge timestamp, so a fresh incident later nudges
    at NUDGE_AFTER_FAILURES again. A wake where every model call failed
    increments the counter; at NUDGE_AFTER_FAILURES one nudge goes out,
    repeated only after RENUDGE_AFTER_DAYS while the failures continue.
    Never raises: a failure anywhere in here must not fail the wake.
    """
    try:
        if client is None:
            return
        successes = int(getattr(client, "successful_calls", 0) or 0)
        total_failures = int(getattr(client, "exhausted_calls", 0) or 0)

        if successes > 0:
            data = _load_health(today)
            if data["consecutive_model_failures"] or data["last_nudge_at"]:
                logger.write_private(
                    today,
                    "model calls recovered after "
                    f"{data['consecutive_model_failures']} all-failed wake(s)",
                )
                _save_health(_default_health(), today)
            return

        if total_failures == 0:
            return

        data = _load_health(today)
        data["consecutive_model_failures"] += 1
        count = data["consecutive_model_failures"]
        if count >= NUDGE_AFTER_FAILURES and _renudge_due(data["last_nudge_at"]):
            if _send_nudge(state, _nudge_message(count), today):
                data["last_nudge_at"] = datetime.now(timezone.utc).strftime(
                    _TS_FMT
                )
        _save_health(data, today)
    except Exception as exc:
        try:
            logger.write_private(
                today, f"health.observe_wake failed: {type(exc).__name__}"
            )
        except Exception:
            pass

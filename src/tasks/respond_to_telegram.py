"""respond_to_telegram task.

Polls the Telegram Bot API for new private messages, drafts a reply via
OpenRouter, runs the style guard, and posts a plain-text reply via
sendMessage. Each reply ends with the PRD section 11.1 disclosure footer.
Persists the highest acknowledged update id to state.telegram.last_update_id
so messages are never reprocessed.

Skips cleanly when there is no token, no LLM client, or no new messages.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

from src.executor import TaskResult
from src.logger import DISCLOSURE_FOOTER
from src.memory import State
from src.openrouter_client import OpenRouterClient
from src.style_guard import check as style_check


TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGES_PER_WAKE = 10


def _get_token() -> Optional[str]:
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def _get_updates(token: str, offset: int) -> list[dict]:
    url = f"{TELEGRAM_API}/bot{token}/getUpdates"
    params = {
        "offset": offset,
        "timeout": 0,
        "allowed_updates": ["message"],
    }
    resp = httpx.get(url, params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json().get("result", [])


def _send_message(token: str, chat_id: int, text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    resp = httpx.post(url, json=payload, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


def _draft_reply(client: OpenRouterClient, message: dict) -> str:
    text = (message.get("text") or "").strip()
    sender = message.get("from", {}) or {}
    first_name = sender.get("first_name", "unknown")
    user_id = sender.get("id", 0)

    prompt = (
        "You are an autonomous AI agent. Someone sent you a private message "
        "on Telegram. Reply to them directly.\n"
        "\n"
        "Strict rules:\n"
        "- No em dashes anywhere.\n"
        "- Avoid the words delve, leverage (as verb), navigate (as verb), "
        "robust, ensure, furthermore, moreover, and the phrase in conclusion.\n"
        "- Do not invent facts about yourself, your operator, your revenue, "
        "or your offer.\n"
        "- Be direct. One to three short paragraphs maximum.\n"
        "- If you do not know something, say so plainly.\n"
        "- Do not impersonate your operator.\n"
        "- Do not promise future actions you cannot guarantee from one wake.\n"
        "- Plain text only. No Markdown formatting.\n"
        "\n"
        f"Sender first name: {first_name}\n"
        f"Sender Telegram user id: {user_id}\n"
        f"Message text:\n{text}\n"
        "\n"
        "Write only the reply text. A disclosure footer is appended "
        "automatically."
    )

    return client.complete(prompt, max_tokens=600).strip()


def run(state: State, client: Optional[OpenRouterClient]) -> TaskResult:
    if state.telegram.operator_telegram_user_id is None:
        return TaskResult(
            success=True,
            summary=(
                "respond_to_telegram skipped: operator_telegram_user_id is "
                "not set in state/telegram.json. The agent will not read "
                "Telegram messages until you set your Telegram user_id "
                "manually."
            ),
            public_summary=(
                "The agent did not check its private DMs today. "
                "Configuration step pending on the operator side."
            ),
            model_calls_used=0,
        )

    token = _get_token()
    if not token:
        return TaskResult(
            success=True,
            summary="respond_to_telegram skipped: TELEGRAM_BOT_TOKEN is not set",
            public_summary=(
                "The agent has no private DM channel wired yet. Once a "
                "Telegram bot token is added the agent will start answering "
                "direct messages."
            ),
            model_calls_used=0,
        )

    if client is None:
        return TaskResult(
            success=True,
            summary="respond_to_telegram skipped: no language model available",
            public_summary=(
                "The agent checked its private inbox but had no language "
                "model available this wake. Will try again tomorrow."
            ),
            model_calls_used=0,
        )

    offset = state.telegram.last_update_id + 1

    try:
        updates = _get_updates(token, offset)
    except httpx.HTTPError as exc:
        return TaskResult(
            success=False,
            summary=f"respond_to_telegram: Telegram getUpdates failed: {exc}",
            public_summary=(
                "The agent could not reach Telegram to check for private "
                "messages today. Will try again tomorrow."
            ),
            model_calls_used=0,
        )

    raw_max_update_id = state.telegram.last_update_id
    for update in updates:
        uid = update.get("update_id")
        if isinstance(uid, int) and uid > raw_max_update_id:
            raw_max_update_id = uid

    operator_id = state.telegram.operator_telegram_user_id
    text_messages: list[dict] = []
    for update in updates:
        message = update.get("message")
        if not message:
            continue
        if not (message.get("text") or "").strip():
            continue
        sender = message.get("from", {}) or {}
        sender_id = sender.get("id")
        if sender_id != operator_id:
            continue
        text_messages.append(update)

    text_messages.sort(key=lambda u: u.get("update_id", 0))
    text_messages = text_messages[:MAX_MESSAGES_PER_WAKE]

    if not text_messages:
        state.telegram.last_update_id = raw_max_update_id
        return TaskResult(
            success=True,
            summary="respond_to_telegram: no new messages today",
            public_summary=(
                "Zero private messages arrived for the agent today."
            ),
            model_calls_used=0,
        )

    summary_lines: list[str] = ["respond_to_telegram log:"]
    model_calls_used = 0
    replies_sent = 0
    max_update_id = raw_max_update_id

    for update in text_messages:
        update_id = update.get("update_id", 0)
        message = update["message"]
        sender = message.get("from", {}) or {}
        first_name = sender.get("first_name", "unknown")
        user_id = sender.get("id", 0)
        chat = message.get("chat", {}) or {}
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()
        short_excerpt = text[:80] + ("..." if len(text) > 80 else "")

        if chat_id is None:
            summary_lines.append(
                f"update_id={update_id}: skipped, no chat id on message "
                f"from {first_name} (user_id={user_id})"
            )
            if update_id > max_update_id:
                max_update_id = update_id
            continue

        state.telegram.last_chat_id = chat_id

        try:
            reply_text = _draft_reply(client, message)
            model_calls_used += 1
        except Exception as exc:
            summary_lines.append(
                f"update_id={update_id}: model call failed for "
                f"{first_name} (user_id={user_id}): {exc}"
            )
            if update_id > max_update_id:
                max_update_id = update_id
            continue

        violations = style_check(reply_text)
        if violations:
            summary_lines.append(
                f"update_id={update_id}: style guard rejected reply to "
                f"{first_name} (user_id={user_id}): {', '.join(violations)}"
            )
            if update_id > max_update_id:
                max_update_id = update_id
            continue

        full_text = f"{reply_text}\n\n{DISCLOSURE_FOOTER}"

        try:
            _send_message(token, chat_id, full_text)
        except httpx.HTTPError as exc:
            summary_lines.append(
                f"update_id={update_id}: sendMessage failed for "
                f"{first_name} (user_id={user_id}, chat_id={chat_id}): {exc}"
            )
            if update_id > max_update_id:
                max_update_id = update_id
            continue

        summary_lines.append(
            f"Telegram reply sent to @{first_name} (user_id={user_id}, "
            f"chat_id={chat_id}) re: {short_excerpt}"
        )
        replies_sent += 1
        if update_id > max_update_id:
            max_update_id = update_id

    state.telegram.last_update_id = max_update_id

    if replies_sent == 0:
        return TaskResult(
            success=False,
            summary="\n".join(summary_lines),
            public_summary=(
                "The agent saw private messages today but could not deliver "
                "any replies. Will retry."
            ),
            model_calls_used=model_calls_used,
        )

    return TaskResult(
        success=True,
        summary="\n".join(summary_lines),
        public_summary=(
            f"The agent answered {replies_sent} private messages today."
        ),
        model_calls_used=model_calls_used,
    )

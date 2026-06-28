"""Private and public log writers for this agent.

write_private appends a wake entry to logs/private/<date>.md with a UTC
timestamp separator. write_public runs the content through the style guard
and, on success, appends to logs/public/<date>.md with the required
disclosure footer from PRD section 11.1.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from src import style_guard

REPO_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_DIR = REPO_ROOT / "logs" / "private"
PUBLIC_DIR = REPO_ROOT / "logs" / "public"

OPERATOR_NAME = os.environ.get("OPERATOR_NAME", "the operator")
DISCLOSURE_FOOTER = (
    f"Produced by an autonomous AI agent operated by {OPERATOR_NAME}."
)


class StyleGuardRejected(Exception):
    """Raised by write_public when style_guard.check returns violations."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"style guard rejected content: {violations}")


def _timestamp_separator() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"\n\n---\n## {now}\n\n"


def _append(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = _timestamp_separator() if existing else f"## {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(separator)
        fh.write(body)
        if not body.endswith("\n"):
            fh.write("\n")
    return path


def write_private(date: str, content: str) -> Path:
    """Append content to logs/private/<date>.md and return the path."""
    path = PRIVATE_DIR / f"{date}.md"
    return _append(path, content)


def write_public(date: str, content: str) -> Path:
    """Style-guard content, then append to logs/public/<date>.md.

    Raises StyleGuardRejected if style_guard.check returns any violations.
    Appends the required disclosure footer if not already present.
    """
    violations = style_guard.check(content)
    if violations:
        raise StyleGuardRejected(violations=violations)

    body = content if DISCLOSURE_FOOTER in content else f"{content.rstrip()}\n\n{DISCLOSURE_FOOTER}"
    path = PUBLIC_DIR / f"{date}.md"
    return _append(path, body)

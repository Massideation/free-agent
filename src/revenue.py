"""Pending vs confirmed revenue ledger for agent-001.

Per PRD section 13 and INTERFACES.md, revenue confirmation is manual.
The agent appends pending events; the operator confirms or rejects via CLI.
Only confirmed events count toward level progression.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_DIR = REPO_ROOT / "ledger"
PENDING_PATH = LEDGER_DIR / "revenue_pending.jsonl"
CONFIRMED_PATH = LEDGER_DIR / "revenue.jsonl"
PRIVATE_LOGS_DIR = REPO_ROOT / "logs" / "private"


class PendingRevenue(BaseModel):
    id: str
    ts: str
    amount_usd: float
    source: str
    evidence: str
    claimed_by_wake: str


class ConfirmedRevenue(BaseModel):
    id: str
    ts: str
    amount_usd: float
    source: str
    evidence: str
    claimed_by_wake: str
    confirmed_at: str


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def append_pending(event: PendingRevenue) -> None:
    """Append one JSON line to ledger/revenue_pending.jsonl."""
    _ensure_parent(PENDING_PATH)
    with PENDING_PATH.open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")


def list_pending() -> list[PendingRevenue]:
    """Read ledger/revenue_pending.jsonl and return parsed entries."""
    if not PENDING_PATH.exists():
        return []
    entries: list[PendingRevenue] = []
    with PENDING_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(PendingRevenue.model_validate_json(line))
    return entries


def _write_pending(entries: list[PendingRevenue]) -> None:
    _ensure_parent(PENDING_PATH)
    tmp = PENDING_PATH.with_suffix(PENDING_PATH.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")
    tmp.replace(PENDING_PATH)


def confirm(rev_id: str) -> ConfirmedRevenue:
    """Move the matching pending entry into ledger/revenue.jsonl.

    Returns the confirmed record. Raises KeyError if not found.
    """
    pending = list_pending()
    match: PendingRevenue | None = None
    remaining: list[PendingRevenue] = []
    for entry in pending:
        if entry.id == rev_id and match is None:
            match = entry
        else:
            remaining.append(entry)
    if match is None:
        raise KeyError(rev_id)

    confirmed = ConfirmedRevenue(
        id=match.id,
        ts=match.ts,
        amount_usd=match.amount_usd,
        source=match.source,
        evidence=match.evidence,
        claimed_by_wake=match.claimed_by_wake,
        confirmed_at=datetime.now(timezone.utc).isoformat(),
    )

    _ensure_parent(CONFIRMED_PATH)
    with CONFIRMED_PATH.open("a", encoding="utf-8") as f:
        f.write(confirmed.model_dump_json() + "\n")

    _write_pending(remaining)
    return confirmed


def reject(rev_id: str) -> None:
    """Remove the matching pending entry and log a rejection note."""
    pending = list_pending()
    match: PendingRevenue | None = None
    remaining: list[PendingRevenue] = []
    for entry in pending:
        if entry.id == rev_id and match is None:
            match = entry
        else:
            remaining.append(entry)
    if match is None:
        raise KeyError(rev_id)

    _write_pending(remaining)

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = PRIVATE_LOGS_DIR / f"{today}.md"
    _ensure_parent(log_path)
    ts = datetime.now(timezone.utc).isoformat()
    line = (
        f"- {ts} revenue rejected: id={match.id} "
        f"amount_usd={match.amount_usd} source={match.source}\n"
    )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def total_confirmed_usd() -> float:
    """Sum amount_usd across ledger/revenue.jsonl."""
    if not CONFIRMED_PATH.exists():
        return 0.0
    total = 0.0
    with CONFIRMED_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            total += float(record.get("amount_usd", 0))
    return total


def _main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m src.revenue")
    sub = parser.add_subparsers(dest="command", required=True)

    p_confirm = sub.add_parser("confirm", help="Confirm a pending revenue id.")
    p_confirm.add_argument("id")

    p_reject = sub.add_parser("reject", help="Reject a pending revenue id.")
    p_reject.add_argument("id")

    args = parser.parse_args(argv)

    try:
        if args.command == "confirm":
            confirmed = confirm(args.id)
            print(
                f"confirmed {confirmed.id} amount_usd={confirmed.amount_usd} "
                f"at {confirmed.confirmed_at}"
            )
            return 0
        if args.command == "reject":
            reject(args.id)
            print(f"rejected {args.id}")
            return 0
    except KeyError as e:
        print(f"error: pending revenue id not found: {e.args[0]}", file=sys.stderr)
        return 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

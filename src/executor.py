"""Task dispatcher. Owns the TaskResult shared type."""

from __future__ import annotations

import dataclasses
import importlib

from src.memory import State
from src.openrouter_client import OpenRouterClient


@dataclasses.dataclass
class TaskResult:
    success: bool
    summary: str
    public_summary: str
    model_calls_used: int = 0


def run(
    task_name: str,
    state: State,
    client: OpenRouterClient | None,
) -> TaskResult:
    """Import src.tasks.<task_name> and dispatch to its run function."""
    try:
        module = importlib.import_module(f"src.tasks.{task_name}")
    except ModuleNotFoundError as exc:
        return TaskResult(
            success=False,
            summary=f"task {task_name} not found: {exc}",
            public_summary="The agent attempted a task today and it errored. Logged privately.",
        )

    try:
        return module.run(state, client)
    except Exception as exc:
        return TaskResult(
            success=False,
            summary=f"task {task_name} crashed: {exc}",
            public_summary="The agent attempted a task today and it errored. Logged privately.",
        )

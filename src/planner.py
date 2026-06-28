"""Task selection for one wake cycle.

If the agent has not named itself yet, Wake 1 runs reflect_and_name.
Otherwise the agent decides each wake what to do via decide_next.
The prescriptive priority list from the original PRD is removed; the agent
chooses its own actions through an LLM call inside decide_next.
"""

from __future__ import annotations

from src.memory import State


REFLECT_AND_NAME = "reflect_and_name"
DECIDE_NEXT = "decide_next"


def choose_task(state: State) -> str:
    """Return the name of the task to run this wake."""
    if state.identity is None:
        return REFLECT_AND_NAME
    return DECIDE_NEXT

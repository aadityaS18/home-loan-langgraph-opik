"""
Simple conversation store for resumable loan applications.

For now, state is stored as JSON files using thread_id/application_id.

Later this can be replaced with Postgres checkpointing.
"""

import json
from pathlib import Path
from typing import Any


DATA_DIR = Path("data/conversations")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _safe_thread_id(thread_id: str) -> str:
    """Make thread_id safe for file paths."""

    return (
        thread_id.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def get_state_path(thread_id: str) -> Path:
    """Return JSON path for a thread_id."""

    safe_id = _safe_thread_id(thread_id)
    return DATA_DIR / f"{safe_id}.json"


def load_conversation_state(thread_id: str) -> dict[str, Any] | None:
    """Load conversation state for a thread_id."""

    path = get_state_path(thread_id)

    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return None


def save_conversation_state(thread_id: str, state: dict[str, Any]) -> None:
    """Save conversation state for a thread_id."""

    path = get_state_path(thread_id)

    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def delete_conversation_state(thread_id: str) -> None:
    """Delete saved conversation state."""

    path = get_state_path(thread_id)

    if path.exists():
        path.unlink()
"""Pure helpers for transcribe modal queue state transitions."""

from typing import Optional


TERMINAL_MESSAGE_TYPES = {"error", "complete", "cancelled"}


def resolve_terminal_message_type(
    current_terminal: Optional[str], incoming_type: str, cancel_requested: bool
) -> Optional[str]:
    """Resolve terminal message type deterministically.

    Rules:
    - Keep existing terminal once set.
    - Ignore non-terminal message types.
    - Treat "complete" as "cancelled" when user cancellation was requested.
    """
    if current_terminal:
        return current_terminal

    if incoming_type not in TERMINAL_MESSAGE_TYPES:
        return None

    if incoming_type == "complete" and cancel_requested:
        return "cancelled"

    return incoming_type

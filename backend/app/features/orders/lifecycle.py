"""Order status lifecycle — pure, testable state machine."""
from __future__ import annotations

# Allowed forward transitions. Terminal states map to an empty set.
TRANSITIONS: dict[str, set[str]] = {
    "pending": {"accepted", "cancelled"},
    "accepted": {"preparing", "cancelled"},
    "preparing": {"packed", "cancelled"},
    "packed": {"out_for_delivery", "cancelled"},
    "out_for_delivery": {"delivered", "cancelled"},
    "delivered": {"refunded"},
    "cancelled": set(),
    "refunded": set(),
}

# Customer may cancel only before it leaves the kitchen.
CUSTOMER_CANCELLABLE = {"pending", "accepted", "preparing"}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def next_states(current: str) -> set[str]:
    return TRANSITIONS.get(current, set())


def is_terminal(status: str) -> bool:
    return not TRANSITIONS.get(status)

"""Order state-machine tests (pure)."""
from app.features.orders.lifecycle import (
    can_transition,
    is_terminal,
    next_states,
)


def test_happy_path_transitions():
    chain = ["pending", "accepted", "preparing", "packed", "out_for_delivery", "delivered"]
    for a, b in zip(chain, chain[1:]):
        assert can_transition(a, b), f"{a}->{b} should be allowed"


def test_illegal_transitions_blocked():
    assert not can_transition("pending", "delivered")
    assert not can_transition("delivered", "pending")
    assert not can_transition("out_for_delivery", "preparing")


def test_cancel_allowed_before_dispatch():
    for s in ["pending", "accepted", "preparing", "packed", "out_for_delivery"]:
        assert can_transition(s, "cancelled")


def test_terminal_states():
    assert is_terminal("cancelled")
    assert is_terminal("refunded")
    assert not is_terminal("pending")
    assert next_states("cancelled") == set()

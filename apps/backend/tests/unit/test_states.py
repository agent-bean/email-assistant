from uuid import uuid4

import pytest

from email_assistant.domain.states import ACTION_EDGES, RUN_EDGES, content_hash, validate_snapshot

pytestmark = pytest.mark.unit


def test_terminal_states_and_revision_hash():
    assert {state for state, edges in RUN_EDGES.items() if not edges} == {
        "succeeded",
        "partial",
        "failed",
        "canceled",
    }
    assert ACTION_EDGES["unknown"] == {"succeeded", "failed_known"}
    assert not ACTION_EDGES["succeeded"]
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})
    assert content_hash({"a": 1}) != content_hash({"a": 2})
    with pytest.raises(ValueError):
        content_hash({"value": float("nan")})


@pytest.mark.parametrize(
    "kind,destinations,attachments",
    [
        ("unknown", ["x@example.test"], []),
        ("send_reply", [], []),
        ("send_reply", ["bad\r\n@example.test"], []),
        ("send_reply", ["x@example.test"], [{"id": str(uuid4()), "hash": "short"}]),
    ],
)
def test_invalid_snapshots(kind, destinations, attachments):
    with pytest.raises(ValueError):
        validate_snapshot(kind, destinations, attachments)

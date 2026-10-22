"""Storage states and exact revision snapshots; no owner authentication here."""

import hashlib
import json
import re
from typing import Any

RUN_EDGES = {
    "queued": {"running", "canceled"},
    "running": {"awaiting_owner", "succeeded", "partial", "failed", "canceled"},
    "awaiting_owner": {"queued", "canceled"},
    "succeeded": set(),
    "partial": set(),
    "failed": set(),
    "canceled": set(),
}
ACTION_EDGES = {
    "draft": {"awaiting_approval"},
    "awaiting_approval": {"approved", "draft"},
    "approved": {"claimed", "draft"},
    "claimed": {"succeeded", "failed_known", "unknown"},
    "failed_known": {"approved", "draft"},
    "unknown": {"succeeded", "failed_known"},
    "succeeded": set(),
}


def content_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_snapshot(
    kind: str, destinations: list[str], attachments: list[dict[str, str]]
) -> None:
    if kind not in {"send_reply", "forward_report", "publish_knowledge"}:
        raise ValueError("Unsupported action kind")
    if not isinstance(destinations, list) or not destinations:
        raise ValueError("Exact destinations required")
    for value in destinations:
        if not isinstance(value, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            if kind != "publish_knowledge" or not isinstance(value, str) or not value.strip():
                raise ValueError("Invalid destination")
    if not isinstance(attachments, list):
        raise ValueError("Invalid attachments")
    from uuid import UUID

    seen = set()
    for item in attachments:
        if not isinstance(item, dict) or set(item) != {"id", "hash"}:
            raise ValueError("Invalid attachment reference")
        try:
            key = UUID(item["id"])
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid attachment identity") from None
        if key in seen or not re.fullmatch(r"[0-9a-f]{64}", item["hash"]):
            raise ValueError("Invalid attachment hash or duplicate identity")
        seen.add(key)

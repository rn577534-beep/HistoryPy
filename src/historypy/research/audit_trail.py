"""Append-only, hash-linked research activity records.

The chain detects accidental or deliberate edits to recorded entries; it is
not a digital signature and does not prove who authored an entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from datetime import datetime


def _canonical(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ResearchAction:
    action_id: str
    timestamp: str
    actor: str
    operation: str
    target_type: str
    target_id: str
    rationale: str
    before_hash: str | None
    after_hash: str | None
    previous_hash: str | None
    entry_hash: str

    def __post_init__(self) -> None:
        for name in ("action_id", "timestamp", "actor", "operation", "target_type", "target_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} cannot be empty")
        datetime.fromisoformat(self.timestamp)
        if self.before_hash is not None and not self.before_hash.strip():
            raise ValueError("before_hash cannot be empty")
        if self.after_hash is not None and not self.after_hash.strip():
            raise ValueError("after_hash cannot be empty")


def content_hash(value: object) -> str:
    """Return a stable SHA-256 digest of JSON-compatible content."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _entry_payload(entry: ResearchAction) -> dict[str, object]:
    return {name: getattr(entry, name) for name in (
        "action_id", "timestamp", "actor", "operation", "target_type", "target_id",
        "rationale", "before_hash", "after_hash", "previous_hash",
    )}


def append_research_action(
    entries: tuple[ResearchAction, ...], *, action_id: str, timestamp: str,
    actor: str, operation: str, target_type: str, target_id: str,
    rationale: str, before: object | None = None, after: object | None = None,
) -> tuple[ResearchAction, ...]:
    """Return a new chain with one appended action; existing entries are untouched."""
    if not all(isinstance(item, ResearchAction) for item in entries):
        raise TypeError("entries must contain ResearchAction records")
    if any(item.action_id == action_id for item in entries):
        raise ValueError(f"Duplicate action_id: {action_id}")
    valid, errors = verify_research_audit_trail(entries)
    if not valid:
        raise ValueError(f"Cannot append to an invalid audit trail: {errors[0]}")
    previous = entries[-1].entry_hash if entries else None
    provisional = ResearchAction(
        action_id, timestamp, actor, operation, target_type, target_id, rationale,
        content_hash(before) if before is not None else None,
        content_hash(after) if after is not None else None,
        previous, "pending",
    )
    digest = sha256(_canonical(_entry_payload(provisional)).encode("utf-8")).hexdigest()
    return (*entries, ResearchAction(**{**_entry_payload(provisional), "entry_hash": digest}))


def verify_research_audit_trail(
    entries: tuple[ResearchAction, ...],
) -> tuple[bool, tuple[str, ...]]:
    """Verify entry hashes, unique IDs, and previous-hash links in order."""
    errors: list[str] = []
    previous = None
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, ResearchAction):
            errors.append(f"Entry {index} is not a ResearchAction")
            continue
        if entry.action_id in seen:
            errors.append(f"Duplicate action_id at entry {index}: {entry.action_id}")
        seen.add(entry.action_id)
        if entry.previous_hash != previous:
            errors.append(f"Broken previous_hash at entry {index}")
        expected = sha256(_canonical(_entry_payload(entry)).encode("utf-8")).hexdigest()
        if entry.entry_hash != expected:
            errors.append(f"Invalid entry_hash at entry {index}")
        previous = entry.entry_hash
    return not errors, tuple(errors)

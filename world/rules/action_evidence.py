"""Bounded recent-action evidence recording and queries (light-penance-events).

Records trustworthy evidence of recent forced interactions on the acting
perpetrator only when a committed resistance outcome has ``resisted is False``
AND ``auto_comply is False``. Expiry is evaluated against world-clock seconds
with an exclusive boundary (``now < expires_at``); repeated incidents refresh
expiry via ``max(old_expires_at, event_time + duration)`` and never stack
strike counts. Queries are read-only and never mutate storage.
"""

from collections.abc import Mapping
from typing import Any

ACTION_EVIDENCE_ATTR: str = "action_evidence"
EVIDENCE_KINDS: frozenset[str] = frozenset({"forced_interaction"})
LIGHT_EVIDENCE_DURATION: int = 60


def get_current_world_time(context: Any = None) -> int:
    """Resolve the effective world tick from context or the world clock.

    Supports in-band deterministic testing via context event_context overrides
    (``now`` or ``tick``), falling back to the read-only world clock query.
    """
    if context is not None:
        event_context = getattr(context, "event_context", None)
        if isinstance(event_context, Mapping):
            if "now" in event_context and isinstance(
                event_context["now"], (int, float)
            ):
                return int(event_context["now"])
            if "tick" in event_context and isinstance(
                event_context["tick"], (int, float)
            ):
                return int(event_context["tick"])
        elif isinstance(context, Mapping):
            if "now" in context and isinstance(context["now"], (int, float)):
                return int(context["now"])
            if "tick" in context and isinstance(context["tick"], (int, float)):
                return int(context["tick"])
    try:
        from world.rules.clock import read_world_clock

        clock = read_world_clock()
        if clock is not None:
            return int(clock.tick)
    except Exception:  # observability: ignore R2: optional clock fallback degrades to tick 0
        pass
    return 0


def has_action_evidence(
    actor: Any,
    kind: str,
    *,
    now: int | None = None,
) -> bool:
    """Return whether ``actor`` carries active evidence of ``kind``.

    Queries are strictly read-only and never mutate storage even when an
    entry is expired. The expiry boundary is exclusive: active while
    ``effective_now < expires_at``. Fails closed on malformed or missing
    attributes.
    """
    if actor is None or kind not in EVIDENCE_KINDS:
        return False
    attributes = getattr(actor, "attributes", None)
    if attributes is None:
        return False
    raw = attributes.get(ACTION_EVIDENCE_ATTR, default=None)
    if not isinstance(raw, Mapping):
        return False
    entry = raw.get(kind)
    if not isinstance(entry, Mapping):
        return False
    expires_at = entry.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        return False
    effective_now = get_current_world_time() if now is None else int(now)
    return effective_now < expires_at


def get_action_evidence(
    actor: Any,
    kind: str,
    *,
    now: int | None = None,
) -> dict[str, Any] | None:
    """Return a copy of the active evidence entry for ``kind``, or None.

    Returns ``None`` when evidence is absent, malformed, or expired at
    ``effective_now >= expires_at``. Does not mutate storage.
    """
    if actor is None or kind not in EVIDENCE_KINDS:
        return None
    attributes = getattr(actor, "attributes", None)
    if attributes is None:
        return None
    raw = attributes.get(ACTION_EVIDENCE_ATTR, default=None)
    if not isinstance(raw, Mapping):
        return None
    entry = raw.get(kind)
    if not isinstance(entry, Mapping):
        return None
    expires_at = entry.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        return None
    effective_now = get_current_world_time() if now is None else int(now)
    if effective_now >= expires_at:
        return None
    return dict(entry)


def read_all_action_evidence(actor: Any) -> dict[str, dict[str, Any]]:
    """Return a copy of all stored evidence entries without mutating state."""
    if actor is None:
        return {}
    attributes = getattr(actor, "attributes", None)
    if attributes is None:
        return {}
    raw = attributes.get(ACTION_EVIDENCE_ATTR, default=None)
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(k): dict(v)
        for k, v in raw.items()
        if isinstance(v, Mapping)
    }


def stage_action_evidence(
    actor: Any,
    kind: str,
    *,
    event_time: int,
    duration: int = LIGHT_EVIDENCE_DURATION,
) -> Any:
    """Stage a PendingEffect recording or refreshing evidence on ``actor``."""
    from world.rules.action import PendingEffect, _entity_key

    if kind not in EVIDENCE_KINDS:
        raise ValueError(f"unknown action evidence kind: {kind!r}")

    def apply(
        actor=actor,
        kind=kind,
        event_time=event_time,
        duration=duration,
    ) -> None:
        attributes = getattr(actor, "attributes", None)
        if attributes is None:
            return
        raw = attributes.get(ACTION_EVIDENCE_ATTR, default=None)
        existing_mapping = dict(raw) if isinstance(raw, Mapping) else {}
        old_entry = existing_mapping.get(kind)
        old_expires_at = 0
        if isinstance(old_entry, Mapping):
            val = old_entry.get("expires_at", 0)
            if isinstance(val, (int, float)):
                old_expires_at = int(val)
        new_expires_at = max(old_expires_at, int(event_time + duration))
        actor_id = str(getattr(actor, "pk", None) or getattr(actor, "key", ""))
        existing_mapping[kind] = {
            "kind": kind,
            "actor_id": actor_id,
            "recorded_at": int(event_time),
            "expires_at": new_expires_at,
        }
        attributes.add(ACTION_EVIDENCE_ATTR, existing_mapping)

    attributes = getattr(actor, "attributes", None)
    raw = attributes.get(ACTION_EVIDENCE_ATTR, default=None) if attributes is not None else None
    old_expires_at = 0
    if isinstance(raw, Mapping):
        old_entry = raw.get(kind)
        if isinstance(old_entry, Mapping):
            val = old_entry.get("expires_at", 0)
            if isinstance(val, (int, float)):
                old_expires_at = int(val)
    staged_expires_at = max(old_expires_at, int(event_time + duration))

    return PendingEffect(
        entity=actor,
        description=(
            f"action_evidence|{_entity_key(actor)}|{kind}|{int(event_time)}|{staged_expires_at}"
        ),
        surfaces=frozenset({"action_evidence"}),
        apply=apply,
    )


def action_evidence_planner(request: Any, event_log: Any) -> list[Any]:
    """Derive recent-action evidence from committed action event log entries.

    Inspects ``event_log.entries`` for ``sexual_resist`` entries where
    ``resisted is False`` AND ``auto_comply is False``. When one or more
    qualifying outcomes are committed, stages evidence on ``request.actor``.
    Fails closed on malformed entries without penalizing or rejecting the cast.
    """
    actor = getattr(request, "actor", None)
    if actor is None:
        return []
    has_qualifying = False
    for entry in getattr(event_log, "entries", ()):
        if getattr(entry, "kind", None) != "sexual_resist":
            continue
        data = getattr(entry, "data", None)
        if not isinstance(data, Mapping):
            continue
        if data.get("resisted") is False and data.get("auto_comply") is False:
            has_qualifying = True
            break
    if not has_qualifying:
        return []
    event_time = get_current_world_time(getattr(request, "context", None))
    return [
        stage_action_evidence(
            actor,
            "forced_interaction",
            event_time=event_time,
            duration=LIGHT_EVIDENCE_DURATION,
        )
    ]


def register_action_evidence_planner() -> None:
    """Register the action evidence planner idempotently in ActionResolver."""
    from world.rules.action import register_event_effect_planner

    register_event_effect_planner("action_evidence", action_evidence_planner)

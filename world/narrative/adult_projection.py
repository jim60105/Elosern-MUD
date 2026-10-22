"""Per-recipient adult knowledge boundary for nomination and memory projection.

OpenSpec change: authorize-adult-deed-memory-projections
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5.1

One deterministic projection decides what a single recipient may know about an
``adult_action`` occurrence. ``world.narrative.recent_deeds`` uses it for
epithet nomination and ``world.narrative.memory`` uses it for cognition
projection, so the two consumers never disagree about what one participant may
learn.

Event visibility is consumption authority only. A public occurrence (one
recorded with a third entity present) is still projected field by field per
recipient: presence never authorizes another participant's private milestone,
roll, compliance reasoning or counter. The projection is a pure function of the
immutable event content; it imports no AI proposer and writes no gameplay
state.
"""

from __future__ import annotations

from typing import Any, Mapping

#: Closed narrative event type this boundary projects.
ADULT_EVENT_TYPE = "adult_action"

#: Owner-memory category for one authorized adult participation.
ADULT_MEMORY_CATEGORY = "adult_experience"

#: Combat provenance fields a recipient may read, with their stated type.
#: ``session_id`` is diagnostic transport metadata; ``encounter_id`` is the
#: occurrence identity. Unknown keys are never copied.
_ENCOUNTER_CONTEXT_FIELDS: tuple[tuple[str, type], ...] = (
    ("encounter_id", str),
    ("session_id", str),
    ("round_number", int),
    ("slot_ordinal", int),
)

#: Every committed settled-effect result field an authorized recipient may see.
#: A new producer result field fails closed here until it is explicitly
#: authorized; the union is deliberately narrow because another participant's
#: roll, compliance reasoning and unshared counters never belong in it.
_EFFECT_RESULT_FIELDS = frozenset(
    {"amount", "hit", "gauge", "direction", "buff_key", "count"}
)

#: Field names of one committed effect row, in output order.
_EFFECT_ROW_FIELDS = ("kind", "actor_id", "target_id", "target_name", "result")

_SCALAR_TYPES = (str, int, float, bool, type(None))


class AdultProjectionError(ValueError):
    """Raised when an adult payload cannot be authorized for a recipient.

    The condition is a source-shape defect, so every consumer treats it as a
    fail-closed record: no partial projection is ever returned.
    """


def _malformed(source_id: str, detail: str) -> AdultProjectionError:
    """Return one bounded, source-identifying projection error."""
    return AdultProjectionError(f"malformed adult_action {detail} in {source_id}")


def _detached_scalar(value: Any, *, source_id: str, field: str) -> Any:
    """Return a detached copy of one allowlisted scalar field."""
    if isinstance(value, _SCALAR_TYPES):
        return value
    raise _malformed(source_id, f"{field} value")


def _text(
    row: Mapping[str, Any],
    field: str,
    *,
    source_id: str,
) -> str:
    """Return one required text field or raise a bounded diagnostic."""
    value = row.get(field)
    if not isinstance(value, str):
        raise _malformed(source_id, f"{field}")
    return value


def _rows(container: Any, *, source_id: str, field: str) -> list[Mapping[str, Any]]:
    """Return the mapping rows of one list container, or raise when malformed."""
    if container is None:
        return []
    if not isinstance(container, list):
        raise _malformed(source_id, f"{field} collection")
    rows: list[Mapping[str, Any]] = []
    for row in container:
        if not isinstance(row, Mapping):
            raise _malformed(source_id, f"{field} row")
        rows.append(row)
    return rows


def _project_encounter_context(
    content: Mapping[str, Any],
    *,
    source_id: str,
) -> dict[str, Any] | None:
    """Return the detached, allowlisted encounter provenance of one occurrence."""
    context = content.get("encounter_context")
    if context is None:
        return None
    if not isinstance(context, Mapping):
        raise _malformed(source_id, "encounter_context")
    projected: dict[str, Any] = {}
    for field, stated_type in _ENCOUNTER_CONTEXT_FIELDS:
        if field not in context:
            continue
        value = context[field]
        if not isinstance(value, stated_type) or (
            stated_type is int and isinstance(value, bool)
        ):
            raise _malformed(source_id, f"encounter_context {field}")
        projected[field] = value
    return projected


def _project_effect(
    row: Mapping[str, Any],
    *,
    recipient_pk: str,
    allow_every_target: bool,
    source_id: str,
) -> dict[str, Any] | None:
    """Return one detached committed effect visible to the recipient, or None."""
    target_id = row.get("target_id")
    if target_id is not None and not isinstance(target_id, str):
        raise _malformed(source_id, "effect target_id")
    if not allow_every_target and target_id != recipient_pk:
        # Another recipient's effect is not this owner's to validate or know.
        return None
    kind = _text(row, "kind", source_id=source_id)
    if not kind.strip():
        raise _malformed(source_id, "effect kind")
    if set(row) - set(_EFFECT_ROW_FIELDS):
        raise _malformed(source_id, "effect row fields")
    raw_result = row.get("result")
    if not isinstance(raw_result, Mapping):
        raise _malformed(source_id, "effect result")
    unknown = set(raw_result) - _EFFECT_RESULT_FIELDS
    if unknown:
        raise _malformed(source_id, "effect result fields")
    return {
        "kind": kind,
        "actor_id": _text(row, "actor_id", source_id=source_id),
        "target_id": target_id,
        "target_name": str(row.get("target_name", "")),
        "result": {
            field: _detached_scalar(
                raw_result[field], source_id=source_id, field=f"effect result {field}"
            )
            for field in raw_result
        },
    }


def _project_outcomes(
    content: Mapping[str, Any],
    *,
    recipient_pk: str,
    is_actor: bool,
    allowed_tokens: frozenset[str],
    source_id: str,
) -> dict[str, Any]:
    """Return the detached, per-recipient allowlisted outcome families.

    Only families the recipient holds a token for are read, so an unauthorized
    family is never validated, coerced or exposed.
    """
    outcomes = content.get("outcomes")
    if outcomes is None:
        outcomes = {}
    if not isinstance(outcomes, Mapping):
        raise _malformed(source_id, "outcomes")

    projected: dict[str, Any] = {}

    if "physical_effects" in allowed_tokens or "effects_on_target" in allowed_tokens:
        allow_every_target = "physical_effects" in allowed_tokens
        effects = []
        for row in _rows(
            outcomes.get("effects"), source_id=source_id, field="effects"
        ):
            effect = _project_effect(
                row,
                recipient_pk=recipient_pk,
                allow_every_target=allow_every_target,
                source_id=source_id,
            )
            if effect is not None:
                effects.append(effect)
        projected["effects"] = effects

    transitions_token = (
        "own_state_transitions" if is_actor else "target_state_transitions"
    )
    if transitions_token in allowed_tokens:
        projected["transitions"] = [
            {
                "target_id": _text(row, "target_id", source_id=source_id),
                "target_name": str(row.get("target_name", "")),
                "event": _text(row, "event", source_id=source_id),
            }
            for row in _rows(
                outcomes.get("transitions"),
                source_id=source_id,
                field="transitions",
            )
            if str(row.get("target_id", "")) == recipient_pk
        ]

    counters_token = (
        "own_counter_changes" if is_actor else "target_counter_changes"
    )
    if counters_token in allowed_tokens:
        projected["counters"] = [
            {
                "target_id": _text(row, "target_id", source_id=source_id),
                "target_name": str(row.get("target_name", "")),
                "counter": _text(row, "counter", source_id=source_id),
            }
            for row in _rows(
                outcomes.get("counters"), source_id=source_id, field="counters"
            )
            if str(row.get("target_id", "")) == recipient_pk
        ]

    # A resistance verdict is the actual resisted boolean for an identity the
    # recipient may know. Dice rolls and automatic-compliance reasoning are
    # never copied, whatever the payload carries.
    if "resistance_verdict" in allowed_tokens:
        verdicts = []
        for row in _rows(
            outcomes.get("resistance"), source_id=source_id, field="resistance"
        ):
            target_id = _text(row, "target_id", source_id=source_id)
            if not is_actor and target_id != recipient_pk:
                continue
            resisted = row.get("resisted", False)
            if not isinstance(resisted, bool):
                raise _malformed(source_id, "resistance verdict")
            verdicts.append(
                {
                    "target_id": target_id,
                    "target_name": str(row.get("target_name", "")),
                    "resisted": resisted,
                }
            )
        projected["resistance"] = verdicts

    return projected


def _project_milestones(
    content: Mapping[str, Any],
    *,
    recipient_pk: str,
    allowed_tokens: frozenset[str],
    source_id: str,
) -> list[dict[str, Any]]:
    """Return only the recipient's own milestone summaries, never another's."""
    if not ({"actor_milestones", "target_milestones"} & allowed_tokens):
        return []
    milestones = []
    for row in _rows(
        content.get("milestones"), source_id=source_id, field="milestones"
    ):
        if str(row.get("entity_id", "")) != recipient_pk:
            continue
        milestones.append(
            {
                "source_id": _text(row, "source_id", source_id=source_id),
                "milestone_kind": _text(row, "milestone_kind", source_id=source_id),
                "identifier": _text(row, "identifier", source_id=source_id),
                "entity_id": recipient_pk,
            }
        )
    return milestones


def project_adult_action_for_recipient(
    content: Any,
    *,
    recipient_pk: str,
    source_id: str,
) -> dict[str, Any] | None:
    """Project adult_action content for one recipient's authorized field access.

    Returns ``None`` when the recipient holds no field grant at all (the owner
    is not authorized and receives no projection). Raises
    :class:`AdultProjectionError` when the record's shape is unsupported. Both
    consumers share this one decision, so a public occurrence never widens it.
    """
    clean_recipient = str(recipient_pk)
    if not isinstance(content, Mapping):
        raise _malformed(source_id, "content")
    field_access = content.get("field_access")
    if not isinstance(field_access, Mapping):
        raise _malformed(source_id, "field_access")

    perms = field_access.get(clean_recipient)
    if not isinstance(perms, (list, tuple, set, frozenset)):
        return None
    # A token that is not text grants nothing; it is never coerced.
    allowed_tokens = frozenset(token for token in perms if isinstance(token, str))
    if not allowed_tokens:
        return None

    actor = content.get("actor")
    if not isinstance(actor, Mapping):
        raise _malformed(source_id, "actor")
    actor_id = _text(actor, "id", source_id=source_id)
    if not actor_id.strip():
        raise _malformed(source_id, "actor identity")
    is_actor = actor_id == clean_recipient

    act_key = _text(content, "act_key", source_id=source_id)
    if not act_key.strip():
        raise _malformed(source_id, "act_key")

    projected: dict[str, Any] = {
        "action_source_id": content.get("action_source_id", source_id),
        "act_key": act_key,
        "act_name": content.get("act_name", ""),
        "category": "sexual_act",
        "encounter_context": _project_encounter_context(content, source_id=source_id),
    }

    # Actor identity
    if "actor" in allowed_tokens:
        projected["actor"] = {
            "id": actor_id,
            "name": str(actor.get("name", "")),
            "role": "actor",
        }
    elif is_actor and "target_own_outcome" in allowed_tokens:
        projected["actor"] = {"id": actor_id, "role": "actor"}
    elif not is_actor:
        projected["actor"] = {"id": actor_id, "role": "actor"}

    # Recipients
    if "recipients" in allowed_tokens:
        projected["recipients"] = [
            {
                "id": str(row.get("id", "")),
                "name": str(row.get("name", "")),
                "role": "recipient",
            }
            for row in _rows(
                content.get("recipients"), source_id=source_id, field="recipients"
            )
        ]
    elif not is_actor and "target_own_outcome" in allowed_tokens:
        # A recipient sees only their own participation, never the full roster.
        projected["recipients"] = [
            {
                "id": str(row.get("id", "")),
                "name": str(row.get("name", "")),
                "role": "recipient",
            }
            for row in _rows(
                content.get("recipients"), source_id=source_id, field="recipients"
            )
            if str(row.get("id", "")) == clean_recipient
        ]
    else:
        projected["recipients"] = []

    projected["milestones"] = _project_milestones(
        content,
        recipient_pk=clean_recipient,
        allowed_tokens=allowed_tokens,
        source_id=source_id,
    )
    outcome_tokens = {
        "physical_effects",
        "effects_on_target",
        "own_state_transitions",
        "target_state_transitions",
        "own_counter_changes",
        "target_counter_changes",
        "resistance_verdict",
    }
    if outcome_tokens & allowed_tokens:
        projected["outcomes"] = _project_outcomes(
            content,
            recipient_pk=clean_recipient,
            is_actor=is_actor,
            allowed_tokens=allowed_tokens,
            source_id=source_id,
        )
    else:
        projected["outcomes"] = {}

    # Privacy declaration
    projected["privacy"] = {
        "consent_inferred": False,
        "willingness_inferred": False,
        "relationship_inferred": False,
        "public_notoriety": False,
    }

    return projected


def build_adult_memory_content(
    projection: Mapping[str, Any],
    *,
    recipient_pk: str,
) -> dict[str, Any]:
    """Return one detached owner-memory payload from an authorized projection.

    The content is a strict subset of the authorized projection, so the stored
    memory can never carry a field the recipient was not granted. The readable
    summary is derived from the same authorized fields and claims no consent,
    willingness, relationship or public recognition.
    """
    actor = projection.get("actor")
    actor_id = str(actor.get("id", "")) if isinstance(actor, Mapping) else ""
    recipient_ids = [
        str(row.get("id", ""))
        for row in projection.get("recipients", [])
        if isinstance(row, Mapping)
    ]
    if actor_id == str(recipient_pk):
        role = "actor"
    elif str(recipient_pk) in recipient_ids:
        role = "recipient"
    else:
        role = "participant"

    act_name = str(projection.get("act_name") or projection.get("act_key") or "")
    if role == "actor":
        summary = f"Adult act as actor: {act_name}"
    elif role == "recipient":
        summary = f"Adult act as recipient: {act_name}"
    else:
        summary = f"Adult act: {act_name}"

    content: dict[str, Any] = {
        "event_type": ADULT_EVENT_TYPE,
        "action_source_id": projection.get("action_source_id", ""),
        "role": role,
        "act_key": projection.get("act_key", ""),
        "act_name": projection.get("act_name", ""),
        "category": projection.get("category", "sexual_act"),
        "encounter_context": projection.get("encounter_context"),
        "summary": summary,
        "outcomes": dict(projection.get("outcomes", {})),
        "milestones": [dict(row) for row in projection.get("milestones", [])],
        "privacy": dict(projection.get("privacy", {})),
    }
    if "actor" in projection:
        content["actor"] = dict(projection["actor"])
    if "recipients" in projection:
        content["recipients"] = [dict(row) for row in projection["recipients"]]
    return content

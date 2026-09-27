"""Exact schema-version-1 ``combat_beats`` panel and presenter.

The presenter serializes the frozen
:class:`~world.rules.combat_beats.CombatBeatsView` of the completing combat
action's round record (design §10.1 of
``docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md``,
change ``combat-beats-panel``) and validates its own output against the exact
bounded schema before returning it to the presentation registry.

Availability is exactly "this publication carries the completing action's
round record": the dispatcher's completion publication for an admitted
``combat.cast``, ``combat.flee``, or in-session ``inventory.use`` that settled
an ordinary round supplies it, and every other publication (a reconnect or
``ui_sync`` snapshot, a text-command refresh, a forfeit, a rejected or stale
completion, a push, a round opened by the overwhelm opening or by a typed
command) builds its context without one and therefore renders the common
unavailable form.

The panel is read-only: it reads its frozen context and never mutates traits,
resources, buffs, sexual state, the battlefield, the combat record, quests,
location, or world time. It reads HP only through the same stored true-HP
source the combat panel's participant rows use, so it never touches the
disguise layer.
"""

from typing import Any

from world.observability import log_warn
from world.rules.combat_beats import (
    BEAT_KINDS,
    MAX_BEATS,
    MAX_BEAT_TEXT,
    MAX_ROUND_ID,
    CombatBeatsError,
    CombatBeatsView,
    RoundRecord,
    build_combat_beats,
)

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError

COMBAT_BEATS_SCHEMA_VERSION = 1

# The panel's own canonical-JSON byte budget (design D8): a typical beat is
# about 130 bytes, so 64 beats fit, and a terminal full snapshot stays well
# under the 65,536-byte envelope.
COMBAT_BEATS_MAX_BYTES = 12_288

# The opaque catalog-key bound, shared with the combat panel's participant rows.
MAX_BEAT_REF = 32

# The bounded diagnostic reasons this presenter may log: the rules builder's
# stable codes plus its two presentation-side classes. ``build_failed`` is
# deliberate belt-and-braces, not an expected path: every raise site in the
# rules builder passes one of the other codes, so it exists only so an
# unforeseen future code can never put free text in a log context.
_BOUNDED_REASONS = frozenset(
    {
        "too_many_beats",
        "beat_text_too_long",
        "round_id_too_long",
        "unknown_damage_target",
        "damage_amount_invalid",
        "hp_mismatch",
        "build_failed",
        "payload_invalid",
    }
)


def _validate_identity(value: Any, field: str) -> str | None:
    """Validate one null-or-decimal-catalog-key beat identity."""
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdecimal()
        or len(value) > MAX_BEAT_REF
    ):
        raise ProtocolValidationError(
            f"{field} must be an opaque decimal catalog key of at most "
            f"{MAX_BEAT_REF} characters, or null"
        )
    return value


def _validate_beat(value: Any, seq: int, previous_action: int) -> dict[str, Any]:
    """Validate one beat object, returning its exact normalized form."""
    name = f"combat_beats beat {seq}"
    _require_exact_fields(
        value,
        name,
        {"seq", "action", "kind", "actor", "target", "amount", "hp_after", "text"},
        {},
    )
    position = _require_int(value, "seq", minimum=0, maximum=MAX_SAFE_INTEGER)
    if position != seq:
        raise ProtocolValidationError(
            "combat_beats seq must be contiguous from 0"
        )
    action = _require_int(value, "action", minimum=0, maximum=MAX_SAFE_INTEGER)
    if action < previous_action:
        raise ProtocolValidationError("combat_beats action must not decrease")
    kind = value["kind"]
    if kind not in BEAT_KINDS:
        raise ProtocolValidationError("combat_beats kind is not a stable value")
    actor = _validate_identity(value["actor"], f"{name} actor")
    target = _validate_identity(value["target"], f"{name} target")
    text = _require_str(value, "text", maximum=MAX_BEAT_TEXT)
    if kind == "damage":
        if target is None:
            raise ProtocolValidationError("a damage beat requires a target")
        amount: int | None = _require_int(
            value, "amount", minimum=0, maximum=MAX_SAFE_INTEGER
        )
        hp_after: int | None = _require_int(
            value, "hp_after", minimum=0, maximum=MAX_SAFE_INTEGER
        )
    else:
        if value["amount"] is not None:
            raise ProtocolValidationError("a non-damage beat carries no amount")
        if value["hp_after"] is not None:
            raise ProtocolValidationError("a non-damage beat carries no hp_after")
        amount = None
        hp_after = None
    return {
        "seq": position,
        "action": action,
        "kind": kind,
        "actor": actor,
        "target": target,
        "amount": amount,
        "hp_after": hp_after,
        "text": text,
    }


def validate_combat_beats(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``combat_beats`` payload.

    Returns a normalized payload or raises :class:`ProtocolValidationError`.
    The common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "combat_beats panel",
        {"schema_version", "available", "round", "beats"},
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != COMBAT_BEATS_SCHEMA_VERSION:
        raise ProtocolValidationError("unsupported combat_beats schema_version")
    if not _require_bool(payload, "available"):
        raise ProtocolValidationError(
            "available must be true for the combat_beats form"
        )
    round_id = _require_str(payload, "round", maximum=MAX_ROUND_ID)
    if not round_id.strip():
        raise ProtocolValidationError("combat_beats round must be non-empty")
    beats = payload["beats"]
    if not isinstance(beats, list) or len(beats) > MAX_BEATS:
        raise ProtocolValidationError("combat_beats beats exceed their bound")
    validated: list[dict[str, Any]] = []
    previous_action = 0
    for seq, beat in enumerate(beats):
        normalized = _validate_beat(beat, seq, previous_action)
        previous_action = normalized["action"]
        validated.append(normalized)
    result = {
        "schema_version": COMBAT_BEATS_SCHEMA_VERSION,
        "available": True,
        "round": round_id,
        "beats": validated,
    }
    if json_byte_size(result) > COMBAT_BEATS_MAX_BYTES:
        raise ProtocolValidationError("combat_beats payload exceeds its byte budget")
    return result


def _serialize(view: CombatBeatsView) -> dict[str, Any]:
    """Serialize one frozen beats view into its exact JSON payload."""
    return {
        "schema_version": COMBAT_BEATS_SCHEMA_VERSION,
        "available": True,
        "round": view.round,
        "beats": [
            {
                "seq": beat.seq,
                "action": beat.action,
                "kind": beat.kind,
                "actor": beat.actor,
                "target": beat.target,
                "amount": beat.amount,
                "hp_after": beat.hp_after,
                "text": beat.text,
            }
            for beat in view.beats
        ],
    }


def _reason_code(error: Exception) -> str:
    """The bounded diagnostic reason for one unavailable beats round."""
    if isinstance(error, CombatBeatsError):
        code = error.args[0] if error.args else ""
        return code if isinstance(code, str) and code in _BOUNDED_REASONS else "build_failed"
    return "payload_invalid"


def combat_beats_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available beats panel, or raise unavailable.

    The panel is available only when the read context carries the completing
    action's frozen round record. A round the builder cannot project (a bound
    is exceeded, a damage beat names a non-participant, or an HP change
    carries no damage entry) logs a bounded diagnostic and renders the common
    unavailable form instead: a payload that violates any bound is never
    emitted, and nothing is ever truncated.
    """
    record = context.combat_round
    if not isinstance(record, RoundRecord):
        raise PanelUnavailableError("this publication carries no settled round")
    try:
        return validate_combat_beats(_serialize(build_combat_beats(record)))
    except (CombatBeatsError, ProtocolValidationError) as error:
        reason = _reason_code(error)
        log_warn(
            "combat_beats_unavailable",
            context={
                "char": str(getattr(context.actor, "pk", "?")),
                "reason": reason,
            },
        )
        raise PanelUnavailableError(reason) from error


__all__ = [
    # Re-exported rules bounds: the panel schema and the client mirror are
    # pinned to these by the dual-direction parity contract.
    "BEAT_KINDS",
    "COMBAT_BEATS_MAX_BYTES",
    "COMBAT_BEATS_SCHEMA_VERSION",
    "MAX_BEATS",
    "MAX_BEAT_REF",
    "MAX_BEAT_TEXT",
    "MAX_ROUND_ID",
    "combat_beats_presenter",
    "validate_combat_beats",
]

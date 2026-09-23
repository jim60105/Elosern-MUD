"""Church rite effect handlers (implement-church-combat-ministry).

The ``session_stamp`` prefix implements the martyrdom-vow rail (church design
§5.8): one staged write stamps the named field of the caster's durable
combat-session record with the session's own id. At defeat settlement the
violation pool filter reads that stamp to identify the marked martyr; a
foreign session id (stale stamp) can never match. The write is staged as a
restorable ``PendingEffect`` on the ``active_combat`` surface, so a failed
commit restores the pre-cast session record with everything else.
"""

from dataclasses import replace
from typing import Any

from world.rules.action.contracts import (
    PendingEffect,
    RejectedAction,
    RejectReason,
    _entity_key,
    parse_effect_key,
    register_effect_handler,
)

_MARTYR_KEY_FIELD = "martyr_key"


def _handle_session_stamp(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage the martyr-stamp write for the caster's active session."""
    del targets, context, scale
    field = parse_effect_key(effect_id)
    if field != _MARTYR_KEY_FIELD:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"unsupported session-stamp field {field!r}",
        )
    # Imported function-locally: ``combat_session`` pulls the whole combat
    # package, which imports ``action`` — a module-level import here would
    # cycle while ``action.effects`` is being initialized.
    from world.rules.combat_session.errors import CombatSessionError
    from world.rules.combat_session.records import read_session, to_storage

    try:
        record = read_session(actor)
    except CombatSessionError as error:
        # observability: ignore R2: an unreadable session rejects the cast
        # exactly like an absent one; the session contract stays in the detail
        raise RejectedAction(
            RejectReason.ACTION_FORBIDDEN,
            f"{_MARTYR_KEY_FIELD}: {error}",
        ) from error
    if record is None:
        raise RejectedAction(
            RejectReason.ACTION_FORBIDDEN,
            f"{_MARTYR_KEY_FIELD} requires an active fight",
        )
    stamps = record.martyr_key or ()
    if record.session_id in stamps:
        # A re-cast inside the same session is an idempotent no-op refresh.
        return []

    def _apply_stamp(actor=actor, session_id=record.session_id) -> None:
        # Read-modify-write at commit time: compose from the LIVE durable
        # record so even a mid-cast writer (a round-end persist reshaping
        # active_combat from the durable state) is never overwritten with
        # stale fields; the stamp append itself stays idempotent by
        # session-id membership.
        current = read_session(actor)
        if current is None:
            # The session ended between staging and commit: nothing to stamp.
            return
        stamps = current.martyr_key or ()
        if session_id in stamps:
            return
        setattr(
            actor.db,
            "active_combat",
            to_storage(
                replace(current, martyr_key=(*stamps, session_id))
            ),
        )

    return [
        PendingEffect(
            actor,
            f"session_stamp|{_entity_key(actor)}|{field}",
            frozenset({"active_combat"}),
            _apply_stamp,
        )
    ]


register_effect_handler(
    "session_stamp",
    _handle_session_stamp,
    surfaces=frozenset({"active_combat"}),
    requires_event_context=frozenset(),
)


def _handle_rite_blessing(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage the church rite martial blessing cooldown stamp and buff mount."""
    del targets, context, scale
    buff_key = parse_effect_key(effect_id)

    from world.rules.buffs import apply_buff
    from world.rules.church import read_ledger, record_rite_blessing
    from world.rules.church_rulebook import get_church_rules
    from world.rules.clock import get_world_clock

    ledger = read_ledger(actor)
    if ledger is None:
        raise RejectedAction(
            RejectReason.RITE_NOT_ENROLLED,
            "character is not enrolled in the church",
        )

    rules = get_church_rules().accrual.get("rite_martial_blessing", {})
    cooldown = int(rules.get("cooldown_seconds", 1800))
    clock = get_world_clock()
    last_cast = ledger.get("blessing_last_tick")
    if last_cast is not None and (clock.tick - int(last_cast)) < cooldown:
        raise RejectedAction(
            RejectReason.RITE_COOLDOWN_ACTIVE,
            f"rite cooldown active ({clock.tick - int(last_cast)} < {cooldown})",
        )

    tick = clock.tick
    return [
        PendingEffect(
            actor,
            f"rite_blessing|{_entity_key(actor)}",
            frozenset({"church"}),
            lambda: record_rite_blessing(actor, tick),
        ),
        PendingEffect(
            actor,
            f"self_buff_applied|{_entity_key(actor)}|{buff_key}",
            frozenset({"buffs"}),
            lambda: apply_buff(actor, buff_key),
        ),
    ]


def _handle_rite_shelter(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage the church rite shelter sanctuary rest bonus and day marker."""
    del targets, effect_id, context, scale

    from world.rules.church import _in_church_venue, read_ledger, record_rite_shelter
    from world.rules.church_rulebook import get_church_rules
    from world.rules.clock import _DAY_SECONDS, get_world_clock

    ledger = read_ledger(actor)
    if ledger is None:
        raise RejectedAction(
            RejectReason.RITE_NOT_ENROLLED,
            "character is not enrolled in the church",
        )

    if not _in_church_venue(actor):
        raise RejectedAction(
            RejectReason.RITE_OUTSIDE_VENUE,
            "character is not in a church venue",
        )

    clock = get_world_clock()
    today = clock.tick // _DAY_SECONDS
    daily_block = ledger.get("daily") or {}
    if int(daily_block.get("day", -1)) == today and daily_block.get("shelter"):
        raise RejectedAction(
            RejectReason.RITE_ALREADY_SHELTERED,
            "rite shelter already used today",
        )

    rules = get_church_rules().accrual.get("rite_shelter", {})
    rest_bonus = int(rules.get("rest_bonus", 25))
    tick = clock.tick

    return [
        PendingEffect(
            actor,
            f"rite_shelter|{_entity_key(actor)}",
            frozenset({"church"}),
            lambda: record_rite_shelter(actor, today, tick),
        ),
        PendingEffect(
            actor,
            f"self_heal|{_entity_key(actor)}|{rest_bonus}",
            frozenset({"traits"}),
            lambda: _apply_shelter_traits(actor, rest_bonus),
        ),
    ]


def _apply_shelter_traits(actor: Any, rest_bonus: int) -> None:
    """Apply the sanctuary rest bonus to the actor's HP and SP gauges."""
    hp = getattr(getattr(actor, "traits", None), "hp", None)
    if hp is not None:
        hp.current = min(hp.base, hp.current + rest_bonus)
    sp = getattr(getattr(actor, "traits", None), "sp", None)
    if sp is not None:
        sp.current = min(sp.base, sp.current + rest_bonus)


register_effect_handler(
    "rite_blessing",
    _handle_rite_blessing,
    surfaces=frozenset({"church", "buffs"}),
    requires_event_context=frozenset(),
)

register_effect_handler(
    "rite_shelter",
    _handle_rite_shelter,
    surfaces=frozenset({"church", "traits"}),
    requires_event_context=frozenset(),
)

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
    stamped = replace(record, martyr_key=(*stamps, record.session_id))
    return [
        PendingEffect(
            actor,
            f"session_stamp|{_entity_key(actor)}|{field}",
            frozenset({"active_combat"}),
            lambda actor=actor, stamped=stamped: setattr(
                actor.db, "active_combat", to_storage(stamped)
            ),
        )
    ]


register_effect_handler(
    "session_stamp",
    _handle_session_stamp,
    surfaces=frozenset({"active_combat"}),
    requires_event_context=frozenset(),
)
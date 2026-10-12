"""In-process monster AI tuning recorded for one combat session.

Startup validates the AI tuning rulebook once (``world.rules.monster_behaviour``)
and never reloads it. This module owns the *session-scoped* half of that
contract: at the production decision boundary each monster's tuning is resolved
against its current stored binding and recorded against its session id and
stable actor identity, in process only.

Three properties are deliberate:

* Nothing durable is written. No ORM field, no ``Monster`` attribute and no
  ``CombatSessionRecord`` field carries AI tuning, and no intelligence is
  copied onto an entity (monster-ai-design sections 5 and 9).
* Every call re-resolves against the *current* entity, so a repaired
  ``behaviour_tree`` or species/variant pair is honoured immediately instead of
  a remembered copy.
* A restart clears the whole store by construction -- the mapping is module
  state -- so a reconstructed session adopts the startup tuning the new process
  validated; nothing here reads configuration from disk again.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from world.rules.monster_behaviour import (
    MonsterAIDecision,
    MonsterAITuning,
    resolve_monster_ai,
)

#: session id -> stable actor identity -> the resolution recorded for it.
_SESSION_AI_TUNING: dict[str, dict[str, MonsterAIDecision]] = {}


def _actor_identity(monster: Any) -> str:
    """The stable identity (dbref, else object key) one recording is keyed by."""
    dbref = getattr(monster, "pk", None)
    if dbref is None:
        return f"key:{getattr(monster, 'key', '')}"
    return f"dbref:{dbref}"


def record_session_ai_tuning(
    session_id: str,
    monster: Any,
    *,
    tuning: MonsterAITuning | None = None,
) -> MonsterAIDecision | None:
    """Resolve one monster's AI tuning and record it for its session.

    Returns the recorded resolution, or ``None`` when the entity carries no
    ``threat_tier`` and is therefore not a registered-monster decision target.
    ``tuning`` defaults to the process's validated startup tuning; a caller
    supplies it only to stand in for a restarted process, because production
    never reloads configuration.
    """
    resolution = resolve_monster_ai(monster, tuning=tuning)
    if resolution is None:
        return None
    _SESSION_AI_TUNING.setdefault(session_id, {})[_actor_identity(monster)] = (
        resolution
    )
    return resolution


def session_ai_tuning(session_id: str) -> Mapping[str, MonsterAIDecision]:
    """Return the session's recorded resolutions, keyed by actor identity."""
    return MappingProxyType(dict(_SESSION_AI_TUNING.get(session_id, {})))


def discard_session_ai_tuning(session_id: str) -> None:
    """Drop one finished session's records, leaving every other session intact.

    Called from the session's terminal cleanup, where the session id is still
    known. Records do not outlive the session they describe.
    """
    _SESSION_AI_TUNING.pop(session_id, None)


def clear_session_ai_tuning() -> None:
    """Drop every recorded resolution -- the restart seam.

    A restart clears the store by construction (module state); this explicit
    seam lets a focused test simulate one without a new interpreter.
    """
    _SESSION_AI_TUNING.clear()

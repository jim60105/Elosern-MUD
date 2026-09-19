"""Session-local ``aN``/``eN`` target-token resolution.

Tokens stay bound to the same dbref for the session lifetime because the
persisted ``player_ids`` then ``enemy_ids`` tuples are immutable; the token is
a presentation alias and is never persisted separately.
"""

from typing import Any

from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.records import read_session

_TOKEN_RE = None


def _token_pattern() -> str:
    return r"^(a|e)(\d+)$"


def resolve_target_token(
    actor: Any,
    token: str,
) -> Any:
    """Resolve one session-local ``aN``/``eN`` token to a live participant.

    Tokens stay bound to the same dbref for the session lifetime because the
    persisted ``player_ids`` then ``enemy_ids`` tuples are immutable. The token
    is a presentation alias; it is never persisted separately.
    """
    import re

    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    match = re.fullmatch(_token_pattern(), token.strip())
    if match is None:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    prefix, raw_index = match.groups()
    index = int(raw_index)
    if prefix == "a":
        if not 1 <= index <= len(record.player_ids):
            raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
        dbref = record.player_ids[index - 1]
    else:
        if not 1 <= index <= len(record.enemy_ids):
            raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
        dbref = record.enemy_ids[index - 1]
    from evennia.objects.models import ObjectDB

    entity = ObjectDB.objects.filter(id=dbref).first()
    if entity is None:
        raise CombatSessionError(
            SessionReason.MISSING_PARTICIPANT, f"token dbref {dbref} missing"
        )
    return entity


def parse_session_targets(
    actor: Any,
    target_value: str,
    *,
    search: Any | None = None,
) -> list[Any] | str:
    """Parse an active-session target value into facade input.

    Accepts one ``aN``/``eN`` token, a comma-separated list of tokens only, or
    one complete approved AREA shorthand. A one-target display-name search is
    retained for backward Telnet parity. Rejects duplicate tokens, token/name
    mixtures, and shorthand/token mixtures before preview.
    """
    from world.rules.targeting import AREA_SHORTHANDS

    stripped = target_value.strip()
    if not stripped:
        return []
    if stripped in AREA_SHORTHANDS:
        if "," in stripped:
            raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
        return stripped
    parts = [part.strip() for part in stripped.split(",")]
    if any(part in AREA_SHORTHANDS for part in parts):
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    is_token = lambda part: bool(__import__("re").fullmatch(_token_pattern(), part))
    if all(is_token(part) for part in parts):
        seen: set[str] = set()
        resolved: list[Any] = []
        for part in parts:
            if part in seen:
                raise CombatSessionError(SessionReason.DUPLICATE_PARTICIPANT)
            seen.add(part)
            resolved.append(resolve_target_token(actor, part))
        return resolved
    if any(is_token(part) for part in parts) or len(parts) > 1:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    if search is None:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    target = search(stripped)
    if target is None:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    return [target]

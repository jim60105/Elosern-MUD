"""Party member authority boundary (party-member-authority).

One read-only boundary every member-scoped rule calls before it acts. It
resolves the commander from the authenticated acting character, re-derives a
named member's membership and presence, and exposes the ordered present party
scope and the text member token. Nothing here writes: the transfer, equipment,
field-action, practice, shop and party-window rules import it instead of
trusting a caller-supplied identity.

Decisions (``openspec/changes/party-member-authority/design.md``):

- The commander is the acting ``PlayerCharacter``, or the live player-character
  owner of a possessed *and puppeted* companion. A leftover ``possessed_by``
  flag without a live puppet session grants no authority
  (``is_player_driven``), and the possession mirrors must still name this
  companion with a live session of the owning account, so a flag left behind by
  a released or foreign possession cannot launder authority.
- Membership is re-derived through ``live_companions``. A forged, stale,
  deleted, or non-member identity is rejected with ``not_party_member`` and is
  never replaced by the commander.
- Presence is the commander's room, so a member a failed follow or a non-exit
  relocation left elsewhere is excluded. An optional ``anchor`` cannot widen
  that check: a supplied anchor must share the commander's room.
- The ``act`` purpose additionally excludes a knocked-out companion (stored HP
  at or below the nonlethal floor); ``organize`` admits it, because moving
  items never needs the member to act. The commander itself is never "knocked
  out" by this predicate; defeat aftermath keeps its own rules.
"""

from typing import Any

from world.rules.npc_identity import npc_display_name
from world.rules.party import live_companions
from world.rules.player_control import is_player_driven

# Stable membership rejection codes. Callers branch and render on these; the
# codes never change with prose.
REASON_NOT_PARTY_MEMBER = "not_party_member"
REASON_MEMBER_NOT_PRESENT = "member_not_present"
REASON_MEMBER_CANNOT_ACT = "member_cannot_act"

#: Bag/equipment reorganization; admits a knocked-out member.
PURPOSE_ORGANIZE = "organize"
#: Item use, casting, practice booking; a knocked-out member cannot act.
PURPOSE_ACT = "act"
PURPOSES = frozenset({PURPOSE_ORGANIZE, PURPOSE_ACT})

#: The nonlethal knockout floor ``combat_companions`` applies.
NONLETHAL_HP_FLOOR = 1

# Fixed player-facing rejection lines: one per stable code, shared by every
# member-scoped rule so the transports never drift.
PARTY_SCOPE_MESSAGES: dict[str, str] = {
    REASON_NOT_PARTY_MEMBER: "對方不是你的隊伍成員。",
    REASON_MEMBER_NOT_PRESENT: "對方不在這裡。",
    REASON_MEMBER_CANNOT_ACT: "對方目前無法行動。",
}


class PartyScopeError(RuntimeError):
    """A member-scoped request was rejected; ``reason`` is one stable code.

    ``message`` is the fixed Traditional Chinese line for that code, so a
    caller renders feedback without re-deciding any prose.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.message = PARTY_SCOPE_MESSAGES[reason]


def _resolve_live_object(dbid: int) -> Any | None:
    """Resolve one dbid to its live typeclass object, or ``None`` when absent."""
    from evennia.objects.objects import ObjectDB

    return ObjectDB.objects.filter(id=dbid).first()


def _is_dbid(value: Any) -> bool:
    """Whether ``value`` is an identity dbid (bools and strings are not)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _plain_key(entity: Any) -> str:
    """The entity's plain key, or ``""`` when even that read fails."""
    try:
        key = entity.key
    except Exception:  # observability: ignore R2: never-raise identity read; a broken accessor degrades to an unmatched name
        return ""
    if key is None:
        return ""
    try:
        return str(key)
    except Exception:  # observability: ignore R2: a key whose __str__ raises is not a name
        return ""


def _answers_to(entity: Any, token: str) -> bool:
    """Whether ``entity`` answers to ``token`` by composed name or plain key."""
    if npc_display_name(entity) == token:
        return True
    key = _plain_key(entity)
    return bool(key) and key == token


def _knocked_out(member: Any) -> bool:
    """Whether ``member``'s stored HP is at or below the nonlethal floor."""
    from world.rules.action import stored_gauge_pair

    current, _maximum = stored_gauge_pair(member, "hp")
    return current <= NONLETHAL_HP_FLOOR


def _possession_holds(acting: Any, owner: Any) -> bool:
    """Whether the possession mirrors and a live owner-account session agree.

    The owner-side mirror (``player.db.possession``) names the companion and
    the account that entered the possession; at least one logged-in session of
    that account must still puppet the companion. The flags alone never grant
    authority: a released possession, a foreign session, or a half-written
    binding all read as no authority.
    """
    from world.rules.possession import current_possession

    binding = current_possession(owner)
    if binding is None or binding["npc_dbid"] != int(acting.pk):
        return False
    account_id = binding.get("account_id")
    if account_id is None:
        return False
    sessions = getattr(acting, "sessions", None)
    if not callable(getattr(sessions, "all", None)):
        return False
    for session in sessions.all():
        if getattr(session, "puppet", None) is not acting:
            continue
        if not getattr(session, "logged_in", False):
            continue
        account = getattr(session, "account", None)
        account_pk = getattr(account, "pk", None)
        if account_pk is not None and int(account_pk) == account_id:
            return True
    return False


def resolve_commander(acting: Any) -> Any:
    """The commander behind ``acting``: itself, or a possessed companion's owner.

    Raises ``PartyScopeError(not_party_member)`` for anything else, including
    an NPC whose ``possessed_by`` flag survives without a live owner-account
    possession.
    """
    from typeclasses.characters import PlayerCharacter

    if isinstance(acting, PlayerCharacter):
        return acting
    if not is_player_driven(acting):
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    owner_id = getattr(getattr(acting, "db", None), "possessed_by", None)
    if not _is_dbid(owner_id):
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    owner = _resolve_live_object(owner_id)
    if not isinstance(owner, PlayerCharacter):
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    if not _possession_holds(acting, owner):
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    return owner


def authorize_member(
    commander: Any, member_id: Any, purpose: str, anchor: Any = None
) -> Any:
    """Re-derive one named member for ``purpose`` and return the live object.

    ``member_id`` must be a dbid; the member must be the commander or an
    effective companion of it, and must be in the commander's room. ``anchor``
    is the acting character that scopes the request and defaults to the
    commander; a supplied anchor must share the commander's room, so it can
    never widen the presence check. Raises ``PartyScopeError`` with a stable
    code and never writes.
    """
    if purpose not in PURPOSES:
        raise ValueError(f"unknown party member purpose: {purpose!r}")
    if not _is_dbid(member_id):
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    member = _resolve_live_object(member_id)
    if member is None:
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    if member is not commander and member not in live_companions(commander):
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    room = getattr(commander, "location", None)
    if anchor is not None and getattr(anchor, "location", None) is not room:
        raise PartyScopeError(REASON_MEMBER_NOT_PRESENT)
    if room is None or getattr(member, "location", None) is not room:
        raise PartyScopeError(REASON_MEMBER_NOT_PRESENT)
    if purpose == PURPOSE_ACT and member is not commander and _knocked_out(member):
        raise PartyScopeError(REASON_MEMBER_CANNOT_ACT)
    return member


def present_party_scope(acting: Any) -> tuple[Any, ...]:
    """The ordered party present with the commander: commander first, then roster.

    Effective companions keep ``live_companions`` order and only appear while
    they share the commander's room. The acting character is always part of the
    result: a possessed figure that a relocation left outside the commander's
    room is appended last rather than dropped, so no settlement can omit the
    figure that acted.
    """
    commander = resolve_commander(acting)
    room = getattr(commander, "location", None)
    scope: list[Any] = [commander]
    if room is not None:
        for member in live_companions(commander):
            if member in scope:
                continue
            if getattr(member, "location", None) is room:
                scope.append(member)
    if acting not in scope:
        scope.append(acting)
    return tuple(scope)


def resolve_member_token(acting: Any, token: Any) -> Any:
    """Resolve a ``= <成員>`` / ``由 <成員>`` token to one party member.

    The token matches by exact composed display name or plain key among the
    commander and the effective companions only -- presence is authorized
    separately by :func:`authorize_member`. Zero or several matches reject with
    ``not_party_member``; the caller is never used as a fallback.
    """
    commander = resolve_commander(acting)
    stripped = token.strip() if isinstance(token, str) else ""
    if not stripped:
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    matches = [
        entity
        for entity in (commander, *live_companions(commander))
        if _answers_to(entity, stripped)
    ]
    if len(matches) != 1:
        raise PartyScopeError(REASON_NOT_PARTY_MEMBER)
    return matches[0]


def party_in_combat(acting: Any, *members: Any) -> bool:
    """Whether a combat-barred request involves an active combat session.

    Called with game entities. True when the acting character, the commander,
    or any named member reads an active session, so a possessed figure in a
    session cannot bypass the bar while the owner's body stands outside it. A
    non-party acting character contributes only itself and its named members;
    authorization rejects it separately.
    """
    from world.rules.combat_session import is_in_active_session

    try:
        commander = resolve_commander(acting)
    except PartyScopeError:  # observability: ignore R2: a non-party acting character contributes only itself; authorization rejects it separately
        commander = None

    checked: list[Any] = []
    for actor in (acting, commander, *members):
        if actor is None or any(actor is seen for seen in checked):
            continue
        checked.append(actor)
        if is_in_active_session(actor):
            return True
    return False

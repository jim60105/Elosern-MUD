"""Session-scoped viewed-member selection for the party window; never persistent.

``party.view_member`` records which member of the commander's party this
session is looking at. The selection lives only on ``session.ndb``, is bound to
the commander identity (the party panel's own owner resolution), and is copied
into the immutable read context as one frozen value, so every presenter of the
same commit reads the same selection without touching ``ndb``.

Unlike the combat actor selection it is NOT retired on unpuppet: possession
unpuppets the owner, and the party window must look identical whether or not
the player is possessing, so the selection survives the transition. It is
dropped with the session (a reconnect starts on the commander) and can never
authorize a mutation — every command is reauthorized against canonical state at
the rules boundary.

A selection naming a member who left the party or was deleted is not an error:
:func:`resolve_viewed_member` answers the commander instead, so the next
payload reports a member that really exists.
"""

from dataclasses import dataclass
from typing import Any

from world.rules.party import bound_owner_of, live_companions

#: The session ``ndb`` attribute holding this session's viewed-member selection.
NDB_ATTRIBUTE = "party_view"

#: The closed tab set ``party.view_member`` accepts. The window that renders
#: the tabs lands in later changes; the server stores the choice either way.
TABS = frozenset({"member", "bag", "status", "skills", "lineage", "shop"})


@dataclass(frozen=True)
class PartyViewSelection:
    """One session's viewed member, bound to the commander it was chosen under."""

    commander_id: int
    member_id: int
    tab: str
    #: The skill selected in the 技能 tab, or ``None``. The server never
    #: resolves it here: the ``character`` panel publishes detail only for a
    #: key the viewed member actually owns.
    skill_key: str | None = None
    #: The item selected in the bag or shop surface, or ``None``. The server
    #: resolves it against the registry in the holdings presenter; an unknown
    #: key is stored as ``None`` by the selection adapter.
    item_key: str | None = None


def select_party_view(
    session: Any,
    commander_id: int,
    member_id: int,
    tab: str,
    skill_key: str | None = None,
    item_key: str | None = None,
) -> None:
    """Record one authorized selection for this session.

    The caller has already re-derived the commander and re-checked membership
    through the rules boundary; recording never authorizes anything by itself.
    ``skill_key`` is the already-validated bounded key of the skill selected in
    the 技能 tab (or ``None``); ``item_key`` is the already-validated bounded
    registry key of the item selected for the holdings query (or ``None``).
    A direct call without a session records nothing.
    """
    ndb = getattr(session, "ndb", None)
    if ndb is None:
        return
    ndb.party_view = PartyViewSelection(
        int(commander_id),
        int(member_id),
        str(tab),
        None if skill_key is None else str(skill_key),
        None if item_key is None else str(item_key),
    )


def _commander(actor: Any) -> Any | None:
    """The commander whose party this actor's session presents.

    The same single owner rule the party presenter applies (the possessed
    NPC's ``party_member`` back-reference, else the actor itself), so the panel
    and the selection can never disagree about whose party is on screen.
    """
    from typeclasses.npcs import NPC

    return bound_owner_of(actor) if isinstance(actor, NPC) else actor


def party_view_selection_snapshot(session: Any, actor: Any) -> PartyViewSelection | None:
    """Copy only a selection owned by this session's commander into the context.

    A malformed stored value, an unknown tab, or a selection bound to another
    commander (the session now presents a different party) reads as no
    selection, so the panel falls back to its own commander.
    """
    raw = getattr(getattr(session, "ndb", None), NDB_ATTRIBUTE, None)
    if not isinstance(raw, PartyViewSelection) or raw.tab not in TABS:
        return None
    commander = _commander(actor)
    commander_id = getattr(commander, "pk", None)
    if not isinstance(commander_id, int) or raw.commander_id != commander_id:
        return None
    return raw


def resolve_viewed_member(context: Any) -> Any | None:
    """The viewed member object, or the commander when nothing effective is chosen.

    A selection is effective only while it names the commander or a live
    companion of it; a member who left or was deleted therefore falls back to
    the commander in every presenter that reads this helper. ``None`` means no
    commander resolves at all (the caller's own unavailable form applies).
    """
    commander = _commander(getattr(context, "actor", None))
    if commander is None:
        return None
    commander_id = int(commander.pk)
    selection = getattr(context, "party_view", None)
    if isinstance(selection, PartyViewSelection) and selection.commander_id == commander_id:
        if selection.member_id == commander_id:
            return commander
        for companion in live_companions(commander):
            if int(companion.pk) == selection.member_id:
                return companion
    return commander


def selected_skill_key_for(context: Any, member: Any) -> str | None:
    """The selected 技能-tab skill key when the selection names ``member``.

    Both effectiveness checks apply: the selection must be bound to the
    commander this session presents (the same rule
    :func:`resolve_viewed_member` applies), and its member must be the member
    the panel resolved. A selection left over from a member who left the party
    therefore never attaches its skill detail to the commander. The returned
    key is still unvalidated: the panel publishes detail only for an active
    skill the viewed member actually owns.
    """
    selection = getattr(context, "party_view", None)
    if not isinstance(selection, PartyViewSelection) or member is None:
        return None
    commander = _commander(getattr(context, "actor", None))
    if commander is None or selection.commander_id != int(commander.pk):
        return None
    if selection.member_id != int(member.pk):
        return None
    return selection.skill_key


def selected_item_key_for(context: Any, member: Any) -> str | None:
    """The selected holdings item key when the selection names ``member``.

    Both effectiveness checks apply exactly as for the selected skill: the
    selection must be bound to the commander this session presents, and its
    member must be the member the panel resolved. The returned key is still
    unvalidated; the holdings presenter resolves it against the registry and
    publishes no rows for an unknown key.
    """
    selection = getattr(context, "party_view", None)
    if not isinstance(selection, PartyViewSelection) or member is None:
        return None
    commander = _commander(getattr(context, "actor", None))
    if commander is None or selection.commander_id != int(commander.pk):
        return None
    if selection.member_id != int(member.pk):
        return None
    return selection.item_key


__all__ = [
    "NDB_ATTRIBUTE",
    "TABS",
    "PartyViewSelection",
    "party_view_selection_snapshot",
    "resolve_viewed_member",
    "selected_item_key_for",
    "selected_skill_key_for",
    "select_party_view",
]

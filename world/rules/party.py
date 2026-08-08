"""Party membership: the sole writer of player-party bindings (party-core D-1).

``player.db.party`` holds the list of companion NPC dbids (at most
``PARTY_MAX_COMPANIONS``) and each companion's ``npc.db.party_member`` holds
the player's dbid. Only this module assigns those attributes; joins, leaves,
and deletion purges write both sides inside one transaction with
snapshot/restore of both entities' in-process caches, and reads treat a stale
dbid (a deleted NPC) as an absent companion. The party auto-leave recheck
(``world/rules/affinity.py``) and the dialogue intent applier
(``world/rules/npc_intents.py``) route through this module, so no other code
can create or remove a binding.
"""

from typing import Any

from django.db import transaction

PARTY_MAX_COMPANIONS = 4

# Stable join-gate rejection reasons surfaced through ``PartyJoinError.reason``
# and ``IntentOutcome.reason`` so callers can render distinct feedback.
REASON_NOT_NPC = "not_npc"
REASON_NOT_CO_LOCATED = "not_co_located"
REASON_ALREADY_COMPANION = "already_companion"
REASON_PARTY_FULL = "party_full"

# Fixed player-facing party lines shared by the ``invite``/``leave`` commands
# and the webclient ``explore.party_invite``/``explore.party_leave`` adapters,
# so the two transports never drift. All prose is Traditional Chinese.
JOINED_MESSAGE = "她加入了你的隊伍。"
REFUSED_MESSAGE = "她婉拒了你的邀請。"
ALREADY_COMPANION_MESSAGE = "她已經是你的同伴了。"
PARTY_FULL_MESSAGE = "你的隊伍已經滿了（最多 4 人）。"
NOT_DIALOGUE_MESSAGE = "對方無法回應你的邀請。"
NOT_COMPANION_MESSAGE = "她不是你的同伴。"
LEAVE_DISMISSED_MESSAGE = "你解散了與她的隊伍。"
AUTO_LEAVE_MESSAGE = "她與你的羈絆淡去，隊伍解散了。"
DEGRADED_ACCEPT_MESSAGE = "她願意與你同行。"
DEGRADED_REJECT_MESSAGE = "她搖了搖頭，婉拒了你的邀請。"

JOIN_REJECTION_MESSAGES: dict[str, str] = {
    REASON_PARTY_FULL: PARTY_FULL_MESSAGE,
    REASON_ALREADY_COMPANION: ALREADY_COMPANION_MESSAGE,
    REASON_NOT_CO_LOCATED: "她不在這裡。",
    REASON_NOT_NPC: "那不是你可以邀請的對象。",
}


class PartyError(RuntimeError):
    """A party operation failed; ``reason`` carries a stable code."""


class PartyJoinError(PartyError):
    """A join request violated a deterministic gate (target, location, bound)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PartyWriteError(PartyError):
    """A membership write failed after both surfaces were restored."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def party_ids(player: Any) -> list[int]:
    """The raw companion dbid list (stale dbids included), or ``[]``."""
    raw = player.db.party
    if not raw:
        return []
    return [int(dbid) for dbid in raw]


def _resolve_live_object(dbid: int) -> Any | None:
    """Resolve one dbid to its live typeclass object, or ``None`` when absent."""
    from evennia.objects.objects import ObjectDB

    return ObjectDB.objects.filter(id=dbid).first()


def live_companion_ids(player: Any) -> list[int]:
    """The companion dbids whose NPC still exists (stale dbids are absent)."""
    from typeclasses.npcs import NPC

    live: list[int] = []
    for dbid in party_ids(player):
        obj = _resolve_live_object(dbid)
        if obj is not None and isinstance(obj, NPC):
            live.append(dbid)
    return live


def party_size(player: Any) -> int:
    """The number of live companions (deleted NPCs never count)."""
    return len(live_companion_ids(player))


def is_companion(npc: Any, player: Any) -> bool:
    """Whether ``npc`` is currently bound to ``player`` (O(1) mirror read).

    The player-owned list is the authoritative direction; a stale entry whose
    NPC no longer exists can never be passed in, so a matching pk is always a
    live companion.
    """
    return npc.pk in party_ids(player)


def join_party(npc: Any, player: Any) -> None:
    """Bind ``npc`` as a companion of ``player`` (gate-validated, atomic).

    Raises ``PartyJoinError`` with a stable ``reason`` when a deterministic
    gate fails (target not an NPC, not co-located, already bound, or the party
    is full). The 4-companion bound counts only live companions: stale dbids
    (deleted NPCs) read as absent and are dropped from the stored list by the
    join write, so a deleted NPC can never permanently consume a slot. Raises
    ``PartyWriteError`` after restoring both entities' in-process caches when
    a write fails, so no partial binding is observable.
    """
    from typeclasses.npcs import NPC

    if not isinstance(npc, NPC):
        raise PartyJoinError(REASON_NOT_NPC)
    if player.location is None or npc.location is not player.location:
        raise PartyJoinError(REASON_NOT_CO_LOCATED)
    party = party_ids(player)
    if npc.pk in party or npc.db.party_member is not None:
        raise PartyJoinError(REASON_ALREADY_COMPANION)
    live = live_companion_ids(player)
    if len(live) >= PARTY_MAX_COMPANIONS:
        raise PartyJoinError(REASON_PARTY_FULL)
    _write_binding(npc, player, [*live, npc.pk], player.pk)


def leave_party(npc: Any, player: Any, reason: str) -> None:
    """Remove ``npc`` from ``player``'s party (idempotent, atomic).

    A leave of a non-bound NPC is a no-op success. The NPC-side backref is
    cleared only when it belongs to ``player``; a backref held by another
    player is left untouched so no caller can break a binding it does not own.
    ``reason`` documents the dismissal for callers (``dismissed``,
    ``affinity_below_threshold``) and is not persisted. On a write failure
    both surfaces are restored and ``PartyWriteError`` is raised.
    """
    del reason
    party = party_ids(player)
    member = npc.db.party_member
    member_is_ours = member is not None and int(member) == int(player.pk)
    bound = npc.pk in party or member_is_ours
    if not bound:
        return
    member_after = member if (member is not None and not member_is_ours) else None
    _write_binding(
        npc,
        player,
        [dbid for dbid in party if dbid != npc.pk],
        member_after,
    )


def purge_npc_memberships(npc: Any) -> None:
    """Remove every party binding of ``npc`` (typeclass deletion hook).

    Resolves the bound player through the NPC-side backref, removes the NPC's
    dbid from that player's party list, and clears the backref in one
    transaction. A party list already lacking the dbid degrades to a
    backref-only clear, and a missing player just clears the backref. Runs
    from ``NPC.at_object_delete`` so a deleted companion never consumes a
    companion slot.
    """
    member = npc.db.party_member
    if member is None:
        return
    player = _resolve_live_object(int(member))
    party_before = party_ids(player) if player is not None else []
    try:
        with transaction.atomic():
            if player is not None:
                player.db.party = [
                    dbid for dbid in party_before if dbid != npc.pk
                ]
            npc.db.party_member = None
    except Exception as error:
        if player is not None:
            player.db.party = list(party_before)
        npc.db.party_member = member
        raise PartyWriteError("purge_failed", str(error)) from error


def _write_binding(
    npc: Any, player: Any, party_after: list[int], member_after: Any
) -> None:
    """Commit one mirrored membership write with snapshot/restore of both sides.

    The player-side list and the NPC-side backref are assigned inside one
    ``transaction.atomic()``; on any failure both in-process attributes are
    restored to their pre-write values and ``PartyWriteError`` is raised so
    the caller's outer transaction (if any) can roll back as well.
    """
    party_before = list(party_ids(player))
    member_before = npc.db.party_member
    try:
        with transaction.atomic():
            player.db.party = list(party_after)
            npc.db.party_member = member_after
    except Exception as error:
        player.db.party = party_before
        npc.db.party_member = member_before
        raise PartyWriteError("write_failed", str(error)) from error

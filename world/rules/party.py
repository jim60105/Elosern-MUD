"""Party membership: the sole writer of player-party bindings (party-core D-1).

``player.db.party`` holds one ordered companion ID roster; ``party_meta``
declares general identity and exact quest/role sources. Only valid general
identities count toward ``PARTY_MAX_COMPANIONS``. Each companion's
``npc.db.party_member`` holds the player's dbid. Only this module assigns
these attributes; joins, leaves,
and deletion purges write both sides inside one transaction with
snapshot/restore of both entities' in-process caches, and reads treat a stale
dbid (a deleted NPC) as an absent companion. The party auto-leave recheck
(``world/rules/affinity.py``) and the dialogue intent applier
(``world/rules/npc_intents.py``) route through this module, so no other code
can create or remove a binding.

Companion follow (party-follow D-1) is the same module's read-only movement
contract: ``follow_companions`` moves every effective party member present in
the traverser's source through the shared exit success paths -- never a
teleport or spawn -- with no clock charge, no announce messages, and the party
binding left untouched. Under possession the traverser is the possessed
companion and the follower set also contains the commander's own unpuppeted
body, so the party stays co-located while the player acts through the puppet.
"""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from django.db import transaction

from world.observability import log_info, log_warn
from world.maps.wilderness_provider import WILDERNESS_NAME

PARTY_MAX_COMPANIONS = 4
PARTY_META_ATTRIBUTE = "party_meta"

# Stable join-gate rejection reasons surfaced through ``PartyJoinError.reason``
# and ``IntentOutcome.reason`` so callers can render distinct feedback.
REASON_NOT_NPC = "not_npc"
REASON_NOT_CO_LOCATED = "not_co_located"
REASON_ALREADY_COMPANION = "already_companion"
REASON_PARTY_FULL = "party_full"
REASON_HANDBACK_FIRST = "handback_first"
REASON_NOT_PROTECTED_BINDING = "not_protected_binding"
#: A temporary-only member's companionship is a live escort commission, not a
#: general dismissal: detaching it silently would abandon the quest without the
#: player's chosen commission. Both the ``leave`` command and the webclient
#: ``explore.party_leave`` adapter refuse with this stable reason and name the
#: affected commissions, pointing at the existing quest-abandonment path.
REASON_ESCORT_BOUND = "escort_bound"

# Fixed player-facing party lines shared by the ``invite``/``leave`` commands
# and the webclient ``explore.party_invite``/``explore.party_leave`` adapters,
# so the two transports never drift. All prose is Traditional Chinese.
JOINED_MESSAGE = "她加入了你的隊伍。"
REFUSED_MESSAGE = "她婉拒了你的邀請。"
ALREADY_COMPANION_MESSAGE = "她已經是你的同伴了。"
PARTY_FULL_MESSAGE = "你的隊伍已經滿了（最多 4 人）。"
NOT_DIALOGUE_MESSAGE = "對方無法回應你的邀請。"
HANDBACK_FIRST_MESSAGE = "請先歸位再解散同伴。"
ESCORT_BOUND_MESSAGE = (
    "她仍與你的護送委託同行；請先放棄對應的委託（{quests}）才能解除同行關係。"
)
NOT_COMPANION_MESSAGE = "她不是你的同伴。"
LEAVE_DISMISSED_MESSAGE = "你解散了與她的隊伍。"
AUTO_LEAVE_MESSAGE = "她與你的羈絆淡去，隊伍解散了。"
DEGRADED_ACCEPT_MESSAGE = "她願意與你同行。"
DEGRADED_REJECT_MESSAGE = "她搖了搖頭，婉拒了你的邀請。"

# Fixed player-facing follow lines (party-follow D-4): one 跟丟了 notification
# per traversal naming every left-behind companion; the names are joined with
# 、 so a single template serves one or many failures.
FOLLOW_LOST_MESSAGE = "你跟丟了{names}。"

JOIN_REJECTION_MESSAGES: dict[str, str] = {
    REASON_PARTY_FULL: PARTY_FULL_MESSAGE,
    REASON_ALREADY_COMPANION: ALREADY_COMPANION_MESSAGE,
    REASON_NOT_CO_LOCATED: "她不在這裡。",
    REASON_NOT_NPC: "那不是你可以邀請的對象。",
    REASON_HANDBACK_FIRST: HANDBACK_FIRST_MESSAGE,
    REASON_NOT_PROTECTED_BINDING: "對方沒有可用的護送委託。",
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
    result = []
    for entry in raw:
        try:
            dbid = int(entry)
        except (TypeError, ValueError):  # observability: ignore R2: malformed roster entries grant no membership
            continue
        if dbid > 0 and dbid not in result:
            result.append(dbid)
    return result


def party_meta(player: Any) -> dict[str, dict[str, Any]]:
    """Normalize persisted metadata, including Evennia saved containers."""
    raw = player.db.party_meta
    if not isinstance(raw, Mapping):
        return {}
    result = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.isdecimal() or int(key) <= 0:
            continue
        if not isinstance(value, Mapping) or type(value.get("general")) is not bool:
            continue
        reasons = value.get("reasons")
        if not isinstance(reasons, Sequence) or isinstance(reasons, (str, bytes)):
            continue
        pairs = []
        for pair in reasons:
            if (
                isinstance(pair, Sequence) and not isinstance(pair, (str, bytes))
                and len(pair) == 2 and all(isinstance(item, str) and item for item in pair)
                and list(pair) not in pairs
            ):
                pairs.append(list(pair))
        result[key] = {"general": value["general"], "reasons": pairs}
    return result


def member_meta(player: Any, member_id: int) -> dict[str, Any]:
    """Missing metadata grants no membership; construction declares defaults."""
    return party_meta(player).get(str(member_id), {"general": False, "reasons": []})


def reasons_for(npc: Any, player: Any) -> tuple[tuple[str, str], ...]:
    from world.quests.escort import valid_reason_pairs

    return valid_reason_pairs(
        player, member_meta(player, npc.pk)["reasons"], member_id=npc.pk
    )


def has_general_membership(npc: Any, player: Any) -> bool:
    return member_meta(player, npc.pk)["general"] and npc in live_companions(player)


def general_member_ids(player: Any) -> list[int]:
    metadata = party_meta(player)
    return [
        npc.pk for npc in live_companions(player)
        if metadata.get(str(npc.pk), {}).get("general") is True
    ]


def temporary_member_ids(player: Any) -> list[int]:
    return [npc.pk for npc in live_companions(player) if reasons_for(npc, player)]


def _resolve_live_object(dbid: int) -> Any | None:
    """Resolve one dbid to its live typeclass object, or ``None`` when absent."""
    from evennia.objects.objects import ObjectDB

    return ObjectDB.objects.filter(id=dbid).first()


def live_companion_ids(player: Any) -> list[int]:
    """The companion dbids whose NPC still exists (stale dbids are absent)."""
    return [npc.pk for npc in live_companions(player)]


def party_size(player: Any) -> int:
    """General quota usage; temporary-only members do not consume a slot."""
    return len(general_member_ids(player))


def is_companion(npc: Any, player: Any) -> bool:
    """Whether both binding directions and a legitimate source hold."""
    return npc in live_companions(player)


def bound_owner_of(npc: Any) -> Any | None:
    """Resolve the player whose valid party contains ``npc``, or ``None``.

    The bidirectional safe read used by quest DEFEAT credit (party-quest D-1):
    the candidate owner is the NPC-side back-reference player, and the NPC
    must also appear in that player's valid party list (``live_companions``),
    so a mismatched, stale, or one-sided binding resolves to ``None`` and
    never credits. Read-only and never raises.
    """
    from typeclasses.characters import PlayerCharacter
    from typeclasses.npcs import NPC

    if not isinstance(npc, NPC):
        return None
    member = npc.db.party_member
    if member is None:
        return None
    try:
        player = _resolve_live_object(int(member))
    except (TypeError, ValueError):  # observability: ignore R2: a malformed backref reads as no owner; logging would fire on every hot-path lookup
        return None
    if not isinstance(player, PlayerCharacter):
        return None
    if npc not in live_companions(player):
        return None
    return player


def live_companions(player: Any) -> list[Any]:
    """Resolve the live companion NPC objects of ``player`` (safe accessor).

    Skips stale dbids (deleted NPCs), non-NPC entries, and backref mismatches
    (an NPC whose ``party_member`` points at a different player), so a corrupt
    leftover entry can never raise from a traversal hook or block the other
    companions (party-follow D-3). Each entry is exception-isolated: a malformed
    stored record degrades to that entry being skipped, never a raise.
    """
    from typeclasses.npcs import NPC

    raw = player.db.party
    if not raw:
        return []
    companions: list[Any] = []
    for entry in raw:
        try:
            dbid = int(entry)
        except (TypeError, ValueError):  # observability: ignore R2: malformed entries degrade to skipped per the entry-isolation contract; logging would fire on every hook
            # A non-numeric leftover entry is skipped, never a raise.
            continue
        try:
            obj = _resolve_live_object(dbid)
            if not isinstance(obj, NPC):
                continue
            member = obj.db.party_member
            if member is None or int(member) != int(player.pk):
                continue
            metadata = member_meta(player, dbid)
            if not metadata["general"] and not reasons_for(obj, player):
                continue
            if obj not in companions:
                companions.append(obj)
        except Exception:  # observability: ignore R2: per-entry isolation on a traversal-hook hot path; degrades to skipping that companion
            continue
    return companions


def combat_companions(player: Any) -> list[Any]:
    """Return the bound, co-located, living, non-knocked-out companions.

    Engagement collection for party-combat D-1: resolves through
    ``live_companions`` (stale dbids, non-NPC entries, and backref mismatches
    skipped) and keeps only companions sharing the player's room whose stored
    HP is above the nonlethal floor (1). A knocked-out companion therefore
    stays out of a new engagement until ordinary clock-driven regen lifts its
    HP above 1 (party-combat D-2). Returns in deterministic party order and
    never raises.
    """
    from typeclasses.characters import PlayerCharacter

    if not isinstance(player, PlayerCharacter):
        return []
    from world.rules.action import _stored_trait_value

    companions: list[Any] = []
    for npc in live_companions(player):
        try:
            if npc.location is player.location and _stored_trait_value(npc.traits.hp) > 1:
                companions.append(npc)
        except Exception:  # observability: ignore R2: a companion whose stored traits fail to parse is excluded from engagement, never a raise
            continue
    return companions


def _effective_follow_members(commander: Any, traverser: Any) -> list[Any]:
    """Every party member the follow step considers, traverser excluded.

    The commander's own body leads the list when the traverser is a possessed
    companion; effective companions keep ``live_companions`` order. The
    traverser is never a follower of itself.
    """
    members: list[Any] = []
    if commander is not traverser:
        members.append(commander)
    for npc in live_companions(commander):
        if npc is traverser or npc in members:
            continue
        members.append(npc)
    return members


def follow_scope(
    traverser: Any,
    source_location: Any,
    wilderness_source_coordinates: tuple[int, int] | None = None,
    *,
    log_unresolved: bool = True,
) -> tuple[Any | None, list[Any]]:
    """The commander and the co-located followers of one traversal.

    The commander is resolved from the traverser through the party authority
    boundary: the player character itself, or the owner of a possessed
    companion puppeted by the owner's account. A stale possession flag (an
    NPC whose ``possessed_by`` survives without a live owner-account
    possession) resolves no commander and follows nobody; the settlement
    snapshot suppresses its own diagnostic with ``log_unresolved=False`` so
    one traversal emits at most one such event.

    Followers keep deterministic order (commander body first, then the
    effective companions) and are filtered by the existing co-location
    predicate against the source room or wilderness registration. Any
    resolution failure degrades to no followers rather than raising from a
    traversal hook.
    """
    from world.rules.party_scope import PartyScopeError, resolve_commander

    try:
        commander = resolve_commander(traverser)
    except PartyScopeError:
        if log_unresolved and getattr(
            getattr(traverser, "db", None), "possessed_by", None
        ) is not None:
            log_warn(
                "party_follow_commander_unresolved",
                context={"obj": str(traverser), "possessed": True},
            )
        return None, []
    except Exception as error:
        log_warn(
            "party_follow_commander_unresolved",
            exc=error,
            context={
                "obj": str(traverser),
                "possessed": getattr(
                    getattr(traverser, "db", None), "possessed_by", None
                )
                is not None,
            },
        )
        return None, []
    followers: list[Any] = []
    for member in _effective_follow_members(commander, traverser):
        try:
            if _companion_co_located(
                member, source_location, wilderness_source_coordinates
            ):
                followers.append(member)
        except Exception:  # observability: ignore R2: co-location probe isolation on a traversal-hook hot path; degrades to leaving that member behind
            continue
    return commander, followers


def follow_companions(
    traverser: Any,
    source_location: Any,
    *,
    destination: Any | None = None,
    wilderness_coordinates: tuple[int, int] | None = None,
    wilderness_source_coordinates: tuple[int, int] | None = None,
    wilderness_name: str = WILDERNESS_NAME,
) -> None:
    """Move every co-located party member to the traverser's destination.

    Called from the exit traversal success paths only (party-follow D-1):
    grid/instance/base exits through the shared ``at_post_traverse`` hook,
    the wilderness gate entry, the ordinary wilderness step, and the
    wilderness return. The follower set is derived from effective membership
    through ``follow_scope``: for a player traverser it is every co-located
    companion; for a possessed companion it also contains the commander's own
    unpuppeted body, so the whole party stays co-located while the player
    acts through the puppet. A bound member elsewhere is never pulled.
    Co-location is room-based (``member.location is source_location``) and,
    in wilderness mode, also registration-based: the contrib recycles a
    wilderness room as soon as no account is inside it, so a member left in
    that room ends up with ``location=None`` while still registered in the
    script's ``itemcoordinates`` at the source coordinates
    (``wilderness_source_coordinates``).

    Companions use quiet ``move_to`` (no announce messages, and the project's
    arrival observers are all ``PlayerCharacter``-gated) or the provider's
    coordinate API in wilderness mode. The owner body instead runs the
    destination's receive gate explicitly and then moves with
    ``move_hooks=False`` (or the provider API) so no player-arrival side
    effect -- action options, arrival lore, encounter activation -- is
    attributed to a body nobody is playing; its map knowledge records the
    destination once. A member leaving the wilderness through a grid
    destination is deregistered from the script's ``itemcoordinates`` after a
    successful move, so ``move_to`` never strands it in the wilderness
    bookkeeping. No world-clock charge occurs here -- the clock advances only
    on the traverser's own traversal -- and the party binding is never
    changed. After the moves complete, the commander's quest arrival
    observation re-runs once (quest progression only for a possessed owner
    body, never arrival lore) so co-presence on the first arrival is visible
    (party-quest D-2); the one-transition rule keeps it idempotent.

    A member whose move fails stays put and the acting character -- the
    possessed puppet while possessing, else the player -- receives one fixed
    Traditional Chinese 「跟丟了」 notification naming every left-behind
    member, exactly once per traversal.

    Never raises from a traversal hook: stale and corrupt entries are skipped
    by ``live_companions``, each member's resolution, co-location check, and
    move are exception-isolated, and the notification itself is isolated --
    a failure at any point degrades to fewer (or no) moves and a missing (or
    logged) notification, never a broken traversal.
    """
    commander, followers = follow_scope(
        traverser, source_location, wilderness_source_coordinates
    )
    if commander is None:
        return
    possessed = commander is not traverser
    if not followers:
        return
    members = _effective_follow_members(commander, traverser)
    destination_had_companion = destination is not None and any(
        member.location is destination for member in members
    )
    destination_wilderness = (
        getattr(destination, "wilderness", None) if destination is not None else None
    )
    body_arrived = not possessed
    left_behind: list[Any] = []
    for member in followers:
        try:
            if member is commander:
                moved = _move_commander_body(
                    commander,
                    source_location,
                    destination,
                    wilderness_coordinates=wilderness_coordinates,
                    wilderness_name=wilderness_name,
                )
                body_arrived = moved
            elif destination_wilderness is not None:
                # A non-exit relocation into a wilderness room: a plain
                # move_to would run the terrain room's receive hook, which
                # re-routes an already-registered member to its old
                # coordinates. Use the provider's coordinate API instead.
                from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

                moved = enter_wilderness(
                    member,
                    coordinates=destination.coordinates,
                    name=destination_wilderness.db_key or wilderness_name,
                )
            elif destination is not None:
                moved = member.move_to(destination, quiet=True)
                if moved and member.ndb.wilderness is not None:
                    # Leaving the wilderness: clear the script's registration
                    # so the member is not stranded in the bookkeeping.
                    member.ndb.wilderness.at_post_object_leave(member)
            else:
                from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

                moved = enter_wilderness(
                    member, coordinates=wilderness_coordinates, name=wilderness_name
                )
        except Exception:  # observability: ignore R2: a failed move degrades visibly to the left-behind notification below
            moved = False
        if not moved:
            left_behind.append(member)
    if body_arrived:
        _reobserve_quest_arrival(
            commander,
            destination_had_companion=destination_had_companion,
            possessed=possessed,
        )
    if not left_behind:
        return
    try:
        names = "、".join(obj.key or f"#{obj.pk}" for obj in left_behind)
        traverser.msg(FOLLOW_LOST_MESSAGE.format(names=names))
    except Exception as error:
        # A failed notification must never break the traversal.
        log_warn(
            "party_follow_notification_failed",
            exc=error,
            context={
                "obj": str(traverser),
                "left_behind": len(left_behind),
                "possessed": possessed,
            },
        )


def _move_commander_body(
    body: Any,
    source_location: Any,
    destination: Any | None,
    *,
    wilderness_coordinates: tuple[int, int] | None,
    wilderness_name: str,
) -> bool:
    """Move the commander's unpuppeted body without firing player-arrival hooks.

    The receiving gate runs explicitly because ``move_hooks=False`` skips Evennia's
    own pre-receive check; a refusal is an ordinary left-behind. Grid
    destinations use ``move_to(..., quiet=True, move_hooks=False)`` and a
    wilderness destination room (only reachable through a non-exit relocation)
    uses the provider's coordinate API. Wilderness entry and steps resolve the
    target room the provider already created and run the same explicit gate
    before ``enter_wilderness``. The commander's map knowledge records the
    arrival exactly once, after the move succeeds.
    """
    if destination is not None:
        wilderness = getattr(destination, "wilderness", None)
        if wilderness is not None:
            if not destination.at_pre_object_receive(body, source_location):
                return False
            from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

            moved = enter_wilderness(
                body,
                coordinates=destination.coordinates,
                name=wilderness.db_key or wilderness_name,
            )
        else:
            if not destination.at_pre_object_receive(body, source_location):
                return False
            moved = body.move_to(destination, quiet=True, move_hooks=False)
            if moved and body.ndb.wilderness is not None:
                body.ndb.wilderness.at_post_object_leave(body)
    else:
        target = _wilderness_destination_room(
            wilderness_name, wilderness_coordinates
        )
        if target is not None and not target.at_pre_object_receive(
            body, source_location
        ):
            return False
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        moved = enter_wilderness(
            body, coordinates=wilderness_coordinates, name=wilderness_name
        )
    if not moved:
        return False
    from world.rules.map_knowledge import record_arrival

    record_arrival(body)
    return True


def _wilderness_destination_room(
    wilderness_name: str, coordinates: tuple[int, int] | None
) -> Any | None:
    """The live room the provider will use for ``coordinates``, if it exists."""
    if coordinates is None:
        return None
    from evennia.contrib.grid.wilderness.wilderness import WildernessScript

    script = WildernessScript.objects.filter(db_key=wilderness_name).first()
    if script is None:
        return None
    return (script.db.rooms or {}).get(tuple(coordinates))


def _reobserve_quest_arrival(
    commander: Any, *, destination_had_companion: bool, possessed: bool
) -> None:
    """Re-run the commander's quest arrival observation after the follow moves.

    The commander's own ``at_object_receive`` observation runs before the
    follow moves (for a player traversal) or does not run at all (the owner
    body moves hook-free), so a companion arriving *with* the commander would
    be invisible to the first observation; the re-run happens after the moves
    (party-quest D-2) and the quest observer's one-transition rule makes the
    repeated observation idempotent for the shipped quantity-1 objectives.
    When a companion was already present in the destination before an ordinary
    player traversal, the first observation has already advanced every
    matching stage for this arrival event, so the re-run is skipped: it would
    otherwise count the same event a second time (for example a defensive
    non-1 quantity could jump two progress points on one arrival). A possessed
    traversal has no earlier commander observation, so it always observes
    exactly once. Arrival lore is never scheduled for the owner body -- the
    pinned footstep is the only commander surface a possessed traversal may
    write. Never raises from a traversal hook.
    """
    if destination_had_companion and not possessed:
        return
    from world.quests.room_observation import observe_room_entry

    try:
        observe_room_entry(
            commander.location, commander, observe_lore=not possessed
        )
    except Exception as error:
        log_warn(
            "party_follow_quest_reobservation_failed",
            exc=error,
            context={
                "obj": str(commander),
                "key": "location",
                "possessed": possessed,
            },
        )


def _companion_co_located(
    npc: Any,
    source_location: Any,
    wilderness_source_coordinates: tuple[int, int] | None,
) -> bool:
    """Whether ``npc`` was in the same room as the player before the move.

    Room-based match covers grid/instance/base moves and wilderness rooms
    that survived recycling; the registration match covers companions whose
    wilderness room the contrib recycled (location ``None`` but still tracked
    in the script's ``itemcoordinates`` at the source coordinates).
    """
    if npc.location is source_location:
        return True
    if wilderness_source_coordinates is None:
        return False
    wilderness = npc.ndb.wilderness
    return (
        wilderness is not None
        and wilderness.itemcoordinates.get(npc) == wilderness_source_coordinates
    )


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
    member = npc.db.party_member
    if has_general_membership(npc, player) or (
        member is not None and int(member) != int(player.pk)
    ):
        raise PartyJoinError(REASON_ALREADY_COMPANION)
    live = live_companion_ids(player)
    if party_size(player) >= PARTY_MAX_COMPANIONS:
        raise PartyJoinError(REASON_PARTY_FULL)
    metadata = party_meta(player)
    identity = member_meta(player, npc.pk)
    identity["general"] = True
    metadata[str(npc.pk)] = identity
    _write_binding(npc, player, list(dict.fromkeys([*live, npc.pk])), player.pk, metadata)


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
    remaining = reasons_for(npc, player)
    if not remaining and getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
        if int(npc.db.possessed_by) == int(player.pk):
            raise PartyJoinError(REASON_HANDBACK_FIRST)
    party = party_ids(player)
    member = npc.db.party_member
    member_is_ours = member is not None and int(member) == int(player.pk)
    bound = npc.pk in party or member_is_ours
    if not bound:
        return
    metadata = party_meta(player)
    if remaining and member_is_ours:
        metadata[str(npc.pk)] = {"general": False, "reasons": [list(pair) for pair in remaining]}
        _write_binding(npc, player, party, member, metadata)
        return
    metadata.pop(str(npc.pk), None)
    member_after = member if (member is not None and not member_is_ours) else None
    _write_binding(
        npc,
        player,
        [dbid for dbid in party if dbid != npc.pk],
        member_after,
        metadata,
    )
    # A departed companion ends any conversation held with it
    # (webclient-align-07): the conditional clear touches only sessions
    # naming this NPC, inside the same transaction as the binding write.
    from world.rules.dialogue import clear_dialogue_session

    clear_dialogue_session(player, npc=npc)


def purge_npc_memberships(npc: Any) -> None:
    """Remove every party binding of ``npc`` (typeclass deletion hook).

    Resolves the bound player through the NPC-side backref, removes the NPC's
    dbid from that player's party list, and clears the backref in one
    transaction. A party list already lacking the dbid degrades to a
    backref-only clear, and a missing player just clears the backref. Runs
    from ``NPC.at_object_delete`` so a deleted companion never consumes a
    companion slot.
    """
    possessed_by = getattr(getattr(npc, "db", None), "possessed_by", None)
    if possessed_by is not None:
        from world.rules.possession import purge_possession_on_delete

        purge_possession_on_delete(npc)
    member = npc.db.party_member
    if member is None:
        return
    player = _resolve_live_object(int(member))
    party_before = party_ids(player) if player is not None else []
    meta_before = party_meta(player) if player is not None else {}
    try:
        with transaction.atomic():
            if player is not None:
                player.db.party = [
                    dbid for dbid in party_before if dbid != npc.pk
                ]
                metadata = deepcopy(meta_before)
                metadata.pop(str(npc.pk), None)
                player.db.party_meta = metadata
            npc.db.party_member = None
    except Exception as error:
        if player is not None:
            player.db.party = list(party_before)
            player.db.party_meta = meta_before
        npc.db.party_member = member
        raise PartyWriteError("purge_failed", str(error)) from error


def _write_binding(
    npc: Any, player: Any, party_after: list[int], member_after: Any,
    meta_after: dict[str, dict[str, Any]],
) -> None:
    """Commit one mirrored membership write with snapshot/restore of both sides.

    The player-side list and the NPC-side backref are assigned inside one
    ``transaction.atomic()``; on any failure both in-process attributes are
    restored to their pre-write values and ``PartyWriteError`` is raised so
    the caller's outer transaction (if any) can roll back as well.
    """
    party_before = list(party_ids(player))
    meta_before = deepcopy(player.db.party_meta)
    member_before = npc.db.party_member
    try:
        with transaction.atomic():
            player.db.party = list(party_after)
            player.db.party_meta = meta_after
            npc.db.party_member = member_after
    except Exception as error:
        player.db.party = party_before
        player.db.party_meta = meta_before
        npc.db.party_member = member_before
        raise PartyWriteError("write_failed", str(error)) from error
    log_info("party_membership_commit", context={"char": player.pk, "npc": npc.pk})


def restore_membership_surfaces(
    player: Any,
    party_before: list[int],
    members_before: dict[int, Any],
    meta_before: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Restore the in-process party surfaces after a rolled-back transaction.

    The idmapper attribute cache is not transaction-aware: a rolled-back
    ``db.party`` / ``db.party_member`` write still leaves the post-write value
    readable in-process. Callers that snapshot membership before an atomic
    block invoke this helper in the failure path so readers never observe the
    rolled-back state. Only this module assigns party attributes (party-core
    single-writer contract).
    """
    if meta_before is None:
        # Existing outer owners call after rollback. Retire the Attribute cache
        # before reading metadata so a nested successful write cannot survive it.
        player.attributes.reset_cache()
        meta_before = party_meta(player)
    player.db.party = list(party_before)
    player.db.party_meta = meta_before
    for npc_pk, member in members_before.items():
        npc = _resolve_live_object(npc_pk)
        if npc is not None:
            npc.db.party_member = member


def add_temporary_source(npc: Any, player: Any, record_id: str, role_id: str) -> None:
    """Add one quest-owned exact source without consuming a general slot."""
    from typeclasses.npcs import NPC
    from world.quests.escort import valid_reason_pairs

    if not isinstance(npc, NPC):
        raise PartyJoinError(REASON_NOT_NPC)
    member = npc.db.party_member
    if member is not None and int(member) != int(player.pk):
        raise PartyJoinError(REASON_ALREADY_COMPANION)
    pair = [record_id, role_id]
    if not valid_reason_pairs(player, [pair], member_id=npc.pk):
        raise PartyJoinError(REASON_NOT_PROTECTED_BINDING)
    metadata = party_meta(player)
    identity = member_meta(player, npc.pk)
    if pair in identity["reasons"] and is_companion(npc, player):
        return
    identity["reasons"].append(pair)
    metadata[str(npc.pk)] = identity
    _write_binding(
        npc, player, list(dict.fromkeys([*party_ids(player), npc.pk])), player.pk, metadata
    )


def remove_reason(npc: Any, player: Any, record_id: str, role_id: str) -> None:
    """Remove exactly one source, handing back control only on actual release."""
    metadata = party_meta(player)
    identity = member_meta(player, npc.pk)
    pair = [record_id, role_id]
    if pair not in identity["reasons"]:
        return
    identity["reasons"] = [entry for entry in identity["reasons"] if entry != pair]
    from world.quests.escort import valid_reason_pairs

    surviving = valid_reason_pairs(player, identity["reasons"], member_id=npc.pk)
    retained = identity["general"] or bool(surviving)
    identity["reasons"] = [list(entry) for entry in surviving]
    if retained:
        metadata[str(npc.pk)] = identity
    else:
        metadata.pop(str(npc.pk), None)
    member = npc.db.party_member
    from world.rules.possession import (
        release_for_party_change, restore_party_control, snapshot_party_control,
    )

    party_before = party_ids(player)
    meta_before = deepcopy(player.db.party_meta)
    control = snapshot_party_control(player, npc)
    try:
        with transaction.atomic():
            if not retained and member == player.pk:
                release_for_party_change(npc, player)
            _write_binding(
                npc, player,
                party_before if retained else [dbid for dbid in party_before if dbid != npc.pk],
                member if retained or member != player.pk else None, metadata,
            )
    except Exception:
        restore_membership_surfaces(player, party_before, {npc.pk: member}, meta_before)
        restore_party_control(player, npc, control)
        raise


def release_record_reasons(player: Any, record_id: str) -> None:
    """Release record sources without disturbing another identity."""
    for dbid, identity in tuple(party_meta(player).items()):
        npc = _resolve_live_object(int(dbid))
        if npc is None:
            continue
        for quest_id, role_id in identity["reasons"]:
            if quest_id == record_id:
                remove_reason(npc, player, quest_id, role_id)

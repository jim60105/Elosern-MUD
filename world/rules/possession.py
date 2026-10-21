"""Deterministic companion possession writer, gates, and transitions.

This module is the SINGLE WRITER of ``player.db.possession`` (mapping
``{"npc_dbid": int, "since_tick": int}``) and ``npc.db.possessed_by``
(int dbid of the owning player character).

Documented order:
- enter: gates -> mirrored write -> puppet-transfer hook -> cmdset-mount hook -> facade info event
- release: unmount cmdset -> unpuppet hook -> mirrored clear -> facade info event
"""

from copy import deepcopy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_error, log_info, log_warn

def _resolve_account(player: Any, npc: Any) -> Any | None:
    """Resolve the owning account for player and npc, even when unpuppeted."""
    account = getattr(player, "account", None) or getattr(npc, "account", None)
    if account is not None:
        return account
    # Try account_id recorded in player possession mirror
    curr = current_possession(player)
    if curr is not None and "account_id" in curr:
        from evennia.accounts.models import AccountDB

        acc = AccountDB.objects.filter(id=curr["account_id"]).first()
        if acc is not None:
            return acc
    # Try creator_id on player
    creator_id = getattr(getattr(player, "db", None), "creator_id", None)
    if creator_id is not None:
        from evennia.accounts.models import AccountDB

        acc = AccountDB.objects.filter(id=creator_id).first()
        if acc is not None:
            return acc
    # Try live sessions
    from evennia.server.sessionhandler import SESSION_HANDLER

    for sess in SESSION_HANDLER.values():
        acc = getattr(sess, "account", None)
        if acc is not None:
            if player in _account_characters(acc):
                return acc
            if npc is not None and getattr(sess, "puppet", None) is npc:
                return acc
    # Check ObjectDB for account that owns npc
    npc_acc = getattr(npc, "db_account", None) if npc is not None else None
    if npc_acc is not None:
        return npc_acc
    # Check AccountDB _last_puppet
    from evennia.accounts.models import AccountDB

    for acc in AccountDB.objects.all():
        if getattr(getattr(acc, "db", None), "_last_puppet", None) == player:
            return acc
    return None


def _account_characters(account: Any) -> list[Any]:
    """Resolve all characters owned by this account.

    Covers CharactersHandler, db._playable_characters, and the db_account
    foreign key relation on ObjectDB.
    """
    if account is None:
        return []
    chars: list[Any] = []
    seen: set[int] = set()

    if hasattr(account, "characters"):
        handler = account.characters
        char_list = []
        if callable(getattr(handler, "all", None)):
            char_list = handler.all()
        elif hasattr(handler, "__iter__"):
            char_list = list(handler)
        for c in char_list:
            if c is not None and hasattr(c, "pk") and c.pk not in seen:
                seen.add(c.pk)
                chars.append(c)

    playable = getattr(getattr(account, "db", None), "_playable_characters", None)
    if isinstance(playable, list):
        for c in playable:
            if c is not None and hasattr(c, "pk") and c.pk not in seen:
                seen.add(c.pk)
                chars.append(c)

    if hasattr(account, "pk"):
        for c in ObjectDB.objects.filter(db_account=account):
            if c.pk not in seen:
                seen.add(c.pk)
                chars.append(c)

    last_puppet = getattr(getattr(account, "db", None), "_last_puppet", None)
    if last_puppet is not None and hasattr(last_puppet, "pk") and last_puppet.pk not in seen:
        seen.add(last_puppet.pk)
        chars.append(last_puppet)

    return chars


# Stable gate & write reason codes
REASON_NOT_BOUND = "not_bound"
REASON_NOT_CO_LOCATED = "not_co_located"
REASON_IN_COMBAT = "in_combat"
REASON_DIALOGUE_OPEN = "dialogue_open"
REASON_ALREADY_POSSESSING = "already_possessing"
REASON_WRITE_FAILED = "write_failed"
REASON_MISMATCHED_POSSESSION = "mismatched_possession"
REASON_TRANSFER_REFUSED = "transfer_refused"
REASON_RELEASE_REFUSED = "release_refused"
REASON_POSSESSED_TALK = "possessed_talk"
REASON_POSSESSED_ENGAGE = "possessed_engage"
# Sleep-driven contextual handoff (handoff-sleeping-party-control). The query
# and confirmation share these stable codes so the text and browser transports
# never invent a second vocabulary.
REASON_NOT_POSSESSING = "not_possessing"
REASON_NOT_SLEEPING = "not_sleeping"
REASON_STALE_HANDOFF = "stale_handoff"
REASON_NO_CANDIDATE = "no_candidate"
REASON_SESSION_MISMATCH = "session_mismatch"

# D10 stable refusal messages for possessed actor
POSSESSED_REFUSAL_MESSAGES: dict[str, str] = {
    REASON_POSSESSED_TALK: "附身狀態下無法與他人開啟對話。",
    REASON_POSSESSED_ENGAGE: "附身狀態下無法主動發起戰鬥。",
}


# Player-facing localized messages
POSSESSION_REJECTION_MESSAGES: dict[str, str] = {
    REASON_NOT_BOUND: "對方不是你的同伴。",
    REASON_NOT_CO_LOCATED: "對方不在這裡。",
    REASON_IN_COMBAT: "戰鬥中無法附身。",
    REASON_DIALOGUE_OPEN: "對方正在對話中，無法附身。",
    REASON_ALREADY_POSSESSING: "你目前已經在附身狀態。",
    REASON_TRANSFER_REFUSED: "此刻無法附身於他。",
    REASON_NOT_POSSESSING: "你目前並未控制任何同伴的身體。",
    REASON_NOT_SLEEPING: "目前的身體尚未入睡，不需要交接。",
    REASON_STALE_HANDOFF: "交接選項已經失效，請重新選擇。",
    REASON_NO_CANDIDATE: "目前沒有可以接手控制的清醒同伴。",
    REASON_SESSION_MISMATCH: "這個操作必須由目前控制該身體的連線發出。",
}

UNPOSSESS_RELEASED_MESSAGE = "你的意識回到了自己的身體。"
UNPOSSESS_REFUSED_RETURN_MESSAGE = "你的身體搖搖欲墜,彷彿從很深的水裡被拉回來。"


class PossessionError(Exception):
    """Base exception for possession failures."""


class PossessionGateError(PossessionError):
    """A deterministic entry gate rejected possession."""

    def __init__(self, reason: str, *, candidates: tuple[Any, ...] = ()) -> None:
        super().__init__(reason)
        self.reason = reason
        # A stale handoff confirmation carries the current choices so the
        # caller can re-render them without substituting a different target.
        self.candidates = tuple(candidates)


class PossessionWriteError(PossessionError):
    """A possession write or integrity check failed."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _resolve_live_object(dbid: int) -> Any | None:
    """Resolve one dbid to its live typeclass object, or ``None``."""
    return ObjectDB.objects.filter(id=dbid).first()


def current_possession(player: Any) -> dict[str, Any] | None:
    """Return the validated possession mapping of ``player``, or ``None``."""
    raw = getattr(getattr(player, "db", None), "possession", None)
    if not isinstance(raw, Mapping):
        return None
    npc_dbid = raw.get("npc_dbid")
    since_tick = raw.get("since_tick")
    if not isinstance(npc_dbid, int) or isinstance(npc_dbid, bool) or npc_dbid <= 0:
        return None
    if not isinstance(since_tick, int) or isinstance(since_tick, bool) or since_tick < 0:
        return None
    res = {"npc_dbid": int(npc_dbid), "since_tick": int(since_tick)}
    if "account_id" in raw and isinstance(raw["account_id"], int) and not isinstance(raw["account_id"], bool):
        res["account_id"] = int(raw["account_id"])
    return res


def restore_possession_surfaces(
    player: Any, npc: Any, player_before: Any, npc_before: Any
) -> None:
    """Restore both in-process surfaces after a failed transaction.

    Mirrors the idmapper-cache discipline of ``world/rules/party.py``:
    a rolled-back write must never remain readable in-process.
    """
    if player is not None and hasattr(player, "db"):
        player.db.possession = player_before
    if npc is not None and hasattr(npc, "db"):
        npc.db.possessed_by = npc_before


# ---------------------------------------------------------------------------
# Lock and Session Helpers
# ---------------------------------------------------------------------------


def _grant_puppet_lock(npc: Any, account: Any) -> None:
    """Additively grant puppet access for account on npc.

    Snapshots the pre-grant lock definition so release can restore it
    deterministically without fragile string manipulation.
    """
    if npc is None or account is None or not hasattr(npc, "locks"):
        return
    existing = npc.locks.get("puppet") or ""
    if getattr(getattr(npc, "db", None), "possession_lock_before", None) is None:
        if hasattr(npc, "db"):
            npc.db.possession_lock_before = existing

    grant_func = f"id({account.id})"
    if not existing:
        npc.locks.add(f"puppet:{grant_func}")
    elif grant_func not in existing:
        npc.locks.add(f"{existing} or {grant_func}")


def _strip_puppet_lock(npc: Any, account: Any) -> None:
    """Restore npc's pre-grant puppet lock."""
    if npc is None or not hasattr(npc, "locks"):
        return
    lock_before = getattr(getattr(npc, "db", None), "possession_lock_before", None)
    if lock_before is not None:
        if lock_before:
            npc.locks.add(lock_before)
        else:
            npc.locks.remove("puppet")
        if hasattr(npc, "db"):
            npc.db.possession_lock_before = None
    else:
        existing = npc.locks.get("puppet") or ""
        if account is not None:
            grant_func = f"id({account.id})"
            if grant_func in existing:
                parts = existing.split(":", 1)
                if len(parts) == 2:
                    terms = [
                        t.strip()
                        for t in parts[1].split(" or ")
                        if t.strip() != grant_func
                    ]
                    if terms:
                        npc.locks.add(f"{parts[0]}:{' or '.join(terms)}")
                    else:
                        npc.locks.remove("puppet")


def _acting_sessions(entity: Any) -> list[Any]:
    """Find all active sessions currently puppeting entity or owned by its account."""
    sessions: list[Any] = []
    seen: set[int] = set()
    if hasattr(getattr(entity, "sessions", None), "all"):
        for sess in entity.sessions.all():
            sessid = getattr(sess, "sessid", id(sess))
            if sessid not in seen:
                seen.add(sessid)
                sessions.append(sess)
    account = getattr(entity, "account", None)
    if account is not None and hasattr(getattr(account, "sessions", None), "all"):
        for sess in account.sessions.all():
            sessid = getattr(sess, "sessid", id(sess))
            if sessid not in seen and getattr(sess, "puppet", None) is entity:
                seen.add(sessid)
                sessions.append(sess)
    return sessions


#: Logout-restore Attributes Evennia writes on puppet and on the last-session
#: unpuppet. The companion must keep no stale restore target once its occupied
#: room has been restored by this writer.
_LOGOUT_LOCATION_ATTRIBUTES = ("prelogout_location", "prelog_location")


def _snapshot_logout_attributes(entity: Any) -> dict[str, Any]:
    """Capture presence and value of the logout-location Attributes.

    Presence is tracked separately from value so compensation can restore a
    present-but-``None`` Attribute exactly instead of dropping it.
    """
    attributes = getattr(entity, "attributes", None)
    captured: dict[str, Any] = {}
    if attributes is None:
        return captured
    for key in _LOGOUT_LOCATION_ATTRIBUTES:
        if attributes.has(key):
            captured[key] = attributes.get(key)
    return captured


def _restore_logout_attributes(entity: Any, captured: Mapping[str, Any]) -> None:
    """Re-establish the exact logout-location Attribute presence and values."""
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return
    for key in _LOGOUT_LOCATION_ATTRIBUTES:
        if key in captured:
            attributes.add(key, captured[key])
        else:
            attributes.remove(key)


def _clear_logout_location_residuals(entity: Any) -> None:
    """Drop the logout-location restore targets left by the unpuppet hook."""
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return
    for key in _LOGOUT_LOCATION_ATTRIBUTES:
        attributes.remove(key)


def _restore_occupied_location(npc: Any, location: Any) -> None:
    """Return a stashed companion to its snapshotted occupied room.

    A direct location assignment reverses the framework's last-session stash
    and keeps Evennia's contents cache in step; ``move_to`` would add an
    unrelated world traversal and its movement hooks. Only a non-null snapshot
    is a restoration source.
    """
    if location is None or getattr(npc, "location", None) is location:
        return
    npc.location = location


def _materialize_wilderness_location(player: Any) -> None:
    """Give a registered wilderness body its coordinates' room before repuppet.

    A failed follow can leave the unpuppeted owner body with ``location=None``
    while the wilderness script still tracks it at its coordinates (the
    contrib recycles a room as soon as no account remains inside it). Evennia's
    ``at_pre_puppet`` would then restore the body from its logout target or
    ``home``; materializing the registered position instead keeps a release
    from reuniting a party a failed follow left apart. Best-effort: a body
    with no registration falls through to Evennia's existing restoration.
    """
    if getattr(player, "location", None) is not None:
        return
    wilderness = getattr(getattr(player, "ndb", None), "wilderness", None)
    if wilderness is None:
        return
    coordinates = wilderness.itemcoordinates.get(player)
    if coordinates is None:
        return
    wilderness.move_obj(player, coordinates)


# ---------------------------------------------------------------------------
# Seam implementations for companion-possession-transition
# ---------------------------------------------------------------------------


def _transfer_puppet(player: Any, npc: Any) -> None:
    """Transfer account puppet session from player to npc with verify-then-recover ladder.

    # possession: seam R1-transition
    """
    account = getattr(player, "account", None)
    if account is None:
        return

    sessions = _acting_sessions(player)
    if not sessions:
        raise PossessionGateError(REASON_TRANSFER_REFUSED)

    from web.webclient.actions.dispatcher import retire_sequence
    from web.webclient.presentation.ingress import (
        reset_client_sequence,
        send_unpuppet_transition,
        synchronize_session,
    )

    # Phase 2: retire/send/reset loop over ALL acting sessions
    for session in sessions:
        send_unpuppet_transition(session)
        retire_sequence(session)
        reset_client_sequence(session)

    # Phase 3: grant puppet lock ONCE, then access/puppet/verify ladder
    _grant_puppet_lock(npc, account)

    successful_sessions: list[Any] = []

    def _rollback_all(failing_session: Any) -> None:
        sessions_to_restore = list(successful_sessions)
        if failing_session not in sessions_to_restore:
            sessions_to_restore.append(failing_session)
        restore_failed = False
        for s in sessions_to_restore:
            try:
                account.puppet_object(s, player)
            except Exception:  # observability: ignore R2: best-effort recovery hop on puppet failure
                pass
            current_p = account.get_puppet(s)
            if current_p is not player:
                restore_failed = True
            synchronize_session(s, current_p)
            if hasattr(s, "msg"):
                s.msg(POSSESSION_REJECTION_MESSAGES[REASON_TRANSFER_REFUSED])
        _strip_puppet_lock(npc, account)
        if restore_failed:
            # observability: ignore R3: state-condition write error raised immediately after facade call
            log_error(
                "possession_puppet_transfer_rollback_incomplete",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "npc": str(getattr(npc, "pk", "?")),
                },
            )
            raise PossessionWriteError(REASON_WRITE_FAILED)
        raise PossessionGateError(REASON_TRANSFER_REFUSED)

    for session in sessions:
        if hasattr(npc, "access") and not npc.access(account, "puppet"):
            _rollback_all(session)

        try:
            account.puppet_object(session, npc)
        except Exception as exc:
            log_warn(
                "possession_puppet_raised",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "npc": str(getattr(npc, "pk", "?")),
                },
                exc=exc,
            )

        if account.get_puppet(session) is not npc:
            _rollback_all(session)

        successful_sessions.append(session)
        synchronize_session(session, npc)


def _mount_cmdset(npc: Any) -> None:
    """Mount trimmed possessed character cmdset onto npc.

    # possession: seam R1-transition
    """
    if npc is not None and hasattr(npc, "cmdset"):
        from commands.default_cmdsets import PossessedCharacterCmdSet

        npc.cmdset.add(PossessedCharacterCmdSet, persistent=False)


def _unmount_cmdset(npc: Any) -> None:
    """Remove possessed character cmdset from npc.

    # possession: seam R1-transition
    """
    if npc is not None and hasattr(npc, "cmdset"):
        from commands.default_cmdsets import PossessedCharacterCmdSet

        try:
            npc.cmdset.remove(PossessedCharacterCmdSet)
        except Exception:  # observability: ignore R2: cmdset unmount is best-effort idempotent cleanup
            pass


def _unpuppet(player: Any, npc: Any, reason: str = "handback") -> None:
    """Hand back account puppet session from npc to player.

    # possession: seam R1-transition
    """
    if npc is None:
        return

    account = _resolve_account(player, npc)

    if reason == "disconnect":
        if account is not None:
            for session in _acting_sessions(npc):
                try:
                    account.unpuppet_object(session)
                except Exception:  # observability: ignore R2: best-effort session unpuppet on disconnect
                    pass
            _strip_puppet_lock(npc, account)
        return

    # Evennia's last-session unpuppet stashes the character (``location = None``)
    # and records a logout restore target. Snapshot the occupied room before any
    # unpuppet so the deterministic writer can reverse that bookkeeping.
    occupied_location = getattr(npc, "location", None)

    if account is None:
        _strip_puppet_lock(npc, None)
        if occupied_location is not None:
            _clear_logout_location_residuals(npc)
        return

    sessions = _acting_sessions(npc)
    if not sessions:
        if account is not None and hasattr(getattr(account, "sessions", None), "all"):
            sessions = [
                s
                for s in account.sessions.all()
                if getattr(s, "logged_in", False)
                and getattr(s, "puppet", None) in (npc, None)
            ]

    from web.webclient.actions.dispatcher import retire_sequence
    from web.webclient.presentation.ingress import (
        reset_client_sequence,
        send_unpuppet_transition,
        synchronize_session,
    )

    for session in sessions:
        send_unpuppet_transition(session)
        retire_sequence(session)
        reset_client_sequence(session)
        try:
            account.unpuppet_object(session)
        except Exception as exc:
            log_warn(
                "possession_unpuppet_raised",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "npc": str(getattr(npc, "pk", "?")),
                },
                exc=exc,
            )
        finally:
            # A hook that stashes and then raises must not skip room restoration.
            _restore_occupied_location(npc, occupied_location)

        try:
            account.puppet_object(session, player)
        except Exception as exc:
            log_warn(
                "possession_repuppet_raised",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "player": str(getattr(player, "pk", "?")),
                },
                exc=exc,
            )

        if account.get_puppet(session) is not player:
            # observability: ignore R3: silent refusal during release raises PossessionWriteError below
            log_error(
                "possession_release_failed",
                context={
                    "char": str(getattr(player, "pk", "?")),
                    "npc": str(getattr(npc, "pk", "?")),
                    "step": "possession_release",
                },
            )
            session.msg(UNPOSSESS_REFUSED_RETURN_MESSAGE)
            synchronize_session(session, account.get_puppet(session))
            raise PossessionWriteError(
                REASON_RELEASE_REFUSED,
                "Re-puppeting player failed during possession release",
            )

        synchronize_session(session, player)

    _strip_puppet_lock(npc, account)
    if occupied_location is not None:
        _clear_logout_location_residuals(npc)


# ---------------------------------------------------------------------------
# Gate helper
# ---------------------------------------------------------------------------


def _dialogue_open(npc: Any, player: Any) -> bool:
    """Check whether ``npc`` is in an open dialogue session with anyone."""
    from typeclasses.characters import PlayerCharacter
    from world.rules.dialogue import live_dialogue_session

    session = live_dialogue_session(player)
    if session is not None and session.npc_id == getattr(npc, "pk", None):
        return True

    location = getattr(npc, "location", None)
    if location is not None and hasattr(location, "contents"):
        for obj in location.contents:
            if isinstance(obj, PlayerCharacter) and obj.pk != player.pk:
                other_sess = live_dialogue_session(obj)
                if other_sess is not None and other_sess.npc_id == getattr(npc, "pk", None):
                    return True
    return False


# ---------------------------------------------------------------------------
# Sleep-driven contextual handoff (handoff-sleeping-party-control)
# ---------------------------------------------------------------------------


#: Whether the sleeping body may hand control over, and to whom, is derived
#: from committed state only. This monotonic per-body episode counter is owned
#: by this module (the possession writer) and advanced once per voluntary sleep
#: entry, so a captured choice can never become valid again after a wake and a
#: later sleep.
SLEEP_HANDOFF_EPISODE_ATTRIBUTE = "sleep_handoff_episode"

#: Candidate semantics: returning to the owner body versus taking over an awake
#: companion.
SLEEP_HANDOFF_RETURN = "return"
SLEEP_HANDOFF_POSSESS = "possess"


@dataclass(frozen=True)
class SleepHandoffCandidate:
    """One lawful handoff choice derived from committed state."""

    dbid: int
    name: str
    kind: str
    reserve_percent: int | None


@dataclass(frozen=True)
class SleepHandoffOptions:
    """The contextual choices of one sleeping controlled body, or its reason."""

    transition_id: str | None
    candidates: tuple[SleepHandoffCandidate, ...]
    reason: str | None

    @property
    def available(self) -> bool:
        """Whether confirmation of one of ``candidates`` can be attempted."""
        return self.reason is None and bool(self.candidates)


def _sleep_posture_blocks(entity: Any) -> bool:
    """Whether one body's committed posture forbids ordinary actions."""
    from world.rules.fatigue import sleep_blocks_actions

    return sleep_blocks_actions(entity)


def _sleep_handoff_transition_id(current_body: Any, binding: Mapping[str, Any] | None) -> str:
    """Return the stable identity of the current sleep-control episode.

    The recorded episode is written by :func:`begin_sleep_handoff` once per
    voluntary sleep entry. A forced-sleep episode has no voluntary entry, so it
    falls back to its committed observation: the world tick, the posture, and
    the exact reserve. A forced wake only happens after elapsed time, so a
    later collapse can never reproduce the same identity.
    """
    from world.rules.clock import read_world_clock
    from world.rules.fatigue import read_optional_fatigue_state, SleepPosture

    attributes = getattr(current_body, "attributes", None)
    episode = None
    if attributes is not None:
        episode = attributes.get(SLEEP_HANDOFF_EPISODE_ATTRIBUTE, default=None)
    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)
    posture = SleepPosture.AWAKE.value
    reserve = 0
    try:
        state = read_optional_fatigue_state(current_body)
    except Exception:  # observability: ignore R2: a malformed reserve only degrades the fallback identity to the committed tick/posture; no state is written
        state = None
    if state is not None:
        posture = state.posture.value
        reserve = int(state.reserve_units)
    if (
        posture == SleepPosture.VOLUNTARY.value
        and isinstance(episode, int)
        and not isinstance(episode, bool)
        and episode >= 0
    ):
        return f"{int(current_body.pk)}:v:{episode}"
    since_tick = 0 if binding is None else int(binding.get("since_tick", 0))
    return f"{int(current_body.pk)}:f:{tick}:{posture}:{reserve}:{since_tick}"


def record_sleep_handoff_episode(current_body: Any) -> None:
    """Advance one body's sleep-control episode identity.

    Called after a committed voluntary-sleep posture write. A malformed prior
    value is replaced rather than trusted; the counter never decreases.
    """
    attributes = getattr(current_body, "attributes", None)
    if attributes is None:
        raise PossessionWriteError(REASON_WRITE_FAILED, "sleeping body has no attributes")
    previous = attributes.get(SLEEP_HANDOFF_EPISODE_ATTRIBUTE, default=0)
    if isinstance(previous, int) and not isinstance(previous, bool) and previous >= 0:
        episode = previous + 1
    else:
        episode = 1
    with transaction.atomic():
        attributes.add(SLEEP_HANDOFF_EPISODE_ATTRIBUTE, episode)


def _session_controls_body(session: Any, account: Any, body: Any) -> bool:
    """Whether one authenticated session currently puppets ``body``."""
    if session is None or body is None:
        return False
    if not getattr(session, "logged_in", False):
        return False
    if getattr(session, "puppet", None) is not body:
        return False
    session_account = getattr(session, "account", None)
    account_pk = getattr(session_account, "pk", None)
    return account_pk is not None and int(account_pk) == int(getattr(account, "pk", -1))


def _sleep_handoff_owner(account: Any, commander: Any, current_body: Any) -> bool:
    """Whether ``account`` is the canonical owner of ``commander``."""
    from typeclasses.characters import PlayerCharacter

    if account is None or not isinstance(commander, PlayerCharacter):
        return False
    owner = _resolve_account(commander, current_body)
    if owner is None or not hasattr(owner, "pk") or not hasattr(account, "pk"):
        return False
    return int(owner.pk) == int(account.pk)


def _account_possession_holder(account: Any) -> Any | None:
    """Return the account character holding a possession, if any."""
    if account is None:
        return None
    for char in _account_characters(account):
        if current_possession(char) is not None:
            return char
    return None


def _candidate_action_capable(candidate: Any) -> bool:
    """Awake, living, and able to act: reuse the shared capability decision."""
    from world.rules.action.gates import capability_failure
    from world.rules.buffs import blocks_action
    from world.rules.party_scope import is_knocked_out

    if _sleep_posture_blocks(candidate):
        return False
    try:
        if is_knocked_out(candidate):
            return False
        attributes = getattr(candidate, "attributes", None)
        blocked = bool(
            attributes is not None
            and attributes.has("buffs")
            and blocks_action(candidate)
        )
        return capability_failure(candidate, blocked) is None
    except Exception:  # observability: ignore R2: a candidate without readable HP is not action-capable; this display read writes nothing
        return False


def _candidate_reserve_percent(candidate: Any) -> int | None:
    """The candidate's display-only reserve percentage, or None when unknown."""
    from world.rules.fatigue import read_optional_fatigue_state, reserve_percent

    try:
        state = read_optional_fatigue_state(candidate)
    except Exception:  # observability: ignore R2: malformed physiology only leaves the display value unknown; eligibility is decided separately
        return None
    if state is None:
        return None
    return reserve_percent(state)


def _sleep_handoff_candidate(member: Any, kind: str) -> SleepHandoffCandidate:
    return SleepHandoffCandidate(
        dbid=int(member.pk),
        name=str(getattr(member, "key", "?")),
        kind=kind,
        reserve_percent=_candidate_reserve_percent(member),
    )


def _lawful_sleep_handoff_candidates(
    commander: Any, current_body: Any
) -> tuple[SleepHandoffCandidate, ...]:
    """The ordered lawful choices: awake owner first, then awake companions."""
    from world.rules.party import is_companion, live_companions

    room = getattr(commander, "location", None)
    candidates: list[SleepHandoffCandidate] = []

    def lawful(member: Any) -> bool:
        if member is current_body:
            return False
        if getattr(member, "location", None) is not room:
            return False
        if not _candidate_action_capable(member):
            return False
        if getattr(getattr(member, "db", None), "possessed_by", None) is not None:
            return False
        if member is not commander and not is_companion(member, commander):
            return False
        if _dialogue_open(member, commander):
            return False
        return True

    if current_body is not commander and lawful(commander):
        candidates.append(_sleep_handoff_candidate(commander, SLEEP_HANDOFF_RETURN))
    companions = [
        member
        for member in live_companions(commander)
        if member is not current_body and lawful(member)
    ]
    for member in sorted(companions, key=lambda obj: int(obj.pk)):
        candidates.append(_sleep_handoff_candidate(member, SLEEP_HANDOFF_POSSESS))
    return tuple(candidates)


def _sleep_handoff_options(
    account: Any, commander: Any, current_body: Any, *, session: Any = None
) -> SleepHandoffOptions:
    """Derive the contextual choices from committed state; never writes."""
    from world.rules.party import is_companion

    if not _sleep_handoff_owner(account, commander, current_body):
        return SleepHandoffOptions(None, (), REASON_SESSION_MISMATCH)

    binding = current_possession(commander)
    if current_body is commander:
        if binding is not None or getattr(getattr(commander, "db", None), "possessed_by", None) is not None:
            return SleepHandoffOptions(None, (), REASON_NOT_POSSESSING)
    else:
        if binding is None or int(binding["npc_dbid"]) != int(current_body.pk):
            return SleepHandoffOptions(None, (), REASON_NOT_POSSESSING)
        possessed_by = getattr(getattr(current_body, "db", None), "possessed_by", None)
        if not isinstance(possessed_by, int) or possessed_by != int(commander.pk):
            return SleepHandoffOptions(None, (), REASON_NOT_POSSESSING)
        if not is_companion(current_body, commander):
            return SleepHandoffOptions(None, (), REASON_NOT_POSSESSING)

    room = getattr(commander, "location", None)
    if room is None or getattr(current_body, "location", None) is not room:
        return SleepHandoffOptions(None, (), REASON_NOT_POSSESSING)
    if not _sleep_posture_blocks(current_body):
        return SleepHandoffOptions(None, (), REASON_NOT_SLEEPING)
    if session is not None and not _session_controls_body(session, account, current_body):
        return SleepHandoffOptions(None, (), REASON_SESSION_MISMATCH)

    holder = _account_possession_holder(account)
    if holder is not None and holder is not commander:
        return SleepHandoffOptions(None, (), REASON_ALREADY_POSSESSING)

    transition_id = _sleep_handoff_transition_id(current_body, binding)
    candidates = _lawful_sleep_handoff_candidates(commander, current_body)
    reason = None if candidates else REASON_NO_CANDIDATE
    return SleepHandoffOptions(transition_id, candidates, reason)


def sleep_handoff_candidates(
    account: Any, commander: Any, current_body: Any, *, session: Any = None
) -> SleepHandoffOptions:
    """Return the lawful sleep-driven handoff choices of the controlled body.

    A pure read: no time, posture, possession, draft, or session state is
    written. ``commander`` is the owner body behind the control, ``current_body``
    is the body the authenticated session currently puppets (the owner itself,
    or a possessed companion), and ``session`` — when supplied — must be the
    authenticated session that puppets that body.
    """
    return _sleep_handoff_options(account, commander, current_body, session=session)


def begin_sleep_handoff(
    account: Any, commander: Any, current_body: Any, *, session: Any = None
) -> SleepHandoffOptions:
    """Advance the sleep episode, then return its contextual choices.

    Called only after the voluntary-sleep posture has committed, so the query
    sees the committed state. An unsupported origin (an explicitly selected but
    uncontrolled member) yields no offer rather than an exception.
    """
    if not _sleep_handoff_owner(account, commander, current_body):
        return SleepHandoffOptions(None, (), REASON_SESSION_MISMATCH)
    binding = current_possession(commander)
    controlled = current_body is commander or (
        binding is not None
        and int(binding["npc_dbid"]) == int(getattr(current_body, "pk", -1))
        and getattr(getattr(current_body, "db", None), "possessed_by", None)
        == getattr(commander, "pk", None)
    )
    if not controlled:
        return SleepHandoffOptions(None, (), REASON_NOT_POSSESSING)
    record_sleep_handoff_episode(current_body)
    return _sleep_handoff_options(account, commander, current_body, session=session)


def _snapshot_owner_control(player: Any) -> dict[str, Any]:
    """Capture the owner body's location and logout bookkeeping."""
    return {
        "location": getattr(player, "location", None),
        "logout_attributes": _snapshot_logout_attributes(player),
    }


def _restore_owner_control(player: Any, snapshot: Mapping[str, Any]) -> None:
    """Restore the owner body's location and logout bookkeeping."""
    _restore_occupied_location(player, snapshot["location"])
    _restore_logout_attributes(player, snapshot["logout_attributes"])


def _restore_owner_session(player: Any, account: Any, sessions: tuple[Any, ...]) -> None:
    """Verify the owner is puppeted again on every original session.

    A transfer from the owner's own body has no possession snapshot to restore,
    so the non-transactional puppet effect is reversed here under a fresh
    sequence, exactly like the release compensation. An unverifiable restore is
    a truthful failure, never a silently divergent session.
    """
    if account is None:
        return
    from web.webclient.actions.dispatcher import retire_sequence
    from web.webclient.presentation.ingress import (
        reset_client_sequence,
        synchronize_session,
    )

    for session in sessions:
        retire_sequence(session)
        reset_client_sequence(session)
        if account.get_puppet(session) is not player:
            try:
                account.puppet_object(session, player)
            except Exception as error:
                raise PossessionWriteError(REASON_WRITE_FAILED, str(error)) from error
        if account.get_puppet(session) is not player:
            raise PossessionWriteError(
                REASON_RELEASE_REFUSED,
                "Cannot restore the owner body after a failed handoff",
            )
        synchronize_session(session, player)


def _snapshot_handoff_target(target: Any) -> dict[str, Any]:
    """Capture every control surface a contextual transfer may touch."""
    return {
        "possessed_by": deepcopy(getattr(getattr(target, "db", None), "possessed_by", None)),
        "lock": (target.locks.get("puppet") or "") if hasattr(target, "locks") else "",
        "lock_before": deepcopy(getattr(getattr(target, "db", None), "possession_lock_before", None)),
        "location": getattr(target, "location", None),
        "logout_attributes": _snapshot_logout_attributes(target),
    }


def _restore_handoff_target(target: Any, snapshot: Mapping[str, Any]) -> None:
    """Return an attempted target to its exact pre-transition control state."""
    _unmount_cmdset(target)
    if hasattr(target, "db"):
        target.db.possessed_by = snapshot["possessed_by"]
        target.db.possession_lock_before = snapshot["lock_before"]
    if hasattr(target, "locks"):
        if snapshot["lock"]:
            target.locks.add(snapshot["lock"])
        else:
            target.locks.remove("puppet")
    _restore_occupied_location(target, snapshot["location"])
    _restore_logout_attributes(target, snapshot["logout_attributes"])


def _handoff_lock_ids(account: Any, commander: Any, current_body: Any, target: Any) -> list[int]:
    ids = {int(commander.pk), int(current_body.pk), int(target.pk)}
    if account is not None:
        ids.update(int(char.pk) for char in _account_characters(account))
    return sorted(ids)


def _confirm_handoff_return(commander: Any, current_body: Any) -> None:
    """Hand control from the sleeping companion back to the awake owner."""
    release_possession(commander, npc=current_body, reason="sleep_handoff")


def _confirm_handoff_possess(commander: Any, current_body: Any, target: Any) -> None:
    """Take over ``target`` from the sleeping controlled body.

    The caller owns the outer transaction and the compensation snapshots, so
    this is exactly the two existing verified hops: release the old body (when
    there is one) and enter the new body under the validated contextual
    exception.
    """
    if current_body is not commander:
        release_possession(commander, npc=current_body, reason="sleep_handoff")
    _enter_possession(commander, target, contextual_body=current_body)


def confirm_sleep_handoff(
    account: Any,
    commander: Any,
    current_body: Any,
    candidate_id: int,
    *,
    transition_id: str,
    session: Any = None,
) -> SleepHandoffCandidate:
    """Confirm one exact contextual handoff choice.

    Every mutable gate is recomputed under the writer's row locks before any
    side effect: authenticated account/session, the currently unavailable body,
    commander, membership, co-location, awake/living/action state, account-wide
    single possession, and the exact sleep episode identity. A stale or
    ineligible choice refuses with the current choices attached; nothing is
    substituted, and no time advances.
    """
    options = sleep_handoff_candidates(account, commander, current_body, session=session)
    candidate = next(
        (item for item in options.candidates if item.dbid == int(candidate_id)), None
    )
    if options.transition_id != transition_id or candidate is None:
        raise PossessionGateError(REASON_STALE_HANDOFF, candidates=options.candidates)

    target = (
        commander
        if candidate.dbid == int(commander.pk)
        else _resolve_live_object(candidate.dbid)
    )
    if target is None:
        raise PossessionGateError(REASON_STALE_HANDOFF, candidates=options.candidates)

    old_control = snapshot_party_control(commander, current_body)
    owner_sessions = tuple(_acting_sessions(current_body))
    owner_before = _snapshot_owner_control(commander)
    target_before = _snapshot_handoff_target(target)
    attempted = False
    try:
        with transaction.atomic():
            list(
                ObjectDB.objects.select_for_update().filter(
                    id__in=_handoff_lock_ids(account, commander, current_body, target)
                )
            )
            locked = sleep_handoff_candidates(
                account, commander, current_body, session=session
            )
            locked_candidate = next(
                (item for item in locked.candidates if item.dbid == candidate.dbid), None
            )
            if locked.transition_id != transition_id or locked_candidate is None:
                raise PossessionGateError(
                    REASON_STALE_HANDOFF, candidates=locked.candidates
                )
            attempted = True
            if locked_candidate.kind == SLEEP_HANDOFF_RETURN:
                _confirm_handoff_return(commander, current_body)
            else:
                _confirm_handoff_possess(commander, current_body, target)
    except Exception as error:
        if attempted:
            # The enclosing transaction has rolled the durable mirrors back.
            # The puppet/cmdset/location effects are not transactional, so the
            # exact prior control state is restored here, outside the rollback.
            if current_body is not commander:
                restore_party_control(commander, current_body, old_control)
            else:
                # The rollback restored the durable rows, but the idmapper
                # cache still holds the attempted binding; reset both surfaces.
                restore_possession_surfaces(
                    commander, None, old_control["player"], old_control["npc"]
                )
            _restore_owner_control(commander, owner_before)
            # An owner-origin transfer has no possession snapshot to restore:
            # its own sessions must be verified back onto the owner body.
            if current_body is commander:
                _restore_owner_session(commander, account, owner_sessions)
            # Restore the attempted target LAST: repuppeting an owner session
            # unpuppets the target and stashes its occupied room again.
            if locked_candidate.kind != SLEEP_HANDOFF_RETURN:
                _restore_handoff_target(target, target_before)
        if isinstance(error, (PossessionGateError, PossessionWriteError)):
            raise
        # observability: ignore R2: the write failure is re-raised as the stable PossessionWriteError below
        raise PossessionWriteError(REASON_WRITE_FAILED, str(error)) from error

    log_info(
        "sleep_handoff",
        context={
            "char": str(getattr(commander, "pk", "?")),
            "from": str(getattr(current_body, "pk", "?")),
            "to": str(candidate.dbid),
            "kind": candidate.kind,
            "transition": transition_id,
        },
    )
    return candidate


# ---------------------------------------------------------------------------
# Core Writers
# ---------------------------------------------------------------------------


def is_possessed_actor(actor: Any) -> bool:
    """Return True if ``actor`` is an NPC currently possessed by a player."""
    val = getattr(getattr(actor, "db", None), "possessed_by", None)
    return isinstance(val, int) and not isinstance(val, bool)


def _contextual_handoff_gate(player: Any, npc: Any, contextual_body: Any) -> bool:
    """Whether the narrowly validated sleep-driven handoff exception applies.

    The exception relaxes only the combat gate. It is reachable exclusively
    through :func:`confirm_sleep_handoff`, after that function has validated the
    account/session, the unavailable sleeping body, and the exact candidate:
    every other entry gate (membership, co-location, dialogue, already
    possessing, account scope) still runs unchanged.
    """
    from world.rules.party import is_companion

    if contextual_body is None:
        return False
    if not _sleep_posture_blocks(contextual_body):
        return False
    room = getattr(player, "location", None)
    if room is None or getattr(contextual_body, "location", None) is not room:
        return False
    if getattr(npc, "location", None) is not room:
        return False
    if getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
        return False
    if _sleep_posture_blocks(npc):
        return False
    if npc is not player and not is_companion(npc, player):
        return False
    if contextual_body is not player and not is_companion(contextual_body, player):
        return False
    binding = current_possession(player)
    if binding is not None and int(binding["npc_dbid"]) != int(contextual_body.pk):
        return False
    return True


def possession_verdict(
    player: Any, npc: Any, *, contextual_body: Any = None
) -> str | None:
    """Evaluate deterministic entry gates for possessing ``npc`` from ``player``.

    Returns the rejection reason string if any gate fails, or ``None`` if all pass.
    Gates run in deterministic order:
    1. not_bound: target is a live bound companion of player
    2. not_co_located: player and npc share a non-null location
    3. in_combat: neither side is in an active combat session, unless a
       validated contextual sleep-driven handoff supplies ``contextual_body``
    4. dialogue_open: npc is not in an open dialogue session
    5. already_possessing: player, npc, or account's characters do not hold possession
    """
    from world.rules.party import is_companion

    if not is_companion(npc, player):
        return REASON_NOT_BOUND

    if player.location is None or npc.location is None or player.location != npc.location:
        return REASON_NOT_CO_LOCATED

    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(player) or is_in_active_session(npc):
        if not _contextual_handoff_gate(player, npc, contextual_body):
            return REASON_IN_COMBAT

    if _dialogue_open(npc, player):
        return REASON_DIALOGUE_OPEN

    if current_possession(player) is not None or getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
        return REASON_ALREADY_POSSESSING

    account = getattr(player, "account", None)
    if account is not None:
        for char in _account_characters(account):
            if char.pk != player.pk and current_possession(char) is not None:
                return REASON_ALREADY_POSSESSING

    return None


def _enter_possession(
    player: Any, npc: Any, *, contextual_body: Any = None
) -> None:
    """Enter possession, optionally under a validated contextual handoff."""
    verdict = possession_verdict(player, npc, contextual_body=contextual_body)
    if verdict is not None:
        raise PossessionGateError(verdict)

    account = getattr(player, "account", None)

    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)

    player_before = deepcopy(getattr(player.db, "possession", None))
    npc_before = deepcopy(getattr(npc.db, "possessed_by", None))

    try:
        with transaction.atomic():
            ids_to_lock = [player.pk, npc.pk]
            if account is not None:
                for char in _account_characters(account):
                    if char.pk not in ids_to_lock:
                        ids_to_lock.append(char.pk)
            list(ObjectDB.objects.select_for_update().filter(id__in=ids_to_lock))

            # Authoritative re-check of all mutable gates under row lock
            locked_verdict = possession_verdict(
                player, npc, contextual_body=contextual_body
            )
            if locked_verdict is not None:
                raise PossessionGateError(locked_verdict)

            player.db.possession = {
                "npc_dbid": int(npc.pk),
                "since_tick": tick,
                "account_id": (
                    int(account.pk)
                    if account is not None and hasattr(account, "pk")
                    else None
                ),
            }
            npc.db.possessed_by = int(player.pk)

            # Seam call sites: transition change mounts puppet & cmdset here
            _mount_cmdset(npc)  # possession: seam R1-transition
            _transfer_puppet(player, npc)  # possession: seam R1-transition
    except PossessionGateError:
        restore_possession_surfaces(player, npc, player_before, npc_before)
        raise
    except Exception as error:
        # Compensation for post-transfer failures
        _unmount_cmdset(npc)
        if account is not None:
            from web.webclient.presentation.ingress import synchronize_session

            for session in _acting_sessions(npc):
                try:
                    account.puppet_object(session, player)
                    synchronize_session(session, player)
                except Exception:  # observability: ignore R2: best-effort compensation on entry failure
                    pass
            _strip_puppet_lock(npc, account)
        restore_possession_surfaces(player, npc, player_before, npc_before)
        raise PossessionWriteError(REASON_WRITE_FAILED, str(error)) from error

    log_info(
        "possession_enter",
        context={
            "char": str(getattr(player, "pk", "?")),
            "npc": str(getattr(npc, "pk", "?")),
            "tick": str(tick),
        },
    )


def enter_possession(player: Any, npc: Any) -> None:
    """Enter possession of bound companion ``npc`` from ``player``.

    Gates run in deterministic order:
    1. not_bound: target is a live bound companion of player
    2. not_co_located: player and npc share a non-null location
    3. in_combat: neither side is in an active combat session
    4. dialogue_open: npc is not in an open dialogue session
    5. already_possessing: player, npc, or account's characters do not hold possession

    All writes are atomic and serialized under database row locking.
    """
    _enter_possession(player, npc)


def release_possession(
    player: Any, npc: Any | None = None, reason: str = "handback"
) -> None:
    """Release possession held by ``player`` (idempotent, atomic).

    Validates the canonical pair:
    - If player holds no possession:
      - If npc is None or unpossessed: idempotent no-op.
      - If npc is possessed by another player: raises PossessionWriteError
        (never clears someone else's possession marker).
      - If npc is possessed by this player: repairs by clearing npc.
    - If player holds possession:
      - If npc is supplied: requires npc.pk to match the recorded npc_dbid.
      - Resolves target NPC, calls reversal seams, clears mirrors atomically.
    """
    current = current_possession(player)

    if current is None:
        if npc is None:
            return
        npc_possessed_by = getattr(getattr(npc, "db", None), "possessed_by", None)
        if npc_possessed_by is None:
            return
        if int(npc_possessed_by) != int(player.pk):
            raise PossessionWriteError(
                REASON_MISMATCHED_POSSESSION,
                f"NPC {getattr(npc, 'pk', '?')} is possessed by player {npc_possessed_by}, not {getattr(player, 'pk', '?')}",
            )
        # Full lifecycle repair for partial mirror under lock
        with transaction.atomic():
            list(ObjectDB.objects.select_for_update().filter(id__in=sorted([player.pk, npc.pk])))
            _unmount_cmdset(npc)
            account = _resolve_account(player, npc)
            if account is not None:
                for session in _acting_sessions(npc):
                    try:
                        account.unpuppet_object(session)
                    except Exception:  # observability: ignore R2: best-effort session unpuppet on repair
                        pass
                _strip_puppet_lock(npc, account)
            npc.db.possessed_by = None
        return

    canonical_npc_id = current["npc_dbid"]
    if npc is not None and int(npc.pk) != int(canonical_npc_id):
        raise PossessionWriteError(
            REASON_MISMATCHED_POSSESSION,
            f"Supplied NPC {getattr(npc, 'pk', '?')} does not match recorded possession {canonical_npc_id}",
        )

    resolved_npc = npc if npc is not None else _resolve_live_object(canonical_npc_id)

    if resolved_npc is None:
        log_warn(
            "possession_orphan_repaired",
            context={
                "char": str(getattr(player, "pk", "?")),
                "npc_dbid": str(canonical_npc_id),
                "step": "orphan_repair",
            },
        )
        with transaction.atomic():
            list(ObjectDB.objects.select_for_update().filter(id=player.pk))
            player.db.possession = None
        return

    # Lock rows in deterministic ascending order before side effects
    ids_to_lock = sorted([player.pk, resolved_npc.pk])
    if reason != "disconnect":
        try:
            # A failed wilderness follow can leave the owner body location-less
            # but registered. Materialize it in this committed preparation
            # boundary, before the release transaction opens, so Evennia's
            # repuppet never restores the body from a stale logout target or
            # ``home`` and a later rollback cannot strand a rolled-back room.
            _materialize_wilderness_location(player)
        except Exception as error:
            raise PossessionWriteError(
                REASON_WRITE_FAILED,
                f"Could not materialize the owner body's wilderness location: {error}",
            ) from error
    control_before = snapshot_party_control(player, resolved_npc)

    try:
        with transaction.atomic():
            list(ObjectDB.objects.select_for_update().filter(id__in=ids_to_lock))
            # Re-verify under lock
            if current_possession(player) is None:
                return

            _unmount_cmdset(resolved_npc)
            try:
                _unpuppet(player, resolved_npc, reason=reason)
            except Exception:
                _mount_cmdset(resolved_npc)
                raise

            player.db.possession = None
            if hasattr(resolved_npc, "db"):
                if getattr(resolved_npc.db, "possessed_by", None) == int(player.pk):
                    resolved_npc.db.possessed_by = None
    except PossessionWriteError:
        restore_party_control(player, resolved_npc, control_before)
        raise
    except Exception as error:
        restore_party_control(player, resolved_npc, control_before)
        raise PossessionWriteError(REASON_WRITE_FAILED, str(error)) from error

    log_info(
        "possession_release",
        context={
            "char": str(getattr(player, "pk", "?")),
            "npc": str(getattr(resolved_npc, "pk", "?")),
            "reason": str(reason),
            "room": str(getattr(getattr(resolved_npc, "location", None), "pk", "?")),
        },
    )


def release_for_party_change(npc: Any, player: Any) -> None:
    """Full release hook called before party changes (auto-leave, dismissal, purge).

    Idempotent: if no possession exists between player and npc, returns cleanly.
    """
    if player is None or npc is None:
        return
    current = current_possession(player)
    npc_possessed = getattr(getattr(npc, "db", None), "possessed_by", None)
    if current is None and npc_possessed is None:
        return
    if current is not None and int(current.get("npc_dbid", 0)) != int(npc.pk):
        return
    if npc_possessed is not None and int(npc_possessed) != int(player.pk):
        return
    release_possession(player, npc=npc, reason="party_change")


def snapshot_party_control(player: Any, npc: Any) -> dict[str, Any]:
    """Capture control surfaces before a membership owner's outer transaction."""
    return {
        "player": deepcopy(player.db.possession),
        "npc": deepcopy(npc.db.possessed_by),
        "lock": npc.locks.get("puppet") or "",
        "lock_before": deepcopy(npc.db.possession_lock_before),
        "account": _resolve_account(player, npc),
        "sessions": tuple(_acting_sessions(npc)),
        "location": getattr(npc, "location", None),
        "logout_attributes": _snapshot_logout_attributes(npc),
    }


def restore_party_control(player: Any, npc: Any, snapshot: dict[str, Any]) -> None:
    """Restore a rolled-back handback, never reviving a retired client epoch.

    Session transfer is a non-transactional effect. Verify its inverse and
    synchronize the restored puppet under a fresh sequence, so pending work
    from either transitional puppet cannot gain authority after rollback.
    """
    restore_possession_surfaces(player, npc, snapshot["player"], snapshot["npc"])
    npc.db.possession_lock_before = snapshot["lock_before"]
    if snapshot["lock"]:
        npc.locks.add(snapshot["lock"])
    else:
        npc.locks.remove("puppet")
    if snapshot["player"] is None or snapshot["npc"] != player.pk:
        return
    # The handback ran: reverse the framework stash before any recovery puppet,
    # then re-establish the exact logout metadata after the puppet hooks (which
    # write ``prelogout_location`` again).
    _restore_occupied_location(npc, snapshot["location"])
    _mount_cmdset(npc)
    account = snapshot["account"]
    if account is None:
        _restore_logout_attributes(npc, snapshot["logout_attributes"])
        return
    from web.webclient.actions.dispatcher import retire_sequence
    from web.webclient.presentation.ingress import reset_client_sequence, synchronize_session

    try:
        for session in snapshot["sessions"]:
            retire_sequence(session)
            reset_client_sequence(session)
            if account.get_puppet(session) is not npc:
                account.puppet_object(session, npc)
            if account.get_puppet(session) is not npc:
                raise PossessionWriteError(
                    REASON_RELEASE_REFUSED, "Cannot restore possessed companion after rollback"
                )
            synchronize_session(session, npc)
    finally:
        _restore_logout_attributes(npc, snapshot["logout_attributes"])


def purge_possession_on_delete(npc: Any) -> None:
    """Free possession bindings when ``npc`` is being deleted.

    Owned entirely by possession.py to maintain the single-writer invariant.
    Resolves the recorded owner if present and runs release_for_party_change;
    if no owner resolves (orphan mirror), clears the NPC surface safely.
    """
    possessed_by = getattr(getattr(npc, "db", None), "possessed_by", None)
    if possessed_by is None:
        return
    owner = _resolve_live_object(int(possessed_by)) if isinstance(possessed_by, int) else None
    if owner is not None:
        release_for_party_change(npc, owner)
    else:
        with transaction.atomic():
            npc.db.possessed_by = None


def release_on_disconnect(account: Any) -> None:
    """Scan account characters and release any active possession (idempotent)."""
    if account is None:
        return

    # Multisession guard: if any live session of the account still puppets
    # an object holding possessed_by, possession is actively driven; do not release.
    if hasattr(getattr(account, "sessions", None), "all"):
        for sess in account.sessions.all():
            puppet = getattr(sess, "puppet", None)
            if puppet is not None and getattr(getattr(puppet, "db", None), "possessed_by", None) is not None:
                return

    # Find all characters owned by this account
    chars = _account_characters(account)

    for char in chars:
        if current_possession(char) is not None:
            try:
                release_possession(char, reason="disconnect")
            except Exception as exc:
                log_warn(
                    "possession_disconnect_release_failed",
                    context={
                        "account": str(getattr(account, "pk", "?")),
                        "char": str(getattr(char, "pk", "?")),
                    },
                    exc=exc,
                )

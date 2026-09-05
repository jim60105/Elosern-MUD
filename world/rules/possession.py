"""Deterministic companion possession writer and gates (companion-possession-rules).

This module is the SINGLE WRITER of ``player.db.possession`` (mapping
``{"npc_dbid": int, "since_tick": int}``) and ``npc.db.possessed_by``
(int dbid of the owning player character).

Documented order:
- enter: gates -> mirrored write -> puppet-transfer hook -> cmdset-mount hook -> facade info event
- release: unpuppet hook -> cmdset-unmount hook -> mirrored clear -> facade info event

The puppet-transfer and cmdset-mount hooks are documented no-op seams in this
capability (tagged with ``# possession: seam R1-transition``) and are replaced
with real transitions in ``companion-possession-transition``.
"""

from copy import deepcopy
from collections.abc import Mapping
from typing import Any

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn


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
    return chars

# Stable gate & write reason codes
REASON_NOT_BOUND = "not_bound"
REASON_NOT_CO_LOCATED = "not_co_located"
REASON_IN_COMBAT = "in_combat"
REASON_DIALOGUE_OPEN = "dialogue_open"
REASON_ALREADY_POSSESSING = "already_possessing"
REASON_HANDBACK_FIRST = "handback_first"
REASON_WRITE_FAILED = "write_failed"
REASON_MISMATCHED_POSSESSION = "mismatched_possession"

# Player-facing localized messages
POSSESSION_REJECTION_MESSAGES: dict[str, str] = {
    REASON_NOT_BOUND: "對方不是你的同伴。",
    REASON_NOT_CO_LOCATED: "對方不在這裡。",
    REASON_IN_COMBAT: "戰鬥中無法附身。",
    REASON_DIALOGUE_OPEN: "對方正在對話中，無法附身。",
    REASON_ALREADY_POSSESSING: "你目前已經在附身狀態。",
    REASON_HANDBACK_FIRST: "請先歸位再執行此操作。",
}

UNPOSSESS_RELEASED_MESSAGE = "你的意識回到了自己的身體。"


class PossessionError(RuntimeError):
    """Base error for possession failures."""


class PossessionGateError(PossessionError):
    """A deterministic entry gate refused possession."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
    return {"npc_dbid": int(npc_dbid), "since_tick": int(since_tick)}


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
# Seam call sites for companion-possession-transition
# ---------------------------------------------------------------------------


def _transfer_puppet(player: Any, npc: Any) -> None:
    """Transfer account puppet session from player to npc.

    # possession: seam R1-transition
    No-op in companion-possession-rules; companion-possession-transition
    replaces this call with the verified puppet-transfer ladder.
    """
    del player, npc


def _mount_cmdset(npc: Any) -> None:
    """Mount trimmed possessed character cmdset onto npc.

    # possession: seam R1-transition
    No-op in companion-possession-rules; companion-possession-transition
    replaces this call with the dynamic cmdset mount.
    """
    del npc


def _unmount_cmdset(npc: Any) -> None:
    """Remove possessed character cmdset from npc.

    # possession: seam R1-transition
    No-op in companion-possession-rules; companion-possession-transition
    replaces this call with the dynamic cmdset unmount.
    """
    del npc


def _unpuppet(player: Any, npc: Any) -> None:
    """Hand back account puppet session from npc to player.

    # possession: seam R1-transition
    No-op in companion-possession-rules; companion-possession-transition
    replaces this call with the unpuppet/re-puppet ladder.
    """
    del player, npc


# ---------------------------------------------------------------------------
# Gate helper
# ---------------------------------------------------------------------------


def _dialogue_open(npc: Any, player: Any) -> bool:
    """Check whether ``npc`` is in an open dialogue session with anyone."""
    from typeclasses.characters import PlayerCharacter
    from world.rules.dialogue import live_dialogue_session

    # Check caller player
    session = live_dialogue_session(player)
    if session is not None and session.npc_id == getattr(npc, "pk", None):
        return True

    # Check any player character in the same room
    location = getattr(npc, "location", None)
    if location is not None and hasattr(location, "contents"):
        for obj in location.contents:
            if isinstance(obj, PlayerCharacter) and obj != player:
                s = live_dialogue_session(obj)
                if s is not None and s.npc_id == getattr(npc, "pk", None):
                    return True

    # Check direct attribute fallback
    if getattr(getattr(npc, "db", None), "dialogue_session", None) is not None:
        return True

    return False


# ---------------------------------------------------------------------------
# Core Writers
# ---------------------------------------------------------------------------


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
    # 1. not_bound
    from world.rules.party import is_companion

    if not is_companion(npc, player):
        raise PossessionGateError(REASON_NOT_BOUND)

    # 2. not_co_located
    if (
        player.location is None
        or npc.location is None
        or player.location != npc.location
    ):
        raise PossessionGateError(REASON_NOT_CO_LOCATED)

    # 3. in_combat
    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(player) or is_in_active_session(npc):
        raise PossessionGateError(REASON_IN_COMBAT)

    # 4. dialogue_open
    if _dialogue_open(npc, player):
        raise PossessionGateError(REASON_DIALOGUE_OPEN)

    # 5. already_possessing (pre-check)
    if current_possession(player) is not None:
        raise PossessionGateError(REASON_ALREADY_POSSESSING)
    if getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
        raise PossessionGateError(REASON_ALREADY_POSSESSING)

    account = getattr(player, "account", None)
    if account is not None:
        for char in _account_characters(account):
            if char.pk != player.pk and current_possession(char) is not None:
                raise PossessionGateError(REASON_ALREADY_POSSESSING)

    # Atomic write with serialization locking
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)

    player_before = deepcopy(getattr(player.db, "possession", None))
    npc_before = deepcopy(getattr(npc.db, "possessed_by", None))

    try:
        with transaction.atomic():
            # Row-level locking to serialize concurrent possession requests
            ids_to_lock = [player.pk, npc.pk]
            if account is not None:
                for char in _account_characters(account):
                    if char.pk not in ids_to_lock:
                        ids_to_lock.append(char.pk)
            list(ObjectDB.objects.select_for_update().filter(id__in=ids_to_lock))

            # Re-verify gate 5 under the lock
            if current_possession(player) is not None:
                raise PossessionGateError(REASON_ALREADY_POSSESSING)
            if getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
                raise PossessionGateError(REASON_ALREADY_POSSESSING)
            if account is not None:
                for char in _account_characters(account):
                    if char.pk != player.pk and current_possession(char) is not None:
                        raise PossessionGateError(REASON_ALREADY_POSSESSING)

            # Mirrored write
            player.db.possession = {
                "npc_dbid": int(npc.pk),
                "since_tick": tick,
            }
            npc.db.possessed_by = int(player.pk)

            # Seam call sites: transition change mounts puppet & cmdset here
            _transfer_puppet(player, npc)  # possession: seam R1-transition
            _mount_cmdset(npc)  # possession: seam R1-transition
    except PossessionGateError:
        restore_possession_surfaces(player, npc, player_before, npc_before)
        raise
    except Exception as error:
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
        # Inconsistent mirror repair
        with transaction.atomic():
            npc.db.possessed_by = None
        return

    canonical_npc_id = current["npc_dbid"]
    if npc is not None and int(npc.pk) != int(canonical_npc_id):
        raise PossessionWriteError(
            REASON_MISMATCHED_POSSESSION,
            f"Supplied NPC {getattr(npc, 'pk', '?')} does not match recorded possession {canonical_npc_id}",
        )

    resolved_npc = npc if npc is not None else _resolve_live_object(canonical_npc_id)

    # Reversal seams: transition change unmounts cmdset & unpuppets here
    _unmount_cmdset(resolved_npc)  # possession: seam R1-transition
    _unpuppet(player, resolved_npc)  # possession: seam R1-transition

    player_before = deepcopy(getattr(player.db, "possession", None))
    npc_before = (
        deepcopy(getattr(resolved_npc.db, "possessed_by", None))
        if resolved_npc is not None
        else None
    )

    try:
        with transaction.atomic():
            player.db.possession = None
            if resolved_npc is not None:
                if getattr(resolved_npc.db, "possessed_by", None) == int(player.pk):
                    resolved_npc.db.possessed_by = None
    except Exception as error:
        restore_possession_surfaces(player, resolved_npc, player_before, npc_before)
        raise PossessionWriteError(REASON_WRITE_FAILED, str(error)) from error

    log_info(
        "possession_release",
        context={
            "char": str(getattr(player, "pk", "?")),
            "npc": str(getattr(resolved_npc, "pk", "?")),
            "reason": str(reason),
        },
    )


def release_for_party_change(npc: Any, player: Any) -> None:
    """Full release hook called before party changes (auto-leave, dismissal, purge).

    Idempotent: if no possession exists between player and npc, returns cleanly.
    """
    if player is None or npc is None:
        return
    # Only release if there is an active or partial possession involving them
    current = current_possession(player)
    npc_possessed = getattr(getattr(npc, "db", None), "possessed_by", None)
    if current is None and npc_possessed is None:
        return
    if current is not None and int(current.get("npc_dbid", 0)) != int(npc.pk):
        return
    if npc_possessed is not None and int(npc_possessed) != int(player.pk):
        return
    release_possession(player, npc=npc, reason="party_change")


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
    for char in _account_characters(account):
        if current_possession(char) is not None:
            release_possession(char, reason="disconnect")

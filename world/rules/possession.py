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
REASON_HANDBACK_FIRST = "handback_first"
REASON_WRITE_FAILED = "write_failed"
REASON_MISMATCHED_POSSESSION = "mismatched_possession"
REASON_TRANSFER_REFUSED = "transfer_refused"
REASON_RELEASE_REFUSED = "release_refused"
REASON_POSSESSED_SHOP = "possessed_shop"
REASON_POSSESSED_TALK = "possessed_talk"
REASON_POSSESSED_ENGAGE = "possessed_engage"

# D10 stable refusal messages for possessed actor
POSSESSED_REFUSAL_MESSAGES: dict[str, str] = {
    REASON_POSSESSED_SHOP: "附身狀態下無法進行交易。",
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
    REASON_HANDBACK_FIRST: "請先歸位再執行此操作。",
    REASON_TRANSFER_REFUSED: "此刻無法附身於他。",
}

UNPOSSESS_RELEASED_MESSAGE = "你的意識回到了自己的身體。"
UNPOSSESS_REFUSED_RETURN_MESSAGE = "你的身體搖搖欲墜,彷彿從很深的水裡被拉回來。"


class PossessionError(Exception):
    """Base exception for possession failures."""


class PossessionGateError(PossessionError):
    """A deterministic entry gate rejected possession."""

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

    _grant_puppet_lock(npc, account)

    sessions = _acting_sessions(player)
    if not sessions:
        if account is not None:
            _strip_puppet_lock(npc, account)
            raise PossessionGateError(REASON_TRANSFER_REFUSED)
        return

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

        if hasattr(npc, "access") and not npc.access(account, "puppet"):
            _strip_puppet_lock(npc, account)
            synchronize_session(session, player)
            session.msg(POSSESSION_REJECTION_MESSAGES[REASON_TRANSFER_REFUSED])
            raise PossessionGateError(REASON_TRANSFER_REFUSED)

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
            # Recovery ladder on refusal
            try:
                account.puppet_object(session, player)
            except Exception:  # observability: ignore R2: best-effort recovery hop on puppet failure
                pass
            _strip_puppet_lock(npc, account)
            synchronize_session(session, account.get_puppet(session))
            session.msg(POSSESSION_REJECTION_MESSAGES[REASON_TRANSFER_REFUSED])
            raise PossessionGateError(REASON_TRANSFER_REFUSED)

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

    if account is None:
        _strip_puppet_lock(npc, None)
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
# Core Writers
# ---------------------------------------------------------------------------


def is_possessed_actor(actor: Any) -> bool:
    """Return True if ``actor`` is an NPC currently possessed by a player."""
    return getattr(getattr(actor, "db", None), "possessed_by", None) is not None


def possession_verdict(player: Any, npc: Any) -> str | None:
    """Evaluate deterministic entry gates for possessing ``npc`` from ``player``.

    Returns the rejection reason string if any gate fails, or ``None`` if all pass.
    Gates run in deterministic order:
    1. not_bound: target is a live bound companion of player
    2. not_co_located: player and npc share a non-null location
    3. in_combat: neither side is in an active combat session
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
    verdict = possession_verdict(player, npc)
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
            locked_verdict = possession_verdict(player, npc)
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
    player_before = deepcopy(getattr(player.db, "possession", None))
    npc_before = (
        deepcopy(getattr(resolved_npc.db, "possessed_by", None))
        if hasattr(resolved_npc, "db")
        else None
    )

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
        restore_possession_surfaces(player, resolved_npc, player_before, npc_before)
        raise
    except Exception as error:
        # Full inverse compensation if mirror clear fails after unpuppet
        account = _resolve_account(player, resolved_npc)
        if account is not None:
            _grant_puppet_lock(resolved_npc, account)
            _mount_cmdset(resolved_npc)
            from web.webclient.presentation.ingress import synchronize_session
            for session in _acting_sessions(player):
                try:
                    account.puppet_object(session, resolved_npc)
                    synchronize_session(session, resolved_npc)
                except Exception:  # observability: ignore R2: best-effort inverse compensation
                    pass
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

    # Find all characters owned by this account or referenced by its possessed NPCs
    chars = _account_characters(account)
    for npc_obj in ObjectDB.objects.filter(db_account=account):
        possessed_by = getattr(getattr(npc_obj, "db", None), "possessed_by", None)
        if possessed_by is not None:
            owner = _resolve_live_object(int(possessed_by))
            if owner is not None and owner not in chars:
                chars.append(owner)
    if hasattr(getattr(account, "sessions", None), "all"):
        for sess in account.sessions.all():
            puppet = getattr(sess, "puppet", None)
            if puppet is not None and getattr(getattr(puppet, "db", None), "possessed_by", None) is not None:
                owner = _resolve_live_object(int(puppet.db.possessed_by))
                if owner is not None and owner not in chars:
                    chars.append(owner)

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

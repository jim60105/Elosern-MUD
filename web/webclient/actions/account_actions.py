"""Account-scoped actions and puppet-transition machinery.

This module provides the ``account.character.switch`` action adapter and the
reusable puppet-transition helper shared with new-character creation.

Architectural Contract
----------------------
1. **Synchronous Decision / Deferred Transition**:
   An action adapter must NOT perform a puppet transition inline.
   ``retire_sequence`` nulls ``session.ndb.elosern_dispatch`` and
   ``reset_client_sequence`` bumps the presentation epoch. In ``dispatcher.py``,
   ``_publish_completion`` guards on ``state.in_flight``, ``state.epoch``, and
   ``coordinator.epoch``; an inline transition trips all three clauses, causing
   the action result to be dropped completely and leaving the client in an
   uncertain state.
   Therefore, ``account.character.switch`` decides synchronously at admission
   (ownership, combat lock, already-current), returns a result-only outcome
   (``no_presentation=True``), and schedules the mechanical transition for the
   next reactor turn. The wire order becomes ``ui_action_result`` ->
   ``ui_protocol_error(no_puppet)`` -> fresh-epoch ``ui_snapshot``.

2. **Never Unpuppet First / Always Verify**:
   The transition helper does NOT call ``account.unpuppet_object(session)``
   first. Evennia's ``puppet_object`` (``evennia/accounts/accounts.py``) checks
   permissions and unpuppets the previous character internally at line 519,
   after its early guards; letting Evennia own the detach ensures that an early
   refusal leaves the current character attached.
   However, Evennia's ``MAX_NR_SIMULTANEOUS_PUPPETS`` guard can refuse *after*
   that internal unpuppet, returning silently with no exception. The helper
   must therefore verify ``account.get_puppet(session) is target`` and walk an
   explicit recovery ladder rather than assuming success.

3. **At Most One Scheduled Transition Per Session**:
   ``account.character.switch`` and ``account.character.create`` share the session-scoped
   ``session.ndb.elosern_char_transition_pending`` marker. Both adapters check it first at
   admission and refuse a second character-changing request (``transition_pending``) while a
   scheduled-but-unexecuted transition owns the session; the marker is set only after
   ``callLater`` succeeds and cleared in a ``finally`` wrapping the whole scheduled callback.
   A plain boolean suffices: the admission-time rejection makes two concurrently-scheduled
   transitions structurally impossible (see change design D2/D3), so the session-level fact
   "a transition is pending" needs no per-action or generation tracking.
"""

from typing import Any

from django.conf import settings
from twisted.internet import reactor as _default_reactor

from commands.character_creation import creation_start_screen
from web.webclient.actions.dispatcher import retire_sequence
from web.webclient.presentation.ingress import (
    reset_client_sequence,
    send_unpuppet_transition,
    synchronize_session,
)
from world.observability import log_error, log_warn
from world.rules.combat_session import is_in_active_session

# Stable codes and Traditional Chinese messages
SUCCESS_CODE = "character_switched"
SUCCESS_MESSAGE = "已切換角色。"

INVALID_CHARACTER_CODE = "invalid_character"
INVALID_CHARACTER_MESSAGE = "那不是你的角色。"

IN_COMBAT_CODE = "in_combat"
IN_COMBAT_MESSAGE = "戰鬥中無法切換角色。"
CREATE_IN_COMBAT_MESSAGE = "戰鬥中無法建立角色。"

ALREADY_CURRENT_CODE = "already_current"
ALREADY_CURRENT_MESSAGE = "你已經在這個角色上了。"

CREATE_SUCCESS_CODE = "character_created"
CREATE_SUCCESS_MESSAGE = "已建立角色。"

CHARACTER_SLOTS_FULL_CODE = "character_slots_full"
CHARACTER_SLOTS_FULL_MESSAGE = "角色數量已達上限。"

CREATE_FAILED_MESSAGE = "建立角色失敗。"

NO_ACTIVE_SESSION_CODE = "no_active_session"
NO_ACTIVE_SESSION_MESSAGE = "目前沒有作用中的會話。"

TRANSITION_PENDING_CODE = "transition_pending"
TRANSITION_PENDING_MESSAGE = "角色切換正在進行中，請稍候。"

# Player narrative recovery templates
RECOVERY_RETAINED_TEMPLATE = "角色切換未完成，你目前仍在使用「{name}」。"
RECOVERY_RESTORED_TEMPLATE = "切換角色失敗，已為你恢復至原角色「{name}」。"
RECOVERY_FAILED_MESSAGE = "角色切換失敗，你目前未附身任何角色。請使用「進入世界」重新進入遊戲。"

# The action owns no presentation panels (result-only)
AFFECTED_PANELS: tuple[str, ...] = ()

# Module-level injectable clock seam
_clock: Any = None


def get_clock() -> Any:
    """Return the active reactor or test-injected clock."""
    return _clock if _clock is not None else _default_reactor


def set_clock_for_testing(clock: Any) -> None:
    """Override the active reactor for deterministic testing."""
    global _clock
    _clock = clock


def _transition_pending(session: Any) -> bool:
    """Return True while a scheduled-but-unexecuted transition owns this session."""
    ndb = getattr(session, "ndb", None)
    return bool(getattr(ndb, "elosern_char_transition_pending", False))


def _set_transition_pending(session: Any) -> None:
    """Record that a transition is now scheduled for this session.

    Called by the adapters only after ``clock.callLater`` has returned (schedule-then-set),
    so a scheduling failure can never leave the marker set with nothing to clear it.
    """
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        ndb.elosern_char_transition_pending = True


def _clear_transition_pending(session: Any) -> None:
    """Release the session's pending marker once its scheduled callback finishes.

    Called from the ``finally`` of both scheduled callbacks, covering every exit path:
    success, early returns, recovery rungs, and uncaught exceptions.
    """
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        ndb.elosern_char_transition_pending = False


class AccountActionError(ValueError):
    """An account-scoped action payload violates its schema."""


def validate_account_character_switch_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``account.character.switch`` payload.

    Accepts exactly ``{"character_id": <int>}`` where ``character_id`` is a
    positive integer, strictly excluding booleans (as ``bool`` is an ``int``
    subclass in Python). Any missing, extra, non-integer, boolean, or
    non-positive field raises :class:`AccountActionError`.
    """
    if not isinstance(payload, dict):
        raise AccountActionError("account.character.switch payload must be an object")
    if set(payload.keys()) != {"character_id"}:
        raise AccountActionError(
            f"account.character.switch payload must contain exactly 'character_id', got {sorted(payload.keys())}"
        )
    value = payload["character_id"]
    if type(value) is not int or value <= 0:
        raise AccountActionError(
            f"'character_id' must be a positive integer, got {value!r}"
        )
    return {"character_id": value}


def validate_account_character_create_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``account.character.create`` payload.

    Requires an empty dictionary payload ({}). Any field, non-dictionary type,
    or extra keys are refused with an ``AccountActionError``.
    """
    if not isinstance(payload, dict) or len(payload) > 0:
        raise AccountActionError(
            "account.character.create accepts an empty payload"
        )
    return {}


def _send_player_msg(account: Any, session: Any, text: str) -> None:
    """Send one narrative line to the player through account.msg."""
    if account is None:
        return
    try:
        if session is not None:
            account.msg(text, session=session)
        else:
            account.msg(text)
    except Exception as exc:
        log_warn(
            "player_msg_delivery_failed",
            context={
                "account": str(getattr(account, "pk", "?")),
                "session": str(getattr(session, "sessid", "?")),
            },
            exc=exc,
        )


def _set_last_puppet(account: Any, character: Any) -> None:
    """Record a verified character as the account's last active puppet.

    Delegates exclusively to ``account.set_last_puppet`` to preserve the
    account mutation boundary.
    """
    if account is None or character is None:
        return
    setter = getattr(account, "set_last_puppet", None)
    if callable(setter):
        setter(character)


def _attach_puppet(session: Any, account: Any, target: Any) -> bool:
    """Execute the unpuppet signal, sequence reset, and puppeting call.

    Does NOT call ``account.unpuppet_object(session)`` first: Evennia's
    ``puppet_object`` handles releasing the previous puppet internally at line
    519, after its early guards. Returns True if ``get_puppet(session) is target``.
    """
    send_unpuppet_transition(session)
    retire_sequence(session)
    reset_client_sequence(session)
    try:
        account.puppet_object(session, target)
    except Exception as exc:
        log_warn(
            "puppet_object_raised",
            context={
                "account": str(getattr(account, "pk", "?")),
                "session": str(getattr(session, "sessid", "?")),
                "target": str(getattr(target, "pk", "?")),
            },
            exc=exc,
        )
        return False
    return account.get_puppet(session) is target


def _recover_transition(
    session: Any,
    account: Any,
    previous: Any,
    target: Any,
    cause: Any = None,
) -> None:
    """Execute the recovery ladder when a scheduled transition cannot complete.

    Ladder:
    1. Session still holds previous character:
       Log warning, inform player, refresh snapshot for previous puppet.
    2. Session holds no puppet, re-attaching previous succeeds:
       Log error, inform player, refresh snapshot for previous puppet.
    3. Session holds no puppet, re-attaching previous fails:
       Log error, inform player they are OOC (naming 進入世界), send no snapshot.
    4. Session holds an unexpected puppet:
       Log error, inform player, refresh snapshot for actual puppet.
    """
    actual = account.get_puppet(session) if account is not None else None
    base_context = {
        "account": str(getattr(account, "pk", "?")),
        "session": str(getattr(session, "sessid", "?")),
        "previous": str(getattr(previous, "pk", "?")),
        "target": str(getattr(target, "pk", "?")),
        "cause": str(cause) if cause is not None else "unknown",
    }

    # Rung 1: session still holds previous character
    if actual is previous:
        log_warn("char_switch_retained", context=base_context)
        prev_name = getattr(previous, "name", "角色")
        _send_player_msg(account, session, RECOVERY_RETAINED_TEMPLATE.format(name=prev_name))
        _set_last_puppet(account, previous)
        synchronize_session(session, previous)
        return

    # Rung 2 & 3: session holds no puppet
    if actual is None:
        reattach_ok = False
        try:
            reattach_ok = _attach_puppet(session, account, previous)
        except Exception as exc:
            log_warn("char_switch_reattach_raised", context=base_context, exc=exc)
            reattach_ok = False

        if reattach_ok:
            # Rung 2: repaired
            # observability: ignore R3: operational repair event following silent refusal or recovered attach
            log_error("char_switch_repaired", context=base_context)
            prev_name = getattr(previous, "name", "角色")
            _send_player_msg(account, session, RECOVERY_RESTORED_TEMPLATE.format(name=prev_name))
            _set_last_puppet(account, previous)
            synchronize_session(session, previous)
            return

        # Rung 3: terminal failure, remains detached
        # observability: ignore R3: operational terminal failure event when recovery could not restore puppet
        log_error("char_switch_recovery_failed", context=base_context)
        _send_player_msg(account, session, RECOVERY_FAILED_MESSAGE)
        return

    # Session holds an unexpected puppet (neither previous nor None)
    # observability: ignore R3: operational anomaly event when unexpected puppet holds session
    log_error(
        "char_switch_unexpected_puppet",
        context={**base_context, "actual": str(getattr(actual, "pk", "?"))},
    )
    actual_name = getattr(actual, "name", "角色")
    _send_player_msg(account, session, RECOVERY_RETAINED_TEMPLATE.format(name=actual_name))
    _set_last_puppet(account, actual)
    synchronize_session(session, actual)


def _perform_switch(
    session: Any,
    account: Any,
    character_id: int,
    previous: Any,
) -> None:
    """Scheduled transition callback executed on the reactor turn after admission.

    Re-validates committed state, verifies that the session still holds previous,
    attaches target, and handles verification or recovery.
    """
    try:
        # Verify the session still holds the puppet that admitted the switch
        current = account.get_puppet(session) if account is not None else None
        if current is not previous:
            log_warn(
                "char_switch_stale_puppet",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "previous": str(getattr(previous, "pk", "?")),
                    "actual": str(getattr(current, "pk", "?")),
                },
            )
            if current is not None:
                synchronize_session(session, current)
            return

        # Re-validate target ownership
        characters = getattr(account, "characters", None) or []
        target = None
        for char in characters:
            if getattr(char, "pk", None) == character_id or getattr(char, "id", None) == character_id:
                target = char
                break

        if target is None:
            _recover_transition(session, account, previous, previous, cause="target_no_longer_owned")
            return

        if is_in_active_session(previous):
            _recover_transition(session, account, previous, target, cause="entered_combat")
            return

        attached = False
        try:
            attached = _attach_puppet(session, account, target)
        except Exception as exc:  # observability: ignore R2: recovery ladder handles attach failure and logs facade event
            _recover_transition(session, account, previous, target, cause=exc)
            return

        if attached:
            _set_last_puppet(account, target)
            synchronize_session(session, target)
        else:
            _recover_transition(session, account, previous, target, cause="attach_verification_failed")
    finally:
        _clear_transition_pending(session)


def _account_character_switch_adapter(
    actor: Any,
    payload: dict[str, Any],
    session: Any = None,
) -> dict[str, Any]:
    """Decide account.character.switch synchronously and schedule the transition.

    Synchronously verifies ownership, combat lock, and already-current check.
    Returns a result-only success response (no_presentation=True) and schedules
    the puppet transition on the next reactor turn.
    """
    # Admission gate first: a session already owning a scheduled-but-unexecuted
    # transition is refused before any account, character, or combat lookup, so the
    # pending refusal always takes precedence over other rejection reasons.
    if _transition_pending(session):
        return {
            "outcome": "rejected",
            "code": TRANSITION_PENDING_CODE,
            "message": TRANSITION_PENDING_MESSAGE,
            "no_presentation": True,
        }

    account = getattr(actor, "account", None)
    if account is None:
        return {
            "outcome": "rejected",
            "code": INVALID_CHARACTER_CODE,
            "message": INVALID_CHARACTER_MESSAGE,
            "no_presentation": True,
        }

    if is_in_active_session(actor):
        return {
            "outcome": "rejected",
            "code": IN_COMBAT_CODE,
            "message": IN_COMBAT_MESSAGE,
            "no_presentation": True,
        }

    character_id = payload["character_id"]
    characters = getattr(account, "characters", None) or []
    target = None
    for char in characters:
        if getattr(char, "pk", None) == character_id or getattr(char, "id", None) == character_id:
            target = char
            break

    if target is None:
        return {
            "outcome": "rejected",
            "code": INVALID_CHARACTER_CODE,
            "message": INVALID_CHARACTER_MESSAGE,
            "no_presentation": True,
        }

    if target is actor or getattr(actor, "pk", None) == character_id:
        return {
            "outcome": "rejected",
            "code": ALREADY_CURRENT_CODE,
            "message": ALREADY_CURRENT_MESSAGE,
            "no_presentation": True,
        }

    clock = get_clock()
    clock.callLater(0, _perform_switch, session, account, character_id, actor)
    # Schedule-then-set: if callLater itself raised, the marker was never set, so
    # nothing can leak a permanently-pending session (design D6). The reactor cannot
    # run the callback before this call stack returns, so setting after scheduling
    # cannot race it.
    _set_transition_pending(session)

    return {
        "outcome": "success",
        "code": SUCCESS_CODE,
        "message": SUCCESS_MESSAGE,
        "no_presentation": True,
    }


def _perform_create(
    session: Any,
    account: Any,
    previous: Any,
) -> None:
    """Scheduled creation callback executed on the reactor turn after admission.

    Re-validates that the session still holds previous, re-checks capacity and combat,
    calls account.create_character() before detaching, attaches the new shell via
    _attach_puppet, and recovers without destroying the shell on failure.
    """
    try:
        # Verify the session still holds the puppet that admitted the creation
        current = account.get_puppet(session) if account is not None else None
        if current is not previous:
            log_warn(
                "char_create_stale_puppet",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "previous": str(getattr(previous, "pk", "?")),
                    "actual": str(getattr(current, "pk", "?")),
                },
            )
            if current is not None:
                synchronize_session(session, current)
            return

        # Re-validate capacity
        characters = getattr(account, "characters", None) or []
        max_chars = getattr(settings, "MAX_NR_CHARACTERS", 5)
        if len(characters) >= max_chars:
            log_warn(
                "char_create_capacity_reached",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "count": str(len(characters)),
                    "max": str(max_chars),
                },
            )
            _send_player_msg(account, session, CHARACTER_SLOTS_FULL_MESSAGE)
            return

        # Re-validate combat
        if is_in_active_session(previous):
            log_warn(
                "char_create_entered_combat",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "previous": str(getattr(previous, "pk", "?")),
                },
            )
            _send_player_msg(account, session, CREATE_IN_COMBAT_MESSAGE)
            return

        # Create the shell before any detach or puppet change
        shell = None
        errors = None
        try:
            res = account.create_character()
            if isinstance(res, tuple) and len(res) == 2:
                shell, errors = res
            else:
                shell, errors = res, None
        except Exception as exc:
            log_warn(
                "char_create_call_failed",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "previous": str(getattr(previous, "pk", "?")),
                },
                exc=exc,
            )
            _send_player_msg(account, session, CREATE_FAILED_MESSAGE)
            return

        if shell is None:
            err_summary = str(errors[:3])[:100] if isinstance(errors, (list, tuple)) else str(errors)[:100]
            log_warn(
                "char_create_rejected",
                context={
                    "account": str(getattr(account, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                    "previous": str(getattr(previous, "pk", "?")),
                    "errors": err_summary,
                },
            )
            _send_player_msg(account, session, CREATE_FAILED_MESSAGE)
            return

        # Shell created successfully; now attach the new shell
        attached = False
        try:
            attached = _attach_puppet(session, account, shell)
        except Exception as exc:  # observability: ignore R2: recovery ladder handles attach failure and logs facade event
            # A shell that was created but could not be attached is left in place, not deleted:
            # deleting it here would be a destructive write on an error branch, and the roster
            # makes the orphaned shell recoverable via account.character.switch.
            _recover_transition(session, account, previous, shell, cause=exc)
            return

        if attached:
            _set_last_puppet(account, shell)
            synchronize_session(session, shell)
            # Deliver the reusable creation start presentation. World introduction is
            # structurally not sent (login hook only).
            account.msg(creation_start_screen(), session=session)
        else:
            # A shell that was created but could not be attached is left in place, not deleted:
            # deleting it here would be a destructive write on an error branch, and the roster
            # makes the orphaned shell recoverable via account.character.switch.
            _recover_transition(
                session, account, previous, shell, cause="attach_verification_failed"
            )
    finally:
        _clear_transition_pending(session)


def _account_character_create_adapter(
    actor: Any,
    payload: dict[str, Any],
    session: Any = None,
) -> dict[str, Any]:
    """Decide account.character.create synchronously and schedule the transition.

    Synchronously verifies account existence, capacity against settings.MAX_NR_CHARACTERS,
    and combat lock. Returns a result-only success response (no_presentation=True) and
    schedules the creation and puppet transition on the next reactor turn.
    """
    # Admission gate first; see the switch adapter for the ordering rationale.
    if _transition_pending(session):
        return {
            "outcome": "rejected",
            "code": TRANSITION_PENDING_CODE,
            "message": TRANSITION_PENDING_MESSAGE,
            "no_presentation": True,
        }

    account = getattr(actor, "account", None)
    if account is None:
        return {
            "outcome": "rejected",
            "code": NO_ACTIVE_SESSION_CODE,
            "message": NO_ACTIVE_SESSION_MESSAGE,
            "no_presentation": True,
        }

    characters = getattr(account, "characters", None) or []
    max_chars = getattr(settings, "MAX_NR_CHARACTERS", 5)
    if len(characters) >= max_chars:
        return {
            "outcome": "rejected",
            "code": CHARACTER_SLOTS_FULL_CODE,
            "message": CHARACTER_SLOTS_FULL_MESSAGE,
            "no_presentation": True,
        }

    if is_in_active_session(actor):
        return {
            "outcome": "rejected",
            "code": IN_COMBAT_CODE,
            "message": CREATE_IN_COMBAT_MESSAGE,
            "no_presentation": True,
        }

    clock = get_clock()
    clock.callLater(0, _perform_create, session, account, actor)
    # Schedule-then-set; see the switch adapter (design D6).
    _set_transition_pending(session)

    return {
        "outcome": "success",
        "code": CREATE_SUCCESS_CODE,
        "message": CREATE_SUCCESS_MESSAGE,
        "no_presentation": True,
    }


__all__ = [
    "AFFECTED_PANELS",
    "ALREADY_CURRENT_CODE",
    "ALREADY_CURRENT_MESSAGE",
    "AccountActionError",
    "CHARACTER_SLOTS_FULL_CODE",
    "CHARACTER_SLOTS_FULL_MESSAGE",
    "CREATE_FAILED_MESSAGE",
    "CREATE_IN_COMBAT_MESSAGE",
    "CREATE_SUCCESS_CODE",
    "CREATE_SUCCESS_MESSAGE",
    "IN_COMBAT_CODE",
    "IN_COMBAT_MESSAGE",
    "INVALID_CHARACTER_CODE",
    "INVALID_CHARACTER_MESSAGE",
    "NO_ACTIVE_SESSION_CODE",
    "NO_ACTIVE_SESSION_MESSAGE",
    "RECOVERY_FAILED_MESSAGE",
    "RECOVERY_RESTORED_TEMPLATE",
    "RECOVERY_RETAINED_TEMPLATE",
    "SUCCESS_CODE",
    "SUCCESS_MESSAGE",
    "TRANSITION_PENDING_CODE",
    "TRANSITION_PENDING_MESSAGE",
    "_account_character_create_adapter",
    "_account_character_switch_adapter",
    "_attach_puppet",
    "_clear_transition_pending",
    "_set_transition_pending",
    "_transition_pending",
    "_perform_create",
    "_perform_switch",
    "_recover_transition",
    "get_clock",
    "set_clock_for_testing",
    "validate_account_character_create_payload",
    "validate_account_character_switch_payload",
]

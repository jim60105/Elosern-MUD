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
"""

from typing import Any

from twisted.internet import reactor as _default_reactor

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

ALREADY_CURRENT_CODE = "already_current"
ALREADY_CURRENT_MESSAGE = "你已經在這個角色上了。"

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

    return {
        "outcome": "success",
        "code": SUCCESS_CODE,
        "message": SUCCESS_MESSAGE,
        "no_presentation": True,
    }


__all__ = [
    "AFFECTED_PANELS",
    "ALREADY_CURRENT_CODE",
    "ALREADY_CURRENT_MESSAGE",
    "AccountActionError",
    "IN_COMBAT_CODE",
    "IN_COMBAT_MESSAGE",
    "INVALID_CHARACTER_CODE",
    "INVALID_CHARACTER_MESSAGE",
    "RECOVERY_FAILED_MESSAGE",
    "RECOVERY_RESTORED_TEMPLATE",
    "RECOVERY_RETAINED_TEMPLATE",
    "SUCCESS_CODE",
    "SUCCESS_MESSAGE",
    "_account_character_switch_adapter",
    "_attach_puppet",
    "_perform_switch",
    "_recover_transition",
    "get_clock",
    "set_clock_for_testing",
    "validate_account_character_switch_payload",
]

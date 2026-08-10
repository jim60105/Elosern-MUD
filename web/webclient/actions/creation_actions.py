"""Exact creation action payload validators and narrow adapters.

The five production creation actions are ``creation.preset``,
``creation.custom``, ``creation.concept``, ``creation.activate``, and
``creation.reset``. Each validator enforces an exact bounded payload shape;
each adapter re-resolves the owning account from the authenticated session's
puppet, verifies that the puppet is an owned ``PlayerCharacter`` still pending
creation, and calls only the public deterministic creation-wizard APIs
(``save_preset_draft``, ``save_custom_draft``, ``apply_concept_proposal``,
``activate_draft``, ``clear_draft``) plus the unchanged onboarding
relocation/arrival functions. No adapter assigns ``.db`` attributes, traits,
identity attributes, ``creation_pending``, or the draft directly, and no
payload accepts an actor, account, session, host, persona, skill, equipment,
magic-level, or calculated-stat field.
"""

from typing import Any

from twisted.internet.defer import Deferred

from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationError,
    CharacterCreationRequest,
)
from world.rules.creation_messages import rejection_code, rejection_message
from world.rules.creation_wizard import (
    ConceptDraftStaleError,
    activate_draft,
    apply_concept_proposal,
    clear_draft,
    draft_fingerprint,
    save_custom_draft,
    save_preset_draft,
)

# Wire limits (equal to the deterministic bounds and the panel contract).
MAX_KEY_CODE_POINTS = 64
MAX_NAME_CODE_POINTS = 80
# The concept bound mirrors the deterministic command bound
# (``commands.character_creation.MAX_CONCEPT_LENGTH``) and the generative
# layer's prompt cap; a parity test keeps all of them in lock step.
MAX_CONCEPT_CODE_POINTS = 500
# Structural age bounds. The 18 minimum is NOT enforced here: underage values
# must reach the deterministic ``_validate_adult`` inside preflight so the
# stable ``underage_age`` / ``underage_apparent_age`` codes come from the
# creation service, exactly as the adult-gate contract requires.
AGE_WIRE_MINIMUM = 0
AGE_MAXIMUM = 10000
APPARENT_AGE_WIRE_MINIMUM = 0
APPARENT_AGE_MAXIMUM = 10000
ALLOCATION_MINIMUM = 0
ALLOCATION_MAXIMUM = 10000

# Stable panels each admitted creation action may publish. ``creation.activate``
# returns no affected panels so the dispatcher publishes a full snapshot and
# the shell transitions to exploration atomically (design D5).
AFFECTED_CREATION = ("creation",)
AFFECTED_ACTIVATE = ()


class CreationActionError(ValueError):
    """A creation action payload violates its exact bounded schema."""


def _require_non_empty_string(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CreationActionError(f"{field} must be a non-empty string")
    if sum(1 for _ in value) > maximum:
        raise CreationActionError(f"{field} exceeds its bound")
    return value


def _require_int_in_range(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CreationActionError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise CreationActionError(f"{field} must be within {minimum}..{maximum}")
    return value


def _exact_single_field(payload: dict[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CreationActionError("payload must be an object")
    unknown = set(payload) - {field}
    if unknown:
        raise CreationActionError(f"payload has unknown fields {sorted(unknown)}")
    if field not in payload:
        raise CreationActionError(f"payload requires {field}")
    return payload


def validate_creation_preset_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``creation.preset`` payload (one preset key)."""
    body = _exact_single_field(payload, "preset_key")
    return {"preset_key": _require_non_empty_string(
        body["preset_key"], "preset_key", MAX_KEY_CODE_POINTS
    )}


def validate_creation_concept_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``creation.concept`` payload (one bounded concept)."""
    body = _exact_single_field(payload, "concept")
    return {"concept": _require_non_empty_string(
        body["concept"], "concept", MAX_CONCEPT_CODE_POINTS
    )}


def validate_creation_custom_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``creation.custom`` payload (the complete form)."""
    if not isinstance(payload, dict):
        raise CreationActionError("creation.custom payload must be an object")
    if set(payload) != {
        "display_name", "age", "apparent_age", "race", "subrace", "allocations",
    }:
        raise CreationActionError(
            "creation.custom requires exactly display_name, age, apparent_age, "
            "race, subrace, and allocations"
        )
    display_name = _require_non_empty_string(
        payload["display_name"], "display_name", MAX_NAME_CODE_POINTS
    )
    age = _require_int_in_range(payload["age"], "age", AGE_WIRE_MINIMUM, AGE_MAXIMUM)
    apparent_age = _require_int_in_range(
        payload["apparent_age"], "apparent_age", APPARENT_AGE_WIRE_MINIMUM, APPARENT_AGE_MAXIMUM
    )
    race = _require_non_empty_string(payload["race"], "race", MAX_KEY_CODE_POINTS)
    subrace = payload["subrace"]
    if subrace is not None:
        subrace = _require_non_empty_string(subrace, "subrace", MAX_KEY_CODE_POINTS)
    allocations = payload["allocations"]
    if not isinstance(allocations, dict) or set(allocations) != set(ALLOCATABLE_AXES):
        raise CreationActionError(
            "allocations must contain exactly the six starting axes"
        )
    checked_allocations: dict[str, int] = {}
    for axis in ALLOCATABLE_AXES:
        checked_allocations[axis] = _require_int_in_range(
            allocations[axis], axis, ALLOCATION_MINIMUM, ALLOCATION_MAXIMUM
        )
    return {
        "display_name": display_name,
        "age": age,
        "apparent_age": apparent_age,
        "race": race,
        "subrace": subrace,
        "allocations": checked_allocations,
    }


def validate_creation_activate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact empty ``creation.activate`` payload."""
    if not isinstance(payload, dict):
        raise CreationActionError("creation.activate payload must be an object")
    if payload:
        raise CreationActionError("creation.activate requires an empty payload")
    return {}


def validate_creation_reset_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact empty ``creation.reset`` payload."""
    if not isinstance(payload, dict):
        raise CreationActionError("creation.reset payload must be an object")
    if payload:
        raise CreationActionError("creation.reset requires an empty payload")
    return {}


# ---------------------------------------------------------------------------
# Adapter helpers.
# ---------------------------------------------------------------------------


def _rejected(reason: Any) -> dict[str, Any]:
    code = rejection_code(reason)
    return {"outcome": "rejected", "code": code, "message": rejection_message(reason)}


def _success(code: str, message: str, affected: tuple[str, ...]) -> dict[str, Any]:
    return {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": affected,
    }


def _pending_owner(actor: Any):
    """Return the owning account when ``actor`` is an owned pending shell.

    ``actor.account`` may be absent or may not own the puppet in a malformed
    session, so ownership is explicitly re-resolved, never assumed: a missing
    account, a non-``PlayerCharacter`` puppet, or an ownership mismatch returns
    ``None`` and the adapter rejects with a stable reason before any
    deterministic write.
    """
    account = getattr(actor, "account", None)
    if account is None:
        return None
    if not isinstance(actor, PlayerCharacter):
        return None
    try:
        if actor not in account.characters:
            return None
    except TypeError:
        return None
    return account


# ---------------------------------------------------------------------------
# Adapters.
# ---------------------------------------------------------------------------


def _creation_preset_adapter(actor: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the preset key and persist the ``preset_selected`` draft."""
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    try:
        save_preset_draft(account, actor, payload["preset_key"])
    except CharacterCreationError as error:
        return _rejected(error)
    message = "已儲存預設角色選擇。"
    return _success("preset_saved", message, AFFECTED_CREATION)


def _creation_custom_adapter(actor: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete custom form and persist the ``custom_filled`` draft."""
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    request = CharacterCreationRequest(mode="custom", **payload)
    try:
        save_custom_draft(account, actor, request)
    except CharacterCreationError as error:
        return _rejected(error)
    message = "已儲存自訂角色資料。"
    return _success("custom_saved", message, AFFECTED_CREATION)


def _creation_concept_adapter(actor: Any, payload: dict[str, Any]) -> Deferred:
    """Run the guarded concept seam and save the concept draft (D4).

    Resolves the owning account synchronously so a tampered or unowned puppet
    rejects before any client or transport work; the Deferred settles after
    the guarded ``character_creation`` layer resolves. On a valid proposal
    whose draft fingerprint still matches, the deterministic concept-apply
    service saves the ``concept_filled`` draft (including the server-owned
    persona block) and the ``creation`` panel refreshes. On degrade or a
    stale fingerprint the stable outcome is returned with zero state change.
    """
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    if not bool(getattr(actor, "creation_pending", False)):
        return _rejected("already_complete")
    from server.ai_director_service import request_character_proposal

    fingerprint = draft_fingerprint(actor)
    deferred = request_character_proposal(concept=payload["concept"])

    def _on_success(proposal):
        if proposal is None:
            # The single public degraded marker of the guarded layer.
            return _rejected("concept_unavailable")
        # Re-authorize current domain state at completion: the character could
        # have been activated or the ownership changed while the proposal was
        # in flight (webclient-action-dispatch ownership contract).
        current_account = _pending_owner(actor)
        if current_account is None:
            return _rejected("ownership_rejected")
        if not bool(getattr(actor, "creation_pending", False)):
            return _rejected("already_complete")
        try:
            apply_concept_proposal(
                current_account,
                actor,
                {
                    "race_key": proposal.race_key,
                    "subrace_key": proposal.subrace_key,
                    "allocations": dict(proposal.allocations),
                    "persona": dict(proposal.persona),
                },
                expected_fingerprint=fingerprint,
            )
        except ConceptDraftStaleError:
            return {
                "outcome": "stale",
                "code": "concept_stale",
                "message": rejection_message("concept_stale"),
            }
        except CharacterCreationError as error:
            return _rejected(error)
        message = "構想已套用，請填寫姓名與年齡完成建立。"
        return _success("concept_saved", message, AFFECTED_CREATION)

    def _on_failure(failure):
        failure.trap(Exception)
        return _rejected("concept_unavailable")

    deferred.addCallbacks(_on_success, _on_failure)
    return deferred


def _creation_activate_adapter(actor: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Atomically activate the stored draft and hand off to exploration."""
    del payload
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    try:
        result = activate_draft(account, actor)
    except CharacterCreationError as error:
        return _rejected(error)
    from world.rules.onboarding import (
        maybe_play_arrival,
        relocate_to_starting_location,
    )

    relocate_to_starting_location(actor)
    actor.msg(
        f"角色 {result.display_name} 已建立，初始魔法等級為 {result.magic_level}。"
    )
    maybe_play_arrival(actor)
    message = f"角色 {result.display_name} 已建立，初始魔法等級為 {result.magic_level}。"
    # No affected panels: the dispatcher publishes a full snapshot so the mode
    # change to exploration and every panel replacement are one atomic hand-off.
    return _success("activated", message, AFFECTED_ACTIVATE)


def _creation_reset_adapter(actor: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Idempotently clear the staging draft; the character stays pending."""
    del payload
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    if not bool(getattr(actor, "creation_pending", False)):
        return _rejected("already_complete")
    clear_draft(actor)
    message = "已清除角色草稿。"
    return _success("draft_cleared", message, AFFECTED_CREATION)


__all__ = [
    "AGE_MAXIMUM",
    "AGE_WIRE_MINIMUM",
    "ALLOCATION_MAXIMUM",
    "ALLOCATION_MINIMUM",
    "APPARENT_AGE_MAXIMUM",
    "APPARENT_AGE_WIRE_MINIMUM",
    "CreationActionError",
    "MAX_CONCEPT_CODE_POINTS",
    "MAX_KEY_CODE_POINTS",
    "MAX_NAME_CODE_POINTS",
    "validate_creation_activate_payload",
    "validate_creation_concept_payload",
    "validate_creation_custom_payload",
    "validate_creation_preset_payload",
    "validate_creation_reset_payload",
]

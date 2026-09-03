"""Exact creation action payload validators and narrow adapters.

The six production creation actions are ``creation.preset``,
``creation.custom``, ``creation.concept``, ``creation.roll_name``,
``creation.activate``, and ``creation.reset``. Each validator enforces an
exact bounded payload shape;
each adapter re-resolves the owning account from the authenticated session's
puppet, verifies that the puppet is an owned ``PlayerCharacter`` still pending
creation, and calls only the public deterministic creation-wizard APIs
(``save_preset_draft``, ``save_custom_draft``, ``activate_draft``,
``clear_draft``) plus the unchanged onboarding relocation/arrival functions.
``creation.concept`` writes nothing persistent at all: the validated proposal
lands only in the session-scoped transient slot the presentation layer renders
onto the creation panel (retool-concept-transient-fill D1). No adapter assigns
``.db`` attributes, traits, identity attributes, ``creation_pending``, or the
draft directly, and no payload accepts an actor, account, session, host, skill,
equipment, magic-level, or calculated-stat field.
"""

from random import Random
from typing import Any

from twisted.internet.defer import Deferred

from typeclasses.characters import PlayerCharacter
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    CharacterCreationError,
    CharacterCreationRequest,
    _validate_allocations,
    _validate_persona_block,
    resolve_starting_profile,
    max_affinity_elements,
)
from world.rules.creation_messages import rejection_code, rejection_message
from world.rules.creation_wizard import (
    activate_draft,
    clear_draft,
    draft_fingerprint,
    save_custom_draft,
    save_preset_draft,
)
from world.rules.namegen import roll_name_for_race

# Wire limits (equal to the deterministic bounds and the panel contract). The
# display-name limit mirrors the shared entity-key contract
# (fix-import-key-validity D3), so the adapter never accepts a name the
# deterministic creation service would reject on length alone.
MAX_KEY_CODE_POINTS = 64
MAX_NAME_CODE_POINTS = 64
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

# The character ndb key carrying the fingerprint of the draft confirmed by the
# last successful save (fix-creation-finalization-safety D2). Recorded on the
# character rather than the session so the binding survives a transport
# replacement: the webclient reconnect flow retires session state
# (``retire_sequence``), and a reconnect-resumed confirmation must still verify
# against the saved draft.
FINGERPRINT_NDB_KEY = "elosern_confirmed_draft_fingerprint"

# The session ndb key carrying the transient concept proposal slot (mirrors the
# ``session.ndb.options_state`` pattern): ``owner_actor_id`` binding, the
# session-monotonic ``revision``, and the four content keys. Lost with the
# session, cleared by a successful custom save or reset (retool-concept-
# transient-fill D1). The revision sequence lives in its own counter key so a
# consumed slot never restarts it; that counter is only ever lost with the
# session itself.
PROPOSAL_NDB_KEY = "concept_proposal"
PROPOSAL_REVISION_KEY = "concept_proposal_revision"

# The module-level unseeded RNG for ``creation.roll_name`` (design D5): a UI
# dice name is another form of typed input -- no replay semantics, so no
# seed -- and keeping the single instance here confines unseeded randomness
# to exactly this one action path. NPC-flow seeds are constructed per call by
# the deterministic core, never here.
_ROLL_NAME_RNG = Random()


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
    if set(payload) - {"sex"} != {
        "display_name", "age", "apparent_age", "race", "subrace", "allocations",
        "background", "affinity_elements", "persona",
    }:
        raise CreationActionError(
            "creation.custom requires the nine fields display_name, age, "
            "apparent_age, race, subrace, allocations, background, "
            "affinity_elements, and persona, plus an optional sex"
        )
    display_name = _require_non_empty_string(
        payload["display_name"], "display_name", MAX_NAME_CODE_POINTS
    )
    age = _require_int_in_range(payload["age"], "age", AGE_WIRE_MINIMUM, AGE_MAXIMUM)
    apparent_age = _require_int_in_range(
        payload["apparent_age"], "apparent_age", APPARENT_AGE_WIRE_MINIMUM, APPARENT_AGE_MAXIMUM
    )
    race = _require_non_empty_string(payload["race"], "race", MAX_KEY_CODE_POINTS)
    subrace = _require_non_empty_string(payload["subrace"], "subrace", MAX_KEY_CODE_POINTS)
    allocations = payload["allocations"]
    if not isinstance(allocations, dict) or set(allocations) != set(ALLOCATABLE_AXES):
        raise CreationActionError(
            "allocations must contain exactly the seven starting axes"
        )
    checked_allocations: dict[str, int] = {}
    for axis in ALLOCATABLE_AXES:
        checked_allocations[axis] = _require_int_in_range(
            allocations[axis], axis, ALLOCATION_MINIMUM, ALLOCATION_MAXIMUM
        )
    background = _validate_background(payload["background"])
    affinity_elements = _validate_affinity_elements(
        payload["affinity_elements"], race
    )
    persona = _validate_persona_payload(payload["persona"])
    # Sex is the optional tenth key (design D2): the structural layer accepts
    # omission, null, or any bounded string; membership is decided by the
    # deterministic ``_validate_sex`` in preflight -- the same wire-bounds /
    # rules-authority split as the age fields.
    sex: str | None = None
    if "sex" in payload and payload["sex"] is not None:
        sex = _require_non_empty_string(payload["sex"], "sex", MAX_KEY_CODE_POINTS)
    return {
        "display_name": display_name,
        "age": age,
        "apparent_age": apparent_age,
        "race": race,
        "subrace": subrace,
        "allocations": checked_allocations,
        "background": background,
        "affinity_elements": affinity_elements,
        "persona": persona,
        "sex": sex,
    }


def _validate_persona_payload(value: Any) -> dict[str, str] | None:
    """Validate the required nullable ``persona`` payload key.

    ``None`` passes through (the browser convention ships null when all three
    textareas are empty); any other value must be exactly the three bounded
    prose fields through the shared deterministic persona-block validator
    (retool-concept-transient-fill D3).
    """
    if value is None:
        return None
    try:
        return _validate_persona_block(value)
    except CharacterCreationError as error:
        raise CreationActionError(f"persona is malformed: {error}") from error


def _validate_affinity_elements(value: Any, race: str) -> tuple[str, ...] | None:
    """Validate one optional custom affinity set against the race bound.

    ``None`` normalizes to ``None`` (neutral); a non-list, unknown element,
    duplicate, over-bound set, or any set on an elf rejects structurally before
    the deterministic service runs (webclient-character-creation-ui D4).
    """
    if value is None:
        return None
    if not isinstance(value, list):
        raise CreationActionError("affinity_elements must be a list or null")
    if race == "elf" and value:
        raise CreationActionError(
            "an elf must not supply affinity_elements; the subrace is the authority"
        )
    maximum = max_affinity_elements(race)
    if len(value) > maximum:
        raise CreationActionError(
            f"affinity_elements exceeds the {race} maximum of {maximum}"
        )
    checked: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or entry not in ELEMENT_REGISTRY:
            raise CreationActionError(f"unknown affinity element {entry!r}")
        if entry in checked:
            raise CreationActionError(f"duplicate affinity element {entry!r}")
        checked.append(entry)
    return tuple(checked)


def _validate_background(value: Any) -> str | None:
    """Validate one optional bounded background text field.

    A missing or blank value normalizes to ``None`` (the persona record omits
    the key); a non-string or over-bound value rejects structurally before the
    deterministic service runs (webclient-character-creation-ui D4).
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise CreationActionError("background must be text or null")
    text = value.strip()
    if not text:
        return None
    if sum(1 for _ in text) > MAX_PERSONA_FIELD_LENGTH:
        raise CreationActionError("background exceeds its bound")
    return text


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


def validate_creation_roll_name_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``creation.roll_name`` payload.

    Structural layer only (design D5): exactly the three keys ``race``,
    ``subrace``, ``sex``; each is null or a 1..64-character non-empty string.
    Registry/vocabulary membership is the adapter's semantic gate, so a
    structurally valid but unknown value still reaches the roller-free
    rejection path with its stable code.
    """
    if not isinstance(payload, dict):
        raise CreationActionError("creation.roll_name payload must be an object")
    if set(payload) != {"race", "subrace", "sex"}:
        raise CreationActionError(
            "creation.roll_name requires exactly race, subrace, and sex (each "
            "null or a bounded identifier)"
        )
    checked: dict[str, str | None] = {}
    for field in ("race", "subrace", "sex"):
        value = payload[field]
        if value is None:
            checked[field] = None
        else:
            checked[field] = _require_non_empty_string(
                value, field, MAX_KEY_CODE_POINTS
            )
    return checked


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


def _confirmed_success(
    code: str,
    message: str,
    affected: tuple[str, ...],
    actor: Any,
) -> dict[str, Any]:
    """Build a success result bound to the draft that was just saved.

    ``draft_fingerprint`` is captured AFTER the deterministic save so the
    record always names the stored draft; the fingerprint is returned in the
    result and recorded as character-local state so ``creation.activate`` can
    reject a confirmation whose draft changed in between
    (fix-creation-finalization-safety D2).
    """
    fingerprint = draft_fingerprint(actor)
    setattr(actor.ndb, FINGERPRINT_NDB_KEY, fingerprint)
    return {
        **_success(code, message, affected),
        "fingerprint": fingerprint,
    }


def _invalidate_confirmation(actor: Any) -> None:
    """Drop the recorded save confirmation so a later activation is refused.

    Any failed save attempt invalidates the confirmation: the draft the player
    was trying to save was not stored, so a confirmation left over from an
    earlier successful save must not be able to activate that older draft
    (fix-creation-finalization-safety D2, webclient-character-creation-ui
    "Save rejection followed by activation is refused").
    """
    try:
        delattr(actor.ndb, FINGERPRINT_NDB_KEY)
    except AttributeError:
        pass


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
# Transient concept proposal slot.
# ---------------------------------------------------------------------------


def _store_proposal(session: Any, actor: Any, proposal: Any) -> None:
    """Overwrite the session's transient proposal slot with a fresh revision.

    The slot is a plain-data dict (never a live object reference) carrying the
    ``owner_actor_id`` binding — mirroring the options-state owner check — and
    a session-monotonic ``revision`` so the browser distinguishes a panel
    rebuild from a fresh apply even when both contents are byte-identical.
    The five optional transient-fill fields ride along only when the
    normalized proposal carried a value: an absent field is expressed as the
    key not existing (never null), so consumers keep their local defaults
    (bump-creation-panel-proposal-v3 D1).
    The sequence lives in its own ``concept_proposal_revision`` counter: a
    consumed slot (a successful custom save or reset clears it) must never
    restart the sequence, or a mounted overlay would ignore the next fresh
    apply whose revision collides with the last applied one.
    """
    ndb = getattr(session, "ndb", None)
    if ndb is None:
        return
    previous = getattr(ndb, PROPOSAL_REVISION_KEY, None)
    revision = previous + 1 if isinstance(previous, int) and not isinstance(previous, bool) else 1
    setattr(ndb, PROPOSAL_REVISION_KEY, revision)
    slot: dict[str, Any] = {
        "owner_actor_id": getattr(actor, "pk", None),
        "revision": revision,
        "race": proposal.race_key,
        "subrace": proposal.subrace_key,
        "allocations": dict(proposal.allocations),
        "persona": dict(proposal.persona),
    }
    # Absent (None) transient-fill values write no key at all; a carried
    # affinity set — including the normalized empty set (elf) — ships as a
    # plain list.
    for key in ("display_name", "age", "apparent_age", "background"):
        value = getattr(proposal, key, None)
        if value is not None:
            slot[key] = value
    affinity = getattr(proposal, "affinity_elements", None)
    if affinity is not None:
        slot["affinity_elements"] = list(affinity)
    setattr(ndb, PROPOSAL_NDB_KEY, slot)


def _clear_proposal(session: Any) -> None:
    """Idempotently drop the session's transient proposal slot.

    Only the content is consumed: the monotonic revision counter survives so
    every later apply in the same session still raises the sequence.
    """
    ndb = getattr(session, "ndb", None)
    if ndb is None:
        return
    try:
        delattr(ndb, PROPOSAL_NDB_KEY)
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# Adapters.
# ---------------------------------------------------------------------------


def _creation_preset_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Validate the preset key and persist the ``preset_selected`` draft."""
    del session
    account = _pending_owner(actor)
    if account is None:
        _invalidate_confirmation(actor)
        return _rejected("ownership_rejected")
    try:
        save_preset_draft(account, actor, payload["preset_key"])
    except CharacterCreationError as error:
        _invalidate_confirmation(actor)
        return _rejected(error)
    message = "已儲存預設角色選擇。"
    return _confirmed_success("preset_saved", message, AFFECTED_CREATION, actor)


def _creation_custom_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Validate the complete custom form and persist the ``custom_filled`` draft."""
    account = _pending_owner(actor)
    if account is None:
        _invalidate_confirmation(actor)
        return _rejected("ownership_rejected")
    persona = payload["persona"]
    request = CharacterCreationRequest(
        mode="custom",
        display_name=payload["display_name"],
        age=payload["age"],
        apparent_age=payload["apparent_age"],
        race=payload["race"],
        subrace=payload["subrace"],
        allocations=payload["allocations"],
        background=payload["background"],
        affinity_elements=payload["affinity_elements"],
        # ``.get`` for forward-compat with direct test callers of the
        # adapter; the registry validator always emits the key.
        sex=payload.get("sex"),
    )
    try:
        save_custom_draft(account, actor, request, persona=persona)
    except CharacterCreationError as error:
        _invalidate_confirmation(actor)
        return _rejected(error)
    # A successful custom save consumes any pending proposal fill: the form
    # content is now the persisted draft (retool-concept-transient-fill D1).
    _clear_proposal(session)
    message = "已儲存自訂角色資料。"
    return _confirmed_success("custom_saved", message, AFFECTED_CREATION, actor)


def _rejected_result_only(reason: Any) -> dict[str, Any]:
    """Reject a name roll without any completion presentation (design D10).

    A rejected dice click must not publish either: a snapshot or panel
    refresh would re-sync the form to the last SAVED draft and silently wipe
    the player's unsaved edits exactly like a rolled name refresh would.
    """
    return {**_rejected(reason), "no_presentation": True}


def _creation_roll_name_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Roll one display name through the rule layer with zero persistent writes.

    The semantic gate (design D5) rejects dirty input before the roller is
    ever touched: the panel offers a closed vocabulary, so an out-of-registry
    race/subrace or out-of-vocabulary sex is tampering, not an unmade choice.
    The rule-layer random-pack fallback stays reserved for the genuine
    no-race-yet case (``race`` and ``subrace`` both null).
    """
    account = _pending_owner(actor)
    if account is None:
        return _rejected_result_only("ownership_rejected")
    race = payload["race"]
    subrace = payload["subrace"]
    sex = payload["sex"]
    if race is not None and race not in RACE_REGISTRY:
        return _rejected_result_only("unknown_race")
    if subrace is not None:
        if race is None:
            return _rejected_result_only("incompatible_subrace")
        entry = SUBRACE_REGISTRY.get(subrace)
        if entry is None:
            return _rejected_result_only("unknown_subrace")
        if entry.race_key != race:
            return _rejected_result_only("incompatible_subrace")
    if sex is not None and sex not in SEX_VALUES:
        return _rejected_result_only("unknown_sex")
    display_name = roll_name_for_race(race, sex, _ROLL_NAME_RNG)
    return {
        "outcome": "success",
        "code": "name_rolled",
        "message": "已擲出一個候選名字。",
        "data": {"display_name": display_name},
        "no_presentation": True,
    }


def _creation_concept_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> Deferred:
    """Run the guarded concept seam with zero persistent writes (D1).

    Resolves the owning account synchronously so a tampered or unowned puppet
    rejects before any client or transport work; the Deferred settles after
    the guarded ``character_creation`` layer resolves. On a valid proposal the
    adapter re-authorizes the domain state, requires the session still to
    puppet the admitted actor (a late response after a puppet switch writes
    nothing), deterministically re-validates the proposal, and stores it in
    the session-scoped transient slot; the ``creation`` panel refresh carries
    it. The concept path never reads, writes, or invalidates the
    activation-confirmation fingerprint: it saves no draft, so it can neither
    preserve nor manufacture an activation authorization. On degrade the
    stable unavailable outcome is returned with zero state change.
    """
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    if not bool(getattr(actor, "creation_pending", False)):
        return _rejected("already_complete")
    from server.ai_director_service import request_character_proposal

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
        if getattr(session, "puppet", None) is not actor:
            # The session switched puppets while the proposal was in flight;
            # writing the slot would let the proposal follow the session onto
            # a different character.
            return _rejected("ownership_rejected")
        try:
            profile = resolve_starting_profile(
                proposal.race_key, proposal.subrace_key
            )
            _validate_allocations(profile, proposal.allocations)
            _validate_persona_block(proposal.persona)
        except CharacterCreationError:
            # A structurally invalid proposal is a degraded generative result
            # from the player's point of view; nothing is written.
            return _rejected("concept_unavailable")
        _store_proposal(session, actor, proposal)
        message = "構想已套用到表單，請檢查後儲存。"
        return _success("concept_applied", message, AFFECTED_CREATION)

    def _on_failure(failure):
        failure.trap(Exception)
        return _rejected("concept_unavailable")

    deferred.addCallbacks(_on_success, _on_failure)
    return deferred


def _creation_activate_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Atomically activate the stored draft and hand off to exploration.

    Activation is bound to the draft confirmed by the last successful save
    (fix-creation-finalization-safety D2): the recorded fingerprint must match
    the stored draft, otherwise the confirmation is stale (or no successful
    save ever happened) and the activation is refused with a stable code
    before any deterministic write.
    """
    del payload, session
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    if not bool(getattr(actor, "creation_pending", False)):
        return _rejected("already_complete")
    current_fingerprint = draft_fingerprint(actor)
    if current_fingerprint != "absent":
        # A draft is stored; it must be the exact one the confirmation was
        # shown for. A missing record means no successful save happened on
        # this connection's creation flow.
        recorded = getattr(actor.ndb, FINGERPRINT_NDB_KEY, None)
        if recorded is None:
            return _rejected("no_confirmed_save")
        if recorded != current_fingerprint:
            return _rejected("confirmation_stale")
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
        f"角色 {result.display_name} 已建立，初始魔力為 {result.magic_power}。"
    )
    maybe_play_arrival(actor)
    message = f"角色 {result.display_name} 已建立，初始魔力為 {result.magic_power}。"
    # No affected panels: the dispatcher publishes a full snapshot so the mode
    # change to exploration and every panel replacement are one atomic hand-off.
    return _success("activated", message, AFFECTED_ACTIVATE)


def _creation_reset_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Idempotently clear the staging draft; the character stays pending."""
    del payload
    account = _pending_owner(actor)
    if account is None:
        return _rejected("ownership_rejected")
    if not bool(getattr(actor, "creation_pending", False)):
        return _rejected("already_complete")
    clear_draft(actor)
    _clear_proposal(session)
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
    "validate_creation_roll_name_payload",
]

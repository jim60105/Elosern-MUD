"""Rules-owned admission for a pending character's draft portrait request.

A character inside creation has no canonical identity, so the ordinary gallery
seam cannot compose its portrait. This module owns the one admission path that
bypasses that precondition — ``creation.portrait.generate`` — and it does so
without writing any canonical identity:

- the submitted draft values are validated through the pure
  ``world.rules.creation_identity`` rules and the shared gallery prompt
  validator, before any policy, receipt or queue write;
- a known art-service unavailability is refused retryably through the existing
  bounded connectivity probe, also before any write;
- admission runs inside ONE unit ordered as deferred commit callbacks -> the
  shared queue serialization -> one database transaction -> the gallery lock.
  Ownership and pending state are rechecked in that unit, the in-flight request
  is rejected before the policy write, the retained creation image is derived
  from the prior receipt plus the actual gallery reads, the shared named
  policy is established, and exactly one image job plus the bounded
  ``creation_portrait`` receipt are written and committed before the queue
  serialization is released;
- commit callbacks that take locks are deferred past that release, and a
  failed request restores the affected attribute caches and leaves no policy,
  receipt or job behind.

``world.art/`` stays the sole writer of queue/asset records and this module only
requests one image through its common seam. Deferred callbacks are drained
after lock release, so no publication or automatic ensure can reacquire queue
serialization while this admission holds it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.art import connectivity
from world.art.gallery import cards_for
from world.art.gallery_fallback import band_key_for
from world.art.gallery_prompt import GalleryPromptError, validate_custom_prompt
from world.art.queue import _gallery_job_in_flight_locked
from world.art.service import request_gallery_image, serialized_gallery_mutation
from world.art.subjects import DraftPortraitValues, named_character_subject
from world.rules.character_creation import ensure_player_portrait_policy
from world.rules.creation_identity import (
    CharacterCreationError,
    DraftIdentity,
    resolve_draft_identity,
)
from world.rules.creation_messages import rejection_message
from world.rules.presentation_events import defer_publication_callbacks
from world.rules.surfaces import restore_attributes, snapshot_attributes

#: The one bounded receipt attribute the rules owner writes. It holds no
#: prompt text and no identity copy: only the version, the latest admitted
#: image id, the retained readable creation image id, and the ready-descriptor
#: fallback key.
CREATION_PORTRAIT_ATTRIBUTE = "creation_portrait"
CREATION_PORTRAIT_VERSION = 1

#: The attributes the failed-request rollback must restore in process: Django
#: restores the durable rows, but Evennia's idmapped attribute values stay
#: readable after a rollback, so the snapshots are written back.
_ROLLBACK_ATTRIBUTE_KEYS = ("portrait_policy", CREATION_PORTRAIT_ATTRIBUTE)

#: The stable rejection code the panel and the adapter share for a server
#: verdict that is known-unavailable. It is retryable: nothing is stored.
PORTRAIT_SERVICE_UNAVAILABLE = "portrait_service_unavailable"


class PortraitServiceUnavailable(CharacterCreationError):
    """Raised when the art service is known-unavailable for this admission."""


class PortraitInFlight(CharacterCreationError):
    """Raised when the character already has a portrait generation in flight."""


@dataclass(frozen=True)
class DraftPortraitRequest:
    """One submitted pending-character portrait request (structurally valid).

    The adapter validates the exact payload shape; this module validates the
    semantics (registry membership, compatibility, permitted sex, age bounds,
    prompt) before it writes anything.
    """

    race: str
    subrace: str
    sex: str
    apparent_age: int
    custom_prompt: str = ""


@dataclass(frozen=True)
class DraftPortraitAdmission:
    """One admitted draft portrait: the minted job and its bounded receipt."""

    image_id: str
    retained_image_id: str | None
    fallback_key: str
    identity: DraftIdentity


@dataclass(frozen=True)
class PortraitServiceAvailability:
    """The read-only availability snapshot a creation presenter may project.

    ``available`` is false only for a CURRENT failed cache verdict; an absent,
    expired or configuration-mismatched verdict never manufactures
    unavailability. No endpoint, credential, timestamp or prompt enters it.
    """

    available: bool
    reason: str | None = None


def _require_owned_pending(account: Any, character: Any) -> None:
    """Recheck ownership, player type and pending state without writing.

    Imported lazily: the typeclasses layer depends on world state, and this
    module is imported by the action layer, which already imports both.
    """
    from typeclasses.characters import PlayerCharacter

    if account is None or not isinstance(character, PlayerCharacter):
        raise CharacterCreationError("character is not owned by this account")
    try:
        owned = character in account.characters
    except TypeError:  # observability: ignore R2: a malformed account roster owns nothing
        owned = False
    if not owned:
        raise CharacterCreationError("character is not owned by this account")
    if not bool(getattr(character, "creation_pending", False)):
        raise CharacterCreationError("character creation is already complete")


def _prior_receipt(character: Any) -> dict | None:
    """The bounded prior receipt, or ``None`` when absent or malformed."""
    value = character.db.creation_portrait if hasattr(character, "db") else None
    if value is None or not hasattr(value, "get"):
        return None
    value = dict(value)
    if value.get("version") != CREATION_PORTRAIT_VERSION:
        return None
    image_id = value.get("image_id")
    retained = value.get("retained_image_id")
    fallback = value.get("fallback_key")
    if not isinstance(image_id, str) or not isinstance(fallback, str):
        return None
    if retained is not None and not isinstance(retained, str):
        return None
    return {
        "image_id": image_id,
        "retained_image_id": retained,
        "fallback_key": fallback,
    }


def _retained_image_id(prior: dict | None, valid_card_ids: set[str]) -> str | None:
    """The last READABLE creation-owned card the next request may replace.

    The prior receipt's newest admitted id names the latest request, which may
    have FAILED; only an id that resolves to a real card is replaceable.
    Falling back to the receipt's retained id keeps the last successful card
    across any number of failed attempts, and an unrelated gallery default is
    never adopted.
    """
    if prior is None:
        return None
    for key in ("image_id", "retained_image_id"):
        candidate = prior.get(key)
        if isinstance(candidate, str) and candidate in valid_card_ids:
            return candidate
    return None


def read_portrait_service_availability() -> PortraitServiceAvailability:
    """The read-only cached verdict for the creation portrait control.

    Reads the existing single connectivity cache through its pure snapshot
    reader: no client construction, no probe, no cache write and no expiry
    extension. Presenters and drawers call ONLY this; the request path is the
    only caller of ``probe``.
    """
    verdict = connectivity.read_cached_probe()
    if verdict is None or verdict.ok:
        return PortraitServiceAvailability(available=True)
    return PortraitServiceAvailability(
        available=False,
        reason=rejection_message(PORTRAIT_SERVICE_UNAVAILABLE),
    )


def request_draft_portrait(
    account: Any, character: Any, request: DraftPortraitRequest
) -> DraftPortraitAdmission:
    """Admit exactly one portrait request for an owned pending character.

    Validation order is deliberate: structural/domain validation, then the
    read-only ownership/pending check, then the bounded connectivity verdict —
    all BEFORE the queue serialization or the database transaction opens — so a
    rejected request leaves no policy, receipt, draft, confirmation, card or
    job behind. The serialized unit then rechecks ownership/pending, rejects an
    in-flight job before establishing the policy, and commits the policy, the
    one job and the receipt together.
    """
    if not isinstance(request, DraftPortraitRequest):
        raise CharacterCreationError("malformed portrait request")
    identity = resolve_draft_identity(
        request.race, request.subrace, request.sex, request.apparent_age
    )
    try:
        custom = validate_custom_prompt(request.custom_prompt)
    except GalleryPromptError as error:
        # One rejection surface: the shared prompt validator's stable message
        # is preserved verbatim, so ``creation_messages`` maps it to the
        # bounded prompt reason.
        raise CharacterCreationError(str(error)) from error
    _require_owned_pending(account, character)
    verdict = connectivity.probe(force=False)
    if not verdict.ok:
        raise PortraitServiceUnavailable(
            "the art service is currently unavailable for portrait requests"
        )
    subject = named_character_subject(character)
    draft_values = DraftPortraitValues.from_identity(identity)
    with defer_publication_callbacks() as deferral:
        with serialized_gallery_mutation(subject) as token:
            snapshots = snapshot_attributes(character, _ROLLBACK_ATTRIBUTE_KEYS)
            try:
                with transaction.atomic():
                    _require_owned_pending(account, character)
                    if _gallery_job_in_flight_locked(subject):
                        raise PortraitInFlight(
                            "a portrait request is already in flight for this character"
                        )
                    prior = _prior_receipt(character)
                    valid_ids = {
                        str(card["image_id"])
                        for card in cards_for(subject)
                        if isinstance(card.get("image_id"), str)
                    }
                    retained = _retained_image_id(prior, valid_ids)
                    ensure_player_portrait_policy(character)
                    fallback_key = band_key_for(
                        subject.full(), identity.sex, identity.apparent_age
                    )
                    image_id = request_gallery_image(
                        character,
                        custom_prompt=custom,
                        draft_values=draft_values,
                        mutation_token=token,
                        replacement_image_id=retained,
                    )
                    character.db.creation_portrait = {
                        "version": CREATION_PORTRAIT_VERSION,
                        "image_id": image_id,
                        "retained_image_id": retained,
                        "fallback_key": fallback_key,
                    }
                    admission = DraftPortraitAdmission(
                        image_id=image_id,
                        retained_image_id=retained,
                        fallback_key=fallback_key,
                        identity=identity,
                    )
            except BaseException:
                # The mutation did not commit: nothing may stay readable in
                # process, and no deferred publication may escape. Callback
                # failures happen AFTER this block (at the deferral scope's
                # exit) and therefore can never restore a committed admission.
                deferral.discard()
                restore_attributes(character, snapshots)
                raise
    return admission


__all__ = [
    "CREATION_PORTRAIT_ATTRIBUTE",
    "CREATION_PORTRAIT_VERSION",
    "DraftPortraitAdmission",
    "DraftPortraitRequest",
    "PORTRAIT_SERVICE_UNAVAILABLE",
    "PortraitInFlight",
    "PortraitServiceAvailability",
    "PortraitServiceUnavailable",
    "read_portrait_service_availability",
    "request_draft_portrait",
]

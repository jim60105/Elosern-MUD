"""Private creative authoring records: drafts and confirmed request versions.

This module owns the W3 authoring boundary. A draft is a private record of a
negotiated creative direction; a confirmed version is an immutable, versioned
:class:`~world.narrative.models.CreativeRequest` that passed deterministic
validation before scheduling. Authoring data is never in-world knowledge: it
confers no clues, items, quest progress, persistent stat changes, skill
advancement, buffs, or codex unlocks, and it never becomes a ``MemoryRecord``.

Determinism and durability:

- Validation reads only durable rows (referenced threads and committed history
  references) and performs no generation, so confirmation works with every
  generation service offline. Nothing in this module imports ``world.ai``.
- ``draft.confirmed_revision == draft.revision`` means the current version is
  confirmed; editing the draft advances ``revision`` and makes the new version
  unconfirmed again, so editing always requires a new confirmation.
- "Submit once" is enforced by two unique indexes, not by the row lock:
  ``CreativeRequest.submission_key`` (derived from ``draft_id`` and ``version``)
  and ``(draft, version)``. ``select_for_update`` is kept for backends that
  support it, but correctness never depends on it. Do not remove either unique
  constraint as an "optimization".
- A rejected direction changes no durable state. The rejection reason is
  recomputed deterministically by :func:`validate_direction` from the draft's
  stored direction, so the draft itself is the durable record that the content
  remains unconfirmed; there is no stored rejection reason to fall out of sync
  with the content or to leak into logs.
- Boundary events carry identifiers, counts and reason codes only. Player-facing
  prose (a :class:`DirectionReason` message) is returned to the caller and never
  logged.

The last explicitly confirmed version stays authoritative until a newer version
is confirmed; an unconfirmed edit does not retract it, because approval is
explicit (see the approved design, §6.2-6.3).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from django.db import transaction

from world.narrative.models import (
    AuthoringDraft,
    CreativeRequest,
    NarrativeEvent,
    StoryThread,
)
from world.narrative.threads import (
    TERMINAL_THREAD_STATES,
    find_thread,
    thread_accessible,
)
from world.observability import log_info, log_warn

MAX_DRAFT_ID_LENGTH = 128
MAX_OWNER_ID_LENGTH = 255
MAX_SUBMISSION_KEY_LENGTH = 160
MAX_SUMMARY_CHARACTERS = 2000
MAX_LIST_ITEMS = 32
MAX_ITEM_CHARACTERS = 200
MAX_DIRECTION_BYTES = 65536
MAX_SOURCES = 16
MAX_SOURCE_KIND_CHARACTERS = 32
MAX_SOURCE_REF_CHARACTERS = 255

VALID_DIRECTION_KINDS = frozenset({"new_story", "thread_direction"})
REWRITE_ASPECTS = frozenset({"history", "personality", "outcome"})
DIRECTION_KEYS = frozenset(
    {
        "summary",
        "themes",
        "atmosphere",
        "participants",
        "emphasis",
        "exclusions",
        "kind",
        "thread_id",
        "effects",
        "revisions",
    }
)
TEXT_LIST_FIELDS = ("themes", "atmosphere", "emphasis", "exclusions")

# Concrete reason codes. Messages are player-facing prose; codes are the
# stable identifiers used in logs and by callers.
REASON_MESSAGES: dict[str, str] = {
    "malformed_direction": "夢境方向的內容不完整或超出長度限制。",
    "malformed_participants": "夢境方向的參與者名單不完整或重複。",
    "unknown_direction_kind": "夢境方向必須是新故事或既有故事線的走向。",
    "unexpected_thread": "新故事的方向不應指定既有故事線。",
    "unknown_thread": "找不到指定的故事線，無法沿用它的走向。",
    "inaccessible_thread": "這條故事線不屬於你的角色，無法調整它的走向。",
    "terminal_thread": "這條故事線已經結束，無法再調整它的走向。",
    "unknown_reference": "指定的既存事件或記憶並不存在。",
    "committed_history_rewrite": "已發生的事件無法被改寫，只能描述往後的新發展。",
    "established_personality_rewrite": "既有的性格無法被改寫，只能描寫新的反應與關係。",
    "deterministic_outcome_rewrite": "既定的結果無法被改寫。",
    "unauthorized_effects": "夢境僅能描述故事方向，不能給予線索、物品、任務進度、屬性、技能、增益或圖鑑解鎖。",
}
REWRITE_REASON_CODES = {
    "history": "committed_history_rewrite",
    "personality": "established_personality_rewrite",
    "outcome": "deterministic_outcome_rewrite",
}


class AuthoringError(Exception):
    """Base exception for private authoring records."""


class AuthoringAccessError(AuthoringError):
    """Raised when the actor does not own the requested authoring record."""


class AuthoringConflictError(AuthoringError):
    """Raised when a submission identity belongs to a different request."""


@dataclass(frozen=True)
class DirectionReason:
    """One concrete, deterministic rejection reason."""

    code: str
    message: str


@dataclass(frozen=True)
class DirectionValidation:
    """The deterministic outcome of validating one desired direction."""

    valid: bool
    reasons: tuple[DirectionReason, ...]
    direction: dict[str, Any]

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason.code for reason in self.reasons)


class DirectionValidationError(AuthoringError):
    """A refused confirmation: a concrete reason, no durable state change."""

    def __init__(self, reasons: Iterable[DirectionReason]):
        self.reasons = tuple(reasons)
        codes = ", ".join(reason.code for reason in self.reasons) or "unknown"
        super().__init__(f"Creative direction rejected: {codes}")

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason.code for reason in self.reasons)


@dataclass(frozen=True)
class CollaboratorBrief:
    """Spoiler-filtered creative preferences for the collaborator capability.

    Only the explicitly confirmed direction's preference fields and summary are
    exposed: no source references, no validation internals, no other owner's
    data, and no StoryDirector-hidden answers (this record model has none).
    """

    owner_id: str
    submission_key: str
    version: int
    summary: str
    themes: tuple[str, ...]
    atmosphere: tuple[str, ...]
    participants: tuple[str, ...]
    emphasis: tuple[str, ...]
    exclusions: tuple[str, ...]


def _clean_owner_id(owner_id: Any) -> str:
    clean = str(owner_id).strip()
    if not clean or len(clean) > MAX_OWNER_ID_LENGTH:
        raise AuthoringError(
            f"owner_id must contain 1..{MAX_OWNER_ID_LENGTH} characters."
        )
    return clean


def _clean_draft_id(draft_id: Any) -> str:
    clean = str(draft_id).strip()
    if not clean or len(clean) > MAX_DRAFT_ID_LENGTH:
        raise AuthoringError(
            f"draft_id must contain 1..{MAX_DRAFT_ID_LENGTH} characters."
        )
    return clean


def _json_copy(value: Any, *, label: str, max_bytes: int) -> Any:
    """Freeze caller-supplied authoring content into detached plain JSON."""
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise AuthoringError(f"{label} must be plain JSON data.") from error
    if len(serialized.encode("utf-8")) > max_bytes:
        raise AuthoringError(f"{label} exceeds {max_bytes} bytes.")
    return json.loads(serialized)


def _normalize_sources(sources: Iterable[Any]) -> list[dict[str, str]]:
    """Validate and normalize durable source references (kind + ref)."""
    raw = list(sources or [])
    if len(raw) > MAX_SOURCES:
        raise AuthoringError(f"sources must contain at most {MAX_SOURCES} entries.")
    normalized: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise AuthoringError("Each source entry must be a mapping of kind and ref.")
        kind = str(item.get("kind", "")).strip()
        ref = str(item.get("ref", "")).strip()
        if (
            not kind
            or not ref
            or len(kind) > MAX_SOURCE_KIND_CHARACTERS
            or len(ref) > MAX_SOURCE_REF_CHARACTERS
        ):
            raise AuthoringError("Each source entry needs a bounded kind and ref.")
        normalized.append({"kind": kind, "ref": ref})
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in normalized:
        key = (entry["kind"], entry["ref"])
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


def _reasons(*codes: str) -> tuple[DirectionReason, ...]:
    return tuple(DirectionReason(code, REASON_MESSAGES[code]) for code in codes)


def _invalid(*codes: str) -> DirectionValidation:
    return DirectionValidation(valid=False, reasons=_reasons(*codes), direction={})


def _validate_text_list(value: Any) -> Optional[list[str]]:
    """Return the stripped list, or None when the field is not a text list."""
    if not isinstance(value, list) or len(value) > MAX_LIST_ITEMS:
        return None
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        clean = item.strip()
        if not clean or len(clean) > MAX_ITEM_CHARACTERS:
            return None
        items.append(clean)
    return items


def _history_reference_exists(ref: str) -> bool:
    """A committed-history target must be a durable event, memory, or thread row."""
    if NarrativeEvent.objects.filter(source_id=ref).exists():
        return True
    if StoryThread.objects.filter(thread_id=ref).exists():
        return True
    prefix, separator, pk = ref.partition(":")
    return bool(separator) and prefix == "mem" and pk.isdigit()


def validate_direction(direction: Any, *, owner_id: str) -> DirectionValidation:
    """Deterministically validate a desired direction for one owner.

    Returns a :class:`DirectionValidation`; an invalid result carries concrete
    reasons and a normalized direction of ``{}``. Reads durable rows only, so it
    is fully available offline.
    """
    clean_owner = _clean_owner_id(owner_id)
    if not isinstance(direction, Mapping):
        return _invalid("malformed_direction")
    if set(direction) - DIRECTION_KEYS:
        return _invalid("malformed_direction")

    summary = direction.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary.strip()) > MAX_SUMMARY_CHARACTERS:
        return _invalid("malformed_direction")

    theme_lists: dict[str, list[str]] = {}
    for field in TEXT_LIST_FIELDS:
        items = _validate_text_list(direction.get(field, []))
        if items is None:
            return _invalid("malformed_direction")
        theme_lists[field] = items

    participants = _validate_text_list(direction.get("participants", []))
    if participants is None or len(set(participants)) != len(participants):
        return _invalid("malformed_participants")

    kind = direction.get("kind")
    if not isinstance(kind, str) or kind not in VALID_DIRECTION_KINDS:
        return _invalid("unknown_direction_kind")

    thread_id = direction.get("thread_id")
    if kind == "thread_direction":
        if not isinstance(thread_id, str) or not thread_id.strip():
            return _invalid("malformed_direction")
    elif thread_id not in (None, ""):
        return _invalid("unexpected_thread")

    effects = direction.get("effects", [])
    if effects is None:
        effects = []
    if not isinstance(effects, list) or not all(isinstance(item, str) for item in effects):
        return _invalid("malformed_direction")
    if effects:
        return _invalid("unauthorized_effects")

    raw_revisions = direction.get("revisions", [])
    if raw_revisions is None:
        raw_revisions = []
    if not isinstance(raw_revisions, list) or len(raw_revisions) > MAX_LIST_ITEMS:
        return _invalid("malformed_direction")
    revisions: list[dict[str, str]] = []
    for item in raw_revisions:
        if not isinstance(item, Mapping):
            return _invalid("malformed_direction")
        aspect = str(item.get("aspect", "")).strip()
        ref = str(item.get("ref", "")).strip()
        if aspect not in REWRITE_ASPECTS or not ref or len(ref) > MAX_SOURCE_REF_CHARACTERS:
            return _invalid("malformed_direction")
        revisions.append({"aspect": aspect, "ref": ref})

    canonical_thread_id: Optional[str] = None
    if kind == "thread_direction":
        thread = find_thread(thread_id)
        if thread is None:
            return _invalid("unknown_thread")
        if not thread_accessible(thread, clean_owner):
            return _invalid("inaccessible_thread")
        if thread.state in TERMINAL_THREAD_STATES:
            return _invalid("terminal_thread")
        canonical_thread_id = thread.thread_id

    missing = [
        item["ref"]
        for item in revisions
        if item["aspect"] == "history" and not _history_reference_exists(item["ref"])
    ]
    if missing:
        return _invalid("unknown_reference")

    rewrite_codes = sorted({REWRITE_REASON_CODES[item["aspect"]] for item in revisions})
    if rewrite_codes:
        return _invalid(*rewrite_codes)

    normalized: dict[str, Any] = {
        "summary": summary.strip(),
        "participants": participants,
        "kind": kind,
        "thread_id": canonical_thread_id,
        "effects": [],
        "revisions": revisions,
    }
    normalized.update(theme_lists)
    return DirectionValidation(valid=True, reasons=(), direction=normalized)


def submission_key_for(draft_id: Any, version: int) -> str:
    """The unique submission identity of one confirmed draft version."""
    return f"{_clean_draft_id(draft_id)}:v{int(version)}"


def find_draft(draft_id: Any) -> Optional[AuthoringDraft]:
    """Tolerant lookup: the draft, or None when it is absent or malformed."""
    clean = str(draft_id).strip()
    if not clean or len(clean) > MAX_DRAFT_ID_LENGTH:
        return None
    return AuthoringDraft.objects.filter(draft_id=clean).first()


def get_draft(draft_id: Any, owner_id: Any) -> AuthoringDraft:
    """Owner-scoped read; a foreign or missing draft is not visible."""
    clean_owner = _clean_owner_id(owner_id)
    draft = find_draft(draft_id)
    if draft is None or draft.owner_id != clean_owner:
        raise AuthoringAccessError("This authoring draft is not yours.")
    return draft


def list_drafts(owner_id: Any) -> list[AuthoringDraft]:
    """The owner's drafts, in durable creation order."""
    return list(AuthoringDraft.objects.filter(owner_id=_clean_owner_id(owner_id)).order_by("id"))


def draft_is_confirmed(draft: AuthoringDraft) -> bool:
    """True when the draft's current revision is the confirmed version."""
    return draft.confirmed_revision is not None and int(draft.confirmed_revision) == int(draft.revision)


def save_draft(
    *,
    owner_id: Any,
    direction: Any,
    sources: Optional[Iterable[Any]] = None,
    tick: int = 0,
    draft_id: Optional[str] = None,
) -> AuthoringDraft:
    """Create or content-update one private draft.

    Content is never silently discarded: supplying different content for an
    existing ``draft_id`` is an effective edit that advances ``revision`` (so the
    version is unconfirmed again until a new confirmation), and an identical save
    is a no-op. ``sources=None`` keeps the stored references on update; pass a
    list to replace them.
    """
    clean_owner = _clean_owner_id(owner_id)
    if not isinstance(direction, Mapping):
        raise AuthoringError("direction must be a JSON object.")
    frozen_direction = _json_copy(
        dict(direction), label="direction", max_bytes=MAX_DIRECTION_BYTES
    )
    frozen_sources = None if sources is None else _normalize_sources(sources)
    handle = _clean_draft_id(draft_id) if draft_id is not None else uuid4().hex

    with transaction.atomic():
        existing = AuthoringDraft.objects.filter(draft_id=handle).first()
        if existing is not None:
            if existing.owner_id != clean_owner:
                raise AuthoringAccessError("This authoring draft is not yours.")
            changed = existing.direction != frozen_direction or (
                frozen_sources is not None and existing.sources != frozen_sources
            )
            if not changed:
                return existing
            revision = int(existing.revision) + 1
            existing.direction = frozen_direction
            if frozen_sources is not None:
                existing.sources = frozen_sources
            existing.revision = revision
            existing.save(update_fields=["direction", "sources", "revision", "updated_at"])
            _announce(
                "narrative_authoring_draft_edited",
                {
                    "draft_id": existing.draft_id,
                    "owner": existing.owner_id,
                    "revision": revision,
                    "tick": int(tick),
                },
            )
            return existing

        draft = AuthoringDraft.objects.create(
            draft_id=handle,
            owner_id=clean_owner,
            direction=frozen_direction,
            sources=frozen_sources or [],
            revision=1,
            confirmed_revision=None,
            created_tick=int(tick),
        )
        _announce(
            "narrative_authoring_draft_saved",
            {
                "draft_id": draft.draft_id,
                "owner": draft.owner_id,
                "revision": 1,
                "tick": int(tick),
            },
        )
        return draft


def _existing_request(draft: AuthoringDraft, version: int) -> CreativeRequest:
    request = CreativeRequest.objects.filter(draft=draft, version=int(version)).first()
    if request is None:
        raise AuthoringError(
            f"Authoring draft {draft.draft_id!r} claims a confirmed version without a request."
        )
    return request


def confirm_draft(*, draft_id: Any, owner_id: Any, tick: int = 0) -> CreativeRequest:
    """Confirm the draft's current version and durably submit it once.

    Idempotent for an already-confirmed current version, so a duplicate
    confirmation or a restart returns the same request without a second
    submission. An invalid direction raises :class:`DirectionValidationError`
    with concrete reasons and changes no durable state; the draft's stored
    direction is untouched and remains unconfirmed.
    """
    draft = get_draft(draft_id, owner_id)
    clean_owner = draft.owner_id
    version = int(draft.revision)

    if draft_is_confirmed(draft):
        return _existing_request(draft, version)

    validation = validate_direction(draft.direction, owner_id=clean_owner)
    if not validation.valid:
        # No durable state change (deterministic re-validation reproduces this),
        # so the refusal is logged as an attempt with codes only, never prose.
        log_warn(
            "narrative_authoring_validation_rejected",
            context={
                "draft_id": draft.draft_id,
                "owner": clean_owner,
                "revision": version,
                "reasons": list(validation.reason_codes),
                "tick": int(tick),
            },
        )
        raise DirectionValidationError(validation.reasons)

    submission_key = submission_key_for(draft.draft_id, version)
    with transaction.atomic():
        # Kept for backends that support row locking; SQLite ignores it, and the
        # unique constraints below are the real "submit once" guarantee.
        locked = (
            AuthoringDraft.objects.select_for_update()
            .filter(draft_id=draft.draft_id)
            .first()
        )
        if locked is None or locked.owner_id != clean_owner:
            raise AuthoringAccessError("This authoring draft is not yours.")
        if draft_is_confirmed(locked) and int(locked.confirmed_revision) == version:
            return _existing_request(locked, version)

        request, created = CreativeRequest.objects.get_or_create(
            submission_key=submission_key,
            defaults={
                "draft": locked,
                "owner_id": clean_owner,
                "version": version,
                "direction": validation.direction,
                "sources": list(locked.sources or []),
                "validation_status": "valid",
                "submitted_tick": int(tick),
            },
        )
        if not created and (
            request.draft_id != locked.pk
            or request.owner_id != clean_owner
            or int(request.version) != version
        ):
            raise AuthoringConflictError(
                f"Submission {submission_key!r} belongs to a different request."
            )
        if not draft_is_confirmed(locked):
            locked.confirmed_revision = version
            locked.save(update_fields=["confirmed_revision", "updated_at"])
        if created:
            _announce(
                "narrative_authoring_request_submitted",
                {
                    "submission_key": submission_key,
                    "draft_id": locked.draft_id,
                    "owner": clean_owner,
                    "version": version,
                    "tick": int(tick),
                },
            )
        return request


def get_request(submission_key: Any, owner_id: Any) -> CreativeRequest:
    """Owner-scoped read of one confirmed request version."""
    clean_owner = _clean_owner_id(owner_id)
    key = str(submission_key).strip()
    if not key or len(key) > MAX_SUBMISSION_KEY_LENGTH:
        raise AuthoringAccessError("Unknown creative request.")
    request = CreativeRequest.objects.filter(submission_key=key).first()
    if request is None or request.owner_id != clean_owner:
        raise AuthoringAccessError("Unknown creative request.")
    return request


def list_requests(owner_id: Any) -> list[CreativeRequest]:
    """The owner's confirmed request versions, in durable submission order."""
    return list(
        CreativeRequest.objects.filter(owner_id=_clean_owner_id(owner_id)).order_by("id")
    )


def latest_confirmed_request(owner_id: Any) -> Optional[CreativeRequest]:
    """The most recently submitted confirmed version, or None.

    Deterministic tie-break (``submitted_tick``, then ``draft_id``, then
    ``version``) keeps the answer independent of insertion order. An unconfirmed
    edit does not displace the last explicitly confirmed version.
    """
    return (
        CreativeRequest.objects.filter(owner_id=_clean_owner_id(owner_id))
        .order_by("-submitted_tick", "-draft_id", "-version")
        .first()
    )


def collaborator_creative_brief(owner_id: Any) -> Optional[CollaboratorBrief]:
    """The collaborator-permitted creative preferences, or None when unconfirmed."""
    clean_owner = _clean_owner_id(owner_id)
    request = latest_confirmed_request(clean_owner)
    if request is None:
        return None
    direction = request.direction or {}

    def _texts(field: str) -> tuple[str, ...]:
        return tuple(str(item) for item in (direction.get(field) or ()))

    return CollaboratorBrief(
        owner_id=clean_owner,
        submission_key=request.submission_key,
        version=int(request.version),
        summary=str(direction.get("summary", "")),
        themes=_texts("themes"),
        atmosphere=_texts("atmosphere"),
        participants=_texts("participants"),
        emphasis=_texts("emphasis"),
        exclusions=_texts("exclusions"),
    )


def _announce(event: str, boundary: dict[str, Any]) -> None:
    transaction.on_commit(lambda b=boundary: log_info(event, context=b))

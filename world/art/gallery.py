"""Gallery records: the sole writer of per-subject image-card state.

One ``GalleryRecord`` (an Evennia ``DefaultScript``) exists per portrait
subject — ``gallery:<full-subject-key>`` — carrying the subject kind and
un-prefixed subject key (mirroring ``ArtAssetRecord``), an append-ordered list
of image cards, a nullable ``default_image_id``, and the subject's last
generation error. Records are created lazily (first append, first recorded
generation error, first explicit default set) — never by a startup scan — and
a subject with no record is a legal state that reads as an empty card list.

Every card carries the exact reproduction, placement, and provenance contract
(design §3.1, §13): the verbatim prompt pair, the server-reported seed, the
configured checkpoint, the requested fields, a normalized face rectangle, an
image pixel size, an optional equipment binding, the ``generated``/``seed``
source, and the write timestamp. Environment-driven generation parameters are
never stored. The server keeps one image per card and never crops, transforms,
or face-detects: ``face_rect`` is stored verbatim for the browser to apply.

This module is the ONLY writer of gallery records and their cards. Lock
discipline: ``gallery_lock`` serializes every record mutation; a caller that
also holds ``queue_lock`` (the future generation-settle path) must take
``queue_lock`` first — ``queue_lock -> gallery_lock`` is the only allowed
order, and nothing here ever acquires ``queue_lock``.

Each record also carries the subject's PERSONAL OFFICIAL-ART preferences
(change ``official-art-personalization``): the explicitly selected official
image identity and a bounded map of per-identity geometry overrides, written
only through the four public writers below, under the same lock. A preference
is never a card, never participates in card rules, and never touches a file:
the mounted official directory stays read-only and the runtime store is
untouched. Reads are tolerant like the card read — a malformed stored
preference reads as absent with exactly one bounded ``gallery_preference_invalid``
event naming the subject, never fatal.

File deletion resolves the card identity through
``world/art/paths.py::resolved_under_store_root`` so no path outside
``ART_STORE_ROOT`` is ever unlinked. Reads are tolerant: a stored entry that
fails the card contract is skipped and reported once as a
``gallery_card_invalid`` facade event, never fatal.

Imports never touch the generation side of the package (no worker, no
sd-webui client, no connectivity surface) or anything under ``world/ai/``,
keeping the deterministic-path and connectivity import-boundary contracts
intact.
"""

from collections.abc import Iterable, Mapping, Sequence
import math
from dataclasses import dataclass
import threading
import time
import uuid

from evennia import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.create import create_script

from world.art import gallery_kinds
from world.art.formats import STORE_EXTENSIONS
from world.art.paths import resolved_under_store_root
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    parse_subject,
)
from world.observability import log_debug, log_info, log_warn

# The one shared card face rectangle (design §3.1). Applied to every card
# written without an explicit rect; the client composes crops at render time
# from this value. The server stores it verbatim and never derives anything
# from it.
DEFAULT_FACE_RECT: dict[str, float] = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}


def default_face_rect(image_size: Mapping[str, int]) -> dict[str, float]:
    """Return the fitted default face rectangle for an image pixel size.

    Design §3.1, D3: keep the pinned upper-half anchor's width fraction and
    placement, deriving the height fraction so the marked box is pixel-square:
    ``{x: 0.25, y: 0.06, w: 0.5, h: 0.5 * width / height}``. On a square image
    it equals ``DEFAULT_FACE_RECT`` exactly.
    """
    width = image_size["width"]
    height = image_size["height"]
    return {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5 * width / height}

# The declared slot order. A binding mask is always stored in this order so
# the same selection always serializes identically, and an equipment snapshot
# always carries exactly these four keys.
SLOT_ORDER = ("weapon_main", "weapon_off", "armor", "accessories")

# The closed provenance vocabulary (design §12.1: a seeded base image is a
# legitimate card provenance, not a fake generation).
GALLERY_CARD_SOURCES = frozenset({"generated", "seed"})

# The exact stored-card key contract (design §3.1).
CARD_KEYS = frozenset(
    {
        "image_id",
        "stored_identity",
        "prompt",
        "seed",
        "checkpoint",
        "requested_fields",
        "face_rect",
        "image_size",
        "stage",
        "binding",
        "source",
        "created_at",
    }
)

# The closed grammar of a personal official-image identity: the catalog's
# root-relative ``<content-kind>/<content-key>/<filename>`` with one of the
# closed store extensions, bounded so a preference field can never carry an
# unbounded operator-supplied string. One predicate serves the writers, the
# management adapters, and both wire validators, so an identity the panel
# accepts is exactly one the writers accept.
OFFICIAL_IDENTITY_MAX = 192

# The bounded per-identity geometry-override map (design §8's "bounded map").
# Beyond it a NEW identity is refused rather than silently evicting another
# character's adjustment.
MAX_OFFICIAL_GEOMETRY_OVERRIDES = 32

# The two components one stored override may carry.
OFFICIAL_GEOMETRY_KEYS = ("face_rect", "stage")

# The one bounded diagnostic a malformed stored preference emits.
PREFERENCE_INVALID_EVENT = "gallery_preference_invalid"


def _empty_snapshot() -> dict:
    """A fresh fully empty four-slot snapshot (never a shared mutable)."""
    return {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}


def empty_snapshot() -> dict:
    """Public fresh fully empty four-slot snapshot for read-only consumers.

    The resolution chain needs the same empty state ``snapshot_for`` falls
    back to when an entity carries no readable equipment; exporting it here
    keeps the four-slot vocabulary in exactly one module.
    """
    return _empty_snapshot()


# Serializes every gallery-record mutation. The generation-settle path may
# nest this inside queue_lock; never the reverse (module docstring).
gallery_lock = threading.RLock()


class GalleryRecordError(ValueError):
    """Raised for every gallery card-contract or record-state violation."""


class GalleryRecord(DefaultScript):
    """One persistent gallery record keyed ``gallery:<full-subject-key>``."""

    kind: str = AttributeProperty(default="")
    subject_key: str = AttributeProperty(default="")
    cards: list = AttributeProperty(default=list)
    default_image_id: str | None = AttributeProperty(default=None)
    official_selection: str | None = AttributeProperty(default=None)
    official_geometry: dict = AttributeProperty(default=dict)
    last_error_code: str | None = AttributeProperty(default=None)
    last_error_at: float | None = AttributeProperty(default=None)


def record_key(subject: ArtSubject) -> str:
    """The script key for a subject's gallery record."""
    return f"gallery:{subject.full()}"


def _records_for(subject: ArtSubject) -> list[GalleryRecord]:
    return list(GalleryRecord.objects.filter(db_key=record_key(subject)))


def _consolidate(subject: ArtSubject) -> GalleryRecord | None:
    """Keep the first-created record for a subject, delete the rest.

    Enforces per-subject uniqueness even outside the single-process
    assumption, mirroring ``queue._consolidate`` (which ranks by lifecycle
    status; a gallery record has no status, so creation order decides).
    """
    records = sorted(_records_for(subject), key=lambda record: record.id)
    if not records:
        return None
    for duplicate in records[1:]:
        duplicate.delete()
    return records[0]


def _create_record(subject: ArtSubject) -> GalleryRecord:
    record = create_script(
        GalleryRecord, key=record_key(subject), persistent=True, interval=0
    )
    record.db.kind = subject.kind.value
    record.db.subject_key = subject.key
    return record


def record_for(
    subject: ArtSubject, *, create: bool = False
) -> GalleryRecord | None:
    """Return the subject's gallery record, never scanning.

    The read path (``create=False``) never creates: a subject with no record
    is the legal empty-gallery state. Creation is guarded against scene
    subjects — scenes have no gallery (declared, not compared).
    """
    with gallery_lock:
        record = (
            _consolidate(subject) if create
            else GalleryRecord.objects.filter(db_key=record_key(subject)).order_by("pk").first()
        )
        if record is not None or not create:
            return record
        if not gallery_kinds.has_gallery(subject.kind.value):
            raise GalleryRecordError("scene subjects have no gallery")
        return _create_record(subject)


def _is_real_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_list_like(value: object) -> bool:
    """True for any non-string sequence.

    Evennia's DB round-trip replaces plain lists with ``_SaverList`` (a
    ``MutableSequence``, not a ``list``), so every stored-shape list check
    accepts the sequence ABC and rejects only what a list would reject —
    strings and bytes included.
    """
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def validate_stage(stage: object) -> dict:
    """Return a fresh exact bounded presentation triple without coercion."""
    if not isinstance(stage, Mapping) or set(stage) != {"scale", "x", "y"}:
        raise GalleryRecordError("stage must be a mapping of exactly scale, x, y")
    for name, lower, upper in (("scale", 0.2, 2.0), ("x", -0.5, 0.5), ("y", -0.5, 0.5)):
        value = stage[name]
        if not _is_real_number(value) or not lower <= value <= upper:
            raise GalleryRecordError(f"stage.{name} must be a finite real number in [{lower}, {upper}]")
    return {name: stage[name] for name in ("scale", "x", "y")}


def identity_stage() -> dict:
    """Return fresh full-figure identity placement."""
    return {"scale": 1.0, "x": 0.0, "y": 0.0}


def _normalize_stored_stage(entry: object) -> object:
    """Repair only placement on a copy; tolerant reads never persist repairs."""
    if not isinstance(entry, Mapping):
        return entry
    copied = dict(entry)
    try:
        copied["stage"] = validate_stage(copied.get("stage"))
    except GalleryRecordError:  # observability: ignore R2: stage-only tolerant read intentionally supplies identity
        copied["stage"] = identity_stage()
    return copied


def validate_face_rect(rect: object, image_size: Mapping | None = None) -> dict:
    """Return the rect verbatim after enforcing the placement contract.

    Exactly ``x``, ``y``, ``w``, ``h`` as real numbers in ``[0, 1]`` with
    ``x + w <= 1``, ``y + h <= 1``, ``w > 0``, ``h > 0``. NaN values fail the
    comparisons and are rejected. Stored values are never rounded or
    otherwise altered.

    When ``image_size`` is supplied, the rectangle must be pixel-square on that
    image: ``abs(w * width - h * height) <= 1.0``. There is no value exemption:
    even ``DEFAULT_FACE_RECT`` rejects when evaluated against a non-square size.
    """
    if not isinstance(rect, Mapping) or set(rect) != {"x", "y", "w", "h"}:
        raise GalleryRecordError(
            "face_rect must be a mapping of exactly x, y, w, h"
        )
    for name in ("x", "y", "w", "h"):
        value = rect[name]
        if not _is_real_number(value) or not 0.0 <= value <= 1.0:
            raise GalleryRecordError(
                f"face_rect.{name} must be a real number in [0, 1]"
            )
    if rect["x"] + rect["w"] > 1 or rect["y"] + rect["h"] > 1:
        raise GalleryRecordError("face_rect must lie inside the unit square")
    if rect["w"] <= 0 or rect["h"] <= 0:
        raise GalleryRecordError("face_rect w and h must be positive")
    if image_size is not None:
        width = image_size["width"]
        height = image_size["height"]
        pixel_w = rect["w"] * width
        pixel_h = rect["h"] * height
        if abs(pixel_w - pixel_h) > 1.0:
            raise GalleryRecordError(
                f"face_rect must be pixel-square on {width}x{height} (got {pixel_w:.2f}x{pixel_h:.2f})"
            )
    return {name: rect[name] for name in ("x", "y", "w", "h")}


def validate_image_size(size: object) -> dict[str, int]:
    """Return validated image dimensions as ``{'width': int > 0, 'height': int > 0}``."""
    if not isinstance(size, Mapping) or set(size) != {"width", "height"}:
        raise GalleryRecordError(
            "image_size must be a mapping of exactly width and height"
        )
    width = size["width"]
    height = size["height"]
    if (
        not _is_real_number(width)
        or not isinstance(width, int)
        or width <= 0
        or not _is_real_number(height)
        or not isinstance(height, int)
        or height <= 0
    ):
        raise GalleryRecordError(
            "image_size width and height must be positive integers"
        )
    return {"width": width, "height": height}


def validate_binding(binding: object) -> dict | None:
    """Return the normalized binding after enforcing the binding contract.

    ``None`` is legal (unbound). Otherwise exactly ``mask`` and ``snapshot``:
    a non-empty list of distinct declared slots normalized into
    ``SLOT_ORDER`` order, plus a snapshot keyed by exactly the masked slots —
    single slots as non-empty item-key strings or ``None``, accessories as a
    lexicographically sorted list. An all-empty snapshot ("wearing nothing on
    those slots") is legal.
    """
    if binding is None:
        return None
    if not isinstance(binding, Mapping) or set(binding) != {"mask", "snapshot"}:
        raise GalleryRecordError(
            "binding must be None or a mapping of exactly mask and snapshot"
        )
    mask = binding["mask"]
    if not _is_list_like(mask) or not mask:
        raise GalleryRecordError("binding mask must be a non-empty list")
    if not all(isinstance(slot, str) for slot in mask):
        raise GalleryRecordError("binding mask slots must be strings")
    if len(set(mask)) != len(mask):
        raise GalleryRecordError("binding mask must not repeat a slot")
    for slot in mask:
        if slot not in SLOT_ORDER:
            raise GalleryRecordError(f"binding mask carries unknown slot {slot!r}")
    snapshot = binding["snapshot"]
    if not isinstance(snapshot, Mapping) or set(snapshot) != set(mask):
        raise GalleryRecordError("binding snapshot keys must equal the mask")
    normalized_snapshot: dict[str, object] = {}
    for slot in SLOT_ORDER:
        if slot not in mask:
            continue
        value = snapshot[slot]
        if slot == "accessories":
            if not _is_list_like(value) or not all(
                isinstance(item, str) and item for item in value
            ):
                raise GalleryRecordError(
                    "accessories snapshot must be a list of item-key strings"
                )
            normalized_snapshot[slot] = sorted(value)
        else:
            if value is not None and not (
                isinstance(value, str) and value
            ):
                raise GalleryRecordError(
                    f"{slot} snapshot must be an item-key string or None"
                )
            normalized_snapshot[slot] = value
    return {
        "mask": [slot for slot in SLOT_ORDER if slot in set(mask)],
        "snapshot": normalized_snapshot,
    }


def validate_official_identity(identity: object) -> str:
    """Return the identity verbatim when it is a well-formed catalog identity.

    Exactly the catalog layout's root-relative shape — three non-empty
    ``/``-separated segments, none of them a dot segment — whose filename
    carries one of the closed store extensions, at most
    ``OFFICIAL_IDENTITY_MAX`` code points, and printable text (no control,
    format, surrogate, or non-space separator character). The identity stays a
    lookup key only: this validator never touches the filesystem, so whether
    the catalog actually admits it remains the catalog's answer.
    """
    if not isinstance(identity, str) or not identity:
        raise GalleryRecordError("official identity must be a non-empty string")
    if len(identity) > OFFICIAL_IDENTITY_MAX:
        raise GalleryRecordError(
            f"official identity must be at most {OFFICIAL_IDENTITY_MAX} code points"
        )
    if not identity.isprintable():
        raise GalleryRecordError("official identity must be printable text")
    segments = identity.split("/")
    if len(segments) != 3 or not all(segments):
        raise GalleryRecordError(
            "official identity must be <content-kind>/<content-key>/<filename>"
        )
    if any(segment in (".", "..") for segment in segments):
        raise GalleryRecordError("official identity must not carry a dot segment")
    filename = segments[2]
    dot = filename.rfind(".")
    if dot == -1 or filename[dot:] not in STORE_EXTENSIONS:
        raise GalleryRecordError("official identity must carry a known store extension")
    return identity


def validate_official_geometry(entry: object) -> dict:
    """Return a fresh stored-form geometry override.

    A non-empty subset of the two components: a ``face_rect`` passing the
    shared bounded rectangle rule and/or a ``stage`` passing the shared triple
    rule, stored verbatim. The pixel-squareness check against the image's
    decoded dimensions belongs to the caller that knows the catalog image's
    size, exactly as a card's explicit rect is checked against its recorded
    ``image_size`` — this validator knows no image.
    """
    if not isinstance(entry, Mapping):
        raise GalleryRecordError("an official geometry override must be a mapping")
    keys = set(entry)
    if not keys or keys - set(OFFICIAL_GEOMETRY_KEYS):
        raise GalleryRecordError(
            "an official geometry override carries a face_rect, a stage, or both"
        )
    stored: dict = {}
    if "face_rect" in keys:
        stored["face_rect"] = validate_face_rect(entry["face_rect"])
    if "stage" in keys:
        stored["stage"] = validate_stage(entry["stage"])
    return stored


def snapshot_for(entity) -> dict:
    """The entity's four-slot equipment snapshot, read from stored state.

    Reads ``entity.db.equipment`` directly — the same no-create discipline
    ``world/skills/equipment.py::dual_wielding_from_storage`` uses — and never
    materializes an ``EquipmentHandler``, writes ``entity.db.equipment``, or
    mutates entity state. Missing or non-mapping storage reads as the fully
    empty snapshot; a present slot value of the wrong type fails the WHOLE
    snapshot closed to empty rather than raising. Accessory keys come back
    lexicographically sorted.
    """
    raw = entity.db.equipment
    if not isinstance(raw, Mapping):
        return _empty_snapshot()
    snapshot: dict[str, object] = {}
    for slot in SLOT_ORDER:
        value = raw.get(slot)
        if slot == "accessories":
            if value is None:
                snapshot[slot] = []
                continue
            if not _is_list_like(value) or not all(
                isinstance(item, str) and item for item in value
            ):
                return _empty_snapshot()
            snapshot[slot] = sorted(value)
        else:
            if value is None:
                snapshot[slot] = None
                continue
            if not isinstance(value, str) or not value:
                return _empty_snapshot()
            snapshot[slot] = value
    return snapshot


def _canonical_uuid_text(value: object) -> str | None:
    """The value verbatim when it is a canonical lowercase uuid string."""
    if not isinstance(value, str):
        return None
    try:
        parsed = uuid.UUID(value)
    except ValueError:  # observability: ignore R2: unparseable ids are the caller's rejection signal
        return None
    return value if str(parsed) == value else None


def _validate_stored_identity(
    identity: object, kind_directory: str, subject_key: str, image_id: str
) -> str:
    """Return the identity verbatim when it matches the store shape exactly."""
    if not isinstance(identity, str):
        raise GalleryRecordError("stored_identity must be a string")
    segments = identity.split("/")
    if len(segments) != 4 or segments[0] != "gallery":
        raise GalleryRecordError(
            "stored_identity must be gallery/<kind>/<subject-key>/<image-id><ext>"
        )
    if segments[1] != kind_directory or segments[2] != subject_key:
        raise GalleryRecordError(
            "stored_identity must name the card's kind directory and subject key"
        )
    filename = segments[3]
    if not filename.startswith(image_id):
        raise GalleryRecordError("stored_identity must embed the card's image_id")
    extension = filename[len(image_id):]
    if extension not in STORE_EXTENSIONS:
        raise GalleryRecordError(
            "stored_identity must carry a known store extension"
        )
    return identity


def validate_card(
    card: object,
    subject: ArtSubject,
    *,
    existing_ids: Iterable[str] = (),
    api_defaults: bool = True,
) -> dict:
    """Return the stored-form card after enforcing the card contract.

    With ``api_defaults`` (the write boundary) ``face_rect`` and ``created_at``
    may be omitted and are filled with ``default_face_rect(image_size)`` and
    the current epoch time. ``image_size`` must be supplied by the caller as a
    trusted dimension mapping. Every other contract key is required, no extra
    key is tolerated, and no environment-driven generation parameter can be
    stored. Reads pass ``api_defaults=False``, which requires the complete
    twelve-key stored contract.
    """
    if not isinstance(card, Mapping):
        raise GalleryRecordError("a gallery card must be a mapping")
    keys = set(card)
    missing = CARD_KEYS - keys
    extra = keys - CARD_KEYS
    if api_defaults:
        missing -= {"face_rect", "created_at", "stage"}
    if missing or extra:
        raise GalleryRecordError(
            "gallery card keys must be exactly the contract set"
            f" (missing {sorted(missing)}, unexpected {sorted(extra)})"
        )
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if not capability.has_gallery:
        raise GalleryRecordError("scene subjects have no gallery cards")
    kind_directory = capability.store_directory

    image_id = _canonical_uuid_text(card["image_id"])
    if image_id is None:
        raise GalleryRecordError("image_id must be a canonical lowercase uuid string")
    if image_id in set(existing_ids):
        raise GalleryRecordError(f"image_id {image_id} already exists on this record")

    prompt = card["prompt"]
    if prompt is not None:
        if not isinstance(prompt, Mapping) or set(prompt) != {
            "positive",
            "negative",
        }:
            raise GalleryRecordError(
                "prompt must be None or a mapping of exactly positive and negative"
            )
        if not all(isinstance(text, str) for text in prompt.values()):
            raise GalleryRecordError("prompt text must be strings")
        prompt = {"positive": prompt["positive"], "negative": prompt["negative"]}

    seed = card["seed"]
    if seed is not None and (not _is_real_number(seed) or not isinstance(seed, int) or seed < 0):
        raise GalleryRecordError("seed must be a non-negative integer or None")

    checkpoint = card["checkpoint"]
    if checkpoint is not None and not (
        isinstance(checkpoint, str) and checkpoint
    ):
        raise GalleryRecordError("checkpoint must be a non-empty string or None")

    requested_fields = card["requested_fields"]
    if not _is_list_like(requested_fields) or not all(
        isinstance(field, str) and field for field in requested_fields
    ):
        raise GalleryRecordError("requested_fields must be a list of field-id strings")

    source = card["source"]
    if not isinstance(source, str) or source not in GALLERY_CARD_SOURCES:
        raise GalleryRecordError("source must be one of generated, seed")
    image_size = validate_image_size(card["image_size"])

    if api_defaults and "created_at" not in card:
        created_at = time.time()
    else:
        created_at = card["created_at"]
    if not _is_real_number(created_at) or not math.isfinite(created_at):
        raise GalleryRecordError("created_at must be a finite epoch timestamp")

    if api_defaults and "face_rect" not in card:
        face_rect = validate_face_rect(default_face_rect(image_size), image_size=image_size)
    else:
        face_rect = validate_face_rect(card["face_rect"], image_size=image_size)
    binding = validate_binding(card["binding"])
    stored_identity = _validate_stored_identity(
        card["stored_identity"], kind_directory, subject.key, image_id
    )
    return {
        "image_id": image_id,
        "stored_identity": stored_identity,
        "prompt": prompt,
        "seed": seed,
        "checkpoint": checkpoint,
        "requested_fields": list(requested_fields),
        "face_rect": face_rect,
        "image_size": image_size,
        "stage": validate_stage(card.get("stage", identity_stage()) if api_defaults else card["stage"]),
        "binding": binding,
        "source": source,
        "created_at": created_at,
    }


def _raw_image_ids(record: GalleryRecord) -> frozenset[str]:
    """The raw stored ids (malformed entries included) for uniqueness checks."""
    ids = set()
    for entry in record.db.cards or []:
        if isinstance(entry, Mapping) and isinstance(entry.get("image_id"), str):
            ids.add(entry["image_id"])
    return frozenset(ids)


def referenced_stored_identities() -> set[str]:
    """Read-only: every stored identity referenced by any gallery card.

    Exposed for the startup orphan prune (change ``gallery-generation-jobs``):
    the single-writer rule keeps the record class itself inside this module,
    so cross-record reads go through this accessor. Malformed entries count:
    a referenced file is NEVER deleted, and an unparseable card's file is
    retained until a human resolves it.
    """
    identities: set[str] = set()
    for record in GalleryRecord.objects.all():
        for entry in record.db.cards or []:
            if isinstance(entry, Mapping) and isinstance(entry.get("stored_identity"), str):
                identity = entry["stored_identity"]
                if identity:
                    identities.add(identity)
    return identities


@dataclass(frozen=True)
class GallerySubjectState:
    """One record's read-only summary: subject, cards, default, last error."""

    subject: ArtSubject
    card_count: int
    has_default: bool
    error_code: str | None
    error_at: float | None


def _scan_gallery_states() -> list[GallerySubjectState]:
    """One tolerant read-only pass over every gallery record.

    The shared scan behind the two cross-record accessors below. Raw and
    write-free: card entries are validated straight off the record
    (``validate_card`` with ``api_defaults=False`` after the same stage-only
    identity normalization ``cards_for`` applies, so a stage-less legacy card
    counts there and here alike) and a malformed entry is skipped exactly as
    ``cards_for`` skips it. No per-subject fetch — which consolidates
    duplicate records — runs during a listing. A record whose persisted
    kind/subject no longer parses is skipped, so one corrupt row can never
    blind an operator surface.
    """
    states: list[GallerySubjectState] = []
    for record in GalleryRecord.objects.all():
        try:
            subject = parse_subject(f"{record.db.kind}:{record.db.subject_key}")
        except ArtSubjectError:  # observability: ignore R2: corrupt row skipped so one bad row cannot blind the whole operator surface; the surface's own listing is the report
            continue
        card_count = 0
        for entry in record.db.cards or []:
            try:
                validate_card(_normalize_stored_stage(entry), subject, api_defaults=False)
            except GalleryRecordError:
                log_warn(
                    "gallery_card_invalid",
                    context={
                        "subject": subject.full(),
                        "image_id": (
                            entry.get("image_id")
                            if isinstance(entry, Mapping)
                            else None
                        ),
                    },
                )
                continue
            card_count += 1
        states.append(
            GallerySubjectState(
                subject=subject,
                card_count=card_count,
                has_default=record.db.default_image_id is not None,
                error_code=record.db.last_error_code,
                error_at=record.db.last_error_at,
            )
        )
    return states


def erroring_subjects() -> list[GallerySubjectState]:
    """Read-only: every subject whose record carries a recorded generation error.

    The sole cross-record ERROR read (change ``gallery-failure-visibility``):
    operator surfaces list the subjects whose LAST generation attempt failed,
    each with its bounded code and timestamp, without ever touching the record
    class. Creates nothing, writes nothing, and skips unparseable rows.
    """
    return [state for state in _scan_gallery_states() if state.error_code is not None]


def gallery_states() -> list[GallerySubjectState]:
    """Read-only: one summary per gallery record, healthy records included.

    The per-record state accessor behind the staff status/health surfaces:
    subject, valid card count, whether a default is set, and the recorded
    error code and age source. Same tolerance and write-free discipline as
    ``erroring_subjects``.
    """
    return _scan_gallery_states()


def _delete_stored_file(subject: ArtSubject, identity: object) -> None:
    """Unlink one card file under confinement; never raise out of deletion.

    An identity that fails confinement, a file that is already gone, and an
    unlink failure each produce one bounded facade event; the card removal
    itself stays committed.
    """
    identity_text = identity if isinstance(identity, str) else None
    resolved = (
        resolved_under_store_root(identity_text) if identity_text else None
    )
    context = {"subject": subject.full(), "identity": identity_text}
    if resolved is None:
        log_warn("gallery_card_file_unresolvable", context=context)
        return
    try:
        resolved.unlink()
    except FileNotFoundError:
        log_debug("gallery_card_file_missing", context=context)
    except OSError as exc:
        log_warn("gallery_card_file_delete_failed", context=context, exc=exc)


def append_card(subject: ArtSubject, **card_fields) -> dict:
    """Validate and append one card, returning the stored form.

    The first card of a character record becomes its default; a later append
    never touches the default. A kind whose declaration caps its cards at a
    maximum (only ``1`` is admitted today) installs the new card as its sole
    card — committing first, then deleting any replaced files — and makes it
    the default, exactly as today's monster branch did unconditionally; a kind
    declaring a null maximum never replaces anything. Every violation raises a
    typed ``GalleryRecordError`` before any record or file is touched.
    """
    with gallery_lock:
        record = _consolidate(subject)
        existing_ids = _raw_image_ids(record) if record is not None else frozenset()
        capability = gallery_kinds.capabilities_for(subject.kind.value)
        if (
            capability.has_gallery
            and not capability.supports_bindings
            and card_fields.get("binding") is not None
        ):
            raise GalleryRecordError("monster cards must be unbound")
        # Provenance honesty (``gallery-monster-generation``): card
        # ``requested_fields`` claims which data blocks produced the image, so
        # the write boundary refuses a non-empty provenance for a kind whose
        # declaration supports no field selection — a stored claim the kind
        # could never have requested would make the card lie.
        if (
            capability.has_gallery
            and not capability.supports_field_selection
            and list(card_fields.get("requested_fields") or [])
        ):
            raise GalleryRecordError(
                f"kind {capability.kind_value!r} supports no field selection; "
                "a card's requested_fields must be empty"
            )
        stored = validate_card(
            card_fields, subject, existing_ids=existing_ids
        )
        if record is None:
            record = record_for(subject, create=True)
        previous: list = list(record.db.cards or [])
        if capability.max_cards is not None:
            record.db.cards = [stored]
            record.db.default_image_id = stored["image_id"]
            log_info(
                "gallery_card_replaced",
                context={"subject": subject.full(), "image_id": stored["image_id"]},
            )
            for entry in previous:
                identity = entry.get("stored_identity") if isinstance(entry, Mapping) else None
                _delete_stored_file(subject, identity)
        else:
            record.db.cards = [*previous, stored]
            if not previous:
                # The FIRST card of an empty record becomes its default
                # automatically. That is not an explicit default SET, so it
                # leaves a personal official selection alone (change
                # ``official-art-personalization``): the chain still presents
                # the selection, and a settled generation can never silently
                # discard a choice the player made.
                record.db.default_image_id = stored["image_id"]
            log_info(
                "gallery_card_appended",
                context={"subject": subject.full(), "image_id": stored["image_id"]},
            )
        return dict(stored)


def remove_card(subject: ArtSubject, image_id: str) -> None:
    """Remove one card and unlink exactly its confined file.

    The list change commits before the unlink. Removing the default card
    resets ``default_image_id`` to ``None`` so a record never names a card it
    does not hold. Matches raw entries, so a caller can purge a malformed
    entry by id. A missing or unresolvable file is a bounded log, never a
    raise.
    """
    with gallery_lock:
        record = _consolidate(subject)
        if record is None:
            raise GalleryRecordError("this subject has no gallery record")
        entries = list(record.db.cards or [])
        removed = None
        for entry in entries:
            if isinstance(entry, Mapping) and entry.get("image_id") == image_id:
                removed = entry
                break
        if removed is None:
            raise GalleryRecordError(f"no card with image_id {image_id!r} exists")
        record.db.cards = [
            entry
            for entry in entries
            if not (isinstance(entry, Mapping) and entry.get("image_id") == image_id)
        ]
        if record.db.default_image_id == image_id:
            record.db.default_image_id = None
        log_info(
            "gallery_card_removed",
            context={"subject": subject.full(), "image_id": image_id},
        )
        _delete_stored_file(subject, removed.get("stored_identity"))


def set_default(subject: ArtSubject, image_id: str) -> None:
    """Point ``default_image_id`` at an existing card of the record.

    Validated against the tolerant read, so the default can never name a
    malformed entry the reads themselves would hide. Setting an explicit
    runtime default also CLEARS the personal official selection, so at most
    one personal default governs (change ``official-art-personalization``).
    The automatic first-card default ``append_card`` installs is not an
    explicit default set: appending a card a player generated never discards
    a selection the player made.
    """
    with gallery_lock:
        record = _consolidate(subject)
        if record is None:
            raise GalleryRecordError("this subject has no gallery record")
        known = {card["image_id"] for card in cards_for(subject)}
        if image_id not in known:
            raise GalleryRecordError(
                f"no valid card with image_id {image_id!r} exists to default to"
            )
        record.db.default_image_id = image_id
        cleared_selection = record.db.official_selection
        record.db.official_selection = None
        log_info(
            "gallery_default_set",
            context={
                "subject": subject.full(),
                "image_id": image_id,
                "cleared_official_selection": cleared_selection is not None,
            },
        )


def set_official_selection(subject: ArtSubject, identity: str) -> None:
    """Select one official image as the subject's personal art preference.

    The identity is a validated root-relative catalog identity; whether the
    catalog admits it — and whether it belongs to the subject's own content
    reference — is the caller's scope check, so a stale identity stays a legal
    stored preference that resolution simply ignores. The write creates a
    card-less record on demand, never touches a card, and CLEARS
    ``default_image_id`` so exactly one personal default governs.
    """
    validated = validate_official_identity(identity)
    with gallery_lock:
        record = record_for(subject, create=True)
        cleared_default = record.db.default_image_id
        record.db.official_selection = validated
        record.db.default_image_id = None
        log_info(
            "gallery_official_selection_set",
            context={
                "subject": subject.full(),
                "identity": validated,
                "cleared_default": cleared_default is not None,
            },
        )


def clear_official_selection(subject: ArtSubject) -> None:
    """Clear the personal official selection; a subject with no record no-ops.

    Clearing never restores a runtime default — the invariant is "at most one
    personal default governs", so a cleared selection simply leaves the
    gallery-default slot unset until the player sets one.
    """
    with gallery_lock:
        record = _consolidate(subject)
        if record is None:
            return
        record.db.official_selection = None
        log_info(
            "gallery_official_selection_cleared",
            context={"subject": subject.full()},
        )


def set_official_geometry(
    subject: ArtSubject,
    identity: str,
    *,
    face_rect: object = None,
    stage: object = None,
) -> dict:
    """Replace one identity's personal geometry override; return the stored form.

    The two components are independently nullable and stored verbatim after
    validation: the caller that knows the catalog image's decoded size checks
    the rectangle's squareness before calling (the management adapter does),
    because this writer knows no image. Both ``None`` is a typed refusal — the
    removal of an override is :func:`clear_official_geometry`. A NEW identity
    beyond the bounded map's ceiling is refused rather than evicting another
    identity's adjustment. Files are never touched.
    """
    validated_identity = validate_official_identity(identity)
    stored: dict = {}
    if face_rect is not None:
        stored["face_rect"] = validate_face_rect(face_rect)
    if stage is not None:
        stored["stage"] = validate_stage(stage)
    if not stored:
        raise GalleryRecordError(
            "an official geometry override needs a face_rect, a stage, or both"
        )
    with gallery_lock:
        record = record_for(subject, create=True)
        geometry = dict(record.db.official_geometry or {})
        if (
            validated_identity not in geometry
            and len(geometry) >= MAX_OFFICIAL_GEOMETRY_OVERRIDES
        ):
            raise GalleryRecordError(
                "at most "
                f"{MAX_OFFICIAL_GEOMETRY_OVERRIDES} official geometry overrides "
                "are stored per subject"
            )
        geometry[validated_identity] = stored
        record.db.official_geometry = geometry
        log_info(
            "gallery_official_geometry_set",
            context={
                "subject": subject.full(),
                "identity": validated_identity,
                "components": sorted(stored),
            },
        )
        return dict(stored)


def clear_official_geometry(subject: ArtSubject, identity: str) -> bool:
    """Remove one identity's geometry override; report whether one was stored.

    A subject with no record, or an identity carrying no override, is a no-op
    that creates nothing and writes nothing.
    """
    validated = validate_official_identity(identity)
    with gallery_lock:
        record = _consolidate(subject)
        if record is None:
            return False
        geometry = dict(record.db.official_geometry or {})
        if validated not in geometry:
            return False
        del geometry[validated]
        record.db.official_geometry = geometry
        log_info(
            "gallery_official_geometry_cleared",
            context={"subject": subject.full(), "identity": validated},
        )
        return True


def _update_card_field(subject: ArtSubject, image_id: str, field: str, value) -> dict:
    """Commit one validated field of one existing card under the lock.

    The shared body of the two in-place card writers
    (``gallery-card-update-api``). The entry is located through the same
    tolerant per-entry validation ``cards_for`` performs — a malformed entry
    matching the id is reported once and stays un-updatable, because
    rewriting it would launder corruption into a valid card — and a missing
    match raises the same typed miss ``remove_card`` raises. The FIRST valid
    entry matching the id is the one updated; a duplicate valid id is
    corruption the sole writer cannot produce, and its copies stay untouched.
    The already
    canonical validated form of the located entry is rebuilt with exactly the
    one updated field; every other entry, the card order, and
    ``default_image_id`` are committed unchanged. Files are never touched:
    this seam writes placement/binding metadata only.
    """
    with gallery_lock:
        record = record_for(subject)
        if record is None:
            raise GalleryRecordError("this subject has no gallery record")
        entries = list(record.db.cards or [])
        located_index = None
        located: dict | None = None
        for index, entry in enumerate(entries):
            try:
                validated = validate_card(_normalize_stored_stage(entry), subject, api_defaults=False)
            except GalleryRecordError:  # observability: ignore R2: tolerant locate reports the malformed entry and refuses to update it
                log_warn(
                    "gallery_card_invalid",
                    context={
                        "subject": subject.full(),
                        "image_id": (
                            entry.get("image_id")
                            if isinstance(entry, Mapping)
                            else None
                        ),
                    },
                )
                continue
            if located_index is None and validated["image_id"] == image_id:
                located_index = index
                located = validated
        if located_index is None or located is None:
            raise GalleryRecordError(f"no card with image_id {image_id!r} exists")
        updated = dict(located)
        updated[field] = value
        record.db.cards = [
            updated if index == located_index else entry
            for index, entry in enumerate(entries)
        ]
        log_info(
            "gallery_card_updated",
            context={
                "subject": subject.full(),
                "image_id": image_id,
                "kind": subject.kind.value,
                "field": field,
            },
        )
        return dict(updated)


def set_stage(subject: ArtSubject, image_id: str, stage: object) -> dict:
    """Replace one card's whole presentation triple through the sole writer."""
    validated = validate_stage(stage)
    with gallery_lock:
        updated = _update_card_field(subject, image_id, "stage", validated)
        log_info(
            "gallery_stage_set",
            context={"subject": subject.full(), "image_id": image_id, **validated},
        )
        return updated


def update_card_face_rect(subject: ArtSubject, image_id: str, face_rect) -> dict:
    """Re-mark one existing card's face rectangle, stored verbatim.

    The placement-only in-place writer (``gallery-card-update-api``, D9):
    the incoming rectangle passes the shared ``validate_face_rect`` against
    the card's recorded ``image_size`` before any write and is stored
    unaltered — no crop, no second image, no file write. A malformed or
    missing entry match is the ``remove_card`` miss form — reported once by
    the shared writer's tolerant locate, so this pre-check stays silent —
    and one ``gallery_card_updated`` facade event closes a successful update.
    Returns the updated stored card.
    """
    with gallery_lock:
        record = record_for(subject)
        if record is None:
            raise GalleryRecordError("this subject has no gallery record")
        located = None
        for entry in record.db.cards or []:
            try:
                validated = validate_card(_normalize_stored_stage(entry), subject, api_defaults=False)
            except GalleryRecordError:  # observability: ignore R2: tolerant locate ignores malformed cards
                continue
            if validated["image_id"] == image_id:
                located = validated
                break
        if located is None:
            # No valid entry carries the id. Delegate to the shared writer's
            # tolerant locate, which reports each malformed entry once and
            # then raises the same remove_card miss form; a silent miss here
            # would launder corruption without a trace.
            return _update_card_field(subject, image_id, "face_rect", face_rect)
        valid_rect = validate_face_rect(face_rect, image_size=located["image_size"])
    return _update_card_field(
        subject, image_id, "face_rect", valid_rect
    )


def update_card_binding(subject: ArtSubject, image_id: str, binding) -> dict:
    """Re-save one existing card's equipment binding, stored verbatim.

    The binding-only in-place writer (``gallery-card-update-api``): the
    incoming binding passes the shared ``validate_binding`` (mask/snapshot
    coherence) and an explicit ``None`` unbinds (``binding`` is nullable).
    The kind capability gate runs BEFORE any record read — the refusal is
    unconditional, so a kind declaring no binding support is refused with
    the capability-naming typed error even when it holds no record. The
    message is deliberately identical to the service seam's refusal
    (``world/art/service.py::request_gallery_image``); gallery.py may not
    import service.py, so the alignment is by text, not by call. Files are
    never touched, and one ``gallery_card_updated`` event closes a
    successful update. Returns the updated stored card.
    """
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if not capability.supports_bindings and binding is not None:
        raise GalleryRecordError(
            f"subject kind {subject.kind.value!r} declares no binding support; "
            "a binding argument is rejected"
        )
    return _update_card_field(subject, image_id, "binding", validate_binding(binding))


def cards_for(subject: ArtSubject) -> list[dict]:
    """The subject's valid cards in append order, tolerant of corruption.

    A stored entry that fails the card contract is skipped and reported once
    as a ``gallery_card_invalid`` facade event carrying the subject and the
    offending ``image_id`` when readable. Malformed entries never raise out
    of a read and never reach a caller; the valid cards always come back.
    """
    record = record_for(subject)
    if record is None:
        return []
    cards: list[dict] = []
    for entry in record.db.cards or []:
        try:
            cards.append(
                validate_card(_normalize_stored_stage(entry), subject, api_defaults=False)
            )
        except GalleryRecordError:
            log_warn(
                "gallery_card_invalid",
                context={
                    "subject": subject.full(),
                    "image_id": (
                        entry.get("image_id")
                        if isinstance(entry, Mapping)
                        else None
                    ),
                },
            )
    return cards


@dataclass(frozen=True)
class OfficialPreferences:
    """One record's read-only official-art preference state.

    ``selection`` is the retained personal official selection (``None`` when
    unset or malformed); ``geometry`` maps a validated root-relative official
    identity to its stored ``{face_rect?, stage?}`` override. A malformed
    stored entry is absent from the map — never raised, never returned.
    """

    selection: str | None
    geometry: dict[str, dict]


def official_preferences_for(subject: ArtSubject) -> OfficialPreferences:
    """The subject's personal official-art preferences, tolerantly read.

    Creates nothing and writes nothing. A malformed stored preference — a
    selection that is not a valid identity, a geometry field that is not a
    bounded mapping, or an entry naming an invalid identity or carrying an
    invalid component — reads as absent and emits exactly one bounded
    ``gallery_preference_invalid`` event naming the subject, so one corrupt
    field can never blind the read or fail a presentation.
    """
    record = record_for(subject)
    if record is None:
        return OfficialPreferences(None, {})
    context = {"subject": subject.full()}
    selection = None
    raw_selection = record.db.official_selection
    if raw_selection is not None:
        try:
            selection = validate_official_identity(raw_selection)
        except GalleryRecordError:
            log_warn(
                PREFERENCE_INVALID_EVENT,
                context={**context, "field": "official_selection"},
            )
    geometry: dict[str, dict] = {}
    raw_geometry = record.db.official_geometry
    if raw_geometry:
        if (
            not isinstance(raw_geometry, Mapping)
            or len(raw_geometry) > MAX_OFFICIAL_GEOMETRY_OVERRIDES
        ):
            log_warn(
                PREFERENCE_INVALID_EVENT,
                context={**context, "field": "official_geometry"},
            )
        else:
            for identity, entry in raw_geometry.items():
                try:
                    key = validate_official_identity(identity)
                    geometry[key] = validate_official_geometry(entry)
                except GalleryRecordError:
                    log_warn(
                        PREFERENCE_INVALID_EVENT,
                        context={
                            **context,
                            "field": "official_geometry",
                            "identity": identity if isinstance(identity, str) else None,
                        },
                    )
    return OfficialPreferences(selection, geometry)


def record_error(subject: ArtSubject, code: str) -> None:
    """Record the subject's last generation failure (consumed by generation).

    A failed generation adds no card, so this is the third lazy creation
    point (design §12.3.1): a subject with no record yet gets one carrying
    only the error.
    """
    if not isinstance(code, str) or not code:
        raise GalleryRecordError("an error code must be a non-empty string")
    with gallery_lock:
        record = record_for(subject, create=True)
        record.db.last_error_code = code
        record.db.last_error_at = time.time()
        log_warn(
            "gallery_error_recorded",
            context={"subject": subject.full(), "code": code},
        )


def clear_error(subject: ArtSubject) -> None:
    """Clear the subject's recorded error; a subject with no record no-ops."""
    with gallery_lock:
        record = _consolidate(subject)
        if record is None:
            return
        record.db.last_error_code = None
        record.db.last_error_at = None
        log_info("gallery_error_cleared", context={"subject": subject.full()})

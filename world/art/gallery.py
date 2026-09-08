"""Gallery records: the sole writer of per-subject image-card state.

One ``GalleryRecord`` (an Evennia ``DefaultScript``) exists per portrait
subject — ``gallery:<full-subject-key>`` — carrying the subject kind and
un-prefixed subject key (mirroring ``ArtAssetRecord``), an append-ordered list
of image cards, a nullable ``default_image_id``, and the subject's last
generation error. Records are created lazily (first append, first recorded
generation error, first explicit default set) — never by a startup scan — and
a subject with no record is a legal state that reads as an empty card list.

Every card carries the exact reproduction, placement, and provenance contract
(design §3.1): the verbatim prompt pair, the server-reported seed, the
configured checkpoint, the requested fields, a normalized face rectangle, an
optional equipment binding, the ``generated``/``seed`` source, and the write
timestamp. Environment-driven generation parameters are never stored. The
server keeps one image per card and never crops, transforms, or face-detects:
``face_rect`` is stored verbatim for the browser to apply.

This module is the ONLY writer of gallery records and their cards. Lock
discipline: ``gallery_lock`` serializes every record mutation; a caller that
also holds ``queue_lock`` (the future generation-settle path) must take
``queue_lock`` first — ``queue_lock -> gallery_lock`` is the only allowed
order, and nothing here ever acquires ``queue_lock``.

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

from collections.abc import Iterable, Mapping
from pathlib import Path
import threading
import time
import uuid

from evennia import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.create import create_script

from world.art.formats import STORE_EXTENSIONS
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.observability import log_debug, log_info, log_warn

# The one shared card face rectangle (design §3.1). Applied to every card
# written without an explicit rect; the client composes crops at render time
# from this value. The server stores it verbatim and never derives anything
# from it.
DEFAULT_FACE_RECT: dict[str, float] = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}

# The declared slot order. A binding mask is always stored in this order so
# the same selection always serializes identically, and an equipment snapshot
# always carries exactly these four keys.
SLOT_ORDER = ("weapon_main", "weapon_off", "armor", "accessories")

# The CLOSED kind-directory vocabulary of the gallery store path
# ``gallery/<kind-dir>/<subject-key>/<image-id><ext>``. Scenes have no gallery.
GALLERY_KIND_DIRECTORIES = {
    ArtSubjectKind.CHARACTER: "character",
    ArtSubjectKind.MONSTER: "monster",
}

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
        "binding",
        "source",
        "created_at",
    }
)


def _empty_snapshot() -> dict:
    """A fresh fully empty four-slot snapshot (never a shared mutable)."""
    return {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}


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
    subjects — scenes have no gallery.
    """
    with gallery_lock:
        record = _consolidate(subject)
        if record is not None or not create:
            return record
        if subject.kind not in GALLERY_KIND_DIRECTORIES:
            raise GalleryRecordError("scene subjects have no gallery")
        return _create_record(subject)


def _is_real_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_face_rect(rect: object) -> dict:
    """Return the rect verbatim after enforcing the placement contract.

    Exactly ``x``, ``y``, ``w``, ``h`` as real numbers in ``[0, 1]`` with
    ``x + w <= 1``, ``y + h <= 1``, ``w > 0``, ``h > 0``. NaN values fail the
    comparisons and are rejected. Stored values are never rounded or
    otherwise altered.
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
    return {name: rect[name] for name in ("x", "y", "w", "h")}


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
    if not isinstance(mask, list) or not mask:
        raise GalleryRecordError("binding mask must be a non-empty list")
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
            if not isinstance(value, list) or not all(
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
            if not isinstance(value, list) or not all(
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

    With ``api_defaults`` (the write boundary) ``face_rect`` and
    ``created_at`` may be omitted and are filled with ``DEFAULT_FACE_RECT``
    and the current epoch time; every other contract key is required, no
    extra key is tolerated, and no environment-driven generation parameter
    can be stored. Reads pass ``api_defaults=False``, which requires the
    complete ten-key stored contract.
    """
    if not isinstance(card, Mapping):
        raise GalleryRecordError("a gallery card must be a mapping")
    keys = set(card)
    missing = CARD_KEYS - keys
    extra = keys - CARD_KEYS
    if api_defaults:
        missing -= {"face_rect", "created_at"}
    if missing or extra:
        raise GalleryRecordError(
            "gallery card keys must be exactly the contract set"
            f" (missing {sorted(missing)}, unexpected {sorted(extra)})"
        )
    kind_directory = GALLERY_KIND_DIRECTORIES.get(subject.kind)
    if kind_directory is None:
        raise GalleryRecordError("scene subjects have no gallery cards")

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
    if not isinstance(requested_fields, list) or not all(
        isinstance(field, str) and field for field in requested_fields
    ):
        raise GalleryRecordError("requested_fields must be a list of field-id strings")

    source = card["source"]
    if source not in GALLERY_CARD_SOURCES:
        raise GalleryRecordError("source must be one of generated, seed")

    if api_defaults and "created_at" not in card:
        created_at = time.time()
    else:
        created_at = card["created_at"]
    if not _is_real_number(created_at):
        raise GalleryRecordError("created_at must be a real epoch timestamp")

    if api_defaults and "face_rect" not in card:
        face_rect = dict(DEFAULT_FACE_RECT)
    else:
        face_rect = validate_face_rect(card["face_rect"])
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
    never touches the default. A monster record holds at most one card: the
    append replaces the existing card (commit first, then delete the old
    file) and the new card becomes the default. Every violation raises a
    typed ``GalleryRecordError`` before any record or file is touched.
    """
    with gallery_lock:
        record = record_for(subject)
        existing_ids = _raw_image_ids(record) if record is not None else frozenset()
        if subject.kind is ArtSubjectKind.MONSTER and card_fields.get("binding") is not None:
            raise GalleryRecordError("monster cards must be unbound")
        stored = validate_card(
            card_fields, subject, existing_ids=existing_ids
        )
        if record is None:
            record = record_for(subject, create=True)
        previous: list = list(record.db.cards or [])
        if subject.kind is ArtSubjectKind.MONSTER:
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
        record = record_for(subject)
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
    malformed entry the reads themselves would hide.
    """
    with gallery_lock:
        record = record_for(subject)
        if record is None:
            raise GalleryRecordError("this subject has no gallery record")
        known = {card["image_id"] for card in cards_for(subject)}
        if image_id not in known:
            raise GalleryRecordError(
                f"no valid card with image_id {image_id!r} exists to default to"
            )
        record.db.default_image_id = image_id
        log_info(
            "gallery_default_set",
            context={"subject": subject.full(), "image_id": image_id},
        )


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
                validate_card(entry, subject, api_defaults=False)
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
        record = record_for(subject)
        if record is None:
            return
        record.db.last_error_code = None
        record.db.last_error_at = None
        log_info("gallery_error_cleared", context={"subject": subject.full()})

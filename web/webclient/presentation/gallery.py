"""Version-three gallery projection and exact wire schema; no mutation or service probe."""

import hashlib
import json
import math
import re
import uuid

from evennia.objects.models import ObjectDB

from typeclasses.entities import LivingEntity
from world.art import gallery as gallery_api
from world.art import official as official_api
from world.art import descriptors
from world.art.fallback_keys import FALLBACK_EXTENSION, FALLBACK_KEYS
from world.art.formats import STORE_EXTENSIONS
from world.art.gallery_kinds import capabilities_for
from world.art.gallery_match import card_identity_resolution, fallback_for
from world.art.gallery_prompt import GALLERY_PROMPT_FIELDS
from world.art.presenter import GALLERY_ASPECT_RATIO, MAX_PORTRAIT_MEDIA_URL, media_url_for
from world.art.queue import MAX_PENDING_GALLERY_JOBS, pending_gallery_jobs
from world.art.subjects import (
    ArtSubject, ArtSubjectError, ArtSubjectKind, character_subject_for,
    monster_subject_for, parse_subject,
)
from world.lore.monster_visuals import get_monster_visual_registry
from world.lore.items import ITEM_REGISTRY
from world.observability import log_warn
from world.rules.party import live_companions

from . import artwork as artwork_wire
from .context import PresentationContext
from .protocol import (
    MAX_CANONICAL_JSON_BYTES, MAX_LIST_ITEMS, MAX_SAFE_INTEGER,
    ProtocolValidationError, _require_exact_fields, check_json_safety, json_byte_size,
)
from .registry import PanelUnavailableError

GALLERY_SCHEMA_VERSION = 3
GALLERY_MAX_SUBJECTS = 24
GALLERY_MAX_LABEL = 128
GALLERY_MAX_NAME = 64
GALLERY_MAX_CHIP = 16
# One source of truth for the runtime gallery URL ceiling: the canonical
# descriptor vocabulary's origin ceiling, which the client mirror reads too.
GALLERY_MAX_URL = descriptors.MEDIA_URL_LIMITS[descriptors.ORIGIN_RUNTIME]
GALLERY_MAX_WARNINGS = 5
GALLERY_MAX_CONDITION = 512
# The official-entry read model's bounds (change
# ``official-art-personalization``): a bounded list of the selected subject's
# catalog-admitted images, each row's identity inside the writers' own closed
# identity grammar and each URL inside the shared portrait wire ceiling,
# because a fingerprinted official URL embeds an operator-chosen filename.
GALLERY_MAX_OFFICIAL_ENTRIES = 32
GALLERY_MAX_OFFICIAL_IDENTITY = gallery_api.OFFICIAL_IDENTITY_MAX
GALLERY_MAX_OFFICIAL_URL = MAX_PORTRAIT_MEDIA_URL
OFFICIAL_URL_PREFIX = "/art/official/"
# The committed built-in silhouette route (``gallery-builtin-fallbacks``),
# the one origin the alpha terminal may name.
DEFAULTS_URL_PREFIX = "/art/defaults/"
DEFAULTS_IDENTITY_PREFIX = "defaults/"
OFFICIAL_ROW_FIELDS = ("identity", "artwork", "is_current", "is_catalog_default")
SLOT_LABELS = {"weapon_main": "主手", "weapon_off": "副手", "armor": "防具", "accessories": "飾品"}
SLOTS = gallery_api.SLOT_ORDER
FIELDS = GALLERY_PROMPT_FIELDS
CAPABILITY_FIELDS = (
    "supports_bindings", "supports_field_selection", "supports_free_text",
    "supports_personal_official_preferences", "max_cards"
)
CARD_FIELDS = {
    "image_id", "status", "label", "artwork", "is_default", "chips",
    "requested_fields", "binding_present", "created_at",
}
PANEL_FIELDS = {
    "schema_version", "available", "kind", "subjects", "selected", "filters", "cards",
    "official_entries", "equipment_summary", "capabilities", "binding_warnings",
    "error_state",
}


def _exact(value, keys, name):
    _require_exact_fields(value, name, set(keys), {})


def _text(value, maximum, name):
    if (
        not isinstance(value, str) or not value or len(value) > maximum
        or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ProtocolValidationError(f"invalid {name}")
    return value


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or abs(value) > MAX_SAFE_INTEGER or not math.isfinite(value):
        raise ProtocolValidationError(f"invalid {name}")
    return value


def _integer(value, name):
    _number(value, name)
    if int(value) != value:
        raise ProtocolValidationError(f"invalid integer {name}")
    return value


def validate_gallery_subject_key(value) -> ArtSubject:
    """Validate full gallery subject grammar without querying game state."""
    _text(value, 128, "subject_key")
    try:
        subject = parse_subject(value)
    except (ArtSubjectError, UnicodeError) as exc:  # observability: ignore R2: typed validation rejection is returned to the caller
        raise ProtocolValidationError("invalid gallery subject") from exc
    if subject.full() != value or subject.kind not in (ArtSubjectKind.CHARACTER, ArtSubjectKind.MONSTER):
        raise ProtocolValidationError("subject has no gallery")
    return subject


def _uuid(value):
    if gallery_api._canonical_uuid_text(value) is None:
        raise ProtocolValidationError("image_id must be a canonical UUID")


def _filters(cards):
    return {
        "all": len(cards),
        "defaults": sum(row["is_default"] for row in cards),
        "bound": sum(row["binding_present"] for row in cards),
        "pending": sum(row["status"] == "pending" for row in cards),
        "failed": sum(row["status"] == "failed" for row in cards),
    }


def _validate_equipment(summary):
    _exact(summary, SLOTS, "equipment_summary")
    for slot in SLOTS:
        row = summary[slot]
        if slot != "accessories":
            _exact(row, ("value", "display_name"), "equipment slot")
            if row["value"] is not None:
                _text(row["value"], GALLERY_MAX_NAME, "equipment key")
            _text(row["display_name"], GALLERY_MAX_NAME, "equipment name")
        else:
            _exact(row, ("value", "display_names", "equipped_count"), "accessories")
            values, names = row["value"], row["display_names"]
            if not isinstance(values, list) or not isinstance(names, list) or len(values) > 5 or len(names) != len(values):
                raise ProtocolValidationError("invalid accessories")
            for value in values + names:
                _text(value, GALLERY_MAX_NAME, "accessory")
            if values != sorted(values) or _integer(row["equipped_count"], "equipped_count") != len(values):
                raise ProtocolValidationError("invalid accessory ordering/count")


def _validate_official_url(url):
    """The fingerprinted official media URL vocabulary, exactly."""
    if not url.startswith(OFFICIAL_URL_PREFIX):
        raise ProtocolValidationError("official url must name the official media route")
    fingerprint, separator, tail = url[len(OFFICIAL_URL_PREFIX):].partition("/")
    if (
        not separator
        or len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        raise ProtocolValidationError("official url must carry a sha256 fingerprint")
    # Percent-encoded identities are ASCII printable with no space; anything
    # else could not have been produced by the catalog's own URL builder.
    if not tail or any(not 0x21 <= ord(character) <= 0x7E for character in tail):
        raise ProtocolValidationError("official url must carry an identity path")


def _silhouette_key(resource):
    """The committed built-in key one alpha-terminal resource names, or a refusal.

    The one origin a gallery preview's silhouette may carry: the fixed in-repo
    ``defaults/`` route, a key of the closed fallback vocabulary, the single
    committed extension, and a URL built from that very identity — so a
    terminal can never point at a store file, an official path, or an
    arbitrary name standing in for a figure.
    """
    identity = resource["resource_id"]
    if not identity.startswith(DEFAULTS_IDENTITY_PREFIX):
        raise ProtocolValidationError("silhouette must name the committed defaults route")
    tail = identity[len(DEFAULTS_IDENTITY_PREFIX):]
    if not tail.endswith(FALLBACK_EXTENSION):
        raise ProtocolValidationError("silhouette must name the committed defaults route")
    key = tail[: -len(FALLBACK_EXTENSION)]
    if key not in FALLBACK_KEYS or resource["url"] != DEFAULTS_URL_PREFIX + tail:
        raise ProtocolValidationError("silhouette must name a committed built-in key")
    return key


def _validate_gallery_terminal(terminal):
    """The gallery's one permitted terminal: the subject's silhouette alpha mask.

    Required on every row that carries an image (a card row always has one), so
    a failed preview can always fall back to the subject's own silhouette
    without selecting another original.
    """
    if terminal is None:
        raise ProtocolValidationError("a gallery row with an image carries its alpha terminal")
    if terminal["kind"] != descriptors.TERMINAL_ALPHA_MASK or terminal["rank"] != descriptors.GALLERY_RANK_ALPHA:
        raise ProtocolValidationError("gallery terminal must be the alpha mask at its own rank")
    resource = terminal["resource"]
    if resource["origin"] != descriptors.ORIGIN_SILHOUETTE:
        raise ProtocolValidationError("alpha terminal must be the committed silhouette")
    if terminal["source_id"] != descriptors.gallery_alpha_source_id(_silhouette_key(resource)):
        raise ProtocolValidationError("alpha terminal must name its own fallback key")


def _validate_gallery_url(url, selected, image_id):
    """One exact card's runtime media URL, exactly as the presenter builds it.

    The path must name the selected subject's own image with a store
    extension; the descriptor validator has already accepted at most the one
    closed ``?v=<sha256>`` cache-version suffix.
    """
    directory = "character" if selected.kind is ArtSubjectKind.CHARACTER else "monster"
    prefix = f"/art/gallery/{directory}/{selected.key}/{image_id}"
    path = url.partition("?")[0]
    if not path.startswith(prefix) or path[len(prefix):] not in STORE_EXTENSIONS:
        raise ProtocolValidationError("url must name selected subject and image")


def _validate_card_artwork(row, selected):
    """One card row's descriptor: its exact original at its own rank, or its named fault.

    A stored card contributes exactly one rank-10 runtime candidate naming the
    selected subject's own image, carrying the exact stored geometry. A card
    whose output is missing or refused contributes exactly one rank-10 known
    fault for that same exact image and NO URL, so the row stays identified
    with the requested card. A pending or failed row contributes neither: no
    original candidate, no geometry and no terminal, only its truthful
    recorded generation state.
    """
    descriptor = row["artwork"]
    artwork_wire.validate_artwork(descriptor)
    attempts = descriptor["attempts"]
    if row["status"] != "card":
        if attempts or descriptor["terminal"] is not None:
            raise ProtocolValidationError("synthetic row fabricated an image")
        return
    _validate_gallery_terminal(descriptor["terminal"])
    source = descriptors.gallery_original_source_id(row["image_id"])
    # Exactly one attempt overall, naming this row's own exact image: a second
    # entry (a candidate or an unrelated fault) would let another source stand
    # in for the requested original.
    if len(attempts) != 1 or attempts[0]["source_id"] != source:
        raise ProtocolValidationError("a card row carries exactly one exact-original attempt")
    entry = attempts[0]
    if entry["rank"] != descriptors.GALLERY_RANK_ORIGINAL:
        raise ProtocolValidationError("the exact original must carry its own rank")
    if entry["type"] == "fault":
        return
    resource = entry["resource"]
    if resource["origin"] != descriptors.ORIGIN_RUNTIME:
        raise ProtocolValidationError("the exact original must be a runtime resource")
    _validate_gallery_url(resource["url"], selected, row["image_id"])
    geometry = resource["geometry"]
    if geometry is None or None in (geometry["image_size"], geometry["face_rect"], geometry["stage"]):
        raise ProtocolValidationError("the exact original must carry its stored geometry")


def _validate_official_artwork(row):
    """One official row's descriptor: its exact official candidate, plus named faults.

    The candidate names the row's own catalog identity at the fingerprint route
    the catalog builds, carrying the admitted decoded size and fitted
    rectangle. Retained startup faults (change ``unified-art-source-faults``)
    ride at their own source and rank: an image's ``metadata_invalid`` fault
    shares its candidate's source/rank and precedes it, and a declared-default
    fault names the refused declared identity — so a substituted default is
    attributable without tainting a healthy sibling.
    """
    descriptor = row["artwork"]
    artwork_wire.validate_artwork(descriptor)
    _validate_gallery_terminal(descriptor["terminal"])
    source = descriptors.gallery_official_source_id(row["identity"])
    # Exactly ONE image candidate overall, and it must be this row's own exact
    # identity: a second candidate (from any source) would let a substitute
    # become the official original the editors measure. Fault entries are
    # unconstrained by source — a declared-default fault legitimately names the
    # refused declared identity, not this row's.
    images = [entry for entry in descriptor["attempts"] if entry["type"] == "image"]
    if len(images) != 1 or images[0]["source_id"] != source:
        raise ProtocolValidationError("an official row carries its exact official candidate")
    entry = images[0]
    if entry["rank"] != descriptors.GALLERY_RANK_ORIGINAL:
        raise ProtocolValidationError("the official candidate must carry its own rank")
    resource = entry["resource"]
    if resource["origin"] != descriptors.ORIGIN_OFFICIAL or resource["resource_id"] != row["identity"]:
        raise ProtocolValidationError("the official candidate must name the row identity")
    _validate_official_url(_text(resource["url"], GALLERY_MAX_OFFICIAL_URL, "official url"))
    geometry = resource["geometry"]
    if geometry is None or geometry["face_rect"] is None or geometry["stage"] is not None:
        raise ProtocolValidationError("the official candidate carries its fitted rectangle and no stage")


def _validate_official_entries(entries):
    """Exactly the official-row list: shape, bounds, vocabulary, uniqueness."""
    if not isinstance(entries, list) or len(entries) > GALLERY_MAX_OFFICIAL_ENTRIES:
        raise ProtocolValidationError("invalid official entries")
    identities = set()
    currents = 0
    catalog_defaults = 0
    for row in entries:
        _exact(row, OFFICIAL_ROW_FIELDS, "official row")
        identity = _text(row["identity"], GALLERY_MAX_OFFICIAL_IDENTITY, "official identity")
        try:
            gallery_api.validate_official_identity(identity)
        except gallery_api.GalleryRecordError as exc:  # observability: ignore R2: wire identity rejection is returned to the caller
            raise ProtocolValidationError("invalid official identity") from exc
        if identity in identities:
            raise ProtocolValidationError("duplicate official identity")
        identities.add(identity)
        _validate_official_artwork(row)
        for flag in ("is_current", "is_catalog_default"):
            if type(row[flag]) is not bool:
                raise ProtocolValidationError("official row flags must be booleans")
        currents += row["is_current"]
        catalog_defaults += row["is_catalog_default"]
    if currents > 1 or catalog_defaults > 1:
        raise ProtocolValidationError("at most one current/catalog-default official row")


def validate_gallery(payload):
    """Validate exactly the available form; unavailable forms belong to the registry."""
    _exact(payload, PANEL_FIELDS, "gallery")
    if _integer(payload["schema_version"], "schema_version") != GALLERY_SCHEMA_VERSION or payload["available"] is not True or payload["kind"] != "gallery":
        raise ProtocolValidationError("invalid gallery discriminator")
    subjects = payload["subjects"]
    if not isinstance(subjects, list) or not 1 <= len(subjects) <= GALLERY_MAX_SUBJECTS:
        raise ProtocolValidationError("invalid subject rail")
    seen = set()
    for index, row in enumerate(subjects):
        _exact(row, ("subject_key", "kind", "display_name", "is_puppet"), "subject row")
        subject = validate_gallery_subject_key(row["subject_key"])
        if row["kind"] != subject.kind.value or row["subject_key"] in seen or row["is_puppet"] is not (index == 0):
            raise ProtocolValidationError("incoherent subject rail")
        if index == 0 and subject.kind is not ArtSubjectKind.CHARACTER:
            raise ProtocolValidationError("puppet must be a character")
        _text(row["display_name"], GALLERY_MAX_NAME, "subject display name")
        seen.add(row["subject_key"])
    selected = validate_gallery_subject_key(payload["selected"])
    if payload["selected"] not in seen:
        raise ProtocolValidationError("selected is not in the rail")
    capability = payload["capabilities"]
    _exact(capability, CAPABILITY_FIELDS, "capabilities")
    for field in CAPABILITY_FIELDS[:-1]:
        if type(capability[field]) is not bool:
            raise ProtocolValidationError("capability flags must be booleans")
    if capability["max_cards"] is not None and _integer(capability["max_cards"], "max_cards") != 1:
        raise ProtocolValidationError("invalid card cap")
    if capability["supports_bindings"]:
        _validate_equipment(payload["equipment_summary"])
    elif payload["equipment_summary"] is not None:
        raise ProtocolValidationError("unsupported equipment summary")
    _validate_official_entries(payload["official_entries"])
    cards = payload["cards"]
    if not isinstance(cards, list) or len(cards) > MAX_LIST_ITEMS:
        raise ProtocolValidationError("invalid cards")
    ids = set()
    previous = math.inf
    by_id = {}
    for row in cards:
        _exact(row, CARD_FIELDS, "gallery row")
        _uuid(row["image_id"])
        if row["image_id"] in ids or row["status"] not in ("card", "pending", "failed"):
            raise ProtocolValidationError("invalid row identity/status")
        ids.add(row["image_id"])
        by_id[row["image_id"]] = row
        _text(row["label"], GALLERY_MAX_LABEL, "card label")
        timestamp = _number(row["created_at"], "created_at")
        if timestamp > previous:
            raise ProtocolValidationError("cards must be newest first")
        previous = timestamp
        if type(row["is_default"]) is not bool or type(row["binding_present"]) is not bool:
            raise ProtocolValidationError("card flags must be booleans")
        chips, fields = row["chips"], row["requested_fields"]
        if not isinstance(chips, list) or len(chips) > 6 or not isinstance(fields, list) or len(fields) > len(FIELDS):
            raise ProtocolValidationError("invalid chips/provenance")
        for chip in chips:
            _text(chip, GALLERY_MAX_CHIP, "chip")
        for field in fields:
            if not isinstance(field, str) or field not in FIELDS:
                raise ProtocolValidationError("unknown requested field")
        if len(set(chips)) != len(chips) or len(set(fields)) != len(fields):
            raise ProtocolValidationError("duplicate chip/field")
        if row["status"] != "card" and (
            row["is_default"] or row["binding_present"] or chips or fields
        ):
            raise ProtocolValidationError("synthetic row fabricated card data")
        if row["binding_present"] and not capability["supports_bindings"] or fields and not capability["supports_field_selection"]:
            raise ProtocolValidationError("unsupported card facts")
        _validate_card_artwork(row, selected)
        if row["status"] != "card":
            continue
        slot_chips = [label for label in SLOT_LABELS.values() if label in chips]
        face_chips = [c for c in chips if c in ("預設臉框", "自訂臉框")]
        if len(face_chips) != 1:
            raise ProtocolValidationError("exactly one face chip required")
        expected = slot_chips + face_chips + (["目前預設"] if row["is_default"] else [])
        if chips != expected or bool(slot_chips) != row["binding_present"]:
            raise ProtocolValidationError("incoherent chips")
    filters = payload["filters"]
    _exact(filters, ("all", "defaults", "bound", "pending", "failed"), "filters")
    if any(_integer(value, "filter count") < 0 for value in filters.values()) or filters != _filters(cards):
        raise ProtocolValidationError("filter counts differ from rows")
    if filters["defaults"] > 1 or filters["pending"] > MAX_PENDING_GALLERY_JOBS or filters["failed"] > 1:
        raise ProtocolValidationError("too many default/pending/failed rows")
    error = payload["error_state"]
    if error is not None:
        _exact(error, ("code", "at"), "error_state")
        code = _text(error["code"], 64, "error code")
        if re.fullmatch(r"[a-z0-9_]+", code) is None:
            raise ProtocolValidationError("invalid error identifier")
        _number(error["at"], "error timestamp")
    if bool(filters["failed"]) != (error is not None):
        raise ProtocolValidationError("error state differs from failed row")
    warnings = payload["binding_warnings"]
    if not isinstance(warnings, list) or len(warnings) > GALLERY_MAX_WARNINGS or warnings and not capability["supports_bindings"]:
        raise ProtocolValidationError("invalid binding warnings")
    warning_ids = []
    for warning in warnings:
        _exact(warning, ("image_id", "label", "conditions"), "binding warning")
        _uuid(warning["image_id"])
        card = by_id.get(warning["image_id"])
        if card is None or not card["binding_present"] or warning["label"] != card["label"]:
            raise ProtocolValidationError("warning must name a visible bound card")
        conditions = warning["conditions"]
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 4:
            raise ProtocolValidationError("invalid warning conditions")
        for line in conditions:
            _text(line, GALLERY_MAX_CONDITION, "condition")
        warning_ids.append(warning["image_id"])
    if len(set(warning_ids)) != len(warning_ids) or warning_ids != [row["image_id"] for row in cards if row["image_id"] in warning_ids]:
        raise ProtocolValidationError("warnings must be unique and newest first")
    check_json_safety(payload)
    if json_byte_size(payload) > MAX_CANONICAL_JSON_BYTES:
        raise ProtocolValidationError("gallery exceeds envelope size")
    return payload


def _character_subject(entity, *, puppet=False):
    try:
        subject = character_subject_for(entity)
    except ArtSubjectError as exc:
        log_warn("gallery_subject_invalid", context={"char": entity.pk}, exc=exc)
        subject = None
    if subject is None and (puppet or getattr(entity, "account", None) is not None):
        numeric = ArtSubject(ArtSubjectKind.CHARACTER, str(entity.pk))
        if puppet or gallery_api.record_for(numeric) is not None:
            subject = numeric
    return subject


def gallery_subjects(actor):
    """Ordered rail entries with their typed identities and read-only entity refs."""
    puppet = _character_subject(actor, puppet=True)
    def entry(subject, entity=None, *, is_puppet=False, name=None):
        return ({
            "subject_key": subject.full(), "kind": subject.kind.value,
            "display_name": str(name if name is not None else entity.key)[:GALLERY_MAX_NAME],
            "is_puppet": is_puppet,
        }, subject, entity)
    rail = [entry(puppet, actor, is_puppet=True)]
    seen = {puppet.full()}
    visual_registry = get_monster_visual_registry()
    # Reserve up to 23 stable-key visual species after the puppet
    species_keys = sorted(visual_registry.keys())[:min(len(visual_registry), GALLERY_MAX_SUBJECTS - 1)]
    monsters = [entry(monster_subject_for(key), name=visual_registry[key].display_label) for key in species_keys]
    remaining = max(0, GALLERY_MAX_SUBJECTS - 1 - len(monsters))
    companions = live_companions(actor)
    companion_ids = {entity.pk for entity in companions}
    # Process the small priority group first; then stream candidates in PK order.
    candidates = (sorted(companions, key=lambda entity: entity.pk), ObjectDB.objects.order_by("pk").iterator())
    for group_index, group in enumerate(candidates):
        for entity in group:
            if not remaining:
                break
            if entity.pk == actor.pk or not isinstance(entity, LivingEntity) or group_index == 1 and entity.pk in companion_ids:
                continue
            subject = _character_subject(entity)
            if subject is None or subject.full() in seen:
                continue
            rail.append(entry(subject, entity))
            seen.add(subject.full())
            remaining -= 1
    return rail + monsters


def _item_name(key):
    if key is None:
        return "未裝備"
    item = ITEM_REGISTRY.get(key)
    return str(item.display_name_zh if item is not None else key)[:GALLERY_MAX_NAME]


def _equipment(snapshot):
    result = {slot: {"value": snapshot[slot], "display_name": _item_name(snapshot[slot])} for slot in SLOTS[:-1]}
    keys = snapshot["accessories"]
    result["accessories"] = {"value": keys, "display_names": [_item_name(key) for key in keys], "equipped_count": len(keys)}
    return result


# Stored cards carry no name: every card row reads 肖像 and the client tells
# rows apart by their structured `created_at` (local relative and exact date),
# never by a timestamp baked into this label.
CARD_LABEL = "肖像"
PENDING_LABEL = "肖像（生成中）"

# The exact-image tail of a descriptor's subject identity: a card's canonical
# UUID verbatim, or the digest prefix of a catalog identity that has no UUID,
# cut to the same length so ONE descriptor subject-identity bound covers both.
EXACT_IMAGE_TAIL = 36


def _subject_digest(subject):
    """The bounded stable hash half of one descriptor's subject identity."""
    return hashlib.sha256(subject.full().encode("utf-8")).hexdigest()


def _card_subject_id(subject, image_id):
    """One card's exact subject identity: the subject digest plus its image UUID."""
    return f"{_subject_digest(subject)}:{image_id}"


def _official_subject_id(subject, identity):
    """One official row's exact subject identity, same shape and bound as a card's."""
    return f"{_subject_digest(subject)}:{descriptors.identity_version(identity)[:EXACT_IMAGE_TAIL]}"


def _generation_facts(subject, record, cards, pending):
    """The subject's recorded generation key and state, independent of any candidate.

    The gallery's own recorded generation truth: a live in-flight request is
    ``pending``, a recorded failure is ``failed``, a stored card means a
    completed generation exists, and a subject with none of the three is
    factually ``missing``. Nothing here erases a recorded failure, and nothing
    here invents an active job: a deliberately disabled or merely unstarted
    subject claims nothing.
    """
    if pending:
        state = descriptors.GENERATION_PENDING
    elif record is not None and record.db.last_error_code:
        state = descriptors.GENERATION_FAILED
    elif cards:
        state = descriptors.GENERATION_DONE
    else:
        state = descriptors.GENERATION_MISSING
    return subject.full(), state


def _alpha_terminal(subject, entity):
    """The subject's committed silhouette as a descriptor's terminal alpha mask.

    Read-only: the seam is consulted with ``report=False`` because the
    silhouette rides beside the exact original as a decorative fallback rather
    than being the presented figure. A subject with no resolvable silhouette (a
    scene) contributes no terminal; every gallery subject resolves one.
    """
    fallback = fallback_for(subject, entity=entity, report=False)
    if not isinstance(fallback, dict):
        return None
    identity, key = fallback.get("identity"), fallback.get("key")
    if not isinstance(identity, str) or not identity or not isinstance(key, str) or not key:
        return None
    try:
        rect = gallery_api.validate_face_rect(fallback.get("face_rect"))
    except gallery_api.GalleryRecordError:  # observability: ignore R2: the seam's rectangle defaults per contract
        rect = dict(gallery_api.DEFAULT_FACE_RECT)
    return descriptors.terminal(
        descriptors.TERMINAL_ALPHA_MASK,
        descriptors.gallery_alpha_source_id(key),
        descriptors.GALLERY_RANK_ALPHA,
        descriptors.resource(
            identity,
            descriptors.identity_version(identity),
            media_url_for(identity),
            descriptors.ORIGIN_SILHOUETTE,
            geometry_payload=descriptors.geometry(
                face_rect=rect, aspect_ratio=GALLERY_ASPECT_RATIO
            ),
        ),
    )


def _card_artwork(subject, card, generation, terminal):
    """The exact-original descriptor of one stored card row.

    One original identity plus its attributed source facts. A readable card
    contributes its rank-10 runtime candidate carrying the exact stored
    geometry, and authorizes retention of that same source while it stays
    applicable; a card whose output is missing or refused contributes a
    rank-10 known fault naming that exact image with NO URL, and authorizes no
    retention — so a vanished output can never leave old pixels standing in
    for it and never hands the original role to another card.
    """
    generation_subject, generation_state = generation
    source_id = descriptors.gallery_original_source_id(card["image_id"])
    identity, fault_reason = card_identity_resolution(subject, card)
    if fault_reason is not None:
        attempts = [
            descriptors.fault_attempt(
                source_id, descriptors.GALLERY_RANK_ORIGINAL, fault_reason
            )
        ]
        retention = []
    else:
        attempts = [
            descriptors.image_attempt(
                source_id,
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.resource(
                    identity,
                    descriptors.identity_version(identity),
                    media_url_for(identity),
                    descriptors.ORIGIN_RUNTIME,
                    geometry_payload=descriptors.geometry(
                        image_size=descriptors.image_size_payload(**card["image_size"]),
                        face_rect=card["face_rect"],
                        stage=card["stage"],
                        aspect_ratio=GALLERY_ASPECT_RATIO,
                    ),
                ),
            )
        ]
        # The token covers the subject, the generation subject, the exact image
        # and its current authorized binding — never its geometry and never the
        # pending/failed regeneration state, so a re-render or an in-flight
        # regeneration cannot revoke a still-valid known-good card.
        retention = [
            descriptors.retention_source(
                source_id,
                descriptors.retention_token(
                    subject.full(),
                    generation_subject,
                    card["image_id"],
                    json.dumps(card["binding"], sort_keys=True),
                    identity,
                ),
            )
        ]
    return descriptors.descriptor(
        subject_id=_card_subject_id(subject, card["image_id"]),
        generation_subject=generation_subject,
        generation_state=generation_state,
        attempts=attempts,
        terminal_payload=terminal,
        retention_sources=retention,
    )


def _synthetic(subject, image_id, timestamp, status, label, generation_subject, generation_state):
    """One pending or failed row: truthful generation state and no image at all.

    A request with no stored output carries no candidate, no geometry and no
    terminal — only the subject's recorded generation state — so a client
    renders its synthetic treatment and can never mistake a placeholder for an
    image, nor read a generation state off a candidate. The state is the ROW's
    own recorded fact: an in-flight request reads ``pending`` and a recorded
    failure reads ``failed``, even while other requests of the same subject are
    still in flight.
    """
    return {
        "image_id": image_id, "status": status, "label": label,
        "artwork": descriptors.descriptor(
            subject_id=_card_subject_id(subject, image_id),
            generation_subject=generation_subject,
            generation_state=generation_state,
            attempts=[], terminal_payload=None, retention_sources=[],
        ),
        "is_default": False, "chips": [], "requested_fields": [],
        "binding_present": False, "created_at": timestamp,
    }


def _official_entries(subject, entity, generation, terminal) -> list[dict]:
    """The selected subject's catalog-admitted official images, as wire rows.

    Read-only and bounded. The subject's OFFICIAL CONTENT REFERENCE — never a
    display name or a threat tier — names one catalog content directory, and
    its admitted images become rows in the catalog's deterministic filename
    order. Each row's descriptor carries that ONE exact image as its rank-10
    official candidate — the admitted decoded size and the catalog's validated
    metadata-or-fitted rectangle — plus the retained startup faults the source
    facts recorded: the directory's declared-default fault precedes the
    deterministic substitute it caused, and an image's own metadata fault sits
    at its candidate's source and rank. ``is_current`` marks the subject's
    retained personal selection and ``is_catalog_default`` the content's
    default image. An identity or URL outside the shared wire budget is
    omitted with one bounded diagnostic instead of failing the panel, exactly
    as the portrait payload's official branch falls through over budget. An
    entity declaring no reference, or a reference the snapshot does not hold,
    yields an empty list.
    """
    from world.art.official import current_catalog
    from world.art.official_refs import official_content_reference_for_entity

    if entity is None:
        return []
    reference = official_content_reference_for_entity(entity)
    if reference is None:
        return []
    catalog = current_catalog()
    content = catalog.content(reference.kind, reference.key)
    if content is None:
        return []
    selection = gallery_api.official_preferences_for(subject).selection
    generation_subject, generation_state = generation
    declared_faults = [
        (descriptors.gallery_official_source_id(fault.identity), fault.reason)
        for fault in catalog.source_faults(reference.kind, reference.key)
        if fault.scope == official_api.SOURCE_SCOPE_DEFAULT
    ]
    entries: list[dict] = []
    for identity in content.images:
        if len(entries) >= GALLERY_MAX_OFFICIAL_ENTRIES:
            break
        image = catalog.entry(identity)
        url = catalog.url_for(identity)
        if image is None or url is None:
            continue
        if (
            len(identity) > GALLERY_MAX_OFFICIAL_IDENTITY
            or len(url) > GALLERY_MAX_OFFICIAL_URL
        ):
            log_warn(
                "gallery_official_entry_skipped",
                context={"subject": subject.full(), "identity": identity},
            )
            continue
        source_id = descriptors.gallery_official_source_id(identity)
        attempts: list[dict] = []
        if identity == content.default_identity:
            # The directory's declared-default fault precedes the substitute it
            # forced, and never taints a healthy sibling.
            for fault_source, reason in declared_faults:
                if fault_source != source_id:
                    attempts.append(
                        descriptors.fault_attempt(
                            fault_source, descriptors.GALLERY_RANK_ORIGINAL, reason
                        )
                    )
        own_fault = catalog.fault_for(identity)
        if own_fault is not None:
            attempts.append(
                descriptors.fault_attempt(
                    source_id, descriptors.GALLERY_RANK_ORIGINAL, own_fault.reason
                )
            )
        attempts.append(
            descriptors.image_attempt(
                source_id,
                descriptors.GALLERY_RANK_ORIGINAL,
                descriptors.resource(
                    identity,
                    image.fingerprint,
                    url,
                    descriptors.ORIGIN_OFFICIAL,
                    geometry_payload=descriptors.geometry(
                        image_size=descriptors.image_size_payload(**image.image_size),
                        face_rect=dict(image.face_rect),
                        aspect_ratio=GALLERY_ASPECT_RATIO,
                    ),
                ),
            )
        )
        entries.append(
            {
                "identity": identity,
                "artwork": descriptors.descriptor(
                    subject_id=_official_subject_id(subject, identity),
                    generation_subject=generation_subject,
                    generation_state=generation_state,
                    attempts=attempts,
                    terminal_payload=terminal,
                    retention_sources=[
                        descriptors.retention_source(
                            source_id,
                            descriptors.retention_token(
                                subject.full(),
                                generation_subject,
                                identity,
                                image.fingerprint,
                            ),
                        )
                    ],
                ),
                "is_current": identity == selection,
                "is_catalog_default": identity == content.default_identity,
            }
        )
    return entries


def gallery_presenter(context: PresentationContext):
    """Project one selected gallery. Reads never create or consolidate records."""
    from .coordinator import PresentationCoordinator

    if PresentationCoordinator.mode_for(context) != "exploration":
        raise PanelUnavailableError
    rail = gallery_subjects(context.actor)
    selected = next((entry for entry in rail if entry[0]["subject_key"] == context.gallery_subject), rail[0])
    subject, entity = selected[1:]
    capability = capabilities_for(subject.kind.value)
    # Observe jobs first: if one settles before the card read, dedupe favors the card.
    pending = pending_gallery_jobs(subject)
    record = gallery_api.record_for(subject)
    default = record.db.default_image_id if record else None
    error = {"code": record.db.last_error_code, "at": record.db.last_error_at} if record and record.db.last_error_code else None
    snapshot = gallery_api.snapshot_for(entity) if capability.supports_bindings else None
    rows, warnings, seen = [], [], set()
    cards = sorted(gallery_api.cards_for(subject), key=lambda card: -card["created_at"])
    # One generation fact pair and one silhouette per panel: every row's
    # descriptor carries the same subject-level truth, and the exact-original
    # candidates it is presented beside never change it.
    generation = _generation_facts(subject, record, cards, pending)
    terminal = _alpha_terminal(subject, entity)
    for card in cards:
        if card["image_id"] in seen:
            continue
        seen.add(card["image_id"])
        binding = card["binding"] if capability.supports_bindings else None
        chips = [SLOT_LABELS[slot] for slot in SLOTS if binding and slot in binding["mask"]]
        chips.append("預設臉框" if card["face_rect"] == gallery_api.default_face_rect(card["image_size"]) else "自訂臉框")
        is_default = card["image_id"] == default
        if is_default:
            chips.append("目前預設")
        label = CARD_LABEL
        rows.append({
            "image_id": card["image_id"], "status": "card", "label": label,
            "artwork": _card_artwork(subject, card, generation, terminal),
            "is_default": is_default, "chips": chips,
            "requested_fields": card["requested_fields"], "binding_present": binding is not None,
            "created_at": card["created_at"],
        })
        if binding and len(warnings) < GALLERY_MAX_WARNINGS and all(binding["snapshot"][slot] == snapshot[slot] for slot in binding["mask"]):
            conditions = []
            for slot in SLOTS:
                if slot not in binding["mask"]:
                    continue
                value = binding["snapshot"][slot]
                name = ("、".join(_item_name(key) for key in value) or "未裝備") + "（任一）" if slot == "accessories" else _item_name(value)
                conditions.append(f"{SLOT_LABELS[slot]}：{name}")
            warnings.append({"image_id": card["image_id"], "label": label, "conditions": conditions})
    for job in pending:
        if job["image_id"] not in seen:
            rows.append(_synthetic(
                subject, job["image_id"], job["enqueued_at"], "pending", PENDING_LABEL,
                generation[0], descriptors.GENERATION_PENDING,
            ))
    if error:
        image_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{subject.full()}:{error['at']}:{error['code']}"))
        rows.append(_synthetic(
            subject, image_id, error["at"], "failed",
            f"暫時無法生成，稍後再試（{error['code']}）",
            generation[0], descriptors.GENERATION_FAILED,
        ))
    rows.sort(key=lambda row: -row["created_at"])
    return validate_gallery({
        "schema_version": GALLERY_SCHEMA_VERSION, "available": True, "kind": "gallery",
        "subjects": [entry[0] for entry in rail], "selected": subject.full(),
        "filters": _filters(rows), "cards": rows,
        "official_entries": _official_entries(subject, entity, generation, terminal),
        "equipment_summary": _equipment(snapshot) if snapshot is not None else None,
        "capabilities": {field: (subject.kind is ArtSubjectKind.CHARACTER if field == "supports_personal_official_preferences" else getattr(capability, field)) for field in CAPABILITY_FIELDS},
        "binding_warnings": warnings, "error_state": error,
    })

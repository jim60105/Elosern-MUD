"""Version-one gallery projection and exact wire schema; no mutation or service probe."""

from datetime import datetime, timezone
import math
import re
import uuid

from evennia.objects.models import ObjectDB

from typeclasses.entities import LivingEntity
from world.art import gallery as gallery_api
from world.art.formats import STORE_EXTENSIONS
from world.art.gallery_kinds import capabilities_for
from world.art.gallery_match import validated_card_identity
from world.art.gallery_prompt import GALLERY_PROMPT_FIELDS
from world.art.presenter import media_url_for
from world.art.queue import MAX_PENDING_GALLERY_JOBS, pending_gallery_jobs
from world.art.subjects import (
    ArtSubject, ArtSubjectError, ArtSubjectKind, character_subject_for,
    monster_subject_for, parse_subject,
)
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.observability import log_warn
from world.rules.party import live_companions

from .context import PresentationContext
from .protocol import (
    MAX_CANONICAL_JSON_BYTES, MAX_LIST_ITEMS, MAX_SAFE_INTEGER,
    ProtocolValidationError, _require_exact_fields, check_json_safety, json_byte_size,
)
from .registry import PanelUnavailableError

GALLERY_SCHEMA_VERSION = 1
GALLERY_MAX_SUBJECTS = 24
GALLERY_MAX_LABEL = 128
GALLERY_MAX_NAME = 64
GALLERY_MAX_CHIP = 16
GALLERY_MAX_URL = 129
GALLERY_MAX_WARNINGS = 5
GALLERY_MAX_CONDITION = 512
SLOT_LABELS = {"weapon_main": "主手", "weapon_off": "副手", "armor": "防具", "accessories": "飾品"}
SLOTS = gallery_api.SLOT_ORDER
FIELDS = GALLERY_PROMPT_FIELDS
CAPABILITY_FIELDS = ("supports_bindings", "supports_field_selection", "supports_free_text", "max_cards")
CARD_FIELDS = {
    "image_id", "status", "label", "url", "face_rect", "is_default", "chips",
    "requested_fields", "binding_present", "created_at",
}
PANEL_FIELDS = {
    "schema_version", "available", "kind", "subjects", "selected", "filters", "cards",
    "equipment_summary", "capabilities", "binding_warnings", "error_state",
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
        if row["status"] != "card":
            if row["url"] is not None or row["face_rect"] is not None or row["is_default"] or row["binding_present"] or chips or fields:
                raise ProtocolValidationError("synthetic row fabricated card data")
            continue
        url = _text(row["url"], GALLERY_MAX_URL, "gallery url")
        directory = "character" if selected.kind is ArtSubjectKind.CHARACTER else "monster"
        prefix = f"/art/gallery/{directory}/{selected.key}/{row['image_id']}"
        if not url.startswith(prefix) or url[len(prefix):] not in STORE_EXTENSIONS:
            raise ProtocolValidationError("url must name selected subject and image")
        try:
            gallery_api.validate_face_rect(row["face_rect"])
        except gallery_api.GalleryRecordError as exc:  # observability: ignore R2: wire rectangle rejection is returned to the caller
            raise ProtocolValidationError("invalid face_rect") from exc
        slot_chips = [label for label in SLOT_LABELS.values() if label in chips]
        face_chip = "預設臉框" if row["face_rect"] == gallery_api.DEFAULT_FACE_RECT else "自訂臉框"
        expected = slot_chips + [face_chip] + (["目前預設"] if row["is_default"] else [])
        if chips != expected or bool(slot_chips) != row["binding_present"]:
            raise ProtocolValidationError("incoherent chips")
        if row["binding_present"] and not capability["supports_bindings"] or fields and not capability["supports_field_selection"]:
            raise ProtocolValidationError("unsupported card facts")
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
    monsters = [entry(monster_subject_for(key), name=tier.display_name_zh) for key, tier in MONSTER_TIER_REGISTRY.items()]
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


def _timestamp_label(timestamp):
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OverflowError, OSError):  # observability: ignore R2: finite out-of-calendar epochs keep truthful numeric labels
        return str(timestamp)


def _synthetic(image_id, timestamp, status, label):
    return {
        "image_id": image_id, "status": status, "label": label, "url": None,
        "face_rect": None, "is_default": False, "chips": [], "requested_fields": [],
        "binding_present": False, "created_at": timestamp,
    }


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
    for card in cards:
        identity = validated_card_identity(subject, card)
        if identity is None or card["image_id"] in seen:
            continue
        seen.add(card["image_id"])
        binding = card["binding"] if capability.supports_bindings else None
        chips = [SLOT_LABELS[slot] for slot in SLOTS if binding and slot in binding["mask"]]
        chips.append("預設臉框" if card["face_rect"] == gallery_api.DEFAULT_FACE_RECT else "自訂臉框")
        is_default = card["image_id"] == default
        if is_default:
            chips.append("目前預設")
        label = f"肖像 {_timestamp_label(card['created_at'])}"
        rows.append({
            "image_id": card["image_id"], "status": "card", "label": label,
            "url": media_url_for(identity), "face_rect": card["face_rect"],
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
            rows.append(_synthetic(job["image_id"], job["enqueued_at"], "pending", f"肖像 {_timestamp_label(job['enqueued_at'])}（生成中）"))
    if error:
        image_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{subject.full()}:{error['at']}:{error['code']}"))
        rows.append(_synthetic(image_id, error["at"], "failed", f"暫時無法生成，稍後再試（{error['code']}）"))
    rows.sort(key=lambda row: -row["created_at"])
    return validate_gallery({
        "schema_version": GALLERY_SCHEMA_VERSION, "available": True, "kind": "gallery",
        "subjects": [entry[0] for entry in rail], "selected": subject.full(),
        "filters": _filters(rows), "cards": rows,
        "equipment_summary": _equipment(snapshot) if snapshot is not None else None,
        "capabilities": {field: getattr(capability, field) for field in CAPABILITY_FIELDS},
        "binding_warnings": warnings, "error_state": error,
    })

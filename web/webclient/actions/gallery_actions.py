"""Ten webclient-only gallery actions over the public art and rail-store seams.

Wire schemas are kind-neutral and fail before admission (malformed_payload).
The service owns capability/age refusals and prompt normalization. Binding's
capability refusal precedes card lookup, as in the public writer; other named
cards must survive the tolerant read. The dispatcher alone publishes results.

The four personal official-art preference actions (select, clear selection,
set one geometry component, clear one override) re-resolve every
client-supplied official identity through the startup catalog with the same
provenance resolver the presentation chain uses, so an identity can never
reach a subject whose content reference does not own it. The five existing
card-reference mutation adapters refuse an official identity with the stable
``official_read_only`` code before any card read: the official image is shared
read-only artwork, and the frontend's hidden affordances are never the
guarantee.
"""

import re

from web.webclient.presentation.gallery import validate_gallery_subject_key
from web.webclient.presentation.gallery_selection import select_gallery_subject
from world.art import gallery as gallery_api
from world.art.gallery_kinds import capabilities_for
from world.art.gallery_prompt import (
    CUSTOM_PROMPT_MAX, GALLERY_PROMPT_FIELDS, GalleryPromptError,
    validate_custom_prompt, validate_fields,
)
from world.art.service import request_gallery_image, resolve_gallery_subject_by_key
from world.art.subjects import ArtSubjectError, ArtSubjectKind, monster_subject_for
from world.observability import log_info, log_warn

AFFECTED_GALLERY_PANELS = ("gallery", "art", "roster")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
REJECTION_MESSAGES = {
    "unknown_subject": "找不到此肖像圖庫。",
    "unknown_card": "找不到這張肖像。",
    "unknown_official_image": "找不到這張官方圖片。",
    "official_read_only": "官方圖片為唯讀，無法修改。",
    "unknown_field": "生成資料包含未知欄位。",
    "prompt_too_long": "補充提示詞超過字數上限。",
    "field_selection_unsupported": "此類肖像不支援選擇生成資料。",
    "free_text_unsupported": "此類肖像不支援補充提示詞。",
    "binding_unsupported": "此類肖像不支援裝備綁定。",
    "invalid_prompt": "生成資料或補充提示詞格式錯誤。",
    "subject_ineligible": "角色資料不符合肖像生成條件。",
    "gallery_rejected": "無法更新這張肖像。",
    "stage_rejected": "無法儲存比例調整。",
}
_SUCCESS = {
    "gallery.generate": ("gallery_queued", "已加入肖像生成佇列。"),
    "gallery.default.set": ("gallery_default_set", "已設為預設肖像。"),
    "gallery.card.delete": ("gallery_card_deleted", "已刪除肖像。"),
    "gallery.face_rect.update": ("gallery_face_rect_updated", "已儲存臉部框選。"),
    "gallery.stage.update": ("gallery_stage_updated", "已儲存比例調整。"),
    "gallery.binding.save": ("gallery_binding_saved", "已儲存裝備綁定。"),
}
_SUCCESS_OFFICIAL = {
    "gallery.official.select": ("gallery_official_selected", "已設為預設影像。"),
    "gallery.official.clear_selection": (
        "gallery_official_selection_cleared",
        "已清除官方圖片選取。",
    ),
    "gallery.official.geometry.set": (
        "gallery_official_geometry_set",
        "已儲存官方圖片的個人調整。",
    ),
    "gallery.official.geometry.clear": (
        "gallery_official_geometry_cleared",
        "已清除官方圖片的個人調整。",
    ),
}


class GalleryActionError(ValueError):
    """A gallery action payload violates the exact wire schema."""


def _card_reference(value):
    """The closed card-reference union: a card uuid, or an official identity.

    The mutation payloads admit BOTH forms so a direct request naming an
    official identity reaches its adapter and is refused there with the stable
    ``official_read_only`` code — the backend is the authority, while a
    uuid-only schema would degrade that refusal into an indistinguishable
    malformed payload.
    """
    if isinstance(value, str) and _UUID.fullmatch(value) is not None:
        return value
    try:
        return gallery_api.validate_official_identity(value)
    except gallery_api.GalleryRecordError as exc:  # observability: ignore R2: payload rejection is returned to the caller
        raise GalleryActionError(
            "image_id must be a canonical UUID or a validated official identity"
        ) from exc


def _official_identity(value):
    """The identity verbatim when it passes the writers' own closed grammar."""
    try:
        return gallery_api.validate_official_identity(value)
    except gallery_api.GalleryRecordError as exc:  # observability: ignore R2: payload rejection is returned to the caller
        raise GalleryActionError(
            "identity must be a validated root-relative official identity"
        ) from exc


def _payload(payload, keys):
    if not isinstance(payload, dict) or set(payload) != set(keys):
        raise GalleryActionError("gallery payload requires exactly its declared fields")
    validate_gallery_subject_key(payload["subject_key"])
    if "image_id" in keys:
        _card_reference(payload["image_id"])
    if "identity" in keys:
        _official_identity(payload["identity"])
    return dict(payload)


def validate_gallery_subject_select_payload(payload):
    """Accept exactly one grammar-valid rail key; membership is domain state."""
    return _payload(payload, ("subject_key",))


def validate_gallery_generate_payload(payload):
    """Validate catalog and printable prompt bounds without kind capability gates."""
    result = _payload(payload, ("subject_key", "fields", "custom_prompt"))
    fields = payload["fields"]
    if not isinstance(fields, list) or len(fields) > len(GALLERY_PROMPT_FIELDS):
        raise GalleryActionError("fields must be a bounded list")
    validate_fields(fields)
    validate_custom_prompt(payload["custom_prompt"])
    return result


def validate_gallery_card_payload(payload):
    """The same exact identity pair serves default selection and deletion."""
    return _payload(payload, ("subject_key", "image_id"))


def validate_gallery_face_rect_update_payload(payload):
    """The art API owns rectangle bounds; acceptance never changes coordinates."""
    result = _payload(payload, ("subject_key", "image_id", "face_rect"))
    gallery_api.validate_face_rect(payload["face_rect"])
    return result


def validate_gallery_stage_update_payload(payload):
    """Admit an exact whole triple; the gallery API owns placement bounds."""
    result = _payload(payload, ("subject_key", "image_id", "stage"))
    gallery_api.validate_stage(payload["stage"])
    return result


def validate_gallery_binding_save_payload(payload):
    """Only slot ids cross the wire, never client-selected equipment keys."""
    result = _payload(payload, ("subject_key", "image_id", "slots"))
    slots = payload["slots"]
    if (
        not isinstance(slots, list) or not 1 <= len(slots) <= len(gallery_api.SLOT_ORDER)
        or not all(isinstance(slot, str) and slot in gallery_api.SLOT_ORDER for slot in slots)
        or len(set(slots)) != len(slots)
    ):
        raise GalleryActionError("slots must be a nonempty distinct selection of declared slots")
    return result


def validate_gallery_official_select_payload(payload):
    """Select exactly one official identity; scope is domain state."""
    return _payload(payload, ("subject_key", "identity"))


def validate_gallery_official_clear_selection_payload(payload):
    """Clearing the personal selection names only the subject."""
    return _payload(payload, ("subject_key",))


def validate_gallery_official_geometry_payload(payload):
    """One component of an official image's personal geometry, or both.

    ``subject_key`` and ``identity`` are required; ``face_rect`` and ``stage``
    are each optional, but at least one must be present, because a payload
    naming neither asks for no change. An omitted component keeps whatever the
    record already stores for that identity — the union is exactly how the
    client edits one component without rewriting the other.
    """
    if not isinstance(payload, dict) or set(payload) - {
        "subject_key",
        "identity",
        "face_rect",
        "stage",
    }:
        raise GalleryActionError("gallery payload requires exactly its declared fields")
    if not {"subject_key", "identity"} <= set(payload):
        raise GalleryActionError("gallery payload requires exactly its declared fields")
    validate_gallery_subject_key(payload["subject_key"])
    _official_identity(payload["identity"])
    if "face_rect" in payload:
        gallery_api.validate_face_rect(payload["face_rect"])
    if "stage" in payload:
        gallery_api.validate_stage(payload["stage"])
    if not {"face_rect", "stage"} & set(payload):
        raise GalleryActionError(
            "an official geometry payload carries a face_rect, a stage, or both"
        )
    return dict(payload)


def validate_gallery_official_geometry_clear_payload(payload):
    """Clearing one identity's personal geometry override."""
    return _payload(payload, ("subject_key", "identity"))


def _rejected(code):
    return {
        "outcome": "rejected", "code": code, "message": REJECTION_MESSAGES[code],
        "affected_panels": AFFECTED_GALLERY_PANELS,
    }


def _error_code(error, *, resolved):
    """Translate known typed diagnostics; never expose backend text to players.

    Unknown fields and oversized prompts are defensive service mappings: the
    production dispatcher rejects those earlier as malformed_payload. Other
    prompt errors (including duplicates) share invalid_prompt. Unknown future
    record refusals stay bounded instead of inventing a capability or success.
    Diagnostic sources are gallery_prompt.validate_fields/validate_custom_prompt,
    service.request_gallery_image, and gallery's public card writers. Those
    exceptions expose text, not structured codes; the real-service rejection
    tests protect this translation when their diagnostics change.
    """
    if isinstance(error, ArtSubjectError):
        return "subject_ineligible" if resolved else "unknown_subject"
    text = str(error)
    if isinstance(error, GalleryPromptError):
        if text.startswith("unknown gallery prompt field "):
            return "unknown_field"
        if text == f"custom_prompt must be at most {CUSTOM_PROMPT_MAX} code points":
            return "prompt_too_long"
        if "declares no prompt field selection;" in text:
            return "field_selection_unsupported"
        if "declares no free-text support;" in text:
            return "free_text_unsupported"
        return "invalid_prompt"
    if "declares no binding support;" in text:
        return "binding_unsupported"
    if text == "this subject has no gallery record" or text.startswith(("no card with image_id ", "no valid card with image_id ")):
        return "unknown_card"
    if text.startswith("stage"):
        return "stage_rejected"
    return "gallery_rejected"


def _context(action_id, payload):
    context = {
        "subject": payload["subject_key"], "action_id": action_id,
        "image_id": payload.get("image_id"),
        "kind": payload["subject_key"].rsplit(":", 1)[0],
    }
    if "identity" in payload:
        context["identity"] = payload["identity"]
    return context


def _gallery_subject_select_adapter(actor, payload, session=None):
    result = dict(select_gallery_subject(session, actor, payload["subject_key"]))
    result["affected_panels"] = AFFECTED_GALLERY_PANELS
    context = _context("gallery.subject.select", payload)
    if result["outcome"] == "success":
        log_info("gallery_action", context=context)
    else:
        log_warn("gallery_action", context=context)
    return result


def _mutate(action_id, payload):
    context = _context(action_id, payload)
    subject = None
    try:
        parsed = validate_gallery_subject_key(payload["subject_key"])
        if parsed.kind is ArtSubjectKind.CHARACTER:
            subject, entity = resolve_gallery_subject_by_key(payload["subject_key"])
        elif parsed.kind is ArtSubjectKind.MONSTER:
            subject, entity = monster_subject_for(parsed.key), None
        else:
            raise ArtSubjectError("no typed producer resolves this gallery kind")
        image_id = payload.get("image_id")
        if action_id == "gallery.binding.save" and not capabilities_for(subject.kind.value).supports_bindings:
            log_warn("gallery_action", context=context)
            return _rejected("binding_unsupported")
        if image_id is not None and _UUID.fullmatch(image_id) is None:
            # An official identity can never name a card: the mounted artwork is
            # shared and read-only, so a DIRECT request is refused here — before
            # any card read or preference write — with zero side effects.
            log_warn("gallery_action", context=context)
            return _rejected("official_read_only")
        if image_id is not None and not any(card["image_id"] == image_id for card in gallery_api.cards_for(subject)):
            raise gallery_api.GalleryRecordError(f"no card with image_id {image_id!r} exists")
        if action_id == "gallery.generate":
            image_id = request_gallery_image(
                entity if entity is not None else subject,
                fields=payload["fields"], custom_prompt=payload["custom_prompt"],
            )
            context["image_id"] = image_id
        elif action_id == "gallery.default.set":
            gallery_api.set_default(subject, image_id)
        elif action_id == "gallery.card.delete":
            gallery_api.remove_card(subject, image_id)
        elif action_id == "gallery.face_rect.update":
            gallery_api.update_card_face_rect(subject, image_id, payload["face_rect"])
        elif action_id == "gallery.stage.update":
            gallery_api.set_stage(subject, image_id, payload["stage"])
        elif action_id == "gallery.binding.save":
            snapshot = gallery_api.snapshot_for(entity)
            mask = [slot for slot in gallery_api.SLOT_ORDER if slot in payload["slots"]]
            gallery_api.update_card_binding(subject, image_id, {
                "mask": mask, "snapshot": {slot: snapshot[slot] for slot in mask},
            })
        else:
            raise ValueError("unregistered gallery mutation")
    except (ArtSubjectError, GalleryPromptError, gallery_api.GalleryRecordError) as error:
        log_warn("gallery_action", context=context, exc=error)
        return _rejected(_error_code(error, resolved=subject is not None))
    code, message = _SUCCESS[action_id]
    result = {"outcome": "success", "code": code, "message": message, "affected_panels": AFFECTED_GALLERY_PANELS}
    if action_id == "gallery.generate":
        result["data"] = {"image_id": image_id}
    log_info("gallery_action", context=context)
    return result


def _gallery_generate_adapter(actor, payload, session=None):
    return _mutate("gallery.generate", payload)


def _gallery_default_set_adapter(actor, payload, session=None):
    return _mutate("gallery.default.set", payload)


def _gallery_card_delete_adapter(actor, payload, session=None):
    return _mutate("gallery.card.delete", payload)


def _gallery_face_rect_update_adapter(actor, payload, session=None):
    return _mutate("gallery.face_rect.update", payload)


def _gallery_stage_update_adapter(actor, payload, session=None):
    return _mutate("gallery.stage.update", payload)


def _gallery_binding_save_adapter(actor, payload, session=None):
    return _mutate("gallery.binding.save", payload)


def _official_target(subject, entity, identity):
    """The catalog image an identity names inside the subject's OWN reference.

    ``None`` when the entity declares no content reference, the snapshot holds
    no such content directory, or the identity is not one of that directory's
    admitted images. The scope check runs through the same provenance resolver
    the presentation chain uses, so a client-supplied string can never widen a
    subject's reference — and an identity outside it is refused, never stored.
    """
    from world.art import official
    from world.art.official_refs import official_content_reference_for_entity

    if entity is None:
        return None
    reference = official_content_reference_for_entity(entity)
    if reference is None:
        return None
    catalog = official.current_catalog()
    content = catalog.content(reference.kind, reference.key)
    if content is None or identity not in content.images:
        return None
    return catalog.entry(identity)


def _merge_official_geometry(subject, identity, image, payload):
    """Validate the sent components against the image, merge, and persist.

    Only the components the client sent are validated and replaced: an omitted
    component keeps the override already stored for that identity, so editing
    the rectangle never rewrites the stored stage and vice versa. A sent
    rectangle is validated against the catalog image's decoded dimensions
    before the write — the same squareness rule the stored card contract uses
    — so a rectangle illegal for the image's CURRENT bytes never reaches the
    record. The write itself goes through the sole writer's public API.
    """
    stored = gallery_api.official_preferences_for(subject).geometry.get(identity, {})
    face_rect = payload["face_rect"] if "face_rect" in payload else stored.get("face_rect")
    stage = payload["stage"] if "stage" in payload else stored.get("stage")
    merged = {}
    if face_rect is not None:
        merged["face_rect"] = gallery_api.validate_face_rect(
            face_rect, image_size=image.image_size
        )
    if stage is not None:
        merged["stage"] = gallery_api.validate_stage(stage)
    if not merged:
        raise gallery_api.GalleryRecordError(
            "an official geometry override needs a face_rect, a stage, or both"
        )
    gallery_api.set_official_geometry(
        subject, identity, face_rect=merged.get("face_rect"), stage=merged.get("stage")
    )


def _mutate_official(action_id, payload):
    """One personal official-art preference write, re-resolving its identity."""
    context = _context(action_id, payload)
    subject = None
    try:
        parsed = validate_gallery_subject_key(payload["subject_key"])
        if parsed.kind is ArtSubjectKind.CHARACTER:
            subject, entity = resolve_gallery_subject_by_key(payload["subject_key"])
        elif parsed.kind is ArtSubjectKind.MONSTER:
            subject, entity = monster_subject_for(parsed.key), None
        else:
            raise ArtSubjectError("no typed producer resolves this gallery kind")
        if action_id == "gallery.official.clear_selection":
            # Clearing touches only the subject's own record: no identity is
            # named, so no reference scope applies.
            gallery_api.clear_official_selection(subject)
        else:
            identity = payload["identity"]
            image = _official_target(subject, entity, identity)
            if image is None:
                log_warn("gallery_action", context=context)
                return _rejected("unknown_official_image")
            if action_id == "gallery.official.select":
                gallery_api.set_official_selection(subject, identity)
            elif action_id == "gallery.official.geometry.set":
                _merge_official_geometry(subject, identity, image, payload)
            elif action_id == "gallery.official.geometry.clear":
                gallery_api.clear_official_geometry(subject, identity)
            else:
                raise ValueError("unregistered gallery preference action")
    except (ArtSubjectError, gallery_api.GalleryRecordError) as error:
        log_warn("gallery_action", context=context, exc=error)
        return _rejected(_error_code(error, resolved=subject is not None))
    code, message = _SUCCESS_OFFICIAL[action_id]
    log_info("gallery_action", context=context)
    return {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": AFFECTED_GALLERY_PANELS,
    }


def _gallery_official_select_adapter(actor, payload, session=None):
    return _mutate_official("gallery.official.select", payload)


def _gallery_official_clear_selection_adapter(actor, payload, session=None):
    return _mutate_official("gallery.official.clear_selection", payload)


def _gallery_official_geometry_set_adapter(actor, payload, session=None):
    return _mutate_official("gallery.official.geometry.set", payload)


def _gallery_official_geometry_clear_adapter(actor, payload, session=None):
    return _mutate_official("gallery.official.geometry.clear", payload)

"""Six webclient-only gallery actions over the public art and rail-store seams.

Wire schemas are kind-neutral and fail before admission (malformed_payload).
The service owns capability/age refusals and prompt normalization. Binding's
capability refusal precedes card lookup, as in the public writer; other named
cards must survive the tolerant read. The dispatcher alone publishes results.
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

AFFECTED_GALLERY = ("gallery",)
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
REJECTION_MESSAGES = {
    "unknown_subject": "找不到此肖像圖庫。",
    "unknown_card": "找不到這張肖像。",
    "unknown_field": "生成資料包含未知欄位。",
    "prompt_too_long": "補充提示詞超過字數上限。",
    "field_selection_unsupported": "此類肖像不支援選擇生成資料。",
    "free_text_unsupported": "此類肖像不支援補充提示詞。",
    "binding_unsupported": "此類肖像不支援裝備綁定。",
    "invalid_prompt": "生成資料或補充提示詞格式錯誤。",
    "subject_ineligible": "角色資料不符合肖像生成條件。",
    "gallery_rejected": "無法更新這張肖像。",
}
_SUCCESS = {
    "gallery.generate": ("gallery_queued", "已加入肖像生成佇列。"),
    "gallery.default.set": ("gallery_default_set", "已設為預設肖像。"),
    "gallery.card.delete": ("gallery_card_deleted", "已刪除肖像。"),
    "gallery.face_rect.update": ("gallery_face_rect_updated", "已儲存臉部框選。"),
    "gallery.binding.save": ("gallery_binding_saved", "已儲存裝備綁定。"),
}


class GalleryActionError(ValueError):
    """A gallery action payload violates the exact wire schema."""


def _payload(payload, keys):
    if not isinstance(payload, dict) or set(payload) != set(keys):
        raise GalleryActionError("gallery payload requires exactly its declared fields")
    validate_gallery_subject_key(payload["subject_key"])
    if "image_id" in keys:
        value = payload["image_id"]
        if not isinstance(value, str) or _UUID.fullmatch(value) is None:
            raise GalleryActionError("image_id must be canonical lowercase UUID text")
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


def _rejected(code):
    return {
        "outcome": "rejected", "code": code, "message": REJECTION_MESSAGES[code],
        "affected_panels": AFFECTED_GALLERY,
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
    return "gallery_rejected"


def _context(action_id, payload):
    return {
        "subject": payload["subject_key"], "action_id": action_id,
        "image_id": payload.get("image_id"),
        "kind": payload["subject_key"].rsplit(":", 1)[0],
    }


def _gallery_subject_select_adapter(actor, payload, session=None):
    result = dict(select_gallery_subject(session, actor, payload["subject_key"]))
    result["affected_panels"] = AFFECTED_GALLERY
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
    result = {"outcome": "success", "code": code, "message": message, "affected_panels": AFFECTED_GALLERY}
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


def _gallery_binding_save_adapter(actor, payload, session=None):
    return _mutate("gallery.binding.save", payload)

"""Version-3 read-only ``dialogue`` presentation panel.

The presenter serializes the viewer's live dialogue session into the exact
version-3 shape per Shared contract v2:
{schema_version, available, kind, host, actor, bond_stage, context_id,
 delivery, choices, pure_chain, reading_revision, completed_topic_ids, unlock_batch}
"""

from typing import Any

from web.webclient.presentation.affordances import (
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_KEYWORD_ID_CHARS,
    MAX_KEYWORD_LABEL_CODE_POINTS,
    _scripted_keyword_descriptors,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.art_view import ArtViewError, build_art_view, portrait_catalog_key
from world.rules.dialogue import MAX_DIALOGUE_SESSION_LINE_CODE_POINTS

DIALOGUE_SCHEMA_VERSION = 3
DIALOGUE_PANEL_MAX_BYTES = 24576
MAX_DIALOGUE_PORTRAIT_REF = 32
DIALOGUE_MAX_CHOICES = 16


class DialoguePanelError(ProtocolValidationError):
    """The available dialogue payload violates its exact bounded schema."""


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points."""
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise DialoguePanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _bounded_text(value: str, field: str, maximum: int) -> str:
    if not value or not value.strip():
        raise DialoguePanelError(f"{field} must be non-empty")
    if sum(1 for _ in value) > maximum:
        raise DialoguePanelError(f"{field} must be at most {maximum} code points")
    return _reject_lone_surrogates(value, field)


def _validate_entity_descriptor(value: Any, role: str) -> dict[str, Any]:
    _require_exact_fields(
        value, f"dialogue {role}", {"identity", "display_name", "portrait_ref"}, {}
    )
    identity = _require_int(value, "identity", minimum=1, maximum=MAX_SAFE_INTEGER)
    display_name = _bounded_text(
        _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        f"{role} display_name",
        MAX_DISPLAY_NAME_CODE_POINTS,
    )
    portrait_ref = value["portrait_ref"]
    if portrait_ref is not None:
        if not isinstance(portrait_ref, str) or not portrait_ref.isdecimal():
            raise DialoguePanelError(f"{role} portrait_ref must be an opaque decimal catalog key or null")
        if len(portrait_ref) > MAX_DIALOGUE_PORTRAIT_REF:
            raise DialoguePanelError(f"{role} portrait_ref exceeds its bound")
    return {
        "identity": identity,
        "display_name": display_name,
        "portrait_ref": portrait_ref,
    }


def _validate_bond_stage(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DialoguePanelError("bond_stage must be a stage name string or null")
    return _bounded_text(value, "bond_stage", MAX_DISPLAY_NAME_CODE_POINTS)


def _validate_delivery(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(
        value,
        "dialogue delivery",
        {
            "delivery_id",
            "context_id",
            "topic_id",
            "scene_id",
            "scene_revision",
            "phase_revision",
            "kind",
            "lines",
        },
        {},
    )
    delivery_id = _require_str(value, "delivery_id", maximum=64)
    context_id = _require_str(value, "context_id", maximum=64)
    topic_id = value.get("topic_id")
    if topic_id is not None:
        if not isinstance(topic_id, str) or len(topic_id) > 2048:
            raise DialoguePanelError("delivery topic_id must be str <= 2048 or null")
    scene_id = _require_str(value, "scene_id", maximum=2048)
    scene_rev = _require_str(value, "scene_revision", maximum=64)
    kind = value.get("kind")
    if kind not in ("formal", "refusal", "opening", "service"):
        raise DialoguePanelError("delivery kind must be formal, refusal, opening, or service")
    lines = value.get("lines")
    if not isinstance(lines, list):
        raise DialoguePanelError("delivery lines must be a list")
    val_lines = []
    for idx, l in enumerate(lines):
        if not isinstance(l, dict):
            raise DialoguePanelError(f"line {idx} must be an object")
        lkind = l.get("kind")
        if lkind == "speech":
            _require_exact_fields(l, f"speech line {idx}", {"kind", "speaker", "text"}, {})
            spkr = l.get("speaker")
            if spkr not in ("actor", "host"):
                raise DialoguePanelError(f"speech speaker must be actor or host, got {spkr!r}")
            text = _bounded_text(_require_str(l, "text", maximum=2000), f"speech line {idx}", 2000)
            val_lines.append({"kind": "speech", "speaker": spkr, "text": text})
        elif lkind == "narration":
            _require_exact_fields(l, f"narration line {idx}", {"kind", "text"}, {})
            text = _bounded_text(_require_str(l, "text", maximum=2000), f"narration line {idx}", 2000)
            val_lines.append({"kind": "narration", "text": text})
        else:
            raise DialoguePanelError(f"unknown line kind {lkind!r}")
    return {
        "delivery_id": delivery_id,
        "context_id": context_id,
        "topic_id": topic_id,
        "scene_id": scene_id,
        "scene_revision": scene_rev,
        "phase_revision": value.get("phase_revision"),
        "kind": kind,
        "lines": val_lines,
    }


def _validate_choice(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "dialogue choice",
        {
            "topic_id",
            "keyword_id",
            "label",
            "availability",
            "requirement_hint",
            "unread",
            "predecessors",
            "action_payload",
        },
        {},
    )
    topic_id = _require_str(value, "topic_id", maximum=2048)
    if not topic_id.strip():
        raise DialoguePanelError("topic_id must be non-empty")
    keyword_id = _require_str(value, "keyword_id", maximum=MAX_KEYWORD_ID_CHARS)
    if not keyword_id.strip():
        raise DialoguePanelError("keyword_id must be non-empty")
    _reject_lone_surrogates(keyword_id, "keyword_id")
    label = _bounded_text(
        _require_str(value, "label", maximum=MAX_KEYWORD_LABEL_CODE_POINTS),
        "choice label",
        MAX_KEYWORD_LABEL_CODE_POINTS,
    )
    availability = value.get("availability")
    if availability not in ("open", "locked", "hidden"):
        raise DialoguePanelError("availability must be open, locked, or hidden")
    req_hint = value.get("requirement_hint")
    if req_hint is not None and not isinstance(req_hint, str):
        raise DialoguePanelError("requirement_hint must be string or null")
    unread = _require_bool(value, "unread")
    preds = value.get("predecessors", ())
    if not isinstance(preds, (list, tuple)):
        raise DialoguePanelError("predecessors must be a list")
    for p in preds:
        if not isinstance(p, str) or not p:
            raise DialoguePanelError("predecessor ID must be nonempty str")

    payload = value.get("action_payload")
    if not isinstance(payload, dict):
        raise DialoguePanelError("action_payload must be an object")
    _require_exact_fields(payload, "choice action_payload", {"npc_id", "topic_id", "context_id"}, {})
    npc_id = _require_int(payload, "npc_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    action_topic_id = _require_str(payload, "topic_id", maximum=2048)
    ctx_id = payload.get("context_id")
    if ctx_id is not None and (not isinstance(ctx_id, str) or len(ctx_id) > 64):
        raise DialoguePanelError("action_payload context_id must be str <= 64 or null")

    return {
        "topic_id": topic_id,
        "keyword_id": keyword_id,
        "label": label,
        "availability": availability,
        "requirement_hint": req_hint,
        "unread": unread,
        "predecessors": list(preds),
        "action_payload": {
            "npc_id": npc_id,
            "topic_id": action_topic_id,
            "context_id": ctx_id,
        },
    }


MAX_UNLOCK_BATCH_ID_CHARS = 64
MAX_UNLOCK_BATCH_TOPICS = 16


def _validate_unlock_batch(
    value: Any, *, host: dict[str, Any], context_id: str, rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Validate one live watcher's wrapped unlock batch (Shared contract v2).

    ``{batch_id, host_id, context_id, topic_ids}``: an opaque ASCII batch ID,
    this panel's own host identity and context, and 1..16 unique topic IDs
    that are open choices of this same panel, in declaration order.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DialoguePanelError("unlock_batch must be an object or null")
    _require_exact_fields(
        value, "unlock_batch", {"batch_id", "host_id", "context_id", "topic_ids"}, {}
    )
    batch_id = _require_str(value, "batch_id", maximum=MAX_UNLOCK_BATCH_ID_CHARS)
    if not batch_id or not batch_id.isascii():
        raise DialoguePanelError("unlock_batch batch_id must be non-empty ASCII")
    host_id = _require_int(value, "host_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    if host_id != host["identity"]:
        raise DialoguePanelError("unlock_batch host_id must be this panel's host")
    if value["context_id"] != context_id:
        raise DialoguePanelError("unlock_batch context_id must be this panel's context")
    topic_ids = value["topic_ids"]
    if not isinstance(topic_ids, list) or not 1 <= len(topic_ids) <= MAX_UNLOCK_BATCH_TOPICS:
        raise DialoguePanelError(
            f"unlock_batch topic_ids must hold 1..{MAX_UNLOCK_BATCH_TOPICS} entries"
        )
    open_order = [row["topic_id"] for row in rows if row["availability"] == "open"]
    if len(set(topic_ids)) != len(topic_ids):
        raise DialoguePanelError("unlock_batch topic_ids must be unique")
    positions = []
    for topic_id in topic_ids:
        if not isinstance(topic_id, str) or topic_id not in open_order:
            raise DialoguePanelError("unlock_batch topic_ids must be open choices")
        positions.append(open_order.index(topic_id))
    if positions != sorted(positions):
        raise DialoguePanelError("unlock_batch topic_ids must keep declaration order")
    return {
        "batch_id": batch_id,
        "host_id": host_id,
        "context_id": context_id,
        "topic_ids": list(topic_ids),
    }


def validate_dialogue(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``dialogue`` payload."""
    _require_exact_fields(
        payload,
        "dialogue panel",
        {
            "schema_version",
            "available",
            "kind",
            "host",
            "actor",
            "bond_stage",
            "context_id",
            "delivery",
            "choices",
            "pure_chain",
            "reading_revision",
            "completed_topic_ids",
            "unlock_batch",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != DIALOGUE_SCHEMA_VERSION:
        raise DialoguePanelError("unsupported dialogue schema_version")
    if not _require_bool(payload, "available"):
        raise DialoguePanelError("available must be true for the dialogue form")
    if payload["kind"] != "dialogue":
        raise DialoguePanelError("kind must be dialogue")
    host = _validate_entity_descriptor(payload["host"], "host")
    actor = _validate_entity_descriptor(payload["actor"], "actor")
    bond_stage = _validate_bond_stage(payload["bond_stage"])
    context_id = _require_str(payload, "context_id", maximum=64)
    delivery = _validate_delivery(payload.get("delivery"))

    choices = payload["choices"]
    if not isinstance(choices, list) or len(choices) > DIALOGUE_MAX_CHOICES:
        raise DialoguePanelError(
            f"choices must be a list of at most {DIALOGUE_MAX_CHOICES} entries"
        )
    rows = [_validate_choice(entry) for entry in choices]
    topic_ids = [row["topic_id"] for row in rows]
    if len(set(topic_ids)) != len(topic_ids):
        raise DialoguePanelError("dialogue choice topic ids must be unique")

    pure_chain = payload.get("pure_chain", [])
    if not isinstance(pure_chain, list) or len(pure_chain) > 15:
        raise DialoguePanelError("pure_chain must be a list of at most 15 entries")
    validated_chain = []
    for index, entry in enumerate(pure_chain):
        _require_exact_fields(
            entry, f"pure_chain entry {index}", {"delivery", "predecessors"}, {}
        )
        chain_delivery = _validate_delivery(entry["delivery"])
        if chain_delivery is None or not chain_delivery["topic_id"]:
            raise DialoguePanelError(
                f"pure_chain entry {index} needs a formal delivery with a topic"
            )
        if chain_delivery["kind"] != "formal":
            raise DialoguePanelError(
                f"pure_chain entry {index} delivery must be formal"
            )
        predecessors = entry["predecessors"]
        if not isinstance(predecessors, list) or not 1 <= len(predecessors) <= 16:
            raise DialoguePanelError(
                f"pure_chain entry {index} needs 1..16 predecessors"
            )
        for predecessor in predecessors:
            if (
                not isinstance(predecessor, str)
                or not predecessor
                or len(predecessor) > 2048
            ):
                raise DialoguePanelError(
                    f"pure_chain entry {index} predecessor is invalid"
                )
        if len(set(predecessors)) != len(predecessors):
            raise DialoguePanelError(
                f"pure_chain entry {index} predecessors must be unique"
            )
        validated_chain.append(
            {"delivery": chain_delivery, "predecessors": list(predecessors)}
        )

    reading_revision = _require_int(payload, "reading_revision", minimum=0, maximum=MAX_SAFE_INTEGER)

    completed_topic_ids = payload.get("completed_topic_ids", [])
    if not isinstance(completed_topic_ids, list) or len(completed_topic_ids) > 16:
        raise DialoguePanelError("completed_topic_ids must be a list of at most 16 entries")
    if len(set(completed_topic_ids)) != len(completed_topic_ids):
        raise DialoguePanelError("completed_topic_ids must be unique")

    unlock_batch = _validate_unlock_batch(
        payload.get("unlock_batch"), host=host, context_id=context_id, rows=rows
    )

    result = {
        "schema_version": DIALOGUE_SCHEMA_VERSION,
        "available": True,
        "kind": "dialogue",
        "host": host,
        "actor": actor,
        "bond_stage": bond_stage,
        "context_id": context_id,
        "delivery": delivery,
        "choices": rows,
        "pure_chain": validated_chain,
        "reading_revision": reading_revision,
        "completed_topic_ids": completed_topic_ids,
        "unlock_batch": unlock_batch,
    }
    if json_byte_size(result) > DIALOGUE_PANEL_MAX_BYTES:
        raise DialoguePanelError(f"dialogue payload exceeds {DIALOGUE_PANEL_MAX_BYTES} bytes")
    return result


def _resolve_live_host(character: Any) -> Any | None:
    """The session NPC re-resolved as present + talk-interactable, or ``None``."""
    from evennia.objects.objects import ObjectDB

    from typeclasses.npcs import NPC
    from world.rules.dialogue import live_dialogue_session
    from world.rules.npc_intents import intent_context_ok

    session = live_dialogue_session(character)
    if session is None:
        return None
    obj = ObjectDB.objects.filter(id=session.npc_id).first()
    if obj is None or not isinstance(obj, NPC):
        return None
    if not intent_context_ok(obj, character):
        return None
    return obj


def dialogue_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``dialogue`` panel for the authenticated puppet."""
    from world.narrative.dialogue_reading import read_reading
    from world.rules.dialogue import (
        chain_deliveries,
        delivery_to_wire,
        live_dialogue_session,
    )
    from world.rules.dialogue_context import (
        DialogueContextError,
        resolve_dialogue_context,
    )
    from world.rules.npc_identity import npc_display_name

    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    if getattr(actor, "location", None) is None:
        raise PanelUnavailableError
    session = live_dialogue_session(actor)
    if session is None:
        raise PanelUnavailableError
    npc = _resolve_live_host(actor)
    if npc is None:  # observability: ignore R2: race between the liveness read and the re-resolve degrades to the registered unavailable form
        raise PanelUnavailableError
    try:
        owner = resolve_dialogue_context(actor, npc).owner
    except DialogueContextError:  # observability: ignore R2: a stale control context degrades to the unavailable panel
        raise PanelUnavailableError
    # The host's bond is the owning player's relationship: a possessed
    # companion speaks with its own portrait and name but never its own record.
    bond_stage = (
        npc.relations.stage_for(owner).name
        if npc.relations.has_record(owner)
        else None
    )

    host_identity = int(npc.pk)
    portrait_ref = None
    try:
        view = build_art_view(actor)
    except ArtViewError:  # observability: ignore R2: an unbuildable art view is a designed degrade path
        view = None
    if view is not None and any(
        entity.identity == host_identity for entity in view.entities
    ):
        portrait_ref = portrait_catalog_key(host_identity)

    actor_identity = int(actor.pk)
    actor_portrait_ref = None
    if view is not None and any(
        entity.identity == actor_identity for entity in view.entities
    ):
        actor_portrait_ref = portrait_catalog_key(actor_identity)

    if session.delivery:
        delivery_wire = delivery_to_wire(session.delivery)
    elif session.line:
        delivery_wire = {
            "delivery_id": session.line_delivery_id or "line-1",
            "context_id": session.context_id,
            "topic_id": None,
            "scene_id": "native_line",
            "scene_revision": "r1",
            "phase_revision": session.phase_revision,
            "kind": "opening",
            "lines": [{"kind": "speech", "speaker": "host", "text": session.line}],
        }
    else:
        delivery_wire = None
    choices = _scripted_keyword_descriptors(
        npc, actor=actor, context_id=session.context_id
    )[:DIALOGUE_MAX_CHOICES]

    # Reading is owner-shared narrative state: one record read per render gives
    # this connection the owner's revision, its saved completions at this host
    # and the current delivery's pre-delivered public chain. Every field is
    # read-only; a connection whose own scene is playing keeps its delivery.
    reading = read_reading(owner)
    host_reading = reading.hosts.get(session.host_key)
    completed_topic_ids = (
        list(host_reading.completed_topic_ids())[:16]
        if host_reading is not None
        else []
    )
    pure_chain = [
        {"delivery": delivery_to_wire(node.delivery), "predecessors": list(node.predecessors)}
        for node in chain_deliveries(session, npc, actor=actor)
    ]

    return validate_dialogue(
        {
            "schema_version": DIALOGUE_SCHEMA_VERSION,
            "available": True,
            "kind": "dialogue",
            "host": {
                "identity": host_identity,
                "display_name": npc_display_name(npc)[:MAX_DISPLAY_NAME_CODE_POINTS],
                "portrait_ref": portrait_ref,
            },
            "actor": {
                "identity": actor_identity,
                "display_name": getattr(actor, "key", "")[:MAX_DISPLAY_NAME_CODE_POINTS],
                "portrait_ref": actor_portrait_ref,
            },
            "bond_stage": bond_stage,
            "context_id": session.context_id,
            "delivery": delivery_wire,
            "choices": choices,
            "pure_chain": pure_chain,
            "reading_revision": reading.revision,
            "completed_topic_ids": completed_topic_ids,
            "unlock_batch": None,
        }
    )


__all__ = [
    "DIALOGUE_MAX_CHOICES",
    "DIALOGUE_PANEL_MAX_BYTES",
    "DIALOGUE_SCHEMA_VERSION",
    "MAX_DIALOGUE_PORTRAIT_REF",
    "DialoguePanelError",
    "dialogue_presenter",
    "validate_dialogue",
]

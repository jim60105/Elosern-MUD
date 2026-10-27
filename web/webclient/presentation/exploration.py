"""Exact schema-version-5 ``exploration`` panel and presenter (webclient-exploration-menu).

The presenter serializes a read-only exploration surface from canonical room,
entity, component, and service data. It is registered beside ``status``,
``context_actions``, ``local_map``, and ``services`` in the production registry
and never mutates location, knowledge, dialogue, quests, inventory, traits, or
the clock.

The payload carries the exploration root categories composed from registered
server affordances: ``move`` (a bounded list of current Exit descriptors with
the same opaque ``exit_ref`` the ``local_map`` move action uses), ``look`` (a
room marker plus bounded present entity/object lists), ``interact`` (bounded
present targets, each with exactly the affordances that target legally
supports), and the ``character``/``quests``/``inventory`` availability entries.
Affordances use a distinguished shape: an **action** affordance carries a real
``action_id`` (``explore.talk_open`` / ``explore.engage``) while a
**navigation** affordance carries a ``surface`` — the ordinary author editor
(``npc_persona``) is the only navigation surface a target carries. A target's
supported services are the separate bounded ``services`` field.

Version 3 folds each conversable host's talk into exactly one 交談 affordance
naming ``explore.talk_open``, listed before the target's other affordances and
derived from the shared ``world.rules.dialogue.opens_dialogue`` predicate the
adapter uses; the target-level ``keywords`` list and the in-conversation
``explore.talk_scripted`` / ``explore.talk_freeform`` target codes are gone
(the open session's ``dialogue`` panel carries the keyword choices).

Version 4 adds one nullable ``portrait_ref`` to every look entity and interact
target: ``None`` or an unchanged ASCII decimal string of 1..32 characters -- the
exact catalog-key seam the combat participants and the dialogue host already
use. The presenter emits a reference for exactly the identities the current
capped ``art`` panel portrait catalog ADMITS, with no real-image gate: an
admitted subject whose imagery is missing, pending, failed or alpha-only still
carries its reference, and that key names its complete canonical descriptor in
the same committed snapshot. A descriptor therefore never points at a catalog
entry that is absent or cap-dropped, and a ``null`` means the current bounded
view does not admit the subject at all. The ``art`` panel's own membership, cap
and face crops are unchanged. Producer and client bundle cut over together
with no compatibility adapter or data migration.

Version 5 replaces the coarse guild/shop navigation rows with one exact
target-bound ``services`` field: ``{state, entries}`` where ``state`` is
``none``, ``ready`` or ``unreadable`` and each entry carries its stable key,
label, availability with a reason, and the exact route it opens. The field is
outside the eight general-affordance bound, so service rows can never displace
the ordinary editor/party controls, and an unreadable projection is a distinct
state rather than an empty list. The projection itself is
``world.rules.npc_services.project_npc_services``.

The payload shape and the exact shared bounds (design D10) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.
"""

from typing import Any, Callable

from web.webclient.presentation import affordances as affordances_module
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_EXIT_REF_CHARS,
    MAX_INTERACT_TARGETS,
    MAX_LABEL_CODE_POINTS,
    MAX_LOOK_OBJECTS,
    MAX_MOVE_EXITS,
    MAX_NODE_ID_CHARS,
    _DIALOGUE_UNAVAILABLE_REASON,
    _NOT_CONVERSABLE_REASON,
    _bounded_display_name,
    _entity_kind,
    _exit_ref,
    _is_exit,
    _look_entries,
    _move_entries,
    _target_affordance_entries,
    _traversable,
)
from web.webclient.actions.node_ids import node_id_for_location
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.protocol_validation import (
    require_exit_ref,
    require_node_id_shape,
)
from web.webclient.presentation.registry import PanelUnavailableError
from web.webclient.presentation.options import _validate_affordance_params
from world.rules.dialogue import is_dialogue_host, opens_dialogue
from world.rules.art_view import ArtViewError, build_art_view, portrait_catalog_key
from world.rules.map_knowledge import (
    KnowledgeError,
    decode_node,
)
from world.rules.npc_services import (
    MAX_SERVICE_ENTRIES,
    MAX_SERVICE_KEY_CHARS,
    MAX_SERVICE_LABEL_CODE_POINTS,
    MAX_SERVICE_REASON_CODE_CHARS,
    MAX_SERVICE_REASON_MESSAGE_CODE_POINTS,
    ROUTE_COMMAND,
    ROUTE_DIALOGUE,
    ROUTE_KINDS,
    ROUTE_SERVICES,
    SERVICE_SECTIONS,
    SERVICE_STATES,
    STATE_READY,
    STATE_UNREADABLE,
    project_npc_services,
)
from world.rules.service_view import build_services_view

EXPLORATION_SCHEMA_VERSION = 5

# Exact shared bounds (design D10) -- must stay equal in the JS validator.
MAX_LOOK_ENTITIES = 32
MAX_IDENTITY = MAX_SAFE_INTEGER
# The opaque decimal portrait-catalog reference bound (shared seam with the
# combat participant and dialogue host rows): 1..32 ASCII decimal digits.
MAX_PORTRAIT_REF = 32
MAX_KIND_CODE_POINTS = 32
MAX_REASON_MESSAGE_CODE_POINTS = 128

ACTION_KINDS = ("action", "navigate")
# The target-scoped subset of the shared allowlist: ``explore.move``,
# ``explore.look``, and ``explore.wait`` are never per-target affordances, and
# the in-conversation codes are folded into one ``explore.talk_open`` 交談 row,
# so a v4 target carrying either is a protocol error.
ACTION_IDS = tuple(
    code
    for code in ACTION_CODE_ALLOWLIST
    if code not in ("explore.talk_scripted", "explore.talk_freeform")
)
SURFACES = ("npc_persona",)
ENTITY_KINDS = ("character", "npc", "monster")
MAX_TOPIC_ID_CHARS = 2048


class ExplorationPanelError(ProtocolValidationError):
    """The available exploration payload violates its exact bounded schema."""


def _require_node_id(value: Any, field: str) -> str:
    require_node_id_shape(value, field, ProtocolValidationError, MAX_NODE_ID_CHARS)
    try:
        decode_node(value)
    except KnowledgeError as error:
        raise ProtocolValidationError(f"{field} is not a canonical node ID") from error
    return value


def _require_exit_ref(value: Any, field: str) -> str:
    return require_exit_ref(value, field, ProtocolValidationError)


def _require_identity(payload: dict[str, Any], field: str) -> int:
    return _require_int(payload, field, minimum=1, maximum=MAX_IDENTITY)


def _validate_portrait_ref(value: Any) -> str | None:
    """A nullable opaque portrait-catalog reference (schema version 4).

    Accepts ``None`` or an ASCII decimal string of 1..32 characters -- the exact
    seam shared with the combat participant and dialogue host rows: the
    ``isascii()``/``isdecimal()`` pair rejects Unicode-digit and URL-like values
    and the length bound rejects an overlong key, with no coercion or
    cross-panel join. Empty, numeric and subject-key shapes reject here.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ProtocolValidationError(
            "portrait_ref must be an opaque decimal catalog key or null"
        )
    if len(value) > MAX_PORTRAIT_REF:
        raise ProtocolValidationError("portrait_ref exceeds its bound")
    return value


def _validate_disabled_reason(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "disabled_reason", {"code", "message"}, {})
    code = _validate_identifier(value["code"], "disabled_reason code")
    message = _require_str(
        value, "message", maximum=MAX_REASON_MESSAGE_CODE_POINTS
    )
    if not message.strip():
        raise ProtocolValidationError("disabled_reason message must be non-empty")
    return {"code": code, "message": message}


def _validate_affordance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolValidationError("affordance must be a JSON object")
    kind = value.get("kind")
    if kind not in ACTION_KINDS:
        raise ProtocolValidationError("affordance kind is not a stable value")
    # The exact field set depends on kind; require the shared fields and allow
    # the kind-specific one so the branching below can enforce the exact set.
    _require_exact_fields(
        value,
        "affordance",
        {"kind", "label", "enabled", "disabled_reason"},
        # `params` is the schema-version-2 delivery payload; the kind branches
        # below enforce exactly which affordance may carry it.
        {
            "action_id": "conditional",
            "surface": "conditional",
            "params": "conditional",
        },
    )
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("affordance label must be non-empty")
    enabled = _require_bool(value, "enabled")
    disabled_reason = _validate_disabled_reason(value["disabled_reason"])
    if disabled_reason is None:
        if not enabled:
            raise ProtocolValidationError("a disabled affordance requires a disabled_reason")
    elif enabled:
        raise ProtocolValidationError("an enabled affordance must not carry a disabled_reason")

    if kind == "action":
        is_deliver = value.get("action_id") == "explore.deliver"
        _require_exact_fields(
            value,
            "action affordance",
            {"kind", "action_id", "label", "enabled", "disabled_reason"},
            # Schema version 2 (quest-deliver-action): exactly the
            # explore.deliver affordance carries the server validator's
            # normalized dispatch payload; every other action keeps the
            # version-1 exact shape (its payload is re-derived from the target
            # identity at the dock).
            {"params": "required" if is_deliver else "forbidden"},
        )
        action_id = _validate_identifier(value["action_id"], "action_id")
        if action_id not in ACTION_IDS:
            raise ProtocolValidationError("action_id is not a registered exploration action")
        normalized = {
            "kind": kind,
            "action_id": action_id,
            "label": label,
            "enabled": enabled,
            "disabled_reason": disabled_reason,
        }
        if action_id == "explore.deliver":
            normalized["params"] = _validate_affordance_params(
                action_id, value["params"]
            )
        return normalized
    _require_exact_fields(
        value,
        "navigation affordance",
        {"kind", "surface", "label", "enabled", "disabled_reason"},
        {},
    )
    surface = value["surface"]
    if surface not in SURFACES:
        raise ProtocolValidationError("surface is not a stable value")
    return {
        "kind": kind,
        "surface": surface,
        "label": label,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
    }


def _validate_look_entity(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value, "look entity", {"identity", "display_name", "kind", "portrait_ref"}, {}
    )
    identity = _require_identity(value, "identity")
    display_name = _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("entity display_name must be non-empty")
    kind = value["kind"]
    if kind not in ENTITY_KINDS:
        raise ProtocolValidationError("entity kind is not a stable value")
    portrait_ref = _validate_portrait_ref(value["portrait_ref"])
    return {
        "identity": identity,
        "display_name": display_name,
        "kind": kind,
        "portrait_ref": portrait_ref,
    }


def _validate_look_object(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "look object", {"identity", "display_name"}, {})
    identity = _require_identity(value, "identity")
    display_name = _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("object display_name must be non-empty")
    return {"identity": identity, "display_name": display_name}


def _validate_look_room(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "look room", {"identity", "display_name", "room"}, {})
    identity = _require_identity(value, "identity")
    display_name = _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("room display_name must be non-empty")
    if not _require_bool(value, "room"):
        raise ProtocolValidationError("room marker must be true")
    return {"identity": identity, "display_name": display_name, "room": True}


def _validate_look(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "look", {"room", "entities", "objects"}, {})
    room = _validate_look_room(value["room"])
    entities = value["entities"]
    if not isinstance(entities, list) or len(entities) > MAX_LOOK_ENTITIES:
        raise ProtocolValidationError(
            f"look entities must be a list of at most {MAX_LOOK_ENTITIES} entries"
        )
    entities = [_validate_look_entity(entry) for entry in entities]
    objects = value["objects"]
    if not isinstance(objects, list) or len(objects) > MAX_LOOK_OBJECTS:
        raise ProtocolValidationError(
            f"look objects must be a list of at most {MAX_LOOK_OBJECTS} entries"
        )
    objects = [_validate_look_object(entry) for entry in objects]
    return {"room": room, "entities": entities, "objects": objects}


def _validate_interact_target(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "interact target",
        {"identity", "display_name", "portrait_ref", "services", "affordances"},
        {},
    )
    identity = _require_identity(value, "identity")
    display_name = _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("target display_name must be non-empty")
    portrait_ref = _validate_portrait_ref(value["portrait_ref"])
    services = _validate_services(value["services"], identity)
    affordances = value["affordances"]
    if not isinstance(affordances, list) or len(affordances) > MAX_AFFORDANCES:
        raise ProtocolValidationError(
            f"affordances must be a list of at most {MAX_AFFORDANCES} entries"
        )
    affordances = [_validate_affordance(entry) for entry in affordances]
    return {
        "identity": identity,
        "display_name": display_name,
        "portrait_ref": portrait_ref,
        "services": services,
        "affordances": affordances,
    }


def _validate_service_reason(value: Any, enabled: bool) -> dict[str, Any] | None:
    if value is None:
        if not enabled:
            raise ProtocolValidationError(
                "a disabled service entry requires a disabled_reason"
            )
        return None
    if enabled:
        raise ProtocolValidationError(
            "an enabled service entry must not carry a disabled_reason"
        )
    _require_exact_fields(value, "service disabled_reason", {"code", "message"}, {})
    code = _validate_identifier(value["code"], "service disabled_reason code")
    if len(code) > MAX_SERVICE_REASON_CODE_CHARS:
        raise ProtocolValidationError("service disabled_reason code exceeds its bound")
    message = _require_str(
        value, "message", maximum=MAX_SERVICE_REASON_MESSAGE_CODE_POINTS
    )
    if not message.strip():
        raise ProtocolValidationError(
            "service disabled_reason message must be non-empty"
        )
    return {"code": code, "message": message}


def _validate_service_route(value: Any, identity: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolValidationError("service route must be a JSON object")
    _require_exact_fields(
        value,
        "service route",
        {"kind", "npc_id"},
        {"section": "conditional", "topic_id": "conditional", "command": "conditional"},
    )
    kind = value["kind"]
    if kind not in ROUTE_KINDS:
        raise ProtocolValidationError("service route kind is not a stable value")
    npc_id = value["npc_id"]
    if isinstance(npc_id, bool) or not isinstance(npc_id, int) or npc_id != identity:
        raise ProtocolValidationError(
            "a service route must name the exact selected target"
        )
    if kind == ROUTE_SERVICES:
        section = value.get("section")
        if section not in SERVICE_SECTIONS:
            raise ProtocolValidationError("service route section is not a stable value")
        if "topic_id" in value or "command" in value:
            raise ProtocolValidationError("a services route carries only its section")
        return {"kind": kind, "npc_id": npc_id, "section": section}
    if kind == ROUTE_DIALOGUE:
        topic_id = value.get("topic_id")
        if not isinstance(topic_id, str) or not (
            1 <= len(topic_id) <= MAX_TOPIC_ID_CHARS
        ):
            raise ProtocolValidationError(
                "a dialogue route requires a bounded topic_id"
            )
        if "section" in value or "command" in value:
            raise ProtocolValidationError("a dialogue route carries only its topic_id")
        return {"kind": kind, "npc_id": npc_id, "topic_id": topic_id}
    command = value.get("command")
    if command != "church join":
        raise ProtocolValidationError("a command route names the one supported command")
    if "section" in value or "topic_id" in value:
        raise ProtocolValidationError("a command route carries only its command")
    return {"kind": kind, "npc_id": npc_id, "command": command}


def _validate_service_entry(value: Any, identity: int) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "service entry",
        {"key", "label", "enabled", "disabled_reason", "route"},
        {},
    )
    key = _validate_identifier(value["key"], "service key")
    if len(key) > MAX_SERVICE_KEY_CHARS:
        raise ProtocolValidationError("service key exceeds its bound")
    label = _require_str(value, "label", maximum=MAX_SERVICE_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("service label must be non-empty")
    enabled = _require_bool(value, "enabled")
    return {
        "key": key,
        "label": label,
        "enabled": enabled,
        "disabled_reason": _validate_service_reason(value["disabled_reason"], enabled),
        "route": _validate_service_route(value["route"], identity),
    }


def _validate_services(value: Any, identity: int) -> dict[str, Any]:
    """Validate one target's exact bounded contextual service information."""
    _require_exact_fields(value, "services", {"state", "entries"}, {})
    state = value["state"]
    if state not in SERVICE_STATES:
        raise ProtocolValidationError("services state is not a stable value")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_SERVICE_ENTRIES:
        raise ProtocolValidationError(
            f"services entries must be a list of at most {MAX_SERVICE_ENTRIES} entries"
        )
    entries = [_validate_service_entry(entry, identity) for entry in entries]
    if state == STATE_READY and not entries:
        raise ProtocolValidationError("a ready services state requires an entry")
    if state != STATE_READY and entries:
        raise ProtocolValidationError(
            "an empty or unreadable services state carries no entry"
        )
    keys = [entry["key"] for entry in entries]
    if len(set(keys)) != len(keys):
        raise ProtocolValidationError("service entry keys must be unique")
    return {"state": state, "entries": entries}


def _validate_availability(value: Any, name: str) -> dict[str, Any]:
    _require_exact_fields(value, name, {"available"}, {})
    return {"available": _require_bool(value, "available")}


def _validate_move_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value, "move row", {"exit_ref", "label", "destination", "enabled", "disabled_reason"}, {}
    )
    exit_ref = _require_exit_ref(value["exit_ref"], "exit_ref")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("exit label must be non-empty")
    destination = _require_node_id(value["destination"], "destination")
    enabled = _require_bool(value, "enabled")
    disabled_reason = _validate_disabled_reason(value["disabled_reason"])
    if disabled_reason is None:
        if not enabled:
            raise ProtocolValidationError("a disabled exit requires a disabled_reason")
    elif enabled:
        raise ProtocolValidationError("an enabled exit must not carry a disabled_reason")
    return {
        "exit_ref": exit_ref,
        "label": label,
        "destination": destination,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
    }


def validate_exploration(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``exploration`` payload.

    Returns a normalized payload or raises :class:`ExplorationPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "exploration panel",
        {
            "schema_version",
            "available",
            "kind",
            "move",
            "look",
            "interact",
            "character",
            "quests",
            "inventory",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != EXPLORATION_SCHEMA_VERSION:
        raise ExplorationPanelError("unsupported exploration schema_version")
    if not _require_bool(payload, "available"):
        raise ExplorationPanelError("available must be true for the exploration form")
    if payload["kind"] != "exploration":
        raise ExplorationPanelError("exploration panel kind must be exploration")

    move = payload["move"]
    if not isinstance(move, list) or len(move) > MAX_MOVE_EXITS:
        raise ExplorationPanelError(f"move must be a list of at most {MAX_MOVE_EXITS} rows")
    move = [_validate_move_row(row) for row in move]

    look = _validate_look(payload["look"])

    interact = payload["interact"]
    if not isinstance(interact, list) or len(interact) > MAX_INTERACT_TARGETS:
        raise ExplorationPanelError(
            f"interact must be a list of at most {MAX_INTERACT_TARGETS} targets"
        )
    interact = [_validate_interact_target(target) for target in interact]
    identities = [target["identity"] for target in interact]
    if len(set(identities)) != len(identities):
        raise ExplorationPanelError("interact target identities must be unique")

    character = _validate_availability(payload["character"], "character")
    quests = _validate_availability(payload["quests"], "quests")
    inventory = _validate_availability(payload["inventory"], "inventory")

    result = {
        "schema_version": EXPLORATION_SCHEMA_VERSION,
        "available": True,
        "kind": "exploration",
        "move": move,
        "look": look,
        "interact": interact,
        "character": character,
        "quests": quests,
        "inventory": inventory,
    }
    # Envelope guarantee (design D10): a conforming payload must serialize
    # within the OOB envelope limit. The per-field bounds are ceilings, not a
    # guarantee that any combination of them fits, so the validator enforces
    # the serialized size directly -- an over-limit payload fails closed rather
    # than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ExplorationPanelError("exploration payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Serialization from canonical read-only data.
# ---------------------------------------------------------------------------


def _in_exploration_mode(actor: Any) -> bool:
    return affordances_module.in_exploration_mode(actor)


def _move_rows(actor: Any) -> list[dict[str, Any]]:
    """Serialize the bounded move exit list from the shared vocabulary.

    The row's ``exit_ref``, ``label``, ``enabled``, and disabled reason come
    from the canonical move entry; the ``destination`` field (the canonical
    arrival node of the exit, not the actor's current node) is re-derived from
    the exit object exactly like the version-1 panel. Wilderness rooms route
    every direction through the canonical destination resolver
    (fix-wilderness-web-navigation): the contrib's self-loop exits name the
    current room, and the registered gateway south exit actually returns to
    the grid, so ``exit_obj.destination`` can never be trusted there.
    """
    from typeclasses.rooms import TerrainRoom
    from world.maps.wilderness_destination import (
        normalize_wilderness_direction,
        resolve_wilderness_destination,
    )

    location = getattr(actor, "location", None)
    if location is None:
        return []
    wilderness = isinstance(location, TerrainRoom)
    exits_by_ref = {
        _exit_ref(exit_obj): exit_obj
        for exit_obj in location.exits
        if exit_obj.destination is not None
    }
    rows: list[dict[str, Any]] = []
    for entry in _move_entries(actor):
        exit_obj = exits_by_ref.get(entry.params["exit_ref"])
        if exit_obj is None:
            continue
        if wilderness:
            direction = normalize_wilderness_direction(exit_obj.key)
            destination_node = (
                resolve_wilderness_destination(location, direction)
                if direction is not None
                else None
            )
        else:
            destination_node = node_id_for_location(exit_obj.destination)
        if destination_node is None:
            continue
        reason = entry.disabled_reason
        rows.append(
            {
                "exit_ref": entry.params["exit_ref"],
                "label": entry.label,
                "destination": destination_node,
                "enabled": entry.enabled,
                "disabled_reason": (
                    None
                    if reason is None
                    else {"code": reason[0], "message": reason[1]}
                ),
            }
        )
    return rows


def _look_entities(
    actor: Any,
    portrait_ref_for: "Callable[[Any], str | None] | None" = None,
) -> list[dict[str, Any]]:
    """Serialize bounded present character/NPC/monster descriptors (excluding actor).

    ``portrait_ref_for`` is the shared per-presentation art lookup; when it is
    absent every reference is the truthful null (the art panel is optional).
    """
    location = getattr(actor, "location", None)
    if location is None:
        return []
    resolve = portrait_ref_for or (lambda _entity: None)
    present = [
        obj
        for obj in location.contents
        if obj is not actor and _entity_kind(obj) is not None
    ]
    present.sort(key=lambda obj: (int(obj.pk),))
    entities: list[dict[str, Any]] = []
    for obj in present[:MAX_LOOK_ENTITIES]:
        entities.append(
            {
                "identity": int(obj.pk),
                "display_name": _bounded_display_name(obj),
                "kind": _entity_kind(obj),
                "portrait_ref": resolve(obj),
            }
        )
    return entities


def _look_objects(actor: Any) -> list[dict[str, Any]]:
    """Serialize bounded present non-exit object descriptors (shared look entries)."""
    return [
        {"identity": entry.params["target_id"], "display_name": entry.label}
        for entry in _look_entries(actor)
    ]


def _reason_dict(entry: Any) -> dict[str, Any] | None:
    if entry.disabled_reason is None:
        return None
    code, message = entry.disabled_reason
    return {"code": code, "message": message}


def _portrait_ref_lookup(actor: Any) -> Callable[[Any], "str | None"]:
    """A per-presentation portrait-ref resolver over the current art view (design D2).

    Builds ``build_art_view(actor)`` once and answers every identity from that
    one admitted set, so the look and interact paths can never disagree and
    neither re-derives membership. A reference is emitted for every admitted
    identity whether or not real imagery resolves -- an admitted
    missing/pending/failed/alpha-only subject keeps its reference, and that key
    names its complete canonical descriptor in the same committed snapshot. An
    excluded or cap-dropped identity maps to ``None``. When the art view is
    unavailable every reference degrades to ``None`` through this boundary and
    exploration stays available; nothing here writes art records, queues, or
    gameplay state.
    """
    try:
        members = frozenset(
            int(view.identity) for view in build_art_view(actor).entities
        )
    except ArtViewError:
        return lambda _entity: None

    def lookup(entity: Any) -> "str | None":
        identity = int(entity.pk)
        if identity not in members:
            return None
        return portrait_catalog_key(identity)

    return lookup


def _interact_targets(
    actor: Any,
    portrait_ref_for: "Callable[[Any], str | None] | None" = None,
) -> list[dict[str, Any]]:
    """Serialize bounded present NPC/monster targets from the shared vocabulary.

    The per-target affordance rules (party bound/full rules, companion rule,
    dead-monster engage) live in the canonical vocabulary; this serializer maps
    the shared candidates into the exact version-5 descriptor shapes. The
    single 交談 row is derived from the same
    ``opens_dialogue`` predicate the ``explore.talk_open`` adapter commits
    through, so the rendered affordance and the action agree. Each target's
    ``services`` field is the derived projection of its own capabilities and
    explicit dialogue associations; a projection failure degrades to the
    distinct unreadable state, never to a fabricated or stale row.
    """
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC
    from world.rules.dialogue import authorized_dialogue_open
    from world.rules.npc_persona import is_card_available
    from world.rules.possession import (
        POSSESSED_REFUSAL_MESSAGES,
        REASON_POSSESSED_TALK,
        is_possessed_actor,
    )

    location = getattr(actor, "location", None)
    if location is None:
        return []
    resolve = portrait_ref_for or (lambda _entity: None)
    possessed = is_possessed_actor(actor)
    candidates = [
        obj
        for obj in location.contents
        if obj is not actor and isinstance(obj, (NPC, Monster))
    ]
    visible = location.filter_visible(candidates, actor)
    present = [
        obj
        for obj in visible
    ]
    present.sort(key=lambda obj: (int(obj.pk),))
    targets: list[dict[str, Any]] = []
    for obj in present[:MAX_INTERACT_TARGETS]:
        entries = _target_affordance_entries(obj, actor)
        affordances: list[dict[str, Any]] = []
        if opens_dialogue(obj):
            # One 交談 per conversable host, listed before the vocabulary rows.
            # A lawful possessed acting body opens authored scenes with its
            # own body; a forged control context, or a non-authored host,
            # keeps the vocabulary's own possession refusal.
            talk_authorized = authorized_dialogue_open(actor, obj)
            affordances.append(
                {
                    "kind": "action",
                    "action_id": "explore.talk_open",
                    "label": "交談",
                    "enabled": talk_authorized,
                    "disabled_reason": (
                        None
                        if talk_authorized
                        else {
                            "code": REASON_POSSESSED_TALK,
                            "message": POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK],
                        }
                    ),
                }
            )
        elif is_dialogue_host(obj):
            code, message = _DIALOGUE_UNAVAILABLE_REASON
            affordances.append(
                {
                    "kind": "action",
                    "action_id": "explore.talk_open",
                    "label": "交談",
                    "enabled": False,
                    "disabled_reason": {"code": code, "message": message},
                }
            )
        elif isinstance(obj, NPC):
            # The card's fixed common slot 1 (slice U): a visible NPC with no
            # supported conversation keeps 交談, disabled, carrying the stable
            # not-conversable reason, so no conditional or service row can take
            # the slot. It grants no talk authority -- ``explore.talk_open``
            # still rejects with ``not_dialogue_host``.
            code, message = _NOT_CONVERSABLE_REASON
            affordances.append(
                {
                    "kind": "action",
                    "action_id": "explore.talk_open",
                    "label": "交談",
                    "enabled": False,
                    "disabled_reason": {"code": code, "message": message},
                }
            )
        for entry in entries:
            if entry.action_id in (
                "explore.deliver",
                "explore.party_invite",
                "explore.party_leave",
                "explore.engage",
                "explore.possess",
            ):
                row = {
                    "kind": "action",
                    "action_id": entry.action_id,
                    "label": entry.label,
                    "enabled": entry.enabled,
                    "disabled_reason": _reason_dict(entry),
                }
                if entry.action_id == "explore.deliver":
                    # The dock cannot re-derive a bound quest payload from the
                    # target identity alone: the server-normalized params ride
                    # the row (schema version 2, quest-deliver-action).
                    row["params"] = dict(entry.params)
                affordances.append(row)
        if isinstance(obj, NPC):
            # Design D5: Reserve space for the author-editor affordance within MAX_AFFORDANCES
            affordances = affordances[: MAX_AFFORDANCES - 1]
            card_ok = is_card_available(obj)
            if possessed:
                dis_reason = {
                    "code": REASON_POSSESSED_TALK,
                    "message": POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK],
                }
                is_enabled = False
            elif not card_ok:
                dis_reason = {
                    "code": "npc_persona.unavailable",
                    "message": "此角色的設定目前無法編輯或尚未初始化。",
                }
                is_enabled = False
            else:
                dis_reason = None
                is_enabled = True
            affordances.append(
                {
                    "kind": "navigate",
                    "surface": "npc_persona",
                    "label": "編輯人物設定",
                    "enabled": is_enabled,
                    "disabled_reason": dis_reason,
                }
            )
        targets.append(
            {
                "identity": int(obj.pk),
                "display_name": _bounded_display_name(obj),
                "portrait_ref": resolve(obj),
                "services": _services_payload(actor, obj),
                "affordances": affordances[:MAX_AFFORDANCES],
            }
        )
    return targets


def _services_payload(actor: Any, obj: Any) -> dict[str, Any]:
    """Serialize one target's derived services, fail-closed on any failure."""
    services = project_npc_services(actor, actor, obj)
    return services.as_dict()


def _services_available(actor: Any) -> bool:
    """Whether the ``services`` panel would be available for the actor.

    The exploration ``quests``/``inventory`` availability entries mirror the
    services capability: they are available whenever the services view can be
    built in exploration mode. This reads through the same no-mutation read
    model the ``services`` presenter uses (design D1). Any failure degrades
    only these two entries; the exploration panel itself stays available.
    """
    try:
        build_services_view(actor)
        return True
    except Exception:
        return False


def exploration_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``exploration`` panel for the authenticated puppet."""
    actor = context.actor
    if not _in_exploration_mode(actor):
        raise PanelUnavailableError
    location = getattr(actor, "location", None)
    if location is None:
        raise PanelUnavailableError

    room_identity = int(location.pk)
    services_available = _services_available(actor)
    portrait_ref_for = _portrait_ref_lookup(actor)
    payload = {
        "schema_version": EXPLORATION_SCHEMA_VERSION,
        "available": True,
        "kind": "exploration",
        "move": _move_rows(actor),
        "look": {
            "room": {
                "identity": room_identity,
                "display_name": _bounded_display_name(location),
                "room": True,
            },
            "entities": _look_entities(actor, portrait_ref_for),
            "objects": _look_objects(actor),
        },
        "interact": _interact_targets(actor, portrait_ref_for),
        "character": {"available": True},
        "quests": {"available": services_available},
        "inventory": {"available": services_available},
    }
    return validate_exploration(payload)


__all__ = [
    "ACTION_IDS",
    "ACTION_KINDS",
    "ENTITY_KINDS",
    "EXPLORATION_SCHEMA_VERSION",
    "ExplorationPanelError",
    "MAX_AFFORDANCES",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_EXIT_REF_CHARS",
    "MAX_INTERACT_TARGETS",
    "MAX_LOOK_ENTITIES",
    "MAX_LOOK_OBJECTS",
    "MAX_MOVE_EXITS",
    "MAX_NODE_ID_CHARS",
    "SURFACES",
    "exploration_presenter",
    "validate_exploration",
]

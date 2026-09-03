"""Exact schema-version-1 ``exploration`` panel and presenter (webclient-exploration-menu).

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
``action_id`` (``explore.talk_scripted`` / ``explore.talk_freeform`` /
``explore.engage``) while a **navigation** affordance carries a ``surface``
(``"guild"`` / ``"shop"``) and only opens an existing ``services`` submenu.

The payload shape and the exact shared bounds (design D10) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation import affordances as affordances_module
from web.webclient.presentation.affordances import (
    MAX_AFFORDANCES,
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_EXIT_REF_CHARS,
    MAX_INTERACT_TARGETS,
    MAX_KEYWORD_ID_CHARS,
    MAX_KEYWORD_LABEL_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_LOOK_OBJECTS,
    MAX_MOVE_EXITS,
    MAX_NODE_ID_CHARS,
    MAX_SCRIPTED_KEYWORDS,
    _DIALOGUE_UNAVAILABLE_REASON,
    _bounded_display_name,
    _entity_kind,
    _exit_ref,
    _is_exit,
    _look_entries,
    _move_entries,
    _resolve_single_host,
    _scripted_keyword_descriptors,
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
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.dialogue import is_dialogue_host
from world.rules.map_knowledge import (
    KnowledgeError,
    decode_node,
)
from world.rules.npc_identity import npc_display_name
from world.rules.service_view import build_services_view

EXPLORATION_SCHEMA_VERSION = 1

# Exact shared bounds (design D10) -- must stay equal in the JS validator.
MAX_LOOK_ENTITIES = 32
MAX_IDENTITY = MAX_SAFE_INTEGER
MAX_KIND_CODE_POINTS = 32
MAX_REASON_MESSAGE_CODE_POINTS = 128

ACTION_KINDS = ("action", "navigate")
ACTION_IDS = (
    "explore.talk_scripted",
    "explore.talk_freeform",
    "explore.party_invite",
    "explore.party_leave",
    "explore.engage",
)
SURFACES = ("guild", "shop")
ENTITY_KINDS = ("character", "npc", "monster")


def _bounded_entity_name(obj: Any) -> str:
    """Bounded entity-row name: NPC full identity where one exists (D5).

    Players and monsters degrade to their plain key inside the composer, and
    a malformed title degrades there too, so both row kinds can call this
    unconditionally. The slice (never a raise) bounds even corrupt stored
    titles for the wire, mirroring ``_bounded_display_name``; that shared
    helper stays the plain-key source for room, move, and object rows.
    """
    return npc_display_name(obj)[:MAX_DISPLAY_NAME_CODE_POINTS]


class ExplorationPanelError(ProtocolValidationError):
    """The available exploration payload violates its exact bounded schema."""


def _require_node_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_NODE_ID_CHARS:
        raise ProtocolValidationError(f"{field} exceeds the maximum node-ID length")
    try:
        decode_node(value)
    except KnowledgeError as error:
        raise ProtocolValidationError(f"{field} is not a canonical node ID") from error
    return value


def _require_exit_ref(value: Any, field: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_EXIT_REF_CHARS:
        raise ProtocolValidationError(
            f"{field} must be 1..{MAX_EXIT_REF_CHARS} ASCII characters"
        )
    if not value.isascii():
        raise ProtocolValidationError(f"{field} must be ASCII")
    return value


def _require_identity(payload: dict[str, Any], field: str) -> int:
    return _require_int(payload, field, minimum=1, maximum=MAX_IDENTITY)


def _require_keyword_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolValidationError(f"{field} must be a non-empty string")
    if sum(1 for _ in value) > MAX_KEYWORD_ID_CHARS:
        raise ProtocolValidationError(
            f"{field} must be at most {MAX_KEYWORD_ID_CHARS} characters"
        )
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


def _validate_keyword(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "scripted keyword", {"keyword_id", "label"}, {})
    keyword_id = _require_keyword_id(value["keyword_id"], "keyword_id")
    label = _require_str(value, "label", maximum=MAX_KEYWORD_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("keyword label must be non-empty")
    return {"keyword_id": keyword_id, "label": label}


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
        {"action_id": "conditional", "surface": "conditional"},
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
        _require_exact_fields(
            value,
            "action affordance",
            {"kind", "action_id", "label", "enabled", "disabled_reason"},
            {},
        )
        action_id = _validate_identifier(value["action_id"], "action_id")
        if action_id not in ACTION_IDS:
            raise ProtocolValidationError("action_id is not a registered exploration action")
        return {
            "kind": kind,
            "action_id": action_id,
            "label": label,
            "enabled": enabled,
            "disabled_reason": disabled_reason,
        }
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
    if value["portrait_ref"] is not None:
        raise ProtocolValidationError("portrait_ref must be null in this schema version")
    return {
        "identity": identity,
        "display_name": display_name,
        "kind": kind,
        "portrait_ref": None,
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
        {"identity", "display_name", "portrait_ref", "affordances"},
        {"keywords": "conditional"},
    )
    identity = _require_identity(value, "identity")
    display_name = _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("target display_name must be non-empty")
    if value["portrait_ref"] is not None:
        raise ProtocolValidationError("portrait_ref must be null in this schema version")
    affordances = value["affordances"]
    if not isinstance(affordances, list) or len(affordances) > MAX_AFFORDANCES:
        raise ProtocolValidationError(
            f"affordances must be a list of at most {MAX_AFFORDANCES} entries"
        )
    affordances = [_validate_affordance(entry) for entry in affordances]
    keywords = None
    if "keywords" in value:
        keyword_value = value["keywords"]
        if not isinstance(keyword_value, list) or len(keyword_value) > MAX_SCRIPTED_KEYWORDS:
            raise ProtocolValidationError(
                f"keywords must be a list of at most {MAX_SCRIPTED_KEYWORDS} entries"
            )
        keywords = [_validate_keyword(entry) for entry in keyword_value]
        if keywords and not any(
            affordance["kind"] == "action"
            and affordance["action_id"] == "explore.talk_scripted"
            for affordance in affordances
        ):
            raise ProtocolValidationError(
                "keywords require a talk_scripted affordance on the target"
            )
    result: dict[str, Any] = {
        "identity": identity,
        "display_name": display_name,
        "portrait_ref": None,
        "affordances": affordances,
    }
    if keywords is not None:
        result["keywords"] = keywords
    return result


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


def _look_entities(actor: Any) -> list[dict[str, Any]]:
    """Serialize bounded present character/NPC/monster descriptors (excluding actor)."""
    location = getattr(actor, "location", None)
    if location is None:
        return []
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
                "display_name": _bounded_entity_name(obj),
                "kind": _entity_kind(obj),
                "portrait_ref": None,
            }
        )
    return entities


def _look_objects(actor: Any) -> list[dict[str, Any]]:
    """Serialize bounded present non-exit object descriptors (shared look entries)."""
    return [
        {"identity": entry.params["target_id"], "display_name": entry.label}
        for entry in _look_entries(actor)
    ]


def _scripted_keywords(npc: Any) -> list[dict[str, Any]]:
    """Return the bounded scripted keyword descriptors for a dialogue host."""
    return _scripted_keyword_descriptors(npc)


def _reason_dict(entry: Any) -> dict[str, Any] | None:
    if entry.disabled_reason is None:
        return None
    code, message = entry.disabled_reason
    return {"code": code, "message": message}


def _interact_targets(actor: Any) -> list[dict[str, Any]]:
    """Serialize bounded present NPC/monster targets from the shared vocabulary.

    The per-target affordance rules (dialogue-host gating, freeform, party
    bound/full rules, companion rule, dead-monster engage, exact-local-host
    navigation) live in the canonical vocabulary; this serializer maps the
    shared candidates into the exact version-1 descriptor shapes, with the
    scripted keyword buttons reading the authored keyword pool.
    """
    from typeclasses.components import GuildStaff, Merchant
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC

    location = getattr(actor, "location", None)
    if location is None:
        return []
    guild_host = _resolve_single_host(actor, GuildStaff)
    shop_host = _resolve_single_host(actor, Merchant)
    present = [
        obj
        for obj in location.contents
        if obj is not actor and isinstance(obj, (NPC, Monster))
    ]
    present.sort(key=lambda obj: (int(obj.pk),))
    targets: list[dict[str, Any]] = []
    for obj in present[:MAX_INTERACT_TARGETS]:
        entries = _target_affordance_entries(
            obj, actor, guild_host=guild_host, shop_host=shop_host
        )
        affordances: list[dict[str, Any]] = []
        target_keywords: list[dict[str, Any]] | None = None
        scripted_present = any(
            not entry.navigation and entry.action_id == "explore.talk_scripted"
            for entry in entries
        )
        if is_dialogue_host(obj):
            if scripted_present:
                affordances.append(
                    {
                        "kind": "action",
                        "action_id": "explore.talk_scripted",
                        "label": "交談",
                        "enabled": True,
                        "disabled_reason": None,
                    }
                )
                target_keywords = _scripted_keywords(obj) or None
            else:
                code, message = _DIALOGUE_UNAVAILABLE_REASON
                affordances.append(
                    {
                        "kind": "action",
                        "action_id": "explore.talk_scripted",
                        "label": "交談",
                        "enabled": False,
                        "disabled_reason": {"code": code, "message": message},
                    }
                )
        for entry in entries:
            if entry.navigation:
                affordances.append(
                    {
                        "kind": "navigate",
                        "surface": entry.surface,
                        "label": entry.label,
                        "enabled": entry.enabled,
                        "disabled_reason": _reason_dict(entry),
                    }
                )
            elif entry.action_id in (
                "explore.talk_freeform",
                "explore.party_invite",
                "explore.party_leave",
                "explore.engage",
            ):
                affordances.append(
                    {
                        "kind": "action",
                        "action_id": entry.action_id,
                        "label": entry.label,
                        "enabled": entry.enabled,
                        "disabled_reason": _reason_dict(entry),
                    }
                )
        target: dict[str, Any] = {
            "identity": int(obj.pk),
            "display_name": _bounded_entity_name(obj),
            "portrait_ref": None,
            "affordances": affordances[:MAX_AFFORDANCES],
        }
        if target_keywords is not None:
            target["keywords"] = target_keywords
        targets.append(target)
    return targets


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
            "entities": _look_entities(actor),
            "objects": _look_objects(actor),
        },
        "interact": _interact_targets(actor),
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
    "MAX_SCRIPTED_KEYWORDS",
    "SURFACES",
    "exploration_presenter",
    "validate_exploration",
]

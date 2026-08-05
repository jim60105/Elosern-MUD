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

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, Merchant
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
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
from world.onboarding.guide_dialogue import DIALOGUE_TABLE
from world.rules.dialogue import dialogue_key_for, is_dialogue_host
from world.rules.guild import (
    GuildServiceError,
    resolve_local_service_host,
)
from world.rules.map_knowledge import (
    KnowledgeError,
    decode_node,
    encode_grid,
    encode_room,
    encode_wild,
)
from world.rules.service_view import build_services_view

EXPLORATION_SCHEMA_VERSION = 1

# Exact shared bounds (design D10) -- must stay equal in the JS validator.
MAX_MOVE_EXITS = 12
MAX_LOOK_ENTITIES = 32
MAX_LOOK_OBJECTS = 32
MAX_INTERACT_TARGETS = 32
MAX_AFFORDANCES = 8
MAX_SCRIPTED_KEYWORDS = 16
MAX_EXIT_REF_CHARS = 64
MAX_NODE_ID_CHARS = 128
MAX_IDENTITY = MAX_SAFE_INTEGER
MAX_DISPLAY_NAME_CODE_POINTS = 128
MAX_KIND_CODE_POINTS = 32
MAX_LABEL_CODE_POINTS = 128
MAX_KEYWORD_ID_CHARS = 64
MAX_KEYWORD_LABEL_CODE_POINTS = 128
MAX_REASON_MESSAGE_CODE_POINTS = 128

ACTION_KINDS = ("action", "navigate")
ACTION_IDS = ("explore.talk_scripted", "explore.talk_freeform", "explore.engage")
SURFACES = ("guild", "shop")
ENTITY_KINDS = ("character", "npc", "monster")

# Stable localized disabled reasons for move rows.
_LOCKED_REASON = ("locked", "此出口目前無法通行。")
_DIALOGUE_UNAVAILABLE_REASON = ("dialogue_unavailable", "對方目前沒有可以交談的話題。")

# The kind label used by the look entity descriptor for each present living type.
_KIND_BY_TYPE = (PlayerCharacter, "character"), (LLMNPC, "npc"), (NPC, "npc"), (Monster, "monster")


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
    from world.rules.combat_session import is_in_active_session

    if bool(getattr(actor, "creation_pending", False)):
        return False
    if is_in_active_session(actor):
        return False
    return True


def _exit_ref(exit_obj: Any) -> str:
    """An opaque, stable ASCII identifier for a real exit (its dbref)."""
    return str(int(exit_obj.id))


def _traversable(exit_obj: Any, actor: Any) -> bool:
    try:
        return bool(exit_obj.access(actor, "traverse"))
    except Exception:
        return False


def _destination_node(destination: Any) -> str | None:
    """Return the canonical node ID for a destination room, or ``None``."""
    from typeclasses.rooms import GridRoom, TerrainRoom
    from world.maps.wilderness_provider import WILDERNESS_NAME

    if isinstance(destination, GridRoom):
        try:
            x, y, z = destination.xyz
        except Exception:
            return None
        return encode_grid(str(z), x, y)
    if isinstance(destination, TerrainRoom):
        coordinates = destination.coordinates
        if coordinates is None:
            return None
        return encode_wild(WILDERNESS_NAME, coordinates[0], coordinates[1])
    if not getattr(destination, "id", None):
        return None
    return encode_room(int(destination.id))


def _entity_kind(obj: Any) -> str | None:
    for typeclass, kind in _KIND_BY_TYPE:
        if isinstance(obj, typeclass):
            return kind
    return None


def _is_exit(obj: Any) -> bool:
    from evennia.objects.objects import DefaultExit

    return isinstance(obj, DefaultExit)


def _bounded_display_name(obj: Any) -> str:
    return str(getattr(obj, "key", "?"))[:MAX_DISPLAY_NAME_CODE_POINTS]


def _move_rows(actor: Any) -> list[dict[str, Any]]:
    """Serialize the bounded move exit list from the actor's current location."""
    location = getattr(actor, "location", None)
    if location is None:
        return []
    exits = sorted(location.exits, key=lambda exit_obj: (exit_obj.key or "", int(exit_obj.id)))
    rows: list[dict[str, Any]] = []
    for exit_obj in exits[:MAX_MOVE_EXITS]:
        destination = exit_obj.destination
        if destination is None:
            continue
        destination_node = _destination_node(destination)
        if destination_node is None:
            continue
        enabled = _traversable(exit_obj, actor)
        if enabled:
            disabled_reason = None
        else:
            code, message = _LOCKED_REASON
            disabled_reason = {"code": code, "message": message}
        rows.append(
            {
                "exit_ref": _exit_ref(exit_obj),
                "label": _bounded_display_name(exit_obj),
                "destination": destination_node,
                "enabled": enabled,
                "disabled_reason": disabled_reason,
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
                "display_name": _bounded_display_name(obj),
                "kind": _entity_kind(obj),
                "portrait_ref": None,
            }
        )
    return entities


def _look_objects(actor: Any) -> list[dict[str, Any]]:
    """Serialize bounded present non-exit object descriptors."""
    location = getattr(actor, "location", None)
    if location is None:
        return []
    present = [
        obj
        for obj in location.contents
        if obj is not actor and _entity_kind(obj) is None and not _is_exit(obj)
    ]
    present.sort(key=lambda obj: (int(obj.pk),))
    objects: list[dict[str, Any]] = []
    for obj in present[:MAX_LOOK_OBJECTS]:
        objects.append({"identity": int(obj.pk), "display_name": _bounded_display_name(obj)})
    return objects


def _scripted_affordance(npc: Any, actor: Any) -> dict[str, Any]:
    """Build the scripted-talk affordance for a dialogue host (or a disabled one).

    The bounded keyword buttons live on the target descriptor (``keywords``),
    not on the affordance, so the interact payload stays within the global
    JSON-depth bound. A host whose dialogue component resolves but whose
    authored table cannot be resolved degrades to a disabled affordance so the
    failure is confined to that one affordance while the whole panel stays
    available.
    """
    del actor
    dialogue_key = dialogue_key_for(npc)
    definition = DIALOGUE_TABLE.get(dialogue_key) if dialogue_key is not None else None
    keywords: list[dict[str, Any]] = []
    if definition is not None:
        keywords = [
            {"keyword_id": response.keyword, "label": response.keyword}
            for response in definition.responses[:MAX_SCRIPTED_KEYWORDS]
        ]
    if keywords:
        return {
            "kind": "action",
            "action_id": "explore.talk_scripted",
            "label": "交談",
            "enabled": True,
            "disabled_reason": None,
        }
    code, message = _DIALOGUE_UNAVAILABLE_REASON
    return {
        "kind": "action",
        "action_id": "explore.talk_scripted",
        "label": "交談",
        "enabled": False,
        "disabled_reason": {"code": code, "message": message},
    }


def _scripted_keywords(npc: Any) -> list[dict[str, Any]]:
    """Return the bounded scripted keyword descriptors for a dialogue host."""
    dialogue_key = dialogue_key_for(npc)
    definition = DIALOGUE_TABLE.get(dialogue_key) if dialogue_key is not None else None
    if definition is None:
        return []
    return [
        {"keyword_id": response.keyword, "label": response.keyword}
        for response in definition.responses[:MAX_SCRIPTED_KEYWORDS]
    ]


def _freeform_affordance(npc: Any) -> dict[str, Any]:
    return {
        "kind": "action",
        "action_id": "explore.talk_freeform",
        "label": "自由交談",
        "enabled": True,
        "disabled_reason": None,
    }


def _engage_affordance(monster: Any) -> dict[str, Any]:
    living = getattr(getattr(monster, "traits", None), "hp", None) is not None and monster.traits.hp.value > 0
    if not living:
        return {
            "kind": "action",
            "action_id": "explore.engage",
            "label": "戰鬥",
            "enabled": False,
            "disabled_reason": {"code": "target_dead", "message": "目標已經死亡。"},
        }
    return {
        "kind": "action",
        "action_id": "explore.engage",
        "label": "戰鬥",
        "enabled": True,
        "disabled_reason": None,
    }


def _service_affordance(component_class: type, surface: str) -> dict[str, Any]:
    """Return the navigate-kind service affordance for one surface."""
    label = "公會服務" if surface == "guild" else "商店"
    return {
        "kind": "navigate",
        "surface": surface,
        "label": label,
        "enabled": True,
        "disabled_reason": None,
    }


def _resolve_single_host(actor: Any, component_class: type) -> Any | None:
    try:
        return resolve_local_service_host(actor, component_class)
    except GuildServiceError:
        return None


def _interact_targets(actor: Any) -> list[dict[str, Any]]:
    """Serialize bounded present NPC/monster targets with their legal affordances.

    A `navigate`-kind service affordance is attached to the exact local host's
    own target descriptor, never to a remote or unrelated target.
    """
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
        affordances: list[dict[str, Any]] = []
        target_keywords: list[dict[str, Any]] | None = None
        if isinstance(obj, NPC) and is_dialogue_host(obj):
            affordances.append(_scripted_affordance(obj, actor))
            target_keywords = _scripted_keywords(obj) or None
        if isinstance(obj, LLMNPC):
            affordances.append(_freeform_affordance(obj))
        if isinstance(obj, Monster):
            affordances.append(_engage_affordance(obj))
        if guild_host is not None and obj is guild_host:
            affordances.append(_service_affordance(GuildStaff, "guild"))
        if shop_host is not None and obj is shop_host:
            affordances.append(_service_affordance(Merchant, "shop"))
        target: dict[str, Any] = {
            "identity": int(obj.pk),
            "display_name": _bounded_display_name(obj),
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

"""Primitive schema, encoding/decoding, and source-neutral validation for authored dialogue.

This module provides:
- Identity classes: ``StaticDialogueIdentity`` and ``GeneratedDialogueIdentity``.
- Generated ID and stable host_key codec: ``encode_parts``, ``decode_parts``,
  ``make_generated_topic_id``, ``make_generated_scene_id``, ``make_static_host_key``,
  ``make_generated_host_key``, ``parse_generated_topic_id``, ``parse_generated_scene_id``.
- JSON schema factory: ``dialogue_payload_schema(*, identity_kind)``.
- Parser: ``parse_dialogue(payload, *, identity, references, package_roles=None, package_quests=None)``.
- Pure validator: ``validate_dialogue(definition, *, identity, references, package_roles=None, package_quests=None)``.
- Byte budget checks for canonical UTF-8 JSON wire limits:
  Scene <= 8192, delivery + public successors <= 16384, dialogue <= 24576.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from world.lore.dialogue.conditions import (
    AffinityAtLeast,
    All,
    Any as AnyCond,
    Carries,
    CompanionPresent,
    Condition,
    DialogueReferences,
    Exposure,
    GuildRankAtLeast,
    QuestIs,
    RaceIs,
    SkillOwned,
    SocialIdentityIs,
    TimePeriod,
    condition_to_dict,
    validate_condition,
)
from world.lore.dialogue.shape import (
    MAX_KEYWORD_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_PREDECESSORS_PER_TOPIC,
    MAX_TOPICS_PER_DIALOGUE,
    MAX_VARIANTS_PER_TOPIC,
    AuthoredDialogue,
    AuthoredTopic,
    SceneVariant,
    VARIANT_ID_PATTERN,
)
from world.lore.scenes import (
    MAX_LINE_CODE_POINTS,
    MAX_REVISION_ASCII_CHARS,
    MAX_SCENE_CANONICAL_BYTES,
    MAX_SCENE_CODE_POINTS,
    MAX_SCENE_LINES,
    MAX_STATIC_SCENE_ID_CHARS,
    Narration,
    Scene,
    SceneLine,
    Speech,
    canonical_utf8_json_bytes,
    scene_canonical_bytes,
    scene_to_dict,
)

MAX_STATIC_GREETING_CODE_POINTS = 2000
MAX_STATIC_GREETING_BYTES = 8192
MAX_GENERATED_GREETING_CODE_POINTS = 500

MAX_DELIVERY_BUNDLE_CANONICAL_BYTES = 16384
MAX_DIALOGUE_PANEL_CANONICAL_BYTES = 24576

MAX_GENERATED_ID_ASCII_BYTES = 2048
MAX_HOST_KEY_ASCII_BYTES = 768

GENERATED_LOCAL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")
STATIC_SCENE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,95}\Z")
STATIC_TOPIC_SUFFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")


@dataclass(frozen=True)
class StaticDialogueIdentity:
    """Identity for a static dialogue table bound to an NpcProfile and dialogue_key."""

    profile_key: str
    dialogue_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile_key, str) or not self.profile_key:
            raise ValueError("StaticDialogueIdentity profile_key must be a nonempty string")
        if not isinstance(self.dialogue_key, str) or not self.dialogue_key:
            raise ValueError("StaticDialogueIdentity dialogue_key must be a nonempty string")


@dataclass(frozen=True)
class GeneratedDialogueIdentity:
    """Identity for a generated dialogue phase bound to a package, role, and phase."""

    package_id: str
    role_id: str
    phase_id: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("package_id", self.package_id),
            ("role_id", self.role_id),
            ("phase_id", self.phase_id),
        ):
            if not isinstance(value, str) or not (1 <= len(value) <= 64):
                raise ValueError(
                    f"GeneratedDialogueIdentity {field_name} must be 1..64 code points, got {value!r}"
                )


DialogueIdentity = StaticDialogueIdentity | GeneratedDialogueIdentity


def encode_parts(parts: list[str] | tuple[str, ...]) -> str:
    """Encode string parts to unpadded URL-safe base64 of canonical UTF-8 JSON."""
    raw = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_parts(encoded: str) -> list[str]:
    """Decode unpadded URL-safe base64 parts, verifying exact canonical re-encoding."""
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("Encoded parts must be a nonempty string")
    # Pad to multiple of 4 with '='
    remainder = len(encoded) % 4
    padded = encoded + ("=" * (4 - remainder) if remainder else "")
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        parsed = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to decode parts: {encoded!r}") from exc
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise ValueError(f"Decoded parts must be a list of strings: {parsed!r}")
    # Enforce strict roundtrip (no alternate base64 encodings or non-canonical json)
    if encode_parts(parsed) != encoded:
        raise ValueError("Decoded parts do not strictly roundtrip to original string")
    return parsed


def make_generated_topic_id(package_id: str, role_id: str, phase_id: str, local_topic_id: str) -> str:
    """Construct full collision-free generated topic ID."""
    if not GENERATED_LOCAL_ID_PATTERN.match(local_topic_id):
        raise ValueError(f"local_topic_id must match [a-z][a-z0-9_]{{0,31}}, got {local_topic_id!r}")
    encoded = "g:" + encode_parts([package_id, role_id, phase_id, local_topic_id])
    if len(encoded.encode("ascii")) > MAX_GENERATED_ID_ASCII_BYTES:
        raise ValueError(f"Generated topic ID exceeds {MAX_GENERATED_ID_ASCII_BYTES} bytes")
    return encoded


def parse_generated_topic_id(topic_id: str) -> tuple[str, str, str, str]:
    """Parse a full generated topic ID into (package_id, role_id, phase_id, local_topic_id)."""
    if not isinstance(topic_id, str) or not topic_id.startswith("g:"):
        raise ValueError(f"Generated topic ID must start with 'g:', got {topic_id!r}")
    parts = decode_parts(topic_id[2:])
    if len(parts) != 4:
        raise ValueError(f"Generated topic ID must contain exactly 4 parts, got {len(parts)}")
    package_id, role_id, phase_id, local_topic_id = parts
    if not GENERATED_LOCAL_ID_PATTERN.match(local_topic_id):
        raise ValueError(f"Decoded local_topic_id {local_topic_id!r} is invalid")
    return package_id, role_id, phase_id, local_topic_id


def make_generated_scene_id(package_id: str, role_id: str, phase_id: str, local_scene_id: str) -> str:
    """Construct full collision-free generated scene ID."""
    if not GENERATED_LOCAL_ID_PATTERN.match(local_scene_id):
        raise ValueError(f"local_scene_id must match [a-z][a-z0-9_]{{0,31}}, got {local_scene_id!r}")
    encoded = "g:" + encode_parts([package_id, role_id, phase_id, local_scene_id])
    if len(encoded.encode("ascii")) > MAX_GENERATED_ID_ASCII_BYTES:
        raise ValueError(f"Generated scene ID exceeds {MAX_GENERATED_ID_ASCII_BYTES} bytes")
    return encoded


def parse_generated_scene_id(scene_id: str) -> tuple[str, str, str, str]:
    """Parse a full generated scene ID into (package_id, role_id, phase_id, local_scene_id)."""
    if not isinstance(scene_id, str) or not scene_id.startswith("g:"):
        raise ValueError(f"Generated scene ID must start with 'g:', got {scene_id!r}")
    parts = decode_parts(scene_id[2:])
    if len(parts) != 4:
        raise ValueError(f"Generated scene ID must contain exactly 4 parts, got {len(parts)}")
    package_id, role_id, phase_id, local_scene_id = parts
    if not GENERATED_LOCAL_ID_PATTERN.match(local_scene_id):
        raise ValueError(f"Decoded local_scene_id {local_scene_id!r} is invalid")
    return package_id, role_id, phase_id, local_scene_id


def make_static_host_key(profile_key: str) -> str:
    """Return stable host key for static NPC profile."""
    if not isinstance(profile_key, str) or not profile_key:
        raise ValueError("profile_key must be a nonempty string")
    key = f"s:{profile_key}"
    if len(key.encode("ascii")) > MAX_HOST_KEY_ASCII_BYTES:
        raise ValueError("Static host_key exceeds max bytes")
    return key


def make_generated_host_key(package_id: str, role_id: str) -> str:
    """Return stable host key for generated role."""
    key = "g:" + encode_parts([package_id, role_id])
    if len(key.encode("ascii")) > MAX_HOST_KEY_ASCII_BYTES:
        raise ValueError("Generated host_key exceeds max bytes")
    return key


def dialogue_payload_schema(*, identity_kind: Literal["static", "generated_local"]) -> dict[str, Any]:
    """Return the JSON schema for dialogue payloads.

    ``identity_kind`` is either "static" or "generated_local".
    """
    if identity_kind not in ("static", "generated_local"):
        raise ValueError(f"Unknown identity_kind: {identity_kind!r}")

    line_schema = {
        "type": "object",
        "oneOf": [
            {
                "properties": {
                    "kind": {"type": "string", "enum": ["speech"]},
                    "speaker": {"type": "string", "enum": ["actor", "host"]},
                    "text": {"type": "string", "minLength": 1, "maxLength": MAX_LINE_CODE_POINTS},
                },
                "required": ["kind", "speaker", "text"],
                "additionalProperties": False,
            },
            {
                "properties": {
                    "kind": {"type": "string", "enum": ["narration"]},
                    "text": {"type": "string", "minLength": 1, "maxLength": MAX_LINE_CODE_POINTS},
                },
                "required": ["kind", "text"],
                "additionalProperties": False,
            },
        ],
    }

    scene_id_pattern = (
        r"^[a-z][a-z0-9_.-]{0,95}$" if identity_kind == "static" else r"^[a-z][a-z0-9_]{0,31}$"
    )

    scene_schema = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "pattern": scene_id_pattern},
            "revision": {"type": "string", "pattern": r"^[!-~]{1,32}$"},
            "lines": {
                "type": "array",
                "items": line_schema,
                "minItems": 1,
                "maxItems": MAX_SCENE_LINES,
            },
        },
        "required": ["scene_id", "revision", "lines"],
        "additionalProperties": False,
    }

    condition_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "enum": [
                    "all",
                    "any",
                    "race_is",
                    "social_identity_is",
                    "guild_rank_at_least",
                    "quest_is",
                    "affinity_at_least",
                    "carries",
                    "companion_present",
                    "time_period",
                    "skill_owned",
                    "exposure",
                ],
            }
        },
        "required": ["kind"],
    }

    variant_schema = {
        "type": "object",
        "properties": {
            "variant_id": {"type": "string", "pattern": r"^[a-z][a-z0-9_]{0,31}$"},
            "priority": {"type": "integer"},
            "when": condition_schema,
            "scene": scene_schema,
        },
        "required": ["variant_id", "priority", "when", "scene"],
        "additionalProperties": False,
    }

    topic_id_pattern = (
        r"^[a-z][a-z0-9_.-]{0,95}$" if identity_kind == "static" else r"^[a-z][a-z0-9_]{0,31}$"
    )

    topic_schema = {
        "type": "object",
        "properties": {
            "topic_id": {"type": "string", "pattern": topic_id_pattern},
            "keyword": {"type": "string", "minLength": 1, "maxLength": MAX_KEYWORD_CODE_POINTS},
            "label": {"type": "string", "minLength": 1, "maxLength": MAX_LABEL_CODE_POINTS},
            "fallback": scene_schema,
            "variants": {
                "type": "array",
                "items": variant_schema,
                "maxItems": MAX_VARIANTS_PER_TOPIC,
            },
            "requires": condition_schema,
            "unavailable": {"type": "string", "enum": ["hidden", "locked"]},
            "refusal": scene_schema,
            "predecessors": {
                "type": "array",
                "items": {"type": "string", "pattern": topic_id_pattern},
                "maxItems": MAX_PREDECESSORS_PER_TOPIC,
            },
            "disclosure": {"type": "string", "enum": ["qualified", "pure_chain"]},
        },
        "required": ["topic_id", "keyword", "label", "fallback"],
        "additionalProperties": False,
    }

    if identity_kind == "static":
        return {
            "type": "object",
            "properties": {
                "schema_version": {"type": "integer", "enum": [1]},
                "greeting": {
                    "type": ["string", "null"],
                    "maxLength": MAX_STATIC_GREETING_CODE_POINTS,
                },
                "topics": {
                    "type": "array",
                    "items": topic_schema,
                    "maxItems": MAX_TOPICS_PER_DIALOGUE,
                },
            },
            "required": ["schema_version", "greeting", "topics"],
            "additionalProperties": False,
        }
    else:
        # Generated local fragment
        return {
            "type": "object",
            "properties": {
                "greeting": {
                    "type": ["string", "null"],
                    "maxLength": MAX_GENERATED_GREETING_CODE_POINTS,
                },
                "topics": {
                    "type": "array",
                    "items": topic_schema,
                    "maxItems": MAX_TOPICS_PER_DIALOGUE,
                },
            },
            "required": ["greeting", "topics"],
            "additionalProperties": False,
        }


def _parse_condition(node: Any) -> Condition:
    if not isinstance(node, dict):
        raise TypeError(f"Condition node must be a dict, got {type(node)!r}")
    kind = node.get("kind")
    if not isinstance(kind, str):
        raise ValueError(f"Condition node missing string 'kind': {node!r}")

    allowed_keys: dict[str, set[str]] = {
        "all": {"kind", "children"},
        "any": {"kind", "children"},
        "race_is": {"kind", "race_key"},
        "social_identity_is": {"kind", "identity_key"},
        "guild_rank_at_least": {"kind", "rank_key"},
        "quest_is": {"kind", "definition_key", "state"},
        "affinity_at_least": {"kind", "stage_key"},
        "carries": {"kind", "item_key", "minimum"},
        "companion_present": {"kind", "source_kind", "source_key"},
        "time_period": {"kind", "start_daypart", "end_daypart"},
        "skill_owned": {"kind", "skill_key", "min_proficiency"},
        "exposure": {"kind", "minimum", "maximum"},
    }

    if kind not in allowed_keys:
        raise ValueError(f"Unsupported condition kind: {kind!r}")
    extra = set(node.keys()) - allowed_keys[kind]
    if extra:
        raise ValueError(f"Condition {kind!r} declares unexpected fields: {sorted(extra)}")

    if kind == "all":
        children = node.get("children")
        if not isinstance(children, list):
            raise TypeError("All condition children must be a list")
        return All(tuple(_parse_condition(c) for c in children))

    if kind == "any":
        children = node.get("children")
        if not isinstance(children, list):
            raise TypeError("Any condition children must be a list")
        return AnyCond(tuple(_parse_condition(c) for c in children))

    if kind == "race_is":
        return RaceIs(race_key=node.get("race_key"))

    if kind == "social_identity_is":
        return SocialIdentityIs(identity_key=node.get("identity_key"))

    if kind == "guild_rank_at_least":
        return GuildRankAtLeast(rank_key=node.get("rank_key"))

    if kind == "quest_is":
        return QuestIs(definition_key=node.get("definition_key"), state=node.get("state"))

    if kind == "affinity_at_least":
        return AffinityAtLeast(stage_key=node.get("stage_key"))

    if kind == "carries":
        item_key = node.get("item_key")
        minimum = node.get("minimum", 1)
        if isinstance(minimum, bool) or not isinstance(minimum, int):
            raise TypeError("Carries minimum must be an integer")
        return Carries(item_key=item_key, minimum=minimum)

    if kind == "companion_present":
        return CompanionPresent(
            source_kind=node.get("source_kind"), source_key=node.get("source_key")
        )

    if kind == "time_period":
        return TimePeriod(
            start_daypart=node.get("start_daypart"), end_daypart=node.get("end_daypart")
        )

    if kind == "skill_owned":
        min_prof = node.get("min_proficiency")
        if min_prof is not None and (isinstance(min_prof, bool) or not isinstance(min_prof, int)):
            raise TypeError("SkillOwned min_proficiency must be an integer or None")
        return SkillOwned(skill_key=node.get("skill_key"), min_proficiency=min_prof)

    if kind == "exposure":
        minimum = node.get("minimum")
        maximum = node.get("maximum")
        return Exposure(minimum=minimum, maximum=maximum)

    raise ValueError(f"Unhandled condition kind: {kind!r}")


def _parse_line(node: Any) -> SceneLine:
    if not isinstance(node, dict):
        raise TypeError(f"Scene line must be a dict, got {type(node)!r}")
    kind = node.get("kind")
    if kind == "speech":
        extra = set(node.keys()) - {"kind", "speaker", "text"}
        if extra:
            raise ValueError(f"Speech line declares extra fields: {sorted(extra)}")
        return Speech(speaker=node.get("speaker"), text=node.get("text"))
    if kind == "narration":
        extra = set(node.keys()) - {"kind", "text"}
        if extra:
            raise ValueError(f"Narration line declares extra fields: {sorted(extra)}")
        return Narration(text=node.get("text"))
    raise ValueError(f"Unknown scene line kind: {kind!r}")


def _parse_scene(
    node: Any,
    *,
    identity: DialogueIdentity,
) -> Scene:
    if not isinstance(node, dict):
        raise TypeError(f"Scene must be a dict, got {type(node)!r}")
    extra = set(node.keys()) - {"scene_id", "revision", "lines"}
    if extra:
        raise ValueError(f"Scene declares unexpected fields: {sorted(extra)}")
    raw_id = node.get("scene_id")
    revision = node.get("revision")
    lines_raw = node.get("lines")

    if not isinstance(lines_raw, list):
        raise TypeError("Scene lines must be a list")
    parsed_lines = tuple(_parse_line(line) for line in lines_raw)

    if isinstance(identity, GeneratedDialogueIdentity):
        if not isinstance(raw_id, str):
            raise TypeError("Generated scene_id must be a string")
        if raw_id.startswith("g:"):
            raise ValueError(
                f"Generated payload must use local scene_id without 'g:' prefix, got {raw_id!r}"
            )
        full_scene_id = make_generated_scene_id(
            identity.package_id, identity.role_id, identity.phase_id, raw_id
        )
    else:
        full_scene_id = raw_id

    return Scene(scene_id=full_scene_id, revision=revision, lines=parsed_lines)


def _check_formal_scene(scene: Scene) -> None:
    if not scene.lines or not isinstance(scene.lines[0], Speech) or scene.lines[0].speaker != "actor":
        raise ValueError(
            f"Formal scene {scene.scene_id!r} must begin with an actor Speech line"
        )


def parse_dialogue(
    payload: Any,
    *,
    identity: DialogueIdentity,
    references: DialogueReferences,
    package_roles: frozenset[str] | None = None,
    package_quests: frozenset[str] | None = None,
) -> AuthoredDialogue:
    """Parse a primitive payload into deeply immutable AuthoredDialogue and validate it."""
    if not isinstance(payload, dict):
        raise TypeError(f"Dialogue payload must be a dict, got {type(payload)!r}")

    if isinstance(identity, StaticDialogueIdentity):
        allowed_root = {"schema_version", "greeting", "topics"}
        extra = set(payload.keys()) - allowed_root
        if extra:
            raise ValueError(f"Static dialogue payload contains unexpected fields: {sorted(extra)}")
        if payload.get("schema_version") != 1:
            raise ValueError(
                f"Static dialogue requires schema_version 1, got {payload.get('schema_version')!r}"
            )
    elif isinstance(identity, GeneratedDialogueIdentity):
        allowed_root = {"greeting", "topics"}
        extra = set(payload.keys()) - allowed_root
        if extra:
            raise ValueError(f"Generated dialogue payload contains unexpected fields: {sorted(extra)}")
    else:
        raise TypeError(f"Unknown identity type: {type(identity)!r}")

    greeting = payload.get("greeting")
    if greeting is not None and not isinstance(greeting, str):
        raise TypeError("greeting must be a string or null")

    topics_raw = payload.get("topics")
    if not isinstance(topics_raw, list):
        raise TypeError("topics must be a list")

    parsed_topics: list[AuthoredTopic] = []
    allowed_topic_fields = {
        "topic_id",
        "keyword",
        "label",
        "fallback",
        "variants",
        "requires",
        "unavailable",
        "refusal",
        "predecessors",
        "disclosure",
    }

    for idx, t_node in enumerate(topics_raw):
        if not isinstance(t_node, dict):
            raise TypeError(f"Topic {idx} must be a dict")
        extra_t = set(t_node.keys()) - allowed_topic_fields
        if extra_t:
            raise ValueError(f"Topic {idx} contains unexpected fields: {sorted(extra_t)}")

        raw_topic_id = t_node.get("topic_id")
        if not isinstance(raw_topic_id, str):
            raise TypeError(f"Topic {idx} topic_id must be a string")

        if isinstance(identity, GeneratedDialogueIdentity):
            if raw_topic_id.startswith("g:"):
                raise ValueError(
                    f"Generated topic payload must declare local topic_id, got {raw_topic_id!r}"
                )
            full_topic_id = make_generated_topic_id(
                identity.package_id, identity.role_id, identity.phase_id, raw_topic_id
            )
        else:
            full_topic_id = raw_topic_id

        keyword = t_node.get("keyword")
        label = t_node.get("label")

        fallback_node = t_node.get("fallback")
        if fallback_node is None:
            raise ValueError(f"Topic {raw_topic_id!r} is missing fallback scene")
        fallback_scene = _parse_scene(fallback_node, identity=identity)

        variants_raw = t_node.get("variants", [])
        if not isinstance(variants_raw, list):
            raise TypeError(f"Topic {raw_topic_id!r} variants must be a list")
        parsed_variants: list[SceneVariant] = []
        for v_node in variants_raw:
            if not isinstance(v_node, dict):
                raise TypeError(f"Variant in topic {raw_topic_id!r} must be a dict")
            extra_v = set(v_node.keys()) - {"variant_id", "priority", "when", "scene"}
            if extra_v:
                raise ValueError(f"Variant in topic {raw_topic_id!r} has unexpected fields: {sorted(extra_v)}")
            v_id = v_node.get("variant_id")
            priority = v_node.get("priority")
            when = _parse_condition(v_node.get("when"))
            scene = _parse_scene(v_node.get("scene"), identity=identity)
            parsed_variants.append(
                SceneVariant(variant_id=v_id, priority=priority, when=when, scene=scene)
            )

        requires_node = t_node.get("requires")
        requires = _parse_condition(requires_node) if requires_node is not None else None

        unavailable = t_node.get("unavailable", "hidden")
        refusal_node = t_node.get("refusal")
        refusal = (
            _parse_scene(refusal_node, identity=identity)
            if refusal_node is not None
            else None
        )

        predecessors_raw = t_node.get("predecessors", [])
        if not isinstance(predecessors_raw, list):
            raise TypeError(f"Topic {raw_topic_id!r} predecessors must be a list")
        parsed_predecessors: list[str] = []
        for p in predecessors_raw:
            if not isinstance(p, str):
                raise TypeError("predecessor must be a string")
            if isinstance(identity, GeneratedDialogueIdentity):
                if p.startswith("g:"):
                    raise ValueError(
                        f"Generated topic predecessor must be local, got {p!r}"
                    )
                parsed_predecessors.append(
                    make_generated_topic_id(
                        identity.package_id, identity.role_id, identity.phase_id, p
                    )
                )
            else:
                parsed_predecessors.append(p)

        disclosure = t_node.get("disclosure", "qualified")

        parsed_topics.append(
            AuthoredTopic(
                topic_id=full_topic_id,
                keyword=keyword,
                label=label,
                fallback=fallback_scene,
                variants=tuple(parsed_variants),
                requires=requires,
                unavailable=unavailable,
                refusal=refusal,
                predecessors=tuple(parsed_predecessors),
                disclosure=disclosure,
            )
        )

    definition = AuthoredDialogue(greeting=greeting, topics=tuple(parsed_topics))
    return validate_dialogue(
        definition,
        identity=identity,
        references=references,
        package_roles=package_roles,
        package_quests=package_quests,
    )


def validate_dialogue(
    definition: AuthoredDialogue,
    *,
    identity: DialogueIdentity,
    references: DialogueReferences,
    package_roles: frozenset[str] | None = None,
    package_quests: frozenset[str] | None = None,
) -> AuthoredDialogue:
    """Perform complete semantic validation of an AuthoredDialogue instance."""
    if not isinstance(definition, AuthoredDialogue):
        raise TypeError(f"Expected AuthoredDialogue, got {type(definition)!r}")

    # 1. Greeting validation
    if definition.greeting is not None:
        if isinstance(identity, StaticDialogueIdentity):
            if len(definition.greeting) > MAX_STATIC_GREETING_CODE_POINTS:
                raise ValueError(
                    f"Static greeting exceeds {MAX_STATIC_GREETING_CODE_POINTS} code points"
                )
            if len(definition.greeting.encode("utf-8")) > MAX_STATIC_GREETING_BYTES:
                raise ValueError(
                    f"Static greeting exceeds {MAX_STATIC_GREETING_BYTES} UTF-8 bytes"
                )
        elif isinstance(identity, GeneratedDialogueIdentity):
            if len(definition.greeting) > MAX_GENERATED_GREETING_CODE_POINTS:
                raise ValueError(
                    f"Generated greeting exceeds {MAX_GENERATED_GREETING_CODE_POINTS} code points"
                )

    # 2. Topic and Scene uniqueness and identity binding
    topic_map: dict[str, AuthoredTopic] = {}
    declared_scene_ids: set[str] = set()

    for topic in definition.topics:
        # Check topic identity binding
        if isinstance(identity, StaticDialogueIdentity):
            prefix = f"{identity.dialogue_key}."
            if not topic.topic_id.startswith(prefix):
                raise ValueError(
                    f"Static topic_id {topic.topic_id!r} does not match dialogue_key prefix {prefix!r}"
                )
            suffix = topic.topic_id[len(prefix):]
            if not STATIC_TOPIC_SUFFIX_PATTERN.match(suffix):
                raise ValueError(
                    f"Static topic suffix {suffix!r} must match [a-z][a-z0-9_]{{0,31}}"
                )
            if len(topic.topic_id) > 96:
                raise ValueError(f"Static topic_id {topic.topic_id!r} exceeds 96 characters")
        elif isinstance(identity, GeneratedDialogueIdentity):
            try:
                pkg, role, phase, local_t = parse_generated_topic_id(topic.topic_id)
            except Exception as exc:
                raise ValueError(f"Invalid generated topic_id {topic.topic_id!r}") from exc
            if (pkg, role, phase) != (identity.package_id, identity.role_id, identity.phase_id):
                raise ValueError(
                    f"Generated topic_id {topic.topic_id!r} namespace does not match identity {(identity.package_id, identity.role_id, identity.phase_id)}"
                )

        topic_map[topic.topic_id] = topic

        # Validate scenes
        all_topic_scenes = [topic.fallback]
        for v in topic.variants:
            all_topic_scenes.append(v.scene)
        if topic.refusal is not None:
            all_topic_scenes.append(topic.refusal)

        for s in all_topic_scenes:
            if s.scene_id in declared_scene_ids:
                raise ValueError(f"Duplicate scene_id {s.scene_id!r} in dialogue definition")
            declared_scene_ids.add(s.scene_id)

            if isinstance(identity, StaticDialogueIdentity):
                if not STATIC_SCENE_ID_PATTERN.match(s.scene_id):
                    raise ValueError(
                        f"Static scene_id {s.scene_id!r} does not match static pattern [a-z][a-z0-9_.-]{{0,95}}"
                    )
            elif isinstance(identity, GeneratedDialogueIdentity):
                try:
                    pkg, role, phase, local_s = parse_generated_scene_id(s.scene_id)
                except Exception as exc:
                    raise ValueError(f"Invalid generated scene_id {s.scene_id!r}") from exc
                if (pkg, role, phase) != (identity.package_id, identity.role_id, identity.phase_id):
                    raise ValueError(
                        f"Generated scene_id {s.scene_id!r} namespace does not match identity {(identity.package_id, identity.role_id, identity.phase_id)}"
                    )

        # Formal scenes (fallback and all variants) must start with actor Speech
        _check_formal_scene(topic.fallback)
        for v in topic.variants:
            _check_formal_scene(v.scene)

        # Validate conditions
        if topic.requires is not None:
            validate_condition(
                topic.requires,
                references,
                package_roles=package_roles,
                package_quests=package_quests,
            )
        for v in topic.variants:
            validate_condition(
                v.when,
                references,
                package_roles=package_roles,
                package_quests=package_quests,
            )

    # 3. Predecessor DAG and disclosure validation
    for topic in definition.topics:
        for pred_id in topic.predecessors:
            if pred_id not in topic_map:
                raise ValueError(
                    f"Topic {topic.topic_id!r} has dangling predecessor reference {pred_id!r}"
                )

    # Cycle detection in predecessors
    visited: dict[str, int] = {}  # 0: visiting, 1: visited

    def dfs(t_id: str, path: list[str]) -> None:
        visited[t_id] = 0
        topic_obj = topic_map[t_id]
        for pred_id in topic_obj.predecessors:
            if visited.get(pred_id) == 0:
                raise ValueError(
                    f"Cycle detected in dialogue predecessors: {' -> '.join(path + [pred_id])}"
                )
            if pred_id not in visited:
                dfs(pred_id, path + [pred_id])
        visited[t_id] = 1

    for t_id in topic_map:
        if t_id not in visited:
            dfs(t_id, [t_id])

    # 4. Pure chain disclosure validation
    # A pure_chain topic cannot depend on qualified ancestors (must have no requires)
    for topic in definition.topics:
        if topic.disclosure == "pure_chain":
            queue = list(topic.predecessors)
            seen_ancestors = set(queue)
            while queue:
                curr_id = queue.pop(0)
                ancestor = topic_map[curr_id]
                if ancestor.requires is not None:
                    raise ValueError(
                        f"Pure chain topic {topic.topic_id!r} depends on ancestor {ancestor.topic_id!r} with requires condition"
                    )
                for p in ancestor.predecessors:
                    if p not in seen_ancestors:
                        seen_ancestors.add(p)
                        queue.append(p)

    # 5. Canonical UTF-8 JSON limits
    # complete dialogue panel <= 24576 bytes
    dialogue_dict: dict[str, Any] = {
        "greeting": definition.greeting,
        "topics": [
            {
                "topic_id": t.topic_id,
                "keyword": t.keyword,
                "label": t.label,
                "fallback": scene_to_dict(t.fallback),
                "variants": [
                    {
                        "variant_id": v.variant_id,
                        "priority": v.priority,
                        "when": condition_to_dict(v.when),
                        "scene": scene_to_dict(v.scene),
                    }
                    for v in t.variants
                ],
                "requires": condition_to_dict(t.requires) if t.requires else None,
                "unavailable": t.unavailable,
                "refusal": scene_to_dict(t.refusal) if t.refusal else None,
                "predecessors": list(t.predecessors),
                "disclosure": t.disclosure,
            }
            for t in definition.topics
        ],
    }
    panel_canon_bytes = len(canonical_utf8_json_bytes(dialogue_dict))
    if panel_canon_bytes > MAX_DIALOGUE_PANEL_CANONICAL_BYTES:
        raise ValueError(
            f"AuthoredDialogue canonical UTF-8 JSON bytes ({panel_canon_bytes}) exceeds limit of {MAX_DIALOGUE_PANEL_CANONICAL_BYTES}"
        )

    # Worst reachable public bundle: selected delivery + all reachable pure_chain successors <= 16384 bytes
    # Find all successors for each topic
    successors_map: dict[str, list[str]] = {t.topic_id: [] for t in definition.topics}
    for t in definition.topics:
        for p in t.predecessors:
            successors_map[p].append(t.topic_id)

    for selected_t in definition.topics:
        # Candidate scenes for selected topic
        selected_scenes = [selected_t.fallback] + [v.scene for v in selected_t.variants]
        for s_scene in selected_scenes:
            bundle_bytes = scene_canonical_bytes(s_scene)
            # Find reachable pure_chain successors
            reachable_pure: set[str] = set()
            to_visit = [succ for succ in successors_map[selected_t.topic_id] if topic_map[succ].disclosure == "pure_chain"]
            while to_visit:
                curr = to_visit.pop(0)
                if curr not in reachable_pure:
                    reachable_pure.add(curr)
                    for nxt in successors_map[curr]:
                        if topic_map[nxt].disclosure == "pure_chain":
                            to_visit.append(nxt)
            for succ_id in reachable_pure:
                succ_topic = topic_map[succ_id]
                # max scene for successor
                max_succ_scene = max(
                    scene_canonical_bytes(s)
                    for s in [succ_topic.fallback] + [v.scene for v in succ_topic.variants]
                )
                bundle_bytes += max_succ_scene
            if bundle_bytes > MAX_DELIVERY_BUNDLE_CANONICAL_BYTES:
                raise ValueError(
                    f"Selected delivery for topic {selected_t.topic_id!r} with reachable public successors ({bundle_bytes} bytes) exceeds limit of {MAX_DELIVERY_BUNDLE_CANONICAL_BYTES}"
                )

    return definition

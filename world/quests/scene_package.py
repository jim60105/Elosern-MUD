"""Validated scene-package definitions and their canonical payload contract.

A scene package is the bounded, deterministic data shape the quest system
validates and publishes: reusable named roles, typed relationships, provenance-
bearing role-owned knowledge, independently eligible encounters, complete
per-role dialogue phases, and an embedded quest blueprint that may declare a
symbolic role-issued commission. The generative layer may only *propose* this
payload shape; validation and persistence belong here.

Validation is whole-package and happens before any write (design §5.1): locators
resolve through the existing map/registry authorities with no nearest-place
substitution, characterizations and ages reuse the shared validators, phase
coverage/selection/cycles are rejected statically, effects must name registered
domain verbs with validated references, and numeric/typeclass/code injection is
refused. Relationships and world planning grant no knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.quests.characterization import (
    characterize_errors,
    race_lifespan_upper_bound,
)
from world.quests.compile.compiler import CompiledBlueprintCore, compile_blueprint_core
from world.quests.compile.contracts import (
    QuestCompileError,
    StageNpcCharacterization,
)
from world.quests.compile.fields import (
    _compile_characterization,
    _compile_location,
    _require_int,
    _require_mapping,
    _validate_scene_fields,
    _validate_strings,
)
from world.quests.definitions import DestinationKind, RoomLocator
from world.quests.phases import (
    REGISTERED_FACTS,
    condition_matches,
    validate_condition,
)
from world.rules.quest_issuance import npc_issuer_key, IssuerKeyError


class ScenePackageError(QuestCompileError):
    """A scene-package payload violates the bounded package contract."""


#: The closed typed-relationship vocabulary. ``parent_child`` is directed
#: (from_role is the parent, to_role the child); declaring the reverse of an
#: existing pair, or the same ordered pair twice, is an inconsistent reciprocal
#: relation. A relationship never confers private knowledge.
RELATIONSHIP_KINDS: tuple[str, ...] = ("parent_child",)

#: The closed domain-effect vocabulary a scripted topic may name. Every verb
#: resolves through the deterministic commission APIs at execution time; a label
#: or fixed line can never itself award progress or items (design §6). A private
#: commission settles automatically on completion, so the only pre-acceptance
#: interaction a generated issuer offers is accepting its commission.
EFFECT_VERBS: tuple[str, ...] = ("offer_commission",)

MAX_ID_LENGTH = 64
MAX_PHASE_TOPICS = 8
MAX_KNOWLEDGE_CLAIM_TEXT = 200
MAX_PHASE_FREEFORM = 400
MAX_OFFLINE_RESPONSE = 500
MAX_TOPIC_RESPONSE = 500
MAX_PHASE_GREETING = 500


def _reject_package(message: str) -> None:
    raise ScenePackageError(message)


@dataclass(frozen=True)
class RoleDefinition:
    """One reusable named role, defined exactly once and referenced elsewhere."""

    role_id: str
    tier: str
    disposition: str | None
    characterization: StageNpcCharacterization
    conversable: bool
    retention: RoomLocator
    existing_npc_pk: int | None = None


@dataclass(frozen=True)
class RelationshipDefinition:
    from_role: str
    to_role: str
    kind: str


@dataclass(frozen=True)
class KnowledgeClaim:
    role_id: str
    claim_id: str
    text: str
    provenance: dict[str, Any]


@dataclass(frozen=True)
class EncounterDefinition:
    scene_id: str
    role_ids: tuple[str, ...]
    locator: RoomLocator
    archetype: str | None
    anchor_near: str | None
    scene_sentence: str | None
    prerequisites: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PhaseTopic:
    keyword: str
    response: str
    effect_verb: str | None = None
    effect_reference: str | None = None


@dataclass(frozen=True)
class DialoguePhase:
    phase_id: str
    conditions: tuple[dict[str, Any], ...]
    greeting: str
    topics: tuple[PhaseTopic, ...]
    freeform_situation: str
    freeform_goals: str
    offline_response: str


@dataclass(frozen=True)
class RoleDialogue:
    role_id: str
    initial_phase: str
    phases: tuple[DialoguePhase, ...]


@dataclass(frozen=True)
class SymbolicIssuer:
    """A validated role-issued commission that stays unregistered until activation."""

    role_id: str
    issuer_key: str
    definition_key: str


@dataclass(frozen=True)
class ScenePackageDefinition:
    """One fully validated scene package."""

    package_id: str
    display_name: str
    source_id: str | None
    roles: tuple[RoleDefinition, ...]
    relationships: tuple[RelationshipDefinition, ...]
    knowledge: tuple[KnowledgeClaim, ...]
    encounters: tuple[EncounterDefinition, ...]
    dialogue: tuple[RoleDialogue, ...]
    commission: SymbolicIssuer | None
    guild_branch: str | None
    quest: CompiledBlueprintCore

    def role(self, role_id: str) -> RoleDefinition | None:
        return next((r for r in self.roles if r.role_id == role_id), None)

    def encounter(self, scene_id: str) -> EncounterDefinition | None:
        return next((e for e in self.encounters if e.scene_id == scene_id), None)

    def role_dialogue(self, role_id: str) -> RoleDialogue | None:
        return next((d for d in self.dialogue if d.role_id == role_id), None)

    def role_ids(self) -> frozenset[str]:
        return frozenset(r.role_id for r in self.roles)


def _bounded_prose(field: str, value: Any, bound: int, *, required: bool) -> str | None:
    _validate_strings(None, field, value, bound, required=required)
    return value


def _validate_roles(entries: Any) -> tuple[RoleDefinition, ...]:
    if not isinstance(entries, list) or not entries:
        _reject_package("package.roles must be a non-empty array")
    roles: list[RoleDefinition] = []
    seen: set[str] = set()
    for position, entry in enumerate(entries):
        entry = _require_mapping(entry, f"roles[{position}]")
        unknown = set(entry) - {
            "role_id",
            "tier",
            "disposition",
            "characterization",
            "conversable",
            "retention",
            "existing_npc",
        }
        if unknown:
            _reject_package(f"roles[{position}] has unknown fields {sorted(unknown)}")
        role_id = entry.get("role_id")
        if not isinstance(role_id, str) or not role_id:
            _reject_package(f"roles[{position}].role_id must be a non-empty string")
        if len(role_id) > MAX_ID_LENGTH:
            _reject_package(f"role id {role_id!r} exceeds the {MAX_ID_LENGTH}-character cap")
        if role_id in seen:
            _reject_package(f"duplicate role id {role_id!r}")
        seen.add(role_id)
        tier = entry.get("tier")
        if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
            _reject_package(f"role {role_id!r} declares unknown tier {tier!r}")
        disposition = entry.get("disposition")
        if disposition is not None and not isinstance(disposition, str):
            _reject_package(f"role {role_id!r} disposition must be a string or None")
        characterization_entry = _require_mapping(
            entry.get("characterization"), f"role {role_id!r} characterization"
        )
        for message in characterize_errors(
            characterization_entry,
            lifespan_upper_bound=race_lifespan_upper_bound(tier),
        ):
            _reject_package(f"role {role_id!r} {message}")
        characterization = _compile_characterization(characterization_entry)
        conversable = entry.get("conversable", False)
        if not isinstance(conversable, bool):
            _reject_package(f"role {role_id!r} conversable must be a boolean")
        retention = _compile_location(
            _require_mapping(entry.get("retention"), f"role {role_id!r} retention")
        )
        if retention.kind not in (DestinationKind.ANCHOR, DestinationKind.GRID):
            _reject_package(
                f"role {role_id!r} retention must be a permanent anchor or grid locator"
            )
        existing_pk = None
        existing = entry.get("existing_npc")
        if existing is not None:
            existing = _require_mapping(existing, f"role {role_id!r} existing_npc")
            if set(existing) != {"kind", "value"} or existing.get("kind") != "pk":
                _reject_package(
                    f"role {role_id!r} existing_npc must be exactly "
                    "{'kind': 'pk', 'value': <positive int>}; names never select actors"
                )
            existing_pk = _require_int(
                existing.get("value"), f"role {role_id!r} existing_npc.value", minimum=1
            )
        roles.append(
            RoleDefinition(
                role_id=role_id,
                tier=tier,
                disposition=disposition,
                characterization=characterization,
                conversable=conversable,
                retention=retention,
                existing_npc_pk=existing_pk,
            )
        )
    return tuple(roles)


def _validate_relationships(
    entries: Any, role_ids: set[str]
) -> tuple[RelationshipDefinition, ...]:
    if entries is None:
        return ()
    if not isinstance(entries, list):
        _reject_package("package.relationships must be an array")
    relationships: list[RelationshipDefinition] = []
    seen_pairs: set[tuple[str, str]] = set()
    for position, entry in enumerate(entries):
        entry = _require_mapping(entry, f"relationships[{position}]")
        if set(entry) != {"from_role", "to_role", "kind"}:
            _reject_package(
                f"relationships[{position}] must declare exactly from_role, to_role, kind"
            )
        from_role = entry.get("from_role")
        to_role = entry.get("to_role")
        kind = entry.get("kind")
        # Validate the reference types before any membership lookup: a JSON
        # array/object is unhashable and must be a named rejection, not a
        # TypeError escaping the package validator.
        if (
            not isinstance(from_role, str)
            or not isinstance(to_role, str)
            or from_role not in role_ids
            or to_role not in role_ids
        ):
            _reject_package(
                f"relationships[{position}] references an unknown role "
                f"({from_role!r}, {to_role!r})"
            )
        if from_role == to_role:
            _reject_package(f"relationships[{position}] relates role {from_role!r} to itself")
        if kind not in RELATIONSHIP_KINDS:
            _reject_package(f"relationships[{position}] declares unknown kind {kind!r}")
        pair = (from_role, to_role)
        reverse = (to_role, from_role)
        if pair in seen_pairs:
            _reject_package(
                f"relationships[{position}] repeats relation {from_role!r} -> {to_role!r}"
            )
        if reverse in seen_pairs:
            _reject_package(
                f"relationships[{position}] declares the reciprocal of an existing "
                f"relation ({from_role!r} -> {to_role!r}); reciprocal relations are "
                "inconsistent"
            )
        seen_pairs.add(pair)
        relationships.append(
            RelationshipDefinition(from_role=from_role, to_role=to_role, kind=kind)
        )
    return tuple(relationships)


def _validate_knowledge(
    entries: Any, role_ids: set[str]
) -> tuple[KnowledgeClaim, ...]:
    if entries is None:
        return ()
    if not isinstance(entries, list):
        _reject_package("package.knowledge must be an array")
    claims: list[KnowledgeClaim] = []
    seen: set[tuple[str, str]] = set()
    for position, entry in enumerate(entries):
        entry = _require_mapping(entry, f"knowledge[{position}]")
        if set(entry) != {"role_id", "claim_id", "text", "provenance"}:
            _reject_package(
                f"knowledge[{position}] must declare exactly role_id, claim_id, text, "
                "provenance; knowledge is role-owned and visibility is never widened"
            )
        role_id = entry.get("role_id")
        if not isinstance(role_id, str) or role_id not in role_ids:
            _reject_package(f"knowledge[{position}] names unknown role {role_id!r}")
        claim_id = entry.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            _reject_package(f"knowledge[{position}].claim_id must be a non-empty string")
        if (role_id, claim_id) in seen:
            _reject_package(f"duplicate knowledge claim {claim_id!r} for role {role_id!r}")
        seen.add((role_id, claim_id))
        _bounded_prose(
            f"knowledge[{position}].text", entry.get("text"), MAX_KNOWLEDGE_CLAIM_TEXT,
            required=True,
        )
        provenance = _require_mapping(
            entry.get("provenance"), f"knowledge[{position}].provenance"
        )
        if set(provenance) != {"kind", "ref"} or provenance.get("kind") != "role_owner":
            _reject_package(
                f"knowledge[{position}].provenance must be exactly "
                "{'kind': 'role_owner', 'ref': <role id>}"
            )
        if provenance.get("ref") != role_id:
            _reject_package(
                f"knowledge[{position}] provenance owner {provenance.get('ref')!r} "
                f"does not own claim for role {role_id!r}"
            )
        claims.append(
            KnowledgeClaim(
                role_id=role_id,
                claim_id=claim_id,
                text=entry["text"],
                provenance={"kind": "role_owner", "ref": role_id},
            )
        )
    return tuple(claims)


def _require_grid_cell(locator: RoomLocator, where: str) -> None:
    if locator.kind is not DestinationKind.GRID:
        return
    from typeclasses.rooms import GridRoom

    if GridRoom.objects.filter_xyz(xyz=locator.xyz).first() is None:
        _reject_package(f"{where} grid cell {locator.xyz!r} is not materialized")


def _validate_encounters(
    entries: Any, role_ids: set[str]
) -> tuple[EncounterDefinition, ...]:
    if not isinstance(entries, list) or not entries:
        _reject_package("package.encounters must be a non-empty array")
    encounters: list[EncounterDefinition] = []
    seen: set[str] = set()
    for position, entry in enumerate(entries):
        entry = _require_mapping(entry, f"encounters[{position}]")
        if set(entry) != {
            "scene_id",
            "role_ids",
            "locator",
            "prerequisites",
        }:
            _reject_package(
                f"encounters[{position}] must declare exactly scene_id, role_ids, "
                "locator, prerequisites"
            )
        scene_id = entry.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id:
            _reject_package(f"encounters[{position}].scene_id must be a non-empty string")
        if len(scene_id) > MAX_ID_LENGTH:
            _reject_package(f"scene id {scene_id!r} exceeds the {MAX_ID_LENGTH}-character cap")
        if scene_id in seen:
            _reject_package(f"duplicate encounter {scene_id!r}")
        seen.add(scene_id)
        role_refs = entry.get("role_ids")
        if not isinstance(role_refs, list) or not role_refs:
            _reject_package(f"encounter {scene_id!r} must require at least one role")
        for role in role_refs:
            if not isinstance(role, str) or role not in role_ids:
                _reject_package(f"encounter {scene_id!r} references unknown role {role!r}")
        locator_payload = _require_mapping(
            entry.get("locator"), f"encounter {scene_id!r} locator"
        )
        locator = _compile_location(locator_payload)
        _require_grid_cell(locator, f"encounter {scene_id!r}")
        archetype, anchor_near, scene_sentence, _npcs, _chars = _validate_scene_fields(
            position, locator_payload, []
        )
        prerequisites = entry.get("prerequisites")
        if not isinstance(prerequisites, list):
            _reject_package(f"encounter {scene_id!r} prerequisites must be an array")
        normalized: list[dict[str, Any]] = []
        for index, condition in enumerate(prerequisites):
            try:
                normalized.append(validate_condition(condition))
            except ValueError as error:
                _reject_package(f"encounter {scene_id!r} prerequisite {index}: {error}")
        encounters.append(
            EncounterDefinition(
                scene_id=scene_id,
                role_ids=tuple(role_refs),
                locator=locator,
                archetype=archetype,
                anchor_near=anchor_near,
                scene_sentence=scene_sentence,
                prerequisites=tuple(normalized),
            )
        )
    return tuple(encounters)


def _validate_effects(
    entry: dict[str, Any], where: str, definition_keys: set[str]
) -> tuple[str | None, str | None]:
    has_verb = "effect_verb" in entry
    has_reference = "effect_reference" in entry
    if not has_verb and not has_reference:
        return None, None
    if not has_verb or not has_reference:
        _reject_package(
            f"{where} must declare effect_verb and effect_reference together"
        )
    verb = entry.get("effect_verb")
    reference = entry.get("effect_reference")
    if verb not in EFFECT_VERBS:
        _reject_package(f"{where} names unknown effect verb {verb!r}")
    if not isinstance(reference, str) or reference not in definition_keys:
        _reject_package(
            f"{where} effect reference {reference!r} is not a validated package commission"
        )
    return verb, reference


def _validate_dialogue(
    entries: Any,
    roles: dict[str, RoleDefinition],
    definition_keys: set[str],
) -> tuple[RoleDialogue, ...]:
    if not isinstance(entries, list) or not entries:
        _reject_package("package.dialogue must be a non-empty array")
    dialogues: list[RoleDialogue] = []
    seen_roles: set[str] = set()
    for position, entry in enumerate(entries):
        entry = _require_mapping(entry, f"dialogue[{position}]")
        if set(entry) != {"role_id", "initial_phase", "phases"}:
            _reject_package(
                f"dialogue[{position}] must declare exactly role_id, initial_phase, phases"
            )
        role_id = entry.get("role_id")
        if not isinstance(role_id, str) or role_id not in roles:
            _reject_package(f"dialogue[{position}] names unknown role {role_id!r}")
        role = roles[role_id]
        if role_id in seen_roles:
            _reject_package(f"duplicate dialogue definition for role {role_id!r}")
        seen_roles.add(role_id)
        if not role.conversable:
            _reject_package(
                f"role {role_id!r} declares dialogue but is not conversable"
            )
        phases_payload = entry.get("phases")
        if not isinstance(phases_payload, list) or not phases_payload:
            _reject_package(f"role {role_id!r} must declare at least one phase")
        phases: list[DialoguePhase] = []
        phase_ids: set[str] = set()
        defaults = 0
        for index, phase_entry in enumerate(phases_payload):
            phase_entry = _require_mapping(
                phase_entry, f"dialogue[{position}].phases[{index}]"
            )
            if set(phase_entry) != {
                "phase_id",
                "conditions",
                "greeting",
                "topics",
                "freeform_situation",
                "freeform_goals",
                "offline_response",
            }:
                _reject_package(
                    f"dialogue[{position}].phases[{index}] declares an unsupported field set"
                )
            phase_id = phase_entry.get("phase_id")
            if not isinstance(phase_id, str) or not phase_id:
                _reject_package(
                    f"role {role_id!r} phase {index} requires a non-empty phase_id"
                )
            if len(phase_id) > MAX_ID_LENGTH:
                _reject_package(f"phase id {phase_id!r} exceeds the cap")
            if phase_id in phase_ids:
                _reject_package(f"role {role_id!r} repeats phase id {phase_id!r}")
            phase_ids.add(phase_id)
            conditions_payload = phase_entry.get("conditions")
            if not isinstance(conditions_payload, list) or not conditions_payload:
                _reject_package(
                    f"role {role_id!r} phase {phase_id!r} must declare at least one condition"
                )
            conditions: list[dict[str, Any]] = []
            for condition in conditions_payload:
                try:
                    conditions.append(validate_condition(condition))
                except ValueError as error:
                    _reject_package(
                        f"role {role_id!r} phase {phase_id!r} condition: {error}"
                    )
            if any(condition.get("default") for condition in conditions):
                if len(conditions_payload) != 1:
                    _reject_package(
                        f"role {role_id!r} phase {phase_id!r} default must stand alone"
                    )
                defaults += 1
            _bounded_prose(
                f"role {role_id!r} phase {phase_id!r} greeting",
                phase_entry.get("greeting"),
                MAX_PHASE_GREETING,
                required=True,
            )
            _bounded_prose(
                f"role {role_id!r} phase {phase_id!r} freeform_situation",
                phase_entry.get("freeform_situation"),
                MAX_PHASE_FREEFORM,
                required=False,
            )
            _bounded_prose(
                f"role {role_id!r} phase {phase_id!r} freeform_goals",
                phase_entry.get("freeform_goals"),
                MAX_PHASE_FREEFORM,
                required=False,
            )
            _bounded_prose(
                f"role {role_id!r} phase {phase_id!r} offline_response",
                phase_entry.get("offline_response"),
                MAX_OFFLINE_RESPONSE,
                required=True,
            )
            topics_payload = phase_entry.get("topics")
            if not isinstance(topics_payload, list):
                _reject_package(
                    f"role {role_id!r} phase {phase_id!r} topics must be an array"
                )
            if len(topics_payload) > MAX_PHASE_TOPICS:
                _reject_package(
                    f"role {role_id!r} phase {phase_id!r} exceeds "
                    f"{MAX_PHASE_TOPICS} topics"
                )
            topics: list[PhaseTopic] = []
            keywords: set[str] = set()
            for topic_index, topic_entry in enumerate(topics_payload):
                topic_entry = _require_mapping(
                    topic_entry,
                    f"role {role_id!r} phase {phase_id!r} topic {topic_index}",
                )
                allowed = {"keyword", "response", "effect_verb", "effect_reference"}
                if not set(topic_entry).issubset(allowed):
                    _reject_package(
                        f"role {role_id!r} phase {phase_id!r} topic {topic_index} "
                        "declares an unsupported field"
                    )
                keyword = topic_entry.get("keyword")
                if not isinstance(keyword, str) or not keyword:
                    _reject_package(
                        f"role {role_id!r} phase {phase_id!r} topic {topic_index} "
                        "requires a non-empty keyword"
                    )
                if keyword in keywords:
                    _reject_package(
                        f"role {role_id!r} phase {phase_id!r} repeats keyword {keyword!r}"
                    )
                keywords.add(keyword)
                _bounded_prose(
                    f"role {role_id!r} phase {phase_id!r} topic {keyword!r} response",
                    topic_entry.get("response"),
                    MAX_TOPIC_RESPONSE,
                    required=True,
                )
                verb, reference = _validate_effects(
                    topic_entry,
                    f"role {role_id!r} phase {phase_id!r} topic {keyword!r}",
                    definition_keys,
                )
                topics.append(
                    PhaseTopic(
                        keyword=keyword,
                        response=topic_entry["response"],
                        effect_verb=verb,
                        effect_reference=reference,
                    )
                )
            phases.append(
                DialoguePhase(
                    phase_id=phase_id,
                    conditions=tuple(conditions),
                    greeting=phase_entry["greeting"],
                    topics=tuple(topics),
                    freeform_situation=phase_entry.get("freeform_situation") or "",
                    freeform_goals=phase_entry.get("freeform_goals") or "",
                    offline_response=phase_entry["offline_response"],
                )
            )
        if defaults != 1:
            _reject_package(
                f"role {role_id!r} must declare exactly one default phase, got {defaults}"
            )
        initial_phase = entry.get("initial_phase")
        if initial_phase not in phase_ids:
            _reject_package(
                f"role {role_id!r} initial phase {initial_phase!r} is not a declared phase"
            )
        _reject_overlapping_phases(role_id, phases)
        dialogues.append(
            RoleDialogue(
                role_id=role_id,
                initial_phase=initial_phase,
                phases=tuple(phases),
            )
        )
    for role_id, role in roles.items():
        if role.conversable and role_id not in seen_roles:
            _reject_package(
                f"conversable role {role_id!r} has no complete phase dialogue"
            )
    return tuple(dialogues)


def _observation_assignments() -> tuple[dict[str, bool], ...]:
    """Every committed-observation assignment over the registered facts.

    The registry has four Boolean facts, so enumerating all sixteen assignments
    is a complete decision procedure for the declared conditions: it makes
    "exactly one phase is selected for any committed observation" a static
    property instead of one deferred to the transition boundary.
    """
    from itertools import product

    facts = sorted(REGISTERED_FACTS)
    return tuple(
        dict(zip(facts, combination))
        for combination in product((False, True), repeat=len(facts))
    )


def _reject_overlapping_phases(role_id: str, phases: list[DialoguePhase]) -> None:
    """Reject ambiguous or unsatisfiable non-default phase selection (design §6).

    Overlapping selection is ambiguous: two non-default phases that are both
    satisfiable under one committed observation could never be told apart at
    transition time. An unsatisfiable conjunction (a contradiction such as
    ``closure`` true and false together) can never be selected, so it is an
    authored conflict too. Both are rejected at publication by enumerating every
    observation assignment over the registered facts; the runtime boundary
    additionally rejects ambiguity for the concrete observation it receives.
    """
    non_default = [
        phase
        for phase in phases
        if not any(condition.get("default") for condition in phase.conditions)
    ]
    if not non_default:
        return
    assignments = _observation_assignments()
    for phase in non_default:
        if not any(
            all(condition_matches(condition, assignment) for condition in phase.conditions)
            for assignment in assignments
        ):
            _reject_package(
                f"role {role_id!r} phase {phase.phase_id!r} declares an "
                "unsatisfiable condition combination"
            )
    for assignment in assignments:
        matched = [
            phase.phase_id
            for phase in non_default
            if all(condition_matches(condition, assignment) for condition in phase.conditions)
        ]
        if len(matched) > 1:
            _reject_package(
                f"role {role_id!r} phases {matched} overlap for one committed "
                "observation"
            )


def _validate_commission(
    entry: Any, roles: dict[str, RoleDefinition], definition_key: str
) -> SymbolicIssuer | None:
    if entry is None:
        return None
    entry = _require_mapping(entry, "package.commission")
    if set(entry) != {"role_id", "issuer_content_key"}:
        _reject_package(
            "package.commission must declare exactly role_id and issuer_content_key"
        )
    role_id = entry.get("role_id")
    if not isinstance(role_id, str) or role_id not in roles:
        _reject_package(f"package.commission names unknown role {role_id!r}")
    content_key = entry.get("issuer_content_key")
    if not isinstance(content_key, str) or not content_key:
        _reject_package("package.commission.issuer_content_key must be a non-empty string")
    try:
        issuer_key = npc_issuer_key(content_key)
    except IssuerKeyError as error:
        _reject_package(f"package.commission issuer key is invalid: {error}")
    return SymbolicIssuer(
        role_id=role_id, issuer_key=issuer_key, definition_key=definition_key
    )


def validate_scene_package(payload: Any) -> ScenePackageDefinition:
    """Validate a whole proposed package, or raise :class:`ScenePackageError`.

    Shared compile-boundary helpers raise the base ``QuestCompileError``; this
    wrapper normalizes every validation failure to the package-named error so a
    caller catches exactly one exception type for a rejected package.
    """
    try:
        return _validate_package_impl(payload)
    except ScenePackageError:
        raise
    except QuestCompileError as error:
        raise ScenePackageError(str(error)) from error


def _validate_package_impl(payload: Any) -> ScenePackageDefinition:
    """Validate a whole proposed package, or raise :class:`ScenePackageError`.

    Nothing is written and no actor is created. Every reference is resolved
    exactly through its existing authority; an unknown or ambiguous place,
    role, relationship, phase, effect or issuer is a named failure before any
    write.
    """
    payload = _require_mapping(payload, "package payload")
    if set(payload) != {
        "display_name",
        "source_id",
        "quest",
        "roles",
        "relationships",
        "knowledge",
        "encounters",
        "dialogue",
        "commission",
    }:
        _reject_package(
            "package payload must declare exactly display_name, source_id, quest, "
            "roles, relationships, knowledge, encounters, dialogue, commission"
        )
    _bounded_prose("package.display_name", payload.get("display_name"), 80, required=True)
    source_id = payload.get("source_id")
    if source_id is not None and (not isinstance(source_id, str) or not source_id):
        _reject_package("package.source_id must be a non-empty string or None")

    roles = _validate_roles(payload.get("roles"))
    role_ids = {role.role_id for role in roles}
    role_index = {role.role_id: role for role in roles}
    relationships = _validate_relationships(payload.get("relationships"), role_ids)
    knowledge = _validate_knowledge(payload.get("knowledge"), role_ids)

    quest_payload = _require_mapping(payload.get("quest"), "package.quest")
    issuer = quest_payload.get("issuer")
    commission_entry = payload.get("commission")
    quest_core = compile_blueprint_core(quest_payload)
    definition_key = quest_core.definition.key

    commission: SymbolicIssuer | None = None
    guild_branch: str | None = None
    if isinstance(issuer, str) and issuer in GUILD_BRANCH_REGISTRY:
        if commission_entry is not None:
            _reject_package(
                "a guild-branch package must not also declare a symbolic commission"
            )
        guild_branch = issuer
    else:
        if not isinstance(issuer, str) or issuer not in role_ids:
            _reject_package(
                f"package quest issuer {issuer!r} is neither a guild branch nor a "
                "declared package role"
            )
        if not role_index[issuer].conversable:
            _reject_package(
                f"issuer role {issuer!r} must be a conversable generated role"
            )
        commission = _validate_commission(commission_entry, role_index, definition_key)
        if commission is None or commission.role_id != issuer:
            _reject_package(
                "a symbolic package issuer requires a matching package.commission "
                "declaration"
            )
        if quest_core.reward.merit != 0:
            _reject_package(
                f"private commission {commission.issuer_key!r} cannot grant guild "
                f"merit, got {quest_core.reward.merit}"
            )

    definition_keys = {definition_key}
    encounters = _validate_encounters(payload.get("encounters"), role_ids)
    dialogue = _validate_dialogue(payload.get("dialogue"), role_index, definition_keys)

    package_id = scene_package_id(
        {
            "display_name": payload["display_name"],
            "source_id": source_id,
            "quest": quest_payload,
            "roles": payload["roles"],
            "relationships": payload.get("relationships") or [],
            "knowledge": payload.get("knowledge") or [],
            "encounters": payload["encounters"],
            "dialogue": payload["dialogue"],
            "commission": commission_entry,
        }
    )
    return ScenePackageDefinition(
        package_id=package_id,
        display_name=payload["display_name"],
        source_id=source_id,
        roles=roles,
        relationships=relationships,
        knowledge=knowledge,
        encounters=encounters,
        dialogue=dialogue,
        commission=commission,
        guild_branch=guild_branch,
        quest=quest_core,
    )


def scene_package_id(canonical: dict[str, Any]) -> str:
    """Return the stable content identity of a validated package payload."""
    import hashlib
    import json

    encoded = json.dumps(
        canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"pkg_{digest[:24]}"


def select_dialogue_phase(
    role_dialogue: RoleDialogue, facts: dict[str, bool]
) -> DialoguePhase:
    """Return the one complete phase a committed observation selects.

    A non-default phase is selected when every one of its conditions holds under
    the committed observation; the role's declared default phase is the
    fallback. Missing coverage, ambiguous selection and conflicting selection
    all raise :class:`ScenePackageError`, so a role never presents a half-chosen
    phase (design §6).
    """
    matched = [
        phase
        for phase in role_dialogue.phases
        if not any(condition.get("default") for condition in phase.conditions)
        and all(condition_matches(condition, facts) for condition in phase.conditions)
    ]
    if len(matched) > 1:
        _reject_package(
            f"role {role_dialogue.role_id!r} has an ambiguous phase selection for "
            f"one committed observation: {[phase.phase_id for phase in matched]}"
        )
    if matched:
        return matched[0]
    defaults = [
        phase
        for phase in role_dialogue.phases
        if any(condition.get("default") for condition in phase.conditions)
    ]
    if not defaults:
        _reject_package(
            f"role {role_dialogue.role_id!r} has no phase for the committed "
            "observation"
        )
    return defaults[0]


__all__ = [
    "DialoguePhase",
    "EncounterDefinition",
    "EFFECT_VERBS",
    "KnowledgeClaim",
    "PhaseTopic",
    "RELATIONSHIP_KINDS",
    "RelationshipDefinition",
    "RoleDefinition",
    "RoleDialogue",
    "ScenePackageDefinition",
    "ScenePackageError",
    "SymbolicIssuer",
    "scene_package_id",
    "select_dialogue_phase",
    "validate_scene_package",
]

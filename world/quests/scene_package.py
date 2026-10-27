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
from world.lore.dialogue.codec import (
    GENERATED_LOCAL_ID_PATTERN,
    GeneratedDialogueIdentity,
    make_generated_topic_id,
    parse_dialogue,
)
from world.lore.dialogue.shape import AuthoredTopic
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
from world.quests.definitions import (
    RELATIONSHIP_KINDS,
    DestinationKind,
    EscortCompletion,
    ObjectiveKind,
    QuestDefinitionError,
    QuestObjective,
    RoomLocator,
    validate_escort_predicate,
)
from world.quests.phases import (
    REGISTERED_FACTS,
    condition_matches,
    validate_condition,
)
from world.rules.quest_issuance import npc_issuer_key, IssuerKeyError


class ScenePackageError(QuestCompileError):
    """A scene-package payload violates the bounded package contract."""


#: The closed typed-relationship vocabulary is owned by the quest definitions
#: module (``world.quests.definitions.RELATIONSHIP_KINDS``) and re-exported
#: here so the scene-package contract and an escort rendezvous predicate cannot
#: drift: ``parent_child`` is directed (from_role is the parent, to_role the
#: child). Declaring the reverse of an existing pair, or the same ordered pair
#: twice, is an inconsistent reciprocal relation. A relationship never confers
#: private knowledge.

#: The closed domain-effect vocabulary a scripted topic may name. Every verb
#: resolves through the deterministic commission APIs at execution time; a label
#: or fixed line can never itself award progress or items (design §6). A private
#: commission settles automatically on completion, so the only pre-acceptance
#: interaction a generated issuer offers is accepting its commission.
EFFECT_VERBS: tuple[str, ...] = ("offer_commission",)

MAX_ID_LENGTH = 64
MAX_PHASE_TOPICS = 16
MAX_KNOWLEDGE_CLAIM_TEXT = 200
MAX_PHASE_FREEFORM = 400
MAX_OFFLINE_RESPONSE = 500
MAX_PHASE_GREETING = 500

#: The capability types a generated package role may declare. A generated role
#: exists to hold scene narrative: when it issues a commission it declares the
#: scoped issuing authority, and when one of its phases advertises an explicit
#: dialogue service it declares the service-bound dialogue identity. Trade,
#: guild, reception and place-anchored services have no authored place in a
#: generated scene.
GENERATED_CAPABILITY_TYPES = frozenset({"quest_issuer", "scripted_dialogue"})

#: The optional authored kwargs each generated capability may carry beside its
#: trusted scoped ``service_id``. A generated scripted dialogue's
#: ``dialogue_key`` and a commission issuer's ``issuer_key`` are the two
#: authored identities; the scoped identity itself is always trusted.
_GENERATED_CAPABILITY_KWARGS: dict[str, frozenset[str]] = {
    "quest_issuer": frozenset({"issuer_key"}),
    "scripted_dialogue": frozenset({"dialogue_key"}),
}


def _reject_package(message: str) -> None:
    raise ScenePackageError(message)


def generated_role_service_id(package_id: str, role_id: str) -> str:
    """The trusted scoped service identity of one generated role's capability."""
    return f"scene_role:{package_id}:{role_id}"


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
    #: The role's explicit capability declarations (npc-capability-
    #: declarations). Only a commission role declares one, and its scoped
    #: ``service_id`` is the trusted identity the boundary supplies.
    capabilities: tuple[Any, ...] = ()


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
class TopicEffect:
    """One source-owner validated effect association keyed by stable topic ID.

    The association is external to the common prose declaration: the generated
    package declares it beside the scene, and runtime authorization re-reads it
    from the immutable payload. It is never authored inside a scene and never
    inferred from a label.
    """

    topic_id: str
    verb: str
    reference: str


@dataclass(frozen=True)
class DialoguePhase:
    phase_id: str
    conditions: tuple[dict[str, Any], ...]
    greeting: str
    topics: tuple[AuthoredTopic, ...]
    topic_effects: tuple[TopicEffect, ...]
    freeform_situation: str
    freeform_goals: str
    offline_response: str
    #: The phase's explicit service associations (default none). Each row names
    #: a topic of THIS phase whose existing deterministic entry it advertises;
    #: it grants no effect, reading completion, or extra authority.
    services: tuple[Any, ...] = ()


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
class OutcomeResultDefinition:
    """One exclusive group's concrete final-result condition (design §7).

    The same closed predicate an ESCORT objective declares, validated through
    the shared quest-definition seam: a completion discriminator, exact
    protected role references, and — for rendezvous — exact meeting role
    references with an optional typed relation. Every reference names a role
    this package defines, so the condition is executable, never prose.
    """

    completion: EscortCompletion
    protected_role_refs: tuple[str, ...]
    meeting_role_refs: tuple[str, ...]
    relation: tuple[str, str, str] | None


@dataclass(frozen=True)
class OutcomeGroupDefinition:
    """One explicit final-result group and the commissions it obsoletes.

    ``alternative_definition_keys`` names the distinct commission definitions
    that become obsolete once the result holds (design §7). Story-thread
    identity alone implies no exclusivity; only an explicit declaration here
    does. Each alternative keeps its own definition, issuer, record, protected
    roles, deadline and registered reward.
    """

    group_id: str
    result: OutcomeResultDefinition
    alternative_definition_keys: tuple[str, ...]


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
    #: Every distinct role-issued commission this package declares. Empty for a
    #: guild-branch package; at least one entry otherwise, and the quest's
    #: declared issuer role must be among them.
    commissions: tuple[SymbolicIssuer, ...]
    #: Every explicit exclusive outcome group this package declares, in payload
    #: order. Absent from a package that declares no exclusivity.
    outcome_groups: tuple[OutcomeGroupDefinition, ...]
    guild_branch: str | None
    quest: CompiledBlueprintCore

    def role(self, role_id: str) -> RoleDefinition | None:
        return next((r for r in self.roles if r.role_id == role_id), None)

    def encounter(self, scene_id: str) -> EncounterDefinition | None:
        return next((e for e in self.encounters if e.scene_id == scene_id), None)

    def role_dialogue(self, role_id: str) -> RoleDialogue | None:
        return next((d for d in self.dialogue if d.role_id == role_id), None)

    def commission_for_role(self, role_id: str) -> SymbolicIssuer | None:
        """The distinct commission declared for one role, or ``None``.

        A role issues at most one commission per package, so the lookup is
        unambiguous; a role with no declaration issues nothing.
        """
        return next(
            (c for c in self.commissions if c.role_id == role_id),
            None,
        )

    def outcome_group(self, group_id: str) -> OutcomeGroupDefinition | None:
        return next(
            (g for g in self.outcome_groups if g.group_id == group_id), None
        )

    def role_ids(self) -> frozenset[str]:
        return frozenset(r.role_id for r in self.roles)


def _bounded_prose(field: str, value: Any, bound: int, *, required: bool) -> str | None:
    _validate_strings(None, field, value, bound, required=required)
    return value


def _compile_role_capabilities(
    entries: Any, *, package_id: str, role_id: str
) -> tuple[Any, ...]:
    """Compile one role's explicit capability declarations, or reject them.

    A generated role declares at most one capability of each supported type,
    person-bound, and its scoped ``service_id`` is the TRUSTED identity
    ``scene_role:<package_id>:<role_id>`` — the model cannot know the content
    digest, so an absent value is supplied here and a differing authored one is
    a rejection. A service-bound generated dialogue's ``dialogue_key`` is the
    same trusted scoped identity for the same reason. ``issuer_key`` stays an
    authored value: the commission cross-check requires it to equal the
    declared content key. The compiled declarations still go through the shared
    capability core, so the per-type vocabulary and required kwargs have
    exactly one owner.
    """
    from world.rules.npc_capabilities import (
        CapabilityValidationError,
        capability,
        person_bound,
        validate_capabilities,
    )

    if entries is None:
        return ()
    if not isinstance(entries, list):
        _reject_package(f"role {role_id!r} capabilities must be an array")
    trusted_service_id = generated_role_service_id(package_id, role_id)
    compiled: list[Any] = []
    for position, entry in enumerate(entries):
        where = f"role {role_id!r} capabilities[{position}]"
        entry = _require_mapping(entry, where)
        unknown = set(entry) - {"type", "kwargs", "binding"}
        missing = {"type", "kwargs", "binding"} - set(entry)
        if unknown or missing:
            _reject_package(
                f"{where} must declare exactly type, kwargs and binding "
                f"(unknown {sorted(unknown)}, missing {sorted(missing)})"
            )
        type_key = entry.get("type")
        if type_key not in GENERATED_CAPABILITY_TYPES:
            _reject_package(
                f"{where} declares unsupported generated capability {type_key!r}; "
                f"generated roles may declare {sorted(GENERATED_CAPABILITY_TYPES)}"
            )
        kwargs = _require_mapping(entry.get("kwargs"), f"{where}.kwargs")
        unknown_kwargs = (
            set(kwargs) - _GENERATED_CAPABILITY_KWARGS[type_key] - {"service_id"}
        )
        if unknown_kwargs:
            _reject_package(
                f"{where}.kwargs declares {sorted(unknown_kwargs)}, which a "
                f"generated {type_key!r} does not accept"
            )
        authored_service_id = kwargs.get("service_id")
        if authored_service_id is not None and authored_service_id != trusted_service_id:
            _reject_package(
                f"{where}.kwargs service_id {authored_service_id!r} is not the "
                f"trusted scoped identity {trusted_service_id!r}"
            )
        authored_values = {
            key: value for key, value in kwargs.items() if key != "service_id"
        }
        if type_key == "scripted_dialogue":
            authored_dialogue_key = authored_values.get("dialogue_key")
            if (
                authored_dialogue_key is not None
                and authored_dialogue_key != trusted_service_id
            ):
                _reject_package(
                    f"{where}.kwargs dialogue_key {authored_dialogue_key!r} is not "
                    f"the trusted scoped identity {trusted_service_id!r}"
                )
            authored_values["dialogue_key"] = trusted_service_id
        binding = _require_mapping(entry.get("binding"), f"{where}.binding")
        if binding != {"kind": "person"}:
            _reject_package(
                f"{where}.binding must be exactly {{'kind': 'person'}}; a "
                "generated capability travels with its actor"
            )
        compiled.append(
            capability(
                type_key,
                binding=person_bound(),
                service_id=trusted_service_id,
                **authored_values,
            )
        )
    try:
        validate_capabilities(compiled)
    except CapabilityValidationError as error:
        _reject_package(f"role {role_id!r} declares unusable capabilities: {error}")
    return tuple(compiled)


def _validate_roles(
    entries: Any, *, package_id: str
) -> tuple[RoleDefinition, ...]:
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
            "capabilities",
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
        capabilities = _compile_role_capabilities(
            entry.get("capabilities"), package_id=package_id, role_id=role_id
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
                capabilities=capabilities,
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


def _validate_topic_effects(
    entries: Any,
    *,
    where: str,
    phase: tuple[AuthoredTopic, ...],
    identity: GeneratedDialogueIdentity,
    definition_keys: set[str],
    commission_role_ids: frozenset[str],
) -> tuple[TopicEffect, ...]:
    """Validate one phase's external effect associations.

    Every row names a locally declared topic of the same phase, the one
    allowlisted verb and a definition key this package's role actually issues a
    commission for. An effect-bearing topic must be qualified and must carry a
    safe refusal scene, because the deterministic domain authority can refuse
    the effect after disclosure; a public pure-chain successor is never an
    effect topic.
    """
    if entries is None:
        return ()
    if not isinstance(entries, list):
        _reject_package(f"{where} topic_effects must be an array")
    topics_by_id = {topic.topic_id: topic for topic in phase}
    effects: list[TopicEffect] = []
    seen: set[str] = set()
    for position, entry in enumerate(entries):
        row_where = f"{where} topic_effects[{position}]"
        entry = _require_mapping(entry, row_where)
        if set(entry) != {"topic_id", "verb", "reference"}:
            _reject_package(
                f"{row_where} must declare exactly topic_id, verb, reference"
            )
        local_topic_id = entry.get("topic_id")
        if not isinstance(local_topic_id, str) or not GENERATED_LOCAL_ID_PATTERN.match(
            local_topic_id
        ):
            _reject_package(
                f"{row_where} topic_id must be a declared local ID "
                "matching [a-z][a-z0-9_]{0,31}"
            )
        topic_id = make_generated_topic_id(
            identity.package_id,
            identity.role_id,
            identity.phase_id,
            local_topic_id,
        )
        if topic_id in seen:
            _reject_package(f"{row_where} repeats topic {local_topic_id!r}")
        seen.add(topic_id)
        topic = topics_by_id.get(topic_id)
        if topic is None:
            _reject_package(
                f"{row_where} names topic {local_topic_id!r} not declared in "
                f"phase {identity.phase_id!r}"
            )
        verb = entry.get("verb")
        if verb not in EFFECT_VERBS:
            _reject_package(f"{row_where} names unknown effect verb {verb!r}")
        reference = entry.get("reference")
        if reference not in definition_keys:
            _reject_package(
                f"{row_where} effect reference {reference!r} is not a validated "
                "package commission"
            )
        if identity.role_id not in commission_role_ids:
            _reject_package(
                f"{row_where} declares an effect for role {identity.role_id!r}, "
                "which declares no package commission"
            )
        if topic.disclosure == "pure_chain":
            _reject_package(
                f"{row_where} effect topic {local_topic_id!r} must not be a "
                "pure-chain successor"
            )
        if topic.requires is None:
            _reject_package(
                f"{row_where} effect topic {local_topic_id!r} must declare requires"
            )
        if topic.refusal is None:
            _reject_package(
                f"{row_where} effect topic {local_topic_id!r} must declare a safe "
                "refusal scene"
            )
        effects.append(
            TopicEffect(topic_id=topic_id, verb=verb, reference=reference)
        )
    return tuple(effects)


def _validate_generated_services(
    services: Any,
    *,
    where: str,
    topic_effects: tuple[TopicEffect, ...],
    role: RoleDefinition,
) -> None:
    """Reject a phase whose service associations cannot be executed here.

    A generated source may advertise only a topic this same phase bound an
    ``offer_commission`` effect to — an informational topic is never a service.
    The role must carry the service-bound dialogue capability, an
    effect-bearing association also needs its scoped issuing authority, and the
    phase's complete native-plus-associated set must fit the entry bound.
    """
    from world.rules.npc_services import validate_service_capacity
    from world.lore.dialogue.services import OFFER_COMMISSION_VERB

    if not services:
        return
    capability_types = frozenset(item.type for item in role.capabilities)
    if "scripted_dialogue" not in capability_types:
        _reject_package(
            f"{where} declares service associations but role {role.role_id!r} "
            "carries no service-bound scripted_dialogue capability"
        )
    supported = frozenset(
        effect.topic_id
        for effect in topic_effects
        if effect.verb == OFFER_COMMISSION_VERB
    )
    for service in services:
        if service.topic_id not in supported:
            _reject_package(
                f"{where} service {service.key!r} names topic "
                f"{service.topic_id!r}, which this phase does not bind an "
                f"{OFFER_COMMISSION_VERB!r} effect to"
            )
    if supported and "quest_issuer" not in capability_types:
        _reject_package(
            f"{where} advertises an effect-bearing service but role "
            f"{role.role_id!r} carries no scoped quest_issuer capability"
        )
    try:
        validate_service_capacity(capability_types, len(services))
    except (TypeError, ValueError) as error:
        _reject_package(f"{where} {error}")


def _parse_generated_phase(
    *,
    where: str,
    identity: GeneratedDialogueIdentity,
    greeting: Any,
    topics_payload: Any,
    services_payload: Any,
    role_ids: frozenset[str],
    definition_keys: set[str],
) -> tuple[tuple[AuthoredTopic, ...], tuple[Any, ...]]:
    """Parse one phase (topics and explicit service rows) through the one codec."""
    if not isinstance(topics_payload, list):
        _reject_package(f"{where} topics must be an array")
    if len(topics_payload) > MAX_PHASE_TOPICS:
        _reject_package(f"{where} exceeds {MAX_PHASE_TOPICS} topics")
    _reject_duplicate_local_topic_ids(where, topics_payload)
    from world.rules.dialogue_references import static_dialogue_references

    try:
        dialogue = parse_dialogue(
            {
                "greeting": greeting,
                "topics": topics_payload,
                "services": services_payload,
            },
            identity=identity,
            references=static_dialogue_references(),
            package_roles=role_ids,
            package_quests=frozenset(definition_keys),
        )
    except (TypeError, ValueError) as error:
        _reject_package(f"{where} dialogue is invalid: {error}")
    keywords = [topic.keyword for topic in dialogue.topics]
    if len(set(keywords)) != len(keywords):
        _reject_package(f"{where} repeats a topic keyword")
    return dialogue.topics, dialogue.services


def _reject_duplicate_local_topic_ids(where: str, topics_payload: list[Any]) -> None:
    """Reject duplicate local topic IDs and duplicate variant IDs before parsing."""
    seen_topics: set[str] = set()
    for position, entry in enumerate(topics_payload):
        if not isinstance(entry, dict):
            _reject_package(f"{where} topic {position} must be an object")
        topic_id = entry.get("topic_id")
        if not isinstance(topic_id, str) or not topic_id:
            _reject_package(f"{where} topic {position} requires a topic_id")
        if topic_id in seen_topics:
            _reject_package(f"{where} repeats topic id {topic_id!r}")
        seen_topics.add(topic_id)
        variants = entry.get("variants")
        if variants is None:
            continue
        if not isinstance(variants, list):
            _reject_package(f"{where} topic {topic_id!r} variants must be an array")
        seen_variants: set[str] = set()
        for variant in variants:
            if not isinstance(variant, dict):
                _reject_package(f"{where} topic {topic_id!r} variant must be an object")
            variant_id = variant.get("variant_id")
            if not isinstance(variant_id, str) or not variant_id:
                _reject_package(f"{where} topic {topic_id!r} requires a variant_id")
            if variant_id in seen_variants:
                _reject_package(
                    f"{where} topic {topic_id!r} repeats variant {variant_id!r}"
                )
            seen_variants.add(variant_id)


def _validate_dialogue(
    entries: Any,
    roles: dict[str, RoleDefinition],
    *,
    package_id: str,
    definition_keys: set[str],
    commission_role_ids: frozenset[str],
) -> tuple[RoleDialogue, ...]:
    if not isinstance(entries, list) or not entries:
        _reject_package("package.dialogue must be a non-empty array")
    role_ids = frozenset(roles)
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
            allowed_phase_fields = {
                "phase_id",
                "conditions",
                "greeting",
                "topics",
                "services",
                "freeform_situation",
                "freeform_goals",
                "offline_response",
                "topic_effects",
            }
            required_phase_fields = allowed_phase_fields - {
                "services",
                "topic_effects",
            }
            if (
                not set(phase_entry).issubset(allowed_phase_fields)
                or not required_phase_fields.issubset(phase_entry)
            ):
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
            identity = GeneratedDialogueIdentity(package_id, role_id, phase_id)
            where = f"role {role_id!r} phase {phase_id!r}"
            topics, services = _parse_generated_phase(
                where=where,
                identity=identity,
                greeting=phase_entry["greeting"],
                topics_payload=phase_entry.get("topics"),
                services_payload=phase_entry.get("services"),
                role_ids=role_ids,
                definition_keys=definition_keys,
            )
            topic_effects = _validate_topic_effects(
                phase_entry.get("topic_effects"),
                where=where,
                phase=topics,
                identity=identity,
                definition_keys=definition_keys,
                commission_role_ids=commission_role_ids,
            )
            _validate_generated_services(
                services,
                where=where,
                topic_effects=topic_effects,
                role=roles[role_id],
            )
            phases.append(
                DialoguePhase(
                    phase_id=phase_id,
                    conditions=tuple(conditions),
                    greeting=phase_entry["greeting"],
                    topics=tuple(topics),
                    topic_effects=topic_effects,
                    freeform_situation=phase_entry.get("freeform_situation") or "",
                    freeform_goals=phase_entry.get("freeform_goals") or "",
                    offline_response=phase_entry["offline_response"],
                    services=tuple(services),
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


def _validate_commissions(
    entries: Any, roles: dict[str, RoleDefinition], definition_key: str
) -> tuple[SymbolicIssuer, ...]:
    """Validate the package's distinct role-issued commission declarations.

    Each entry declares one exact role and its authored issuer content key; two
    entries may not name the same role (one role issues one commission identity
    per package), and every issuer key must parse under the shared grammar. The
    named role must ALSO declare exactly one person-bound ``quest_issuer``
    capability whose authored ``issuer_key`` is that same content key: the
    capability is what provisions the authority, so a commission without it
    (or with a different identity) rejects before publication.
    """
    if entries is None:
        return ()
    if not isinstance(entries, list):
        _reject_package("package.commissions must be an array")
    commissions: list[SymbolicIssuer] = []
    seen_roles: set[str] = set()
    for position, entry in enumerate(entries):
        entry = _require_mapping(entry, f"package.commissions[{position}]")
        if set(entry) != {"role_id", "issuer_content_key"}:
            _reject_package(
                f"package.commissions[{position}] must declare exactly role_id "
                "and issuer_content_key"
            )
        role_id = entry.get("role_id")
        if not isinstance(role_id, str) or role_id not in roles:
            _reject_package(
                f"package.commissions[{position}] names unknown role {role_id!r}"
            )
        if role_id in seen_roles:
            _reject_package(
                f"package.commissions declares role {role_id!r} more than once"
            )
        seen_roles.add(role_id)
        content_key = entry.get("issuer_content_key")
        if not isinstance(content_key, str) or not content_key:
            _reject_package(
                f"package.commissions[{position}].issuer_content_key must be a "
                "non-empty string"
            )
        try:
            issuer_key = npc_issuer_key(content_key)
        except IssuerKeyError as error:
            _reject_package(
                f"package.commissions[{position}] issuer key is invalid: {error}"
            )
        _require_commission_capability(
            roles[role_id], content_key, position
        )
        commissions.append(
            SymbolicIssuer(
                role_id=role_id, issuer_key=issuer_key, definition_key=definition_key
            )
        )
    return tuple(commissions)


def _require_commission_capability(role: RoleDefinition, content_key: str, position: int) -> None:
    """Reject a commission role whose declared capability is missing/mismatched."""
    from world.rules.npc_capabilities import REQUIRED_KWARGS

    declarations = [item for item in role.capabilities if item.type == "quest_issuer"]
    if len(declarations) != 1:
        _reject_package(
            f"package.commissions[{position}] role {role.role_id!r} must declare "
            "exactly one quest_issuer capability"
        )
    declaration = declarations[0]
    if declaration.binding is None or declaration.binding.kind != "person":
        _reject_package(
            f"package.commissions[{position}] role {role.role_id!r} declares a "
            "quest_issuer capability that is not person-bound"
        )
    required = REQUIRED_KWARGS["quest_issuer"]
    missing = sorted(
        field
        for field in required
        if not isinstance(declaration.kwargs.get(field), str)
        or not declaration.kwargs[field]
    )
    if missing:
        _reject_package(
            f"package.commissions[{position}] role {role.role_id!r} capability "
            f"is missing {missing}"
        )
    if declaration.kwargs.get("issuer_key") != content_key:
        _reject_package(
            f"package.commissions[{position}] role {role.role_id!r} capability "
            f"issuer_key {declaration.kwargs.get('issuer_key')!r} does not match "
            f"its commission content key {content_key!r}"
        )


def _validate_outcome_groups(
    entries: Any,
    role_ids: set[str],
    definition: Any,
) -> tuple[OutcomeGroupDefinition, ...]:
    """Validate the package's explicit exclusive outcome groups (design §7).

    Each group declares a bounded group id, a concrete final-result condition
    validated through the shared escort-predicate seam, and the nonempty,
    de-duplicated set of alternative commission definitions the result
    obsoletes. The result's role references must be roles this package defines,
    so the declared condition is executable against the bound actors; the
    alternative list may reference any definition key, because each alternative
    keeps its own package/definition/reward.
    """
    if entries is None:
        return ()
    if not isinstance(entries, list):
        _reject_package("package.outcome_groups must be an array")
    groups: list[OutcomeGroupDefinition] = []
    seen_ids: set[str] = set()
    for position, entry in enumerate(entries):
        where = f"package.outcome_groups[{position}]"
        entry = _require_mapping(entry, where)
        if set(entry) != {"group_id", "result", "alternatives"}:
            _reject_package(
                f"{where} must declare exactly group_id, result and alternatives"
            )
        group_id = entry.get("group_id")
        if not isinstance(group_id, str) or not group_id:
            _reject_package(f"{where}.group_id must be a non-empty string")
        if len(group_id) > MAX_ID_LENGTH:
            _reject_package(
                f"{where}.group_id exceeds the {MAX_ID_LENGTH}-character bound"
            )
        if group_id in seen_ids:
            _reject_package(f"{where}.group_id {group_id!r} is declared twice")
        seen_ids.add(group_id)
        result = _validate_outcome_result(
            _require_mapping(entry.get("result"), f"{where}.result"), role_ids, definition
        )
        alternatives = entry.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            _reject_package(f"{where}.alternatives must be a non-empty array")
        keys: list[str] = []
        for index, key in enumerate(alternatives):
            if not isinstance(key, str) or not key:
                _reject_package(
                    f"{where}.alternatives[{index}] must be a non-empty "
                    "definition key"
                )
            if len(key) > MAX_ID_LENGTH:
                _reject_package(
                    f"{where}.alternatives[{index}] exceeds the "
                    f"{MAX_ID_LENGTH}-character bound"
                )
            if key in keys:
                _reject_package(
                    f"{where}.alternatives declares {key!r} more than once"
                )
            keys.append(key)
        groups.append(
            OutcomeGroupDefinition(
                group_id=group_id,
                result=result,
                alternative_definition_keys=tuple(keys),
            )
        )
    return tuple(groups)


def _validate_outcome_result(
    entry: dict[str, Any],
    role_ids: set[str],
    definition: Any,
) -> OutcomeResultDefinition:
    """Validate one concrete final-result condition through the shared seam."""
    allowed = {"completion", "protected_role_refs", "meeting_role_refs", "relation"}
    unknown = set(entry) - allowed
    if unknown:
        _reject_package(
            f"outcome result declares unknown fields {sorted(unknown)}"
        )
    completion_value = entry.get("completion")
    if not isinstance(completion_value, str) or completion_value not in {
        completion.value for completion in EscortCompletion
    }:
        _reject_package(
            "an outcome result requires exactly one completion discriminator "
            "(destination or rendezvous)"
        )
    completion = EscortCompletion(completion_value)
    protected = _result_role_refs(entry.get("protected_role_refs"), "protected_role_refs")
    meeting = _result_role_refs(entry.get("meeting_role_refs"), "meeting_role_refs")
    relation = entry.get("relation")
    relation_tuple: tuple[str, str, str] | None = None
    if relation is not None:
        relation = _require_mapping(relation, "outcome result.relation")
        if set(relation) != {"kind", "from_role", "to_role"}:
            _reject_package(
                "an outcome result relation must declare exactly kind, from_role "
                "and to_role"
            )
        relation_tuple = (
            relation.get("kind"),
            relation.get("from_role"),
            relation.get("to_role"),
        )
    referenced = set(protected) | set(meeting)
    unknown_roles = referenced - role_ids
    if unknown_roles:
        _reject_package(
            f"outcome result references undeclared package roles "
            f"{sorted(unknown_roles)}"
        )
    predicate = QuestObjective(
        kind=ObjectiveKind.ESCORT,
        quantity=1,
        completion=completion,
        protected_role_refs=protected,
        meeting_role_refs=meeting,
        relation=relation_tuple,
    )
    try:
        validate_escort_predicate(definition, predicate)
    except QuestDefinitionError as error:
        _reject_package(f"outcome result is not a closed escort predicate: {error}")
    return OutcomeResultDefinition(
        completion=completion,
        protected_role_refs=protected,
        meeting_role_refs=meeting,
        relation=relation_tuple,
    )


def _result_role_refs(value: Any, field_name: str) -> tuple[str, ...]:
    """Decode one outcome-result role-reference list into a strict string tuple."""
    if value is None:
        return ()
    if not isinstance(value, list):
        _reject_package(f"outcome result {field_name} must be an array")
    refs: list[str] = []
    for position, entry in enumerate(value):
        if not isinstance(entry, str) or not entry:
            _reject_package(
                f"outcome result {field_name}[{position}] must be a non-empty "
                "role reference"
            )
        refs.append(entry)
    return tuple(refs)


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
    allowed_keys = {
        "display_name",
        "source_id",
        "quest",
        "roles",
        "relationships",
        "knowledge",
        "encounters",
        "dialogue",
        "commissions",
        "outcome_groups",
    }
    unknown_keys = set(payload) - allowed_keys
    if unknown_keys:
        _reject_package(
            f"package payload declares unknown keys {sorted(unknown_keys)}; allowed "
            "keys are display_name, source_id, quest, roles, relationships, "
            "knowledge, encounters, dialogue, commissions, outcome_groups"
        )
    missing_keys = (allowed_keys - {"outcome_groups"}) - set(payload)
    if missing_keys:
        _reject_package(
            f"package payload is missing required keys {sorted(missing_keys)}"
        )
    _bounded_prose("package.display_name", payload.get("display_name"), 80, required=True)
    source_id = payload.get("source_id")
    if source_id is not None and (not isinstance(source_id, str) or not source_id):
        _reject_package("package.source_id must be a non-empty string or None")

    # The content identity is a pure digest of this proposal's immutable JSON
    # and is independent of the namespaced IDs derived below, so it is computed
    # first: a generated role's trusted scoped service identity derives from it.
    # A revalidation of the stored payload reconstructs the byte-identical id.
    package_id = scene_package_id(
        {
            "display_name": payload["display_name"],
            "source_id": source_id,
            "quest": payload.get("quest"),
            "roles": payload["roles"],
            "relationships": payload.get("relationships") or [],
            "knowledge": payload.get("knowledge") or [],
            "encounters": payload["encounters"],
            "dialogue": payload["dialogue"],
            "commissions": payload.get("commissions") or [],
            "outcome_groups": payload.get("outcome_groups") or [],
        }
    )

    roles = _validate_roles(payload.get("roles"), package_id=package_id)
    role_ids = {role.role_id for role in roles}
    role_index = {role.role_id: role for role in roles}
    relationships = _validate_relationships(payload.get("relationships"), role_ids)
    knowledge = _validate_knowledge(payload.get("knowledge"), role_ids)

    quest_payload = _require_mapping(payload.get("quest"), "package.quest")
    issuer = quest_payload.get("issuer")
    commission_entries = payload.get("commissions")
    # The published package's own validated role set enables the single bounded
    # permanent-occupant exception; a standalone payload passes none.
    quest_core = compile_blueprint_core(quest_payload, package_roles=role_ids)
    definition_key = quest_core.definition.key

    commissions: tuple[SymbolicIssuer, ...] = ()
    guild_branch: str | None = None
    if isinstance(issuer, str) and issuer in GUILD_BRANCH_REGISTRY:
        if commission_entries:
            _reject_package(
                "a guild-branch package must not also declare symbolic commissions"
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
        commissions = _validate_commissions(
            commission_entries, role_index, definition_key
        )
        if issuer not in {commission.role_id for commission in commissions}:
            _reject_package(
                "a symbolic package issuer requires a matching package.commissions "
                "declaration"
            )
        if quest_core.reward.merit != 0:
            _reject_package(
                f"private commissions cannot grant guild merit, got "
                f"{quest_core.reward.merit}"
            )

    outcome_groups = _validate_outcome_groups(
        payload.get("outcome_groups"), role_ids, quest_core.definition
    )

    commission_role_ids = frozenset(
        commission.role_id for commission in commissions
    )
    definition_keys = {definition_key}
    encounters = _validate_encounters(payload.get("encounters"), role_ids)
    dialogue = _validate_dialogue(
        payload.get("dialogue"),
        role_index,
        package_id=package_id,
        definition_keys=definition_keys,
        commission_role_ids=frozenset(
            commission.role_id for commission in commissions
        ),
    )
    _validate_role_capability_ownership(
        roles, dialogue, commission_role_ids=commission_role_ids
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
        commissions=commissions,
        outcome_groups=outcome_groups,
        guild_branch=guild_branch,
        quest=quest_core,
    )


def _validate_role_capability_ownership(
    roles: tuple[RoleDefinition, ...],
    dialogue: tuple[RoleDialogue, ...],
    *,
    commission_role_ids: frozenset[str],
) -> None:
    """Reject a role whose capabilities it cannot justify.

    A scoped issuing authority belongs to a commission role. A service-bound
    dialogue identity belongs to a role whose dialogue declares service
    associations — and a role that declares associations must carry it. A
    narrative-only role therefore stays unbound.
    """
    services_by_role = {
        entry.role_id: any(phase.services for phase in entry.phases)
        for entry in dialogue
    }
    for role in roles:
        types = frozenset(item.type for item in role.capabilities)
        if "quest_issuer" in types and role.role_id not in commission_role_ids:
            _reject_package(
                f"role {role.role_id!r} declares a quest_issuer capability but "
                "issues no commission"
            )
        declares_services = services_by_role.get(role.role_id, False)
        if declares_services and "scripted_dialogue" not in types:
            _reject_package(
                f"role {role.role_id!r} declares dialogue service associations "
                "but carries no service-bound scripted_dialogue capability"
            )
        if "scripted_dialogue" in types and not declares_services:
            _reject_package(
                f"role {role.role_id!r} carries a service-bound scripted_dialogue "
                "capability but declares no dialogue service association"
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


#: A published package's identity IS its content digest and its payload is
#: immutable, so a validated definition may be cached by package id. Runtime
#: state (a role's selected phase, an encounter's activation) is never cached.
_VALIDATED_PACKAGE_CACHE: dict[str, ScenePackageDefinition] = {}
_VALIDATED_PACKAGE_CACHE_LIMIT = 64


def validated_package(package_id: str, payload: Any) -> ScenePackageDefinition | None:
    """Return one published payload's validated definition, or ``None``."""
    cached = _VALIDATED_PACKAGE_CACHE.get(package_id)
    if cached is not None:
        return cached
    try:
        definition = validate_scene_package(payload)
    except Exception:  # noqa: BLE001 - a stored payload that no longer validates yields no definition
        return None
    if len(_VALIDATED_PACKAGE_CACHE) >= _VALIDATED_PACKAGE_CACHE_LIMIT:
        _VALIDATED_PACKAGE_CACHE.pop(next(iter(_VALIDATED_PACKAGE_CACHE)))
    _VALIDATED_PACKAGE_CACHE[package_id] = definition
    return definition


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
    "RELATIONSHIP_KINDS",
    "RelationshipDefinition",
    "RoleDefinition",
    "RoleDialogue",
    "ScenePackageDefinition",
    "ScenePackageError",
    "SymbolicIssuer",
    "TopicEffect",
    "scene_package_id",
    "select_dialogue_phase",
    "validate_scene_package",
]

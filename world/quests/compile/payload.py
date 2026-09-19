"""Durable-mirror payload codec for the compile boundary.

The single serialization/reconstruction pair for the generated-quest store:
``_compiled_to_payload`` converts one compiled aggregate into the JSON-safe
payload appended *before* any process-local registry is touched (design D2),
and ``payload_to_registrations`` reconstructs a stored payload back into the
closed runtime aggregate, rejecting anything that cannot be self-consistent
(design D3). ``_validate_restored_payload`` lives beside the reconstruction it
guards, keeping this module a leaf above the registration publishers.
"""

from dataclasses import asdict
from enum import Enum
from typing import Any

from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.quests.compile.contracts import (
    CompiledQuest,
    IssuanceDescriptor,
    QuestCompileError,
    StageNpcCharacterization,
    StageSpawnRequirement,
    _reject,
)
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
)
from world.rules.guild_offers import (
    ItemQuantity,
    QuestReward,
)
from world.rules.quest_issuance import (
    IssuerKeyError,
    Settlement,
    parse_issuer_key,
)


def _db_safe(value: Any) -> Any:
    """Convert enums and tuples in dataclass output to JSON-safe primitives.

    Mirrors ``world.lore.sync._db_safe`` (without importing that private
    helper): enums become their ``.value`` and tuples become lists, so the
    payload can be stored as plain JSON-safe data.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _db_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_db_safe(item) for item in value]
    if isinstance(value, list):
        return [_db_safe(item) for item in value]
    return value


def _compiled_to_payload(
    compiled: CompiledQuest,
) -> dict[str, Any]:
    """Serialize one compiled quest plus its issuance into a JSON-safe payload.

    The payload is the durable mirror of one ``register_generated_quest``
    publication: the definition, the issuance (issuer key, settlement, and
    reward), and the stage spawn requirements, all converted to plain
    JSON-safe values (enums to their ``.value``, tuples to lists).
    """
    return {
        "definition": _db_safe(asdict(compiled.definition)),
        "issuance": {
            "issuer_key": compiled.issuance.issuer_key,
            "settlement": compiled.issuance.settlement.value,
            "reward": _db_safe(asdict(compiled.reward)),
        },
        "requirements": [
            _db_safe(asdict(requirement))
            for requirement in compiled.stage_requirements
        ],
    }


def _locator_from_payload(data: dict[str, Any] | None) -> RoomLocator | None:
    if data is None:
        return None
    xyz = data["xyz"]
    return RoomLocator(
        kind=DestinationKind(data["kind"]),
        anchor_key=data["anchor_key"],
        xyz=None if xyz is None else tuple(xyz),
    )


def _objective_from_payload(data: dict[str, Any]) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind(data["kind"]),
        quantity=data["quantity"],
        monster_tier=data["monster_tier"],
        destination=_locator_from_payload(data["destination"]),
        requires_bound_targets=data["requires_bound_targets"],
        item_key=data["item_key"],
    )


def _stage_from_payload(data: dict[str, Any]) -> QuestStage:
    return QuestStage(
        index=data["index"],
        objective=_objective_from_payload(data["objective"]),
    )


def _characterization_from_payload(
    data: dict[str, Any] | None,
) -> StageNpcCharacterization | None:
    if data is None:
        return None
    if "title" not in data:
        raise QuestCompileError(
            "stored characterization lacks the required authored title field"
        )
    return StageNpcCharacterization(
        display_name=data["display_name"],
        title=data["title"],
        age=data["age"],
        apparent_age=data["apparent_age"],
        portrait_stable_key=data["portrait_stable_key"],
        background=data.get("background"),
        persona=tuple(tuple(pair) for pair in data.get("persona") or ()),
        combat_traits=tuple(data.get("combat_traits") or ()),
    )


def _requirement_from_payload(data: dict[str, Any]) -> StageSpawnRequirement:
    return StageSpawnRequirement(
        index=data["index"],
        objective_kind=ObjectiveKind(data["objective_kind"]),
        location=_locator_from_payload(data["location"]),
        archetype=data["archetype"],
        anchor_near=data["anchor_near"],
        scene_sentence=data["scene_sentence"],
        npc_reqs=tuple(tuple(entry) for entry in data["npc_reqs"]),
        characterizations=tuple(
            _characterization_from_payload(entry)
            for entry in data["characterizations"]
        ),
    )


def payload_to_registrations(
    payload: Any,
) -> CompiledQuest:
    """Reconstruct one stored payload into the closed runtime aggregate.

    The single reconstruction path for the durable mirror: every value is
    converted back (enums via their ``.value``, lists back to tuples), so the
    restored ``CompiledQuest`` is equal to the original and publishes through
    the same registration path. A malformed payload raises instead of being
    silently dropped (design D3).
    """
    definition_data = payload["definition"]
    definition = QuestDefinition(
        key=definition_data["key"],
        display_name=definition_data["display_name"],
        quest_type=QuestType(definition_data["quest_type"]),
        rank=definition_data["rank"],
        stages=tuple(_stage_from_payload(stage) for stage in definition_data["stages"]),
        deadline_hours=definition_data["deadline_hours"],
    )
    issuance_data = payload["issuance"]
    reward_data = issuance_data["reward"]
    reward = QuestReward(
        copper=reward_data["copper"],
        items=tuple(
            ItemQuantity(item["item_key"], item["quantity"])
            for item in reward_data["items"]
        ),
        merit=reward_data["merit"],
    )
    issuer_key = issuance_data["issuer_key"]
    settlement_value = issuance_data["settlement"]
    requirements = tuple(
        _requirement_from_payload(requirement)
        for requirement in payload["requirements"]
    )
    _validate_restored_payload(definition, issuer_key, settlement_value, reward, requirements)
    return CompiledQuest(
        definition=definition,
        reward=reward,
        issuance=IssuanceDescriptor(
            issuer_key=issuer_key,
            settlement=Settlement(settlement_value),
        ),
        stage_requirements=requirements,
    )


def _validate_restored_payload(
    definition: QuestDefinition,
    issuer_key: str,
    settlement: str,
    reward: QuestReward,
    requirements: tuple[StageSpawnRequirement, ...],
) -> None:
    """Reject a stored payload whose reconstructed values cannot be consistent.

    A payload is trusted only when it reconstructs to a closed, self-consistent
    registration: the issuance must parse against the shared issuer-key
    grammar and obey its namespace rules (a guild key names a registered
    branch; a character key settles automatically and grants zero merit), the
    settlement must be a closed mode, and every spawn requirement must sit at
    its own position with the objective kind of the definition stage it
    describes. The issuance binds the exact definition structurally: the
    payload carries one definition and its one issuance together. Corrupt or
    schema-drifted payloads fail loudly here (design D3) instead of silently
    registering a mismatched pair or leaving the SceneBuilder to fail
    mid-game.
    """
    try:
        parsed = parse_issuer_key(issuer_key)
    except IssuerKeyError as error:
        _reject(f"stored payload issuance key is malformed: {error}")
    try:
        settlement_mode = Settlement(settlement)
    except ValueError as error:
        _reject(f"stored payload settlement {settlement!r} is unknown: {error}")
    if parsed.namespace == "guild":
        if parsed.remainder not in GUILD_BRANCH_REGISTRY:
            _reject(f"stored payload names unknown guild branch {parsed.remainder!r}")
        if settlement_mode is not Settlement.COUNTER:
            _reject(
                f"stored payload guild issuance must settle by counter, "
                f"got {settlement_mode.value!r}"
            )
    else:
        if settlement_mode is not Settlement.AUTO:
            _reject(
                f"stored payload private commission {issuer_key!r} must "
                f"settle automatically, got {settlement_mode.value!r}"
            )
        if reward.merit != 0:
            _reject(
                f"stored payload private commission {issuer_key!r} grants "
                f"guild merit {reward.merit}"
            )
    for position, requirement in enumerate(requirements):
        if requirement.index != position:
            _reject(
                f"stored payload requirement {position} declares index "
                f"{requirement.index}; indices must match their position"
            )
        if not (0 <= requirement.index < len(definition.stages)):
            _reject(
                f"stored payload requirement {requirement.index} has no "
                f"matching stage in definition {definition.key!r}"
            )
        if requirement.objective_kind is not definition.stages[requirement.index].objective.kind:
            _reject(
                f"stored payload requirement {requirement.index} declares "
                f"objective kind {requirement.objective_kind.value!r}, but "
                f"definition {definition.key!r} stage {requirement.index} is "
                f"{definition.stages[requirement.index].objective.kind.value!r}"
            )

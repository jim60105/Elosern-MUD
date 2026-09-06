"""Shared fixtures for quest-runtime tests (registry isolation and builders)."""

from dataclasses import replace
from typing import Any

from world.quests.catalog import INTRODUCTORY_HUNT, register_catalog
from world.quests.compile import SCENE_REQUIREMENT_REGISTRY
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
    register_quest_definition,
)
from world.rules.guild_offers import GUILD_OFFER_REGISTRY, QuestReward
from world.rules.quest_issuance import (
    QUEST_ISSUANCE_REGISTRY,
    QuestIssuance,
    Settlement,
    npc_issuer_key,
    register_quest_issuance,
)
from world.quests.runtime import QuestRecord, accept_quest


class QuestRegistryIsolation:
    """Snapshot and restore the process-global quest registries.

    ``QUEST_DEFINITION_REGISTRY`` and ``QUEST_ISSUANCE_REGISTRY`` are
    module-global and shared across the whole test process, so every quest
    test restores whatever it found rather than clearing state other tests
    (or the catalog) rely on.
    """

    def setUp(self):
        super().setUp()
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._issuance_items = list(QUEST_ISSUANCE_REGISTRY.items())

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        QUEST_ISSUANCE_REGISTRY.clear()
        QUEST_ISSUANCE_REGISTRY.update(self._issuance_items)
        super().tearDown()


#: The process-global registries shared across the whole test process.
_PROCESS_GLOBAL_REGISTRIES = (
    QUEST_DEFINITION_REGISTRY,
    GUILD_OFFER_REGISTRY,
    SCENE_REQUIREMENT_REGISTRY,
    QUEST_ISSUANCE_REGISTRY,
)


class RegistryIsolationMixin:
    """Snapshot and restore the four process-global quest registries.

    ``QUEST_DEFINITION_REGISTRY``, ``GUILD_OFFER_REGISTRY``,
    ``SCENE_REQUIREMENT_REGISTRY``, and ``QUEST_ISSUANCE_REGISTRY`` are
    module-global and shared across the whole test process. The snapshot is
    taken in ``setUp`` and the restoration is registered via ``addCleanup``
    immediately, so even a ``setUp`` that raises after mutating cannot leak
    registry state into later tests (``tearDown`` is skipped when ``setUp``
    fails; cleanups are not).
    """

    def setUp(self):
        super().setUp()
        snapshots = tuple(dict(registry) for registry in _PROCESS_GLOBAL_REGISTRIES)
        self.addCleanup(self._restore_process_global_registries, snapshots)

    def _restore_process_global_registries(self, snapshots):
        for registry, snapshot in zip(_PROCESS_GLOBAL_REGISTRIES, snapshots):
            registry.clear()
            registry.update(snapshot)


def defeat(tier="low", *, bound=False, quantity=1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.DEFEAT,
        quantity=quantity,
        monster_tier=None if bound else tier,
        requires_bound_targets=bound,
    )


def reach(destination: RoomLocator | None = None, quantity=1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.REACH,
        quantity=quantity,
        destination=destination,
    )


def escort(destination: RoomLocator | None = None) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.ESCORT,
        destination=destination,
    )


def acquire(item_key: str, quantity: int = 1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.ACQUIRE,
        quantity=quantity,
        item_key=item_key,
    )


def deliver(item_key: str, quantity: int = 1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.DELIVER,
        quantity=quantity,
        item_key=item_key,
        requires_bound_targets=True,
    )


def anchor_locator() -> RoomLocator:
    return RoomLocator(DestinationKind.ANCHOR, anchor_key="capital_altoria")


def grid_locator(x: int = 2, y: int = 2) -> RoomLocator:
    return RoomLocator(DestinationKind.GRID, xyz=(x, y, "capital_altoria"))


def bound_instance_locator() -> RoomLocator:
    return RoomLocator(DestinationKind.BOUND_INSTANCE)


def quest(
    key: str,
    stages: tuple[QuestStage, ...] | None = None,
    *,
    quest_type: QuestType = QuestType.DEFEAT,
    rank: str = "F",
    deadline_hours: int | None = None,
) -> QuestDefinition:
    if stages is None:
        stages = (QuestStage(index=0, objective=defeat()),)
    return QuestDefinition(
        key=key,
        display_name=f"測試任務 {key}",
        quest_type=quest_type,
        rank=rank,
        stages=stages,
        deadline_hours=deadline_hours,
    )


def register(definition: QuestDefinition) -> QuestDefinition:
    """Register ``definition`` and reload it from the registry for identity."""
    register_quest_definition(definition)
    return QUEST_DEFINITION_REGISTRY[definition.key]


def register_catalog_once() -> None:
    """Register the shipped catalog definitions (idempotent snapshot-safe)."""
    if "introductory_hunt" not in QUEST_DEFINITION_REGISTRY:
        register_catalog()


def intro_hunt_key() -> str:
    return INTRODUCTORY_HUNT.key


#: The shared private commission every issuer-agnostic test acceptance rides.
#: It resolves through ``resolve_issuance`` like any real issuance, so the
#: resolve-before-create rule is exercised, but no test's board or counter
#: assertions depend on it (``QUEST_ISSUANCE_REGISTRY`` is not read by any
#: board or settlement surface this change touches).
TEST_ISSUER_KEY = npc_issuer_key(content_key="test_commission")


def _ensure_test_issuance(definition_key: str) -> str:
    """Guarantee the shared test commission exists for ``definition_key``."""
    if (definition_key, TEST_ISSUER_KEY) not in QUEST_ISSUANCE_REGISTRY:
        register_quest_issuance(
            QuestIssuance(
                definition_key=definition_key,
                issuer_key=TEST_ISSUER_KEY,
                reward=QuestReward(copper=1, items=(), merit=0),
                settlement=Settlement.COUNTER,
            )
        )
    return TEST_ISSUER_KEY


def accept(actor: Any, definition: QuestDefinition | str) -> QuestRecord:
    """Accept ``definition`` under the shared test commission.

    The quest-runtime tests care about record lifecycle, not which commission
    backs the acceptance; this keeps their call sites one line while still
    naming a registered issuance, as ``accept_quest`` now requires.
    """
    key = definition.key if isinstance(definition, QuestDefinition) else str(definition)
    return accept_quest(actor, key, _ensure_test_issuance(key))


# The shared automatic commission: same registry-backed resolution as the
# counter fixture, but completing records under it settle on the spot
# (quest-auto-settlement). Reward defaults to copper only; ``accept_auto``
# forwards a custom reward for item-bearing scenarios.
AUTO_ISSUER_KEY = npc_issuer_key(content_key="test_auto_commission")


def register_auto_issuance(
    definition_key: str, reward: QuestReward | None = None
) -> str:
    """Guarantee an ``AUTO``-settled commission exists for ``definition_key``."""
    if (definition_key, AUTO_ISSUER_KEY) not in QUEST_ISSUANCE_REGISTRY:
        register_quest_issuance(
            QuestIssuance(
                definition_key=definition_key,
                issuer_key=AUTO_ISSUER_KEY,
                reward=(
                    reward
                    if reward is not None
                    else QuestReward(copper=25, items=(), merit=0)
                ),
                settlement=Settlement.AUTO,
            )
        )
    return AUTO_ISSUER_KEY


def accept_auto(
    actor: Any,
    definition: QuestDefinition | str,
    reward: QuestReward | None = None,
) -> QuestRecord:
    """Accept ``definition`` under the shared automatic commission."""
    key = definition.key if isinstance(definition, QuestDefinition) else str(definition)
    register_auto_issuance(key, reward)
    return accept_quest(actor, key, AUTO_ISSUER_KEY)
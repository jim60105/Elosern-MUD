"""Unit tests for deterministic quest definitions (tasks 2.1-2.6)."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestDefinitionError,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
    register_quest_definition,
)

from ._fixtures import (
    QuestRegistryIsolation,
    anchor_locator,
    bound_instance_locator,
    defeat,
    escort,
    grid_locator,
    quest,
    reach,
    register,
)


class DefinitionRegistrationTests(QuestRegistryIsolation, unittest.TestCase):
    def test_explicit_stage_indices_are_inspectable(self):
        stages = (
            QuestStage(index=0, objective=defeat()),
            QuestStage(index=2, objective=defeat()),
        )
        explicit = quest("indices", stages=stages)
        self.assertEqual([stage.index for stage in explicit.stages], [0, 2])
        with self.assertRaises(QuestDefinitionError):
            register(explicit)
        self.assertNotIn("indices", QUEST_DEFINITION_REGISTRY)

    @covers_requirement("quest-blueprint::quest-classifications-and-objective-mechanics-are-separate-closed-vocabularies")
    def test_valid_objective_shapes_register(self):
        quests = (
            quest("tier", stages=(QuestStage(0, defeat(tier="low")),)),
            quest("bound", stages=(QuestStage(0, defeat(bound=True)),)),
            quest(
                "reach-anchor",
                quest_type=QuestType.EXPLORE,
                stages=(QuestStage(0, reach(anchor_locator())),),
            ),
            quest(
                "reach-grid",
                quest_type=QuestType.EXPLORE,
                stages=(QuestStage(0, reach(grid_locator(2, 2))),),
            ),
            quest(
                "reach-instance",
                quest_type=QuestType.EXPLORE,
                stages=(QuestStage(0, reach(bound_instance_locator())),),
            ),
            quest(
                "escort-anchor",
                quest_type=QuestType.ESCORT,
                stages=(QuestStage(0, escort(anchor_locator())),),
            ),
            quest(
                "emergency-defeat",
                quest_type=QuestType.EMERGENCY,
                stages=(QuestStage(0, defeat(tier="mid")),),
            ),
        )
        for candidate in quests:
            with self.subTest(key=candidate.key):
                register(candidate)
        for candidate in quests:
            self.assertIs(QUEST_DEFINITION_REGISTRY[candidate.key], candidate)

    def test_empty_stages_rejected(self):
        with self.assertRaises(QuestDefinitionError):
            register(quest("empty", stages=()))

    def test_non_contiguous_and_nonzero_start_indices_rejected(self):
        invalid = (
            quest("gap", stages=(QuestStage(0, defeat()), QuestStage(2, defeat()))),
            quest("zero-start", stages=(QuestStage(2, defeat()), QuestStage(3, defeat()))),
        )
        for candidate in invalid:
            with self.subTest(key=candidate.key):
                with self.assertRaises(QuestDefinitionError):
                    register(candidate)
                self.assertNotIn(candidate.key, QUEST_DEFINITION_REGISTRY)

    def test_non_positive_quantities_rejected(self):
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                candidate = quest(
                    f"zero-quantity-{quantity}",
                    stages=(QuestStage(0, defeat(quantity=quantity)),),
                )
                with self.assertRaises(QuestDefinitionError):
                    register(candidate)

    def test_defeat_selector_validation(self):
        invalid = (
            ("no-selector", QuestObjective(kind=ObjectiveKind.DEFEAT, quantity=1)),
            (
                "both",
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    monster_tier="low",
                    requires_bound_targets=True,
                ),
            ),
            (
                "unknown-tier",
                QuestObjective(kind=ObjectiveKind.DEFEAT, monster_tier="legendary"),
            ),
            (
                "with-destination",
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    monster_tier="low",
                    destination=anchor_locator(),
                ),
            ),
        )
        for key, objective in invalid:
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))

    def test_reach_and_escort_require_destination_and_no_defeat_selector(self):
        invalid = (
            ("reach-no-dest", reach(None)),
            (
                "reach-with-tier",
                QuestObjective(
                    kind=ObjectiveKind.REACH,
                    monster_tier="low",
                    destination=bound_instance_locator(),
                ),
            ),
            ("escort-no-dest", escort(None)),
        )
        for key, objective in invalid:
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))

    @covers_requirement("quest-blueprint::reach-and-escort-objectives-accept-only-quantity-one")
    def test_reach_and_escort_quantity_must_be_exactly_one(self):
        invalid = (
            (
                "reach-quantity-2",
                QuestType.EXPLORE,
                QuestObjective(
                    kind=ObjectiveKind.REACH,
                    quantity=2,
                    destination=anchor_locator(),
                ),
            ),
            (
                "escort-quantity-2",
                QuestType.ESCORT,
                QuestObjective(
                    kind=ObjectiveKind.ESCORT,
                    quantity=2,
                    destination=anchor_locator(),
                ),
            ),
        )
        for key, quest_type, objective in invalid:
            with self.subTest(key=key):
                with self.assertRaisesRegex(
                    QuestDefinitionError, "quantity must be exactly 1"
                ):
                    register(
                        quest(key, quest_type=quest_type, stages=(QuestStage(0, objective),))
                    )
                self.assertNotIn(key, QUEST_DEFINITION_REGISTRY)
        register(
            quest(
                "reach-quantity-1",
                quest_type=QuestType.EXPLORE,
                stages=(QuestStage(0, reach(anchor_locator())),),
            )
        )
        self.assertIn("reach-quantity-1", QUEST_DEFINITION_REGISTRY)

    def test_placed_anchor_is_structurally_valid_without_a_room_dbref(self):
        self.assertIn("capital_altoria", ANCHOR_PLACEMENT_REGISTRY)
        register(quest("anchor-valid", stages=(QuestStage(0, reach(anchor_locator())),)))
        self.assertIn("anchor-valid", QUEST_DEFINITION_REGISTRY)

    @covers_requirement("quest-blueprint::destinations-distinguish-permanent-locations-from-future-bound-instances")
    def test_lore_known_but_unplaced_anchor_is_rejected(self):
        self.assertNotIn("village_fionnen", ANCHOR_PLACEMENT_REGISTRY)
        unplaced = QuestDefinition(
            key="anchor-unplaced",
            display_name="未落錨",
            quest_type=QuestType.EXPLORE,
            rank="F",
            stages=(
                QuestStage(
                    0,
                    reach(RoomLocator(DestinationKind.ANCHOR, anchor_key="village_fionnen")),
                ),
            ),
        )
        with self.assertRaises(QuestDefinitionError) as caught:
            register(unplaced)
        self.assertIn("village_fionnen", str(caught.exception))
        self.assertNotIn("anchor-unplaced", QUEST_DEFINITION_REGISTRY)

    def test_ambiguous_and_malformed_locators_rejected(self):
        invalid = (
            ("anchor-plus-xyz", RoomLocator(DestinationKind.ANCHOR, anchor_key="capital_altoria", xyz=(2, 2, "capital_altoria"))),
            ("bound-with-anchor", RoomLocator(DestinationKind.BOUND_INSTANCE, anchor_key="capital_altoria")),
            ("bound-with-xyz", RoomLocator(DestinationKind.BOUND_INSTANCE, xyz=(2, 2, "capital_altoria"))),
            ("grid-with-anchor", RoomLocator(DestinationKind.GRID, anchor_key="capital_altoria", xyz=(2, 2, "capital_altoria"))),
            ("grid-unknown-z", RoomLocator(DestinationKind.GRID, xyz=(2, 2, "not_a_map"))),
            ("grid-bad-types", RoomLocator(DestinationKind.GRID, xyz=("x", 2, "capital_altoria"))),
            ("grid-short-tuple", RoomLocator(kind=DestinationKind.GRID, xyz=(2, 2))),
        )
        for key, destination in invalid:
            with self.subTest(key=key):
                candidate = quest(key, stages=(QuestStage(0, reach(destination)),))
                with self.assertRaises(QuestDefinitionError):
                    register(candidate)
                self.assertNotIn(key, QUEST_DEFINITION_REGISTRY)

    def test_wilderness_destination_cannot_be_declared(self):
        self.assertNotIn(
            "wilderness",
            {destination.value for destination in DestinationKind},
        )
        candidate = quest(
            "wilderness-dest",
            stages=(
                QuestStage(
                    0,
                    reach(RoomLocator(DestinationKind.GRID, xyz=(30, 60, "wilderness"))),
                ),
            ),
        )
        with self.assertRaises(QuestDefinitionError):
            register(candidate)

    @covers_requirement("quest-blueprint::registration-validates-every-runtime-critical-objective-field")
    def test_deadline_none_has_one_meaning_and_invalid_values_rejected(self):
        register(quest("no-deadline", deadline_hours=None))
        self.assertIsNone(QUEST_DEFINITION_REGISTRY["no-deadline"].deadline_hours)
        for value in (0, -1, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(f"bad-deadline-{value!r}", deadline_hours=value))

    def test_equal_registration_is_idempotent_no_op(self):
        first = quest("dup", deadline_hours=24)
        register(first)
        before_count = len(QUEST_DEFINITION_REGISTRY)
        register(quest("dup", deadline_hours=24))
        self.assertEqual(len(QUEST_DEFINITION_REGISTRY), before_count)
        self.assertIs(QUEST_DEFINITION_REGISTRY["dup"], first)

    def test_conflicting_registration_is_rejected_keeping_original(self):
        first = quest("conflict", deadline_hours=24)
        register(first)
        with self.assertRaises(QuestDefinitionError) as caught:
            register(quest("conflict", deadline_hours=48))
        self.assertIn("already registered", str(caught.exception))
        self.assertIs(QUEST_DEFINITION_REGISTRY["conflict"], first)

    def test_raw_mapping_and_ai_shaped_input_never_enter_registry(self):
        before = dict(QUEST_DEFINITION_REGISTRY)
        raw_ai_shape = {
            "name": "範例任務",
            "type": "探索",
            "rank": "D",
            "stages": [{"index": 0, "objective": {"kind": "reach_location"}}],
            "reward": {"copper": 3000},
            "failure": {"deadline_hours": 72},
        }
        for value in (raw_ai_shape, {"key": "dict", "stages": []}, "not-a-definition"):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(QuestDefinitionError):
                    register_quest_definition(value)  # type: ignore[arg-type]
        self.assertEqual(dict(QUEST_DEFINITION_REGISTRY), before)

    def test_registered_content_is_deeply_immutable(self):
        candidate = quest(
            "immutable",
            stages=(QuestStage(0, reach(grid_locator(2, 2))),),
        )
        register(candidate)
        registered = QUEST_DEFINITION_REGISTRY["immutable"]
        with self.assertRaises(Exception):
            registered.stages[0].objective.destination.xyz = (3, 3, "capital_altoria")  # type: ignore[misc]
        with self.assertRaises(Exception):
            registered.stages = registered.stages[:1]  # type: ignore[misc]
        self.assertIsInstance(registered.stages, tuple)
        self.assertIsInstance(registered.stages[0].objective.destination.xyz, tuple)

    @covers_requirement("quest-blueprint::questdefinition-is-the-immutable-deterministic-input-to-quest-runtime")
    def test_registered_definition_is_distinct_from_future_ai_blueprint(self):
        # The runtime registry is keyed by QuestDefinition values only; no
        # AI proposal contract can be attached to a registered entry.
        candidate = quest("closed-type", stages=(QuestStage(0, defeat()),))
        register(candidate)
        self.assertIsInstance(QUEST_DEFINITION_REGISTRY["closed-type"], QuestDefinition)
        self.assertNotIn("location_req", vars(QUEST_DEFINITION_REGISTRY["closed-type"]))


class CatalogTests(QuestRegistryIsolation, unittest.TestCase):
    @covers_requirement("quest-blueprint::the-hand-written-catalog-is-idempotent-and-provides-an-offline-quest")
    def test_catalog_declares_an_offline_defeat_hunt(self):
        from world.quests.catalog import INTRODUCTORY_HUNT, register_catalog

        register_catalog()
        registered = QUEST_DEFINITION_REGISTRY[INTRODUCTORY_HUNT.key]
        self.assertEqual(registered.stages[0].objective.kind, ObjectiveKind.DEFEAT)
        self.assertEqual(registered.stages[0].objective.monster_tier, "low")
        self.assertEqual(registered.deadline_hours, None)

    def test_catalog_sync_is_repeatable_and_creates_no_records(self):
        from world.quests.catalog import register_catalog

        register_catalog()
        first = list(QUEST_DEFINITION_REGISTRY.items())
        register_catalog()
        second = list(QUEST_DEFINITION_REGISTRY.items())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

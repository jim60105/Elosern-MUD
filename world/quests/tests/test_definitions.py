"""Data-contract test: quest definition catalog contract
Unit tests for deterministic quest definitions (tasks 2.1-2.6)."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    SYNTH_REGIONS,
    make_monster_species,
    make_monster_variant,
    synthetic_registries,
)
from world.quests.definitions import (
    DestinationKind,
    MAX_DEFINITION_PROSE_LENGTH,
    MAX_DEFINITION_PROSE_TOTAL,
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

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_quest_objective_naming_retired_item_is_rejected(self):
        acquire_bad = quest(
            "bad-acquire",
            stages=(
                QuestStage(
                    0,
                    QuestObjective(
                        kind=ObjectiveKind.ACQUIRE,
                        item_key="synthetic_retired_item",
                        quantity=1,
                    ),
                ),
            ),
        )
        with self.assertRaises(QuestDefinitionError) as caught:
            register(acquire_bad)
        self.assertIn("synthetic_retired_item", str(caught.exception))

        deliver_bad = quest(
            "bad-deliver",
            stages=(
                QuestStage(
                    0,
                    QuestObjective(
                        kind=ObjectiveKind.DELIVER,
                        item_key="synthetic_retired_item",
                        quantity=1,
                        destination=None,
                        requires_bound_targets=True,
                    ),
                ),
            ),
        )
        with self.assertRaises(QuestDefinitionError) as caught:
            register(deliver_bad)
        self.assertIn("synthetic_retired_item", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_completed_quest_retirement_leaves_registration_valid(self):
        valid_quest = quest(
            "valid-acquire-test",
            stages=(
                QuestStage(
                    0,
                    QuestObjective(
                        kind=ObjectiveKind.ACQUIRE,
                        item_key="healing_potion",
                        quantity=1,
                    ),
                ),
            ),
        )
        register(valid_quest)
        self.assertIn("valid-acquire-test", QUEST_DEFINITION_REGISTRY)

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


# The regional species-hunt selector and the two authored prose fields run
# entirely against the kit's synthetic regions, species, and variants: every
# accepted and rejected key below is a kit row or an invented key, never a
# shipped one.
_HUNT_SPECIES = next(iter(SYNTH_MONSTER_SPECIES))
_HUNT_VARIANTS = tuple(
    key
    for key, row in SYNTH_MONSTER_VARIANTS.items()
    if row.species_key == _HUNT_SPECIES
)
_HUNT_ORDINARY = next(
    key
    for key in _HUNT_VARIANTS
    if SYNTH_MONSTER_VARIANTS[key].ordinary_variant
)
_HUNT_STRONGER = next(
    key
    for key in _HUNT_VARIANTS
    if not SYNTH_MONSTER_VARIANTS[key].ordinary_variant
)
_HUNT_REGION = next(iter(SYNTH_REGIONS))
_ABSENT_REGION = "t_absent_region"
_ABSENT_SPECIES = "t_absent_species"
_ABSENT_VARIANT = "t_absent_variant"
_FOREIGN_SPECIES = "t_foreign_species"
_FOREIGN_VARIANT = "t_foreign_variant"

_FOREIGN_SPECIES_ROW = make_monster_species(
    _FOREIGN_SPECIES,
    default_variant_key=_FOREIGN_VARIANT,
    habitat_tags=(_HUNT_REGION,),
)
_FOREIGN_VARIANT_ROW = make_monster_variant(
    _FOREIGN_VARIANT,
    species_key=_FOREIGN_SPECIES,
    ordinary_variant=True,
)
_HUNT_EXTRA = {
    "monster_species": {_FOREIGN_SPECIES: _FOREIGN_SPECIES_ROW},
    "monster_variants": {_FOREIGN_VARIANT: _FOREIGN_VARIANT_ROW},
}

#: The authored prose the hunt fixtures carry. Neither field derives from the
#: other and neither participates in any completion rule.
_RATIONALE = "合成評價理由：合成丘陵的合成強勢型會成群出現，獨行者風險偏高。"
_FLAVOR = "合成背景：合成議會急需合成羽飾，合成獵場的合成喧鬧因此而起。"


def _hunt(
    *,
    region_key: str | None = _HUNT_REGION,
    species_key: str | None = _HUNT_SPECIES,
    countable: tuple[str, ...] | object = (_HUNT_ORDINARY, _HUNT_STRONGER),
    quantity: int = 2,
    **extra: object,
) -> QuestObjective:
    """One synthetic regional species hunt objective (keyword-assembled)."""
    return QuestObjective(
        kind=ObjectiveKind.DEFEAT,
        quantity=quantity,
        region_key=region_key,
        species_key=species_key,
        countable_variant_keys=countable,  # type: ignore[arg-type]
        **extra,  # type: ignore[arg-type]
    )


@synthetic_registries(
    "monster_species",
    "monster_variants",
    "regions",
    extra=_HUNT_EXTRA,
)
class SpeciesHuntDefinitionTests(QuestRegistryIsolation, unittest.TestCase):
    """Registration validation of the species-hunt selector and prose fields."""

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_a_complete_hunt_registers_immutably(self):
        candidate = quest(
            "hunt-valid",
            stages=(QuestStage(0, _hunt()),),
            rating_rationale_zh=_RATIONALE,
            background_flavor_zh=_FLAVOR,
        )
        register(candidate)
        registered = QUEST_DEFINITION_REGISTRY["hunt-valid"]
        objective = registered.stages[0].objective
        self.assertEqual(objective.region_key, _HUNT_REGION)
        self.assertEqual(objective.species_key, _HUNT_SPECIES)
        self.assertEqual(
            objective.countable_variant_keys, (_HUNT_ORDINARY, _HUNT_STRONGER)
        )
        self.assertIsInstance(objective.countable_variant_keys, tuple)
        with self.assertRaises(Exception):
            objective.countable_variant_keys = ()  # type: ignore[misc]

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_partial_hunt_selectors_are_rejected(self):
        partial = (
            ("species-without-region", _hunt(region_key=None)),
            ("region-without-species", _hunt(species_key=None)),
            ("no-countable-variants", _hunt(countable=())),
            (
                "variants-without-species",
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    region_key=_HUNT_REGION,
                    countable_variant_keys=(_HUNT_ORDINARY,),
                ),
            ),
        )
        for key, objective in partial:
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))
                self.assertNotIn(key, QUEST_DEFINITION_REGISTRY)

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_unknown_registry_keys_and_foreign_variants_are_rejected(self):
        invalid = (
            ("unknown-region", _hunt(region_key=_ABSENT_REGION)),
            ("unknown-species", _hunt(species_key=_ABSENT_SPECIES)),
            (
                "unknown-variant",
                _hunt(countable=(_HUNT_ORDINARY, _ABSENT_VARIANT)),
            ),
            (
                "foreign-variant",
                _hunt(countable=(_HUNT_ORDINARY, _FOREIGN_VARIANT)),
            ),
            (
                "duplicate-variant",
                _hunt(countable=(_HUNT_ORDINARY, _HUNT_ORDINARY)),
            ),
            ("non-tuple-variants", _hunt(countable=[_HUNT_ORDINARY])),
        )
        for key, objective in invalid:
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))
                self.assertNotIn(key, QUEST_DEFINITION_REGISTRY)

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_a_hunt_without_an_ordinary_variant_is_rejected(self):
        # Without an ordinary baseline variant the "guarantee ordinary targets"
        # contract could not be expressed at acceptance.
        with self.assertRaises(QuestDefinitionError):
            register(
                quest(
                    "hunt-stronger-only",
                    stages=(QuestStage(0, _hunt(countable=(_HUNT_STRONGER,))),),
                )
            )
        self.assertNotIn("hunt-stronger-only", QUEST_DEFINITION_REGISTRY)

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_two_selector_families_at_once_are_rejected(self):
        combined = (
            (
                "hunt-and-tier",
                _hunt(monster_tier=SYNTH_MONSTER_TIERS["t_faint"].key),
            ),
            ("hunt-and-bound", _hunt(requires_bound_targets=True)),
        )
        for key, objective in combined:
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))
                self.assertNotIn(key, QUEST_DEFINITION_REGISTRY)

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_display_names_are_never_selectors(self):
        species_name = SYNTH_MONSTER_SPECIES[_HUNT_SPECIES].display_name_zh
        region_name = SYNTH_REGIONS[_HUNT_REGION].display_name_zh
        for key, objective in (
            ("species-name", _hunt(species_key=species_name)),
            ("region-name", _hunt(region_key=region_name)),
            (
                "variant-name",
                _hunt(
                    countable=(
                        _HUNT_ORDINARY,
                        SYNTH_MONSTER_VARIANTS[_HUNT_STRONGER].display_name_zh,
                    )
                ),
            ),
        ):
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))

    @covers_requirement(
        "quest-blueprint::registration-validates-every-runtime-critical-objective-field"
    )
    def test_hunt_fields_are_rejected_on_other_objective_kinds(self):
        invalid = (
            (
                "reach-with-hunt",
                QuestObjective(
                    kind=ObjectiveKind.REACH,
                    region_key=_HUNT_REGION,
                    species_key=_HUNT_SPECIES,
                    countable_variant_keys=(_HUNT_ORDINARY,),
                    destination=bound_instance_locator(),
                ),
            ),
            (
                "acquire-with-hunt",
                QuestObjective(
                    kind=ObjectiveKind.ACQUIRE,
                    quantity=1,
                    region_key=_HUNT_REGION,
                    species_key=_HUNT_SPECIES,
                    countable_variant_keys=(_HUNT_ORDINARY,),
                    item_key=next(iter(SYNTH_ITEMS)),
                ),
            ),
        )
        for key, objective in invalid:
            with self.subTest(key=key):
                with self.assertRaises(QuestDefinitionError):
                    register(quest(key, stages=(QuestStage(0, objective),)))

    @covers_requirement(
        "quest-blueprint::questdefinition-is-the-immutable-deterministic-input-to-quest-runtime"
    )
    def test_grade_rationale_and_flavor_stay_three_separate_fields(self):
        stronger = SYNTH_MONSTER_VARIANTS[_HUNT_STRONGER]
        # The variant's individual danger grade never becomes the quest grade.
        self.assertIsNotNone(stronger.danger_grade)
        candidate = quest(
            "hunt-prose",
            stages=(QuestStage(0, _hunt()),),
            rank="F",
            rating_rationale_zh=_RATIONALE,
            background_flavor_zh=_FLAVOR,
        )
        register(candidate)
        registered = QUEST_DEFINITION_REGISTRY["hunt-prose"]
        self.assertEqual(registered.rank, "F")
        self.assertNotEqual(stronger.danger_grade, registered.rank)
        self.assertEqual(registered.rating_rationale_zh, _RATIONALE)
        self.assertEqual(registered.background_flavor_zh, _FLAVOR)
        self.assertNotEqual(registered.rating_rationale_zh, registered.background_flavor_zh)
        self.assertNotIn(registered.rank, registered.rating_rationale_zh)
        # A definition may carry either prose field alone (and none of them).
        for key, overrides in (
            ("prose-rationale-only", {"rating_rationale_zh": _RATIONALE}),
            ("prose-flavor-only", {"background_flavor_zh": _FLAVOR}),
            ("prose-absent", {}),
        ):
            with self.subTest(key=key):
                candidate = quest(
                    key, stages=(QuestStage(0, _hunt()),), **overrides
                )
                register(candidate)
                stored = QUEST_DEFINITION_REGISTRY[key]
                self.assertEqual(stored.rating_rationale_zh, overrides.get("rating_rationale_zh"))
                self.assertEqual(stored.background_flavor_zh, overrides.get("background_flavor_zh"))

    @covers_requirement(
        "quest-blueprint::questdefinition-is-the-immutable-deterministic-input-to-quest-runtime"
    )
    def test_prose_fields_are_bounded_traditional_chinese(self):
        invalid = (
            ("prose-too-long", "評" * 501),
            ("prose-not-a-string", 5),
            ("prose-empty", ""),
            ("prose-ascii-only", "synthetic rationale"),
        )
        for key, value in invalid:
            for field in ("rating_rationale_zh", "background_flavor_zh"):
                with self.subTest(key=key, field=field):
                    with self.assertRaises(QuestDefinitionError):
                        register(
                            quest(
                                f"{key}-{field}",
                                stages=(QuestStage(0, _hunt()),),
                                **{field: value},
                            )
                        )

    @covers_requirement(
        "quest-blueprint::questdefinition-is-the-immutable-deterministic-input-to-quest-runtime"
    )
    def test_the_combined_prose_budget_is_enforced(self):
        # Two individually legal fields can still overflow the rendered detail
        # the frozen web panel carries, so the pair is bounded together.
        over = MAX_DEFINITION_PROSE_TOTAL // 2 + 1
        with self.assertRaises(QuestDefinitionError):
            register(
                quest(
                    "prose-budget-over",
                    stages=(QuestStage(0, _hunt()),),
                    rating_rationale_zh="評" * over,
                    background_flavor_zh="事" * over,
                )
            )
        self.assertNotIn("prose-budget-over", QUEST_DEFINITION_REGISTRY)
        register(
            quest(
                "prose-budget-ok",
                stages=(QuestStage(0, _hunt()),),
                rating_rationale_zh="評" * over,
                background_flavor_zh="事" * (MAX_DEFINITION_PROSE_TOTAL - over),
            )
        )
        stored = QUEST_DEFINITION_REGISTRY["prose-budget-ok"]
        self.assertEqual(
            len(stored.rating_rationale_zh) + len(stored.background_flavor_zh),
            MAX_DEFINITION_PROSE_TOTAL,
        )
        self.assertLessEqual(MAX_DEFINITION_PROSE_LENGTH, MAX_DEFINITION_PROSE_TOTAL)


if __name__ == "__main__":
    unittest.main()

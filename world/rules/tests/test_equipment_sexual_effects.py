"""Equipment sexual-effects tests (P4).

Covers the pure effective-exposure read-time overlay (clamp, fail-closed
malformed storage, handler-free purity, the world-free shared reader and the
loader import edge), the both-contexts condition parity for the exposure
slot, the ``pleasure_percent`` term of the pleasure funnel (golden pairs,
ladder independence, the live cast, and the combat-bundle key-set lock), and
the stored-state-immunity discipline (act progression ignores what is worn,
no field-change event from toggling, read-model label, and the structural
stored/effective consumer allowlist).
"""

from tools.spec_traceability import covers_requirement

import ast
import unittest
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import EXPOSURE_LEVELS
from world.rules.combat_modifiers import (
    _build_context,
    build_no_create_condition_context,
    evaluate_combat_modifiers,
    evaluate_combat_modifiers_no_create,
)
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import (
    effective_exposure,
    equipment_adjustments,
    equipment_exposure_bias,
    equipment_pleasure_gain,
)
from world.rules.sexual_act_effects import compute_pleasure_gain
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.rules.status_query import build_character_read_model, build_status_read_model
from world.rules.stored_sexual_reads import StoredLevel

_ROOT = Path(__file__).resolve().parents[3]
_PRODUCTION_ROOTS = ("commands", "server", "typeclasses", "web", "world")


def _worn(entity, *, armor=None, accessories=()) -> None:
    """Write raw equipment storage directly onto a fixture entity."""
    entity.db.equipment = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": armor,
        "accessories": list(accessories),
    }


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.db.equipment = None
    player.db.inventory = []
    return player


def _wear(entity, *item_keys: str):
    entity.db.inventory = list(item_keys)
    for item_key in item_keys:
        result = toggle_equipment(entity, item_key)
        assert result.outcome == "success", (item_key, result.reason)
    return entity


def _stored_exposure_ordinal(entity) -> int | None:
    """Raw stored exposure ordinal straight from attribute storage."""
    traits = entity.attributes.get("sexual_traits", default=None, category="traits")
    # Evennia persists the handler record as a _SaverDict, which is a Mapping
    # but not a dict subclass.
    if not isinstance(traits, Mapping) or "exposure" not in traits:
        return None
    return traits["exposure"]["value"]


class StoredLevelSemanticsTests(unittest.TestCase):
    """The immutable ordinal view the context builders share."""

    @covers_requirement(
        "combat-modifier-table::condition-contexts-match-on-effective-exposure"
    )
    def test_comparisons_match_ordered_level_trait_parity(self):
        high = StoredLevel(EXPOSURE_LEVELS.index("高"), EXPOSURE_LEVELS)
        # gte-style vocabulary comparison: the rule's threshold resolves
        # through the same levels tuple, exactly like OrderedLevelTrait.
        for other, gte_expected, lte_expected in (
            ("極低", True, False),
            ("中等", True, False),
            ("高", True, True),
            ("極高", False, True),
        ):
            with self.subTest(other=other):
                self.assertEqual(high >= other, gte_expected)
                self.assertEqual(high <= other, lte_expected)
                self.assertEqual(high > other, high.value > EXPOSURE_LEVELS.index(other))
                self.assertEqual(high < other, high.value < EXPOSURE_LEVELS.index(other))
        self.assertTrue(high == "高")
        self.assertTrue(high == 3)
        self.assertTrue(high >= 3)
        self.assertTrue(high <= 3)
        mirrored = StoredLevel(3, EXPOSURE_LEVELS)
        self.assertTrue(high == mirrored)
        self.assertTrue(high >= mirrored)
        self.assertTrue(high <= mirrored)


class EffectiveExposureOverlayTests(EvenniaTestCase):
    """Task 4.1: the overlay accessor's contract."""

    @covers_requirement(
        "equipment-effects::effective-exposure-is-a-pure-clamped-read-time-overlay"
    )
    def test_bias_shifts_and_clamps_to_vocabulary_bounds(self):
        entity = _player("overlay shifter")
        entity.sexual.exposure.value = "中等"
        _worn(entity, armor="enticing_lace_set")
        shifted = effective_exposure(entity)
        self.assertIsInstance(shifted, StoredLevel)
        self.assertEqual(shifted.levels, EXPOSURE_LEVELS)
        self.assertEqual(shifted.levels[shifted.value], "高")
        _worn(entity, armor="saintess_vestments")
        self.assertEqual(equipment_exposure_bias(entity), 2)
        self.assertEqual(effective_exposure(entity).levels[2 + 2], "極高")
        # The vocabulary ceiling never overflows, whatever the bias.
        entity.sexual.exposure.value = "極高"
        self.assertEqual(effective_exposure(entity).value, len(EXPOSURE_LEVELS) - 1)
        # The floor clamp is defensive (no shipped negative bias exists).
        with patch(
            "world.rules.equipment_effects.equipment_exposure_bias", return_value=-5
        ):
            entity.sexual.exposure.value = "中等"
            self.assertEqual(effective_exposure(entity).value, 0)

    @covers_requirement(
        "equipment-effects::effective-exposure-is-a-pure-clamped-read-time-overlay"
    )
    def test_malformed_or_absent_storage_fails_closed(self):
        entity = _player("overlay malformed wearer")
        entity.sexual.exposure.value = "低"
        # Unresolvable gear contributes zero bias: stored level unchanged.
        _worn(
            entity,
            armor="not_a_registered_key",
            accessories=["also_bogus"],
        )
        entity.db.equipment["weapon_main"] = 42
        self.assertEqual(equipment_exposure_bias(entity), 0)
        self.assertEqual(effective_exposure(entity).value, 1)
        # Completely broken equipment storage behaves the same.
        entity.db.equipment = "utter garbage"
        self.assertEqual(effective_exposure(entity).value, 1)
        # An entity with no sexual storage at all passes through unresolved.
        bare = _player("overlay no state")
        self.assertIsNone(effective_exposure(bare))

    @covers_requirement(
        "equipment-effects::effective-exposure-is-a-pure-clamped-read-time-overlay"
    )
    def test_corrupt_vocabulary_never_relabels_a_canonical_band(self):
        entity = _player("overlay corrupt vocab")
        entity.sexual.exposure.value = "中等"
        traits = entity.attributes.get("sexual_traits", category="traits")
        traits["exposure"] = {
            "trait_type": "ordered_level",
            "name": "Exposure",
            "value": 3,
            "levels": ("壞0", "壞1", "壞2", "壞3"),
            "min": 0,
            "max": 3,
        }
        _worn(entity, armor="saintess_vestments")  # bias +2
        # The record passes through with its OWN vocabulary and ordinal —
        # never shifted, never relabeled into the canonical bands.
        resolved = effective_exposure(entity)
        self.assertIsInstance(resolved, StoredLevel)
        self.assertEqual(resolved.levels, ("壞0", "壞1", "壞2", "壞3"))
        self.assertEqual(resolved.value, 3)
        # Rule matching against the corrupt band fails loud exactly as the
        # pre-overlay evaluator did, instead of silently firing the
        # 露出 ≥ 高 penalty on a relabeled ordinal.
        with self.assertRaises(ValueError):
            evaluate_combat_modifiers_no_create(entity)

    @covers_requirement(
        "equipment-effects::effective-exposure-is-a-pure-clamped-read-time-overlay"
    )
    def test_overlay_never_materializes_handlers_or_writes(self):
        entity = _player("overlay pure reader")
        entity.db.sexual = {
            "arousal": "無",
            "wetness": "乾燥",
            "shame": "無",
            "exposure": "低",
            "climax_phase": "未達",
        }
        _worn(entity, armor="sister_vestments")
        before = repr(
            (
                entity.attributes.get("sexual", default=None),
                entity.db.equipment,
            )
        )
        resolved = effective_exposure(entity)
        # The baseline string resolves through the same shared reader.
        self.assertIsInstance(resolved, StoredLevel)
        self.assertEqual(resolved.levels[resolved.value], "中等")
        self.assertIsNone(entity.attributes.get("sexual_traits", category="traits"))
        self.assertEqual(before, repr((entity.attributes.get("sexual"), entity.db.equipment)))

    @covers_requirement(
        "equipment-effects::effective-exposure-is-a-pure-clamped-read-time-overlay"
    )
    def test_shared_reader_imports_no_project_modules(self):
        tree = ast.parse(
            (_ROOT / "world/rules/stored_sexual_reads.py").read_text(encoding="utf-8")
        )
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        project = {"world", "typeclasses", "commands", "server", "web"}
        self.assertEqual(roots & project, set())

    @covers_requirement(
        "equipment-effects::effective-exposure-is-a-pure-clamped-read-time-overlay"
    )
    def test_equipment_effects_never_imports_the_rules_consumers(self):
        # status_display is NOT forbidden: it is the sanctioned neutral leaf
        # P3 uses for immunity display labels (function-local import to keep
        # the combat_modifiers cycle open only lazily).
        forbidden = (
            "world.rules.combat_modifiers",
            "world.rules.status_query",
        )
        tree = ast.parse(
            (_ROOT / "world/rules/equipment_effects.py").read_text(encoding="utf-8")
        )

        def violations(node_tree) -> list[str]:
            hits: list[str] = []
            for node in ast.walk(node_tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module in forbidden:
                        hits.append(node.module)
                elif isinstance(node, ast.Import):
                    hits.extend(alias.name for alias in node.names if alias.name in forbidden)
                elif isinstance(node, ast.Call):
                    function = node.func
                    dynamic = isinstance(function, ast.Attribute) and function.attr in {
                        "import_module",
                        "__import__",
                    }
                    if dynamic:
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                if arg.value in forbidden:
                                    hits.append(arg.value)
            return hits

        self.assertEqual(violations(tree), [])
        # Negative fixture: the same scan catches static and dynamic hits.
        offense = ast.parse(
            "from world.rules.combat_modifiers import evaluate_combat_modifiers\n"
            "import world.rules.status_query\n"
            "import importlib\nimportlib.import_module('world.rules.combat_modifiers')\n"
        )
        self.assertEqual(len(violations(offense)), 3)


class ContextParityTests(EvenniaTest):
    """Task 4.2: both condition contexts match on the effective level."""

    def setUp(self):
        super().setUp()
        self.actor = _player("parity wearer")
        self.actor.location = self.room1

    @covers_requirement(
        "combat-modifier-table::condition-contexts-match-on-effective-exposure"
    )
    def test_both_contexts_carry_the_effective_ordinal_and_view_type(self):
        self.actor.sexual.exposure.value = "中等"
        _worn(self.actor, armor="saintess_vestments")
        live = _build_context(self.actor)["exposure"]
        no_create = build_no_create_condition_context(self.actor)["exposure"]
        self.assertIs(type(live), StoredLevel)
        self.assertIs(type(no_create), StoredLevel)
        self.assertEqual(live.value, no_create.value)
        self.assertEqual(live.value, EXPOSURE_LEVELS.index("高") + 1)
        self.assertTrue(live >= "高")
        self.assertTrue(no_create >= "高")

    @covers_requirement(
        "combat-modifier-table::condition-contexts-match-on-effective-exposure"
    )
    def test_penalty_rule_fires_in_both_paths_only_from_effective_level(self):
        self.actor.sexual.exposure.value = "中等"
        # Stored 中等 alone never meets 高 in either path.
        self.assertEqual(evaluate_combat_modifiers(self.actor), {})
        self.assertEqual(evaluate_combat_modifiers_no_create(self.actor), {})
        # Bias +1 makes it effective, and both paths agree, equipment fold
        # included (修女聖袍 contributes heal_gain only to the bundle).
        _worn(self.actor, armor="sister_vestments")
        live = evaluate_combat_modifiers(self.actor)
        no_create = evaluate_combat_modifiers_no_create(self.actor)
        self.assertEqual(live, no_create)
        self.assertEqual(live, {"defense": -15, "heal_gain": "+10%"})
        self.assertNotIn("pleasure_gain", live)
        # Unequipped golden: back to the stored-only inert result.
        _worn(self.actor)
        self.assertEqual(evaluate_combat_modifiers(self.actor), {})
        self.assertEqual(evaluate_combat_modifiers_no_create(self.actor), {})

    @covers_requirement(
        "combat-modifier-table::condition-contexts-match-on-effective-exposure"
    )
    def test_status_chip_agrees_with_the_effective_level(self):
        self.actor.sexual.exposure.value = "低"
        _worn(self.actor, armor="sister_vestments")
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_exposure_defense_penalty" for c in model.conditions)
        )
        self.actor.sexual.exposure.value = "中等"
        model = build_status_read_model(self.actor)
        self.assertTrue(
            any(c.code == "high_exposure_defense_penalty" for c in model.conditions)
        )


class PleasureFunnelTests(EvenniaTest):
    """Task 4.3/4.4: the equipment percent in the funnel."""

    def setUp(self):
        super().setUp()
        self.actor = _player("funnel subject")
        self.actor.location = self.room1

    @covers_requirement(
        "sexual-act-effects::the-pleasure-funnel-applies-the-equipment-pleasure-percent"
    )
    def test_golden_pairs_on_a_fresh_entity(self):
        # Generic defaults: sensitivity 普通 ×1.0, shame 無 ×1.0, count 1 ×1.0.
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=15),
            46,
        )
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=25),
            50,
        )
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=-100),
            0,
        )
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1),
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=0),
        )

    @covers_requirement(
        "sexual-act-effects::the-pleasure-funnel-applies-the-equipment-pleasure-percent"
    )
    def test_percent_scales_after_the_ladders_without_touching_them(self):
        # The percent multiplies after every ladder, independently.
        self.actor.sexual.sensitivity["私處"].value = "高"
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=15),
            64,  # round(40 × 1.4 × 1.15)
        )
        self.actor.sexual.sensitivity["私處"].value = "普通"
        self.actor.sexual.shame.value = "輕微"
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=15),
            41,  # round(40 × 0.9 × 1.15)
        )
        self.actor.sexual.shame.value = "無"
        self.assertEqual(
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 2, pleasure_percent=15),
            51,  # round(40 × 1.1 × 1.15)
        )
        # Ladders and counters are untouched by the computation itself.
        for _ in range(2):
            compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=15)
        snapshot = repr(self.actor.attributes.get("sexual_traits", category="traits"))
        compute_pleasure_gain(self.actor, "私處", 40, 1.0, 1, pleasure_percent=15)
        self.assertEqual(
            snapshot,
            repr(self.actor.attributes.get("sexual_traits", category="traits")),
        )
        for key in _LIFETIME_COUNTER_KEYS:
            self.assertEqual(getattr(self.actor.sexual, key), 0)

    @covers_requirement(
        "sexual-act-effects::the-pleasure-funnel-applies-the-equipment-pleasure-percent"
    )
    def test_live_cast_applies_the_worn_percent(self):
        from world.rules.action import ActionRequest, ActionResolver
        from world.rules.targeting import RoomActionContext

        bare = _player("funnel bare")
        bare.db.skills = {"active": [], "passive": []}
        before = bare.sexual.pleasure.base
        result = ActionResolver.resolve(
            ActionRequest(bare, "solo_self_touch", [], RoomActionContext(None, {}))
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(bare.sexual.pleasure.base - before, 12)

        geared = _player("funnel geared")
        geared.db.skills = {"active": [], "passive": []}
        _wear(geared, "enticing_lace_set")
        before = geared.sexual.pleasure.base
        result = ActionResolver.resolve(
            ActionRequest(geared, "solo_self_touch", [], RoomActionContext(None, {}))
        )
        self.assertEqual(result.outcome, "success")
        # round(12 × 1.15) = 14 with the lace's +15% pleasure_gain.
        self.assertEqual(geared.sexual.pleasure.base - before, 14)

    @covers_requirement(
        "sexual-act-effects::the-pleasure-funnel-applies-the-equipment-pleasure-percent"
    )
    def test_combat_bundle_keysets_exclude_pleasure_gain(self):
        lace_only = _player("bundle lace only")
        _worn(lace_only, armor="enticing_lace_set")
        self.assertEqual(dict(equipment_adjustments(lace_only)), {})
        self.assertEqual(equipment_pleasure_gain(lace_only), 15)
        self.assertEqual(evaluate_combat_modifiers_no_create(lace_only), {})

        choker = _player("bundle choker")
        _worn(choker, accessories=["passion_silk_choker"])
        bundle = dict(evaluate_combat_modifiers_no_create(choker))
        self.assertEqual(bundle, {"defense": -3})
        self.assertNotIn("pleasure_gain", bundle)
        self.assertEqual(equipment_pleasure_gain(choker), 25)


class StoredStateImmunityTests(EvenniaTest):
    """Task 4.5: bias is an overlay; stored state never moves for it."""

    def setUp(self):
        super().setUp()
        self.actor = _player("immunity subject")
        self.actor.location = self.room1
        self.actor.db.skills = {"active": [], "passive": []}

    def _hem_lift(self, entity):
        from world.rules.action import ActionRequest, ActionResolver
        from world.rules.targeting import RoomActionContext

        result = ActionResolver.resolve(
            ActionRequest(entity, "shame_hem_lift", [], RoomActionContext(entity.location, {}))
        )
        self.assertEqual(result.outcome, "success")

    @covers_requirement(
        "sexual-state-handler::equipment-exposure-bias-never-touches-stored-state"
    )
    def test_progression_matches_the_unequipped_case(self):
        bare = _player("bare hem lifter")
        bare.db.skills = {"active": [], "passive": []}
        bare.location = self.room1
        self._hem_lift(bare)

        geared = _player("geared hem lifter")
        geared.db.skills = {"active": [], "passive": []}
        geared.location = self.room1
        # Equipping writes nothing to sexual storage at all.
        self.assertIsNone(geared.attributes.get("sexual_traits", category="traits"))
        _wear(geared, "saintess_vestments")
        self.assertIsNone(geared.attributes.get("sexual_traits", category="traits"))
        self._hem_lift(geared)
        # Stored progression is identical: the overlay never fed back.
        self.assertEqual(
            _stored_exposure_ordinal(geared), _stored_exposure_ordinal(bare)
        )
        self.assertEqual(geared.sexual.shame.value, bare.sexual.shame.value)
        # While worn, the effective level carries the bias…
        worn_view = effective_exposure(geared)
        self.assertEqual(worn_view.levels[worn_view.value], "高")
        # …and removal drops it straight back to the stored ordinal.
        toggle_equipment(geared, "saintess_vestments")
        self.assertEqual(effective_exposure(geared).value, _stored_exposure_ordinal(geared))

    @covers_requirement(
        "sexual-state-handler::equipment-exposure-bias-never-touches-stored-state"
    )
    def test_read_model_renders_the_effective_label(self):
        self.actor.sexual.exposure.value = "中等"
        _wear(self.actor, "saintess_vestments")
        model = build_character_read_model(self.actor)
        self.assertEqual(model.intimate.exposure, "極高")
        # Every other intimate row keeps the stored value.
        self.assertEqual(model.intimate.shame, self.actor.sexual.shame.level)
        # The stored trait itself is untouched by rendering.
        self.assertEqual(_stored_exposure_ordinal(self.actor), 2)


class ExposureConsumerAllowlistTests(unittest.TestCase):
    """Task 4.6: every shipped exposure consumer is classified."""

    # Modules allowed to read the STORED exposure ordinal alone.
    _STORED_CONSUMERS = frozenset(
        {
            Path("world/rules/sexual_state.py"),
            Path("world/rules/sexual_transitions.py"),
            Path("world/imports/schema.py"),
        }
    )
    # Modules that must consume exposure through the effective overlay.
    _EFFECTIVE_CONSUMERS = frozenset(
        {
            Path("world/rules/combat_modifiers.py"),
            Path("world/rules/equipment_effects.py"),
            Path("world/rules/status_query.py"),
            Path("web/webclient/presentation/character.py"),
        }
    )

    @staticmethod
    def _exposure_offense(tree: ast.AST) -> bool:
        """True when the source names ``exposure`` outside tuple literals.

        Attribute access, subscript keys, call arguments/keyword values, and
        dict keys all bind gameplay meaning to the stored field name, and a
        bare string-constant assignment (``FIELD = "exposure"``) is how an
        indirect reader smuggles that meaning past the literal forms; tuple
        entries (fixed vocabulary row lists) do not.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "exposure":
                return True
            if isinstance(node, ast.Assign):
                value = node.value
                if isinstance(value, ast.Constant) and value.value == "exposure":
                    return True
            if isinstance(node, ast.Subscript):
                key = node.slice
                if isinstance(key, ast.Constant) and key.value == "exposure":
                    return True
            elif isinstance(node, ast.Call):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value == "exposure":
                        return True
                for keyword in node.keywords:
                    if keyword.arg == "exposure" or (
                        isinstance(keyword.value, ast.Constant)
                        and keyword.value.value == "exposure"
                    ):
                        return True
            elif isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and key.value == "exposure":
                        return True
        return False

    def _offenders(self) -> set[Path]:
        offenders: set[Path] = set()
        for root in _PRODUCTION_ROOTS:
            for path in (_ROOT / root).rglob("*.py"):
                relative = path.relative_to(_ROOT)
                if "tests" in relative.parts:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                if self._exposure_offense(tree):
                    offenders.add(relative)
        return offenders

    @covers_requirement(
        "sexual-state-handler::equipment-exposure-bias-never-touches-stored-state"
    )
    def test_every_exposure_consumer_is_classified(self):
        offenders = self._offenders()
        classified = self._STORED_CONSUMERS | self._EFFECTIVE_CONSUMERS
        unclassified = offenders - classified
        self.assertEqual(
            unclassified,
            set(),
            f"raw exposure consumers outside the allowlist: {sorted(map(str, unclassified))}",
        )
        # The classification is live: every listed file really does offend.
        self.assertTrue(offenders >= classified)

    @covers_requirement(
        "sexual-state-handler::equipment-exposure-bias-never-touches-stored-state"
    )
    def test_detector_catches_a_synthesized_consumer(self):
        for snippet in (
            "value = entity.sexual.exposure\n",
            "value = entity.attributes.get('sexual_traits')['exposure']\n",
            "value = handler.get('exposure')\n",
            "value = handler.get(field='exposure')\n",
            "mapping = {'exposure': 1}\n",
            "EXPOSURE_FIELD = 'exposure'\nvalue = traits[EXPOSURE_FIELD]\n",
        ):
            with self.subTest(snippet=snippet):
                self.assertTrue(self._exposure_offense(ast.parse(snippet)))
        self.assertFalse(
            self._exposure_offense(ast.parse("FIELDS = ('wetness', 'shame')\n"))
        )


if __name__ == "__main__":
    unittest.main()

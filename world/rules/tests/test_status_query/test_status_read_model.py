"""Slice of ``test_status_query``: StatusReadModelTests.
"""
from collections.abc import Mapping, Sequence
from dataclasses import replace
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.buffs import apply_buff
from world.rules.combat_session import engage
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.rules.status_query import (
    StatusQueryError,
    build_character_read_model,
    build_status_read_model,
    group_skill_keys,
)
from world.skills.handler import INNATE_SKILL_ORDER
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries
from .._combat_session_helpers import (
    _live_registry,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
# ``flee`` is injected into ``SKILL_REGISTRY`` at import time by
# ``world.rules.disengage`` (the ``universal-action-ownership`` dependency
# direction), so the grouping and split tests import it explicitly to keep
# ``flee`` in scope.
import world.rules.disengage  # noqa: F401  (registers flee)


from ._support import (
    _actor,
)


class StatusReadModelTests(EvenniaTest):
    def setUp(self):
        # The catalogue scope opens before construction so the fixture
        # entities resolve against the kit race/tier rows (the kit's class
        # decorator wraps test* methods only, not setUp).
        open_synthetic_scope(self, "elements", "races", "subraces", "static_tiers")
        super().setUp()
        self.actor = _actor(self)
        self.actor.location = self.room1

    def _provenance_scope(self):
        """Synthetic ownership declarations and matching rules, no live content."""
        from world.rules.rulebook.schema import Rule
        from world.skills.equipment import EquipmentSlot

        stack = ExitStack()
        self.addCleanup(stack.close)
        items = {
            key: SimpleNamespace(
                key=key, display_name_zh=label, modifier_key=key,
                equipment_slot=EquipmentSlot.ACCESSORY,
            )
            for key, label in (("t_a", "合成護符甲"), ("t_b", "合成護符乙"))
        }
        effects = {
            key: SimpleNamespace(attached_buffs=("t_adverse",), exposure_bias=bias)
            for key, bias in (("t_a", 1), ("t_b", -1))
        }
        stack.enter_context(patch.dict("world.rules.equipment.ITEM_REGISTRY", items))
        stack.enter_context(patch.dict("world.rules.equipment_effects.ITEM_REGISTRY", items))
        stack.enter_context(patch.dict("world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", effects))
        stack.enter_context(patch.dict("world.rules.buffs.BUFF_DEFINITIONS", {
            "t_adverse": SimpleNamespace(), "t_other": SimpleNamespace(),
        }))
        stack.enter_context(patch("world.rules.status_query.status.display_for",
                                  return_value=SimpleNamespace(label="合成警告", severity="warning")))
        rules = [
            Rule("t_exposure", {"field": "exposure", "gte": "高"}, {"defense": -15}),
            Rule("t_buff", {"buff_active": "t_adverse"}, {"agility": "-10%"}),
            Rule("t_combined", {"field": "exposure", "gte": "高", "equipment_worn": "t_a"}, {"accuracy": -2}),
            Rule("t_unrelated", {"field": "arousal", "gte": "高度"}, {"accuracy": -3}),
        ]
        stack.enter_context(patch("world.rules.combat_modifiers._RULES", rules))
        self.actor.db.equipment = {
            "weapon_main": None, "weapon_off": None, "armor": None, "accessories": ["t_a"],
        }
        return effects

    @covers_requirement("webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers")
    @covers_requirement(
        "webclient-status-presentation::equipment-condition-provenance-preserves-independent-sources"
    )
    def test_equipment_threshold_provenance_and_actual_match_parity(self):
        from world.rules.status_query.assembly import _assemble
        from world.rules.combat_modifiers import matched_combat_modifiers
        self._provenance_scope()
        for stored, expected in (("中等", "equipment"), ("高", "mixed"), ("極高", "non_equipment")):
            with self.subTest(stored=stored):
                self.actor.sexual.exposure.value = stored
                model = build_status_read_model(self.actor)
                row = next(c for c in model.conditions if c.code == "t_exposure")
                self.assertEqual(row.provenance.kind, expected)
                self.assertEqual(row.modifiers, {"defense": -15})
                self.assertEqual([s.item_key for s in row.provenance.equipment_sources],
                                 [] if expected == "non_equipment" else ["t_a"])
                combined = next(c for c in model.conditions if c.code == "t_combined")
                self.assertEqual(combined.provenance.kind, "equipment")
                self.assertEqual(_assemble(self.actor).matches, matched_combat_modifiers(self.actor))
                self.assertEqual(self.actor.sexual.exposure.value, EXPOSURE_LEVELS.index(stored))
        self.actor.sexual.pleasure.base = 85
        row = next(c for c in build_status_read_model(self.actor).conditions if c.code == "t_unrelated")
        self.assertEqual(row.provenance.kind, "non_equipment")
        self.actor.db.equipment["accessories"] = ["t_b", "t_a"]
        self.actor.sexual.exposure.value = "高"
        row = next(c for c in build_status_read_model(self.actor).conditions if c.code == "t_exposure")
        self.assertEqual(row.provenance.kind, "non_equipment", "net-zero overlay contributes no source")
        self.actor.sexual.exposure.value = "極低"
        self.actor.db.equipment["accessories"] = ["t_b"]
        self.assertFalse(any(c.code == "t_exposure" for c in build_status_read_model(self.actor).conditions))

    @covers_requirement("webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers")
    @covers_requirement(
        "webclient-status-presentation::equipment-condition-provenance-preserves-independent-sources"
    )
    def test_attached_ownership_preserves_independent_instances_and_orphans(self):
        self._provenance_scope()
        caches = {
            "t_adverse:t_a": {"definition_key": "t_adverse", "source_key": "t_a", "stacks": 1, "remaining_seconds": 30},
            "ordinary": {"definition_key": "t_adverse", "source_key": "t_a", "stacks": 1, "remaining_seconds": 120},
            "t_other:t_a": {"definition_key": "t_other", "source_key": "t_a", "stacks": 1, "remaining_seconds": 60},
        }
        self.actor.attributes.add("buffs", caches)
        model = build_status_read_model(self.actor)
        buffs = [c for c in model.conditions if c.code == "t_adverse"]
        self.assertEqual([c.remaining_seconds for c in buffs], [30, 120])
        self.assertEqual([c.provenance.kind for c in buffs], ["equipment", "non_equipment"])
        derived = next(c for c in model.conditions if c.code == "t_buff")
        self.assertEqual(derived.provenance.kind, "mixed")
        self.assertEqual(derived.provenance.equipment_sources[0].label, "合成護符甲")
        self.assertEqual(next(c for c in model.conditions if c.code == "t_other").provenance.kind, "non_equipment")
        del caches["ordinary"]
        self.actor.attributes.add("buffs", caches)
        self.assertEqual(next(c for c in build_status_read_model(self.actor).conditions if c.code == "t_buff").provenance.kind, "equipment")
        for source in (None, "t_b"):
            with self.subTest(source=source):
                caches["t_adverse:t_a"]["source_key"] = source
                self.actor.attributes.add("buffs", caches)
                rows = build_status_read_model(self.actor).conditions
                self.assertEqual(next(c for c in rows if c.code == "t_adverse").provenance.kind, "unknown")
                self.assertEqual(next(c for c in rows if c.code == "t_buff").provenance.kind, "non_equipment")
        caches["t_adverse:t_a"]["source_key"] = "t_a"
        self.actor.db.equipment["accessories"] = []
        self.actor.attributes.add("buffs", caches)
        self.assertEqual(next(c for c in build_status_read_model(self.actor).conditions if c.code == "t_adverse").provenance.kind, "unknown")
        self.actor.db.equipment["accessories"] = ["t_b", "t_a"]
        caches["t_adverse:t_b"] = {"definition_key": "t_adverse", "source_key": "t_b", "stacks": 1}
        self.actor.attributes.add("buffs", caches)
        row = next(c for c in build_status_read_model(self.actor).conditions if c.code == "t_buff")
        self.assertEqual([s.item_key for s in row.provenance.equipment_sources], ["t_a", "t_b"])
        caches["t_adverse:t_a"]["definition_key"] = "t_other"
        self.actor.attributes.add("buffs", caches)
        self.assertEqual(next(c for c in build_status_read_model(self.actor).conditions if c.code == "t_other").provenance.kind, "unknown")

    @covers_requirement("webclient-status-presentation::status-presentation-has-no-mutation-side-effects")
    @covers_requirement(
        "webclient-status-presentation::equipment-condition-provenance-preserves-independent-sources"
    )
    def test_provenance_reads_preserve_materialized_and_unmaterialized_storage(self):
        import copy
        self._provenance_scope()
        for materialized in (False, True):
            with self.subTest(materialized=materialized):
                if not materialized:
                    self.actor.attributes.remove("sexual_traits", category="traits")
                    self.actor.__dict__.pop("sexual", None)
                else:
                    self.actor.sexual.exposure.value = "中等"
                before = copy.deepcopy([
                    self.actor.attributes.get("traits", category="traits"),
                    self.actor.attributes.get("sexual_traits", category="traits"),
                    self.actor.db.equipment, self.actor.attributes.get("buffs"),
                ])
                handlers = set(self.actor.__dict__)
                first = build_status_read_model(self.actor)
                self.assertEqual(build_status_read_model(self.actor), first)
                self.assertEqual(before, [
                    self.actor.attributes.get("traits", category="traits"),
                    self.actor.attributes.get("sexual_traits", category="traits"),
                    self.actor.db.equipment, self.actor.attributes.get("buffs"),
                ])
                self.assertEqual(set(self.actor.__dict__), handlers)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_resources_report_stored_true_values(self):
        maxima = {}
        for key in ("hp", "mp", "sp"):
            raw = self.actor.attributes.get("traits", category="traits")[key]
            maxima[key] = int(round((raw["base"] + raw["mod"]) * raw["mult"]))
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"], model.resources["hp"])
        self.assertEqual(model.resources["hp"].current, maxima["hp"])
        self.assertEqual(model.resources["hp"].maximum, maxima["hp"])
        self.assertEqual(model.resources["mp"].maximum, maxima["mp"])
        self.assertEqual(model.resources["sp"].maximum, maxima["sp"])
        self.actor.traits.hp.current = 30
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"].current, 30)
        self.assertEqual(model.resources["hp"].maximum, maxima["hp"])

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_active_disguise_never_changes_true_resources(self):
        maxima = {}
        for key in ("hp", "mp", "sp"):
            raw = self.actor.attributes.get("traits", category="traits")[key]
            maxima[key] = int(round((raw["base"] + raw["mod"]) * raw["mult"]))
        self.actor.traits.hp.current = 80
        self.actor.traits.mp.current = 40
        self.actor.traits.sp.current = 30
        self.actor.db.disguised_stats = {"hp": 200, "mp": 150, "sp": 90}
        model = build_status_read_model(self.actor)
        self.assertEqual(model.resources["hp"].current, 80)
        self.assertEqual(model.resources["hp"].maximum, maxima["hp"])
        self.assertEqual(model.resources["mp"].current, 40)
        self.assertEqual(model.resources["sp"].current, 30)
        self.assertTrue(model.disguise_active)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_missing_gauge_fails_closed(self):
        self.actor.attributes.remove("traits", category="traits")
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

    @covers_requirement(
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers"
    )
    def test_poisoned_buff_reports_duration_and_exact_adjustment(self):
        apply_buff(self.actor, "poisoned")
        # poison remaining_seconds defaults to definition duration 300.
        model = build_status_read_model(self.actor)
        poisoned = next(
            condition for condition in model.conditions if condition.code == "poisoned"
        )
        self.assertEqual(poisoned.label, "中毒")
        self.assertEqual(poisoned.severity, "harmful")
        self.assertEqual(poisoned.remaining_seconds, 300)
        penalty = next(
            condition
            for condition in model.conditions
            if condition.code == "poison_agility_penalty"
        )
        self.assertEqual(penalty.modifiers, {"agility": "-10%"})

    @covers_requirement(
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers"
    )
    def test_sexual_threshold_appears_only_while_matched(self):
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_arousal_agility_accuracy_penalty" for c in model.conditions)
        )
        self.actor.sexual.pleasure.base = 85
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})
        self.assertEqual(entry.severity, "warning")

    @covers_requirement(
        "combat-modifier-table::high-exposure-defense-penalty-prices-raised-exposure-as-a-combat-cost",
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers",
    )
    def test_high_exposure_defense_penalty_appears_only_while_matched(self):
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_exposure_defense_penalty" for c in model.conditions)
        )
        # The threshold levels come from the shipped ordered vocabulary the
        # rulebook itself compares against (EXPOSURE_LEVELS); the display
        # label resolves through the shipped display table.
        from .._equipment_rulebook_probes import display_label

        trigger = EXPOSURE_LEVELS[EXPOSURE_LEVELS.index(EXPOSURE_LEVELS[-1]) - 1]
        calm = EXPOSURE_LEVELS[1]
        self.actor.sexual.exposure.value = trigger
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_exposure_defense_penalty"
        )
        self.assertEqual(entry.modifiers, {"defense": -15})
        self.assertEqual(entry.severity, "warning")
        self.assertEqual(entry.label, display_label("high_exposure_defense_penalty"))
        self.actor.sexual.exposure.value = calm
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(c.code == "high_exposure_defense_penalty" for c in model.conditions)
        )

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_owned_skill_adjustment_appears_in_status_conditions(self):
        # The rulebook row keyed to the shipped passive whose condition reads
        # ``skill_owned`` for it is located by probe; the entity owns that
        # shipped key (resolved from the row, not a literal), so the match is
        # the real production binding.
        from world.rules.combat_modifiers import _RULES

        (rule,) = [
            rule
            for rule in _RULES
            if rule.id == "defense_instinct_defense_bonus"
        ]
        skill_key = rule.when["skill_owned"]
        self.actor.db.skills = {"active": [], "passive": [skill_key]}
        model = build_status_read_model(self.actor)
        entry = next(c for c in model.conditions if c.code == rule.id)
        self.assertEqual(entry.modifiers, {"defense": 5})
        self.assertEqual(entry.severity, "beneficial")
        from .._equipment_rulebook_probes import display_label

        self.assertEqual(entry.label, display_label(rule.id))

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_all_sink_skill_conditions_match_the_bundle_verbatim(self):
        # The five sink rules are located by their stable condition codes;
        # the owned skill keys and every asserted magnitude come from the
        # loaded rulebook rows themselves.
        from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers

        codes = (
            "defense_instinct_defense_bonus",
            "guardian_instinct_defense_bonus",
            "retainer_martial_training_atk_phys_bonus",
            "precise_mana_control_mp_cost_reduction",
            "extreme_endurance_sp_cost_reduction",
        )
        rows = {rule.id: rule for rule in _RULES if rule.id in codes}
        self.assertEqual(set(rows), set(codes))
        self.actor.db.skills = {
            "active": [],
            "passive": [rows[code].when["skill_owned"] for code in codes],
        }
        expected = {code: dict(rows[code].then) for code in codes}
        defense_sum = sum(
            value
            for code in codes
            for field, value in rows[code].then.items()
            if field == "defense" and isinstance(value, int) and not isinstance(value, bool)
        )
        bundle = evaluate_combat_modifiers(self.actor)
        self.assertEqual(bundle["defense"], defense_sum)
        for code in codes:
            for field, value in rows[code].then.items():
                if field != "defense":
                    self.assertEqual(bundle[field], value)
        model = build_status_read_model(self.actor)
        conditions = {c.code: c for c in model.conditions}
        self.assertEqual(set(conditions) & set(codes), set(codes))
        for code, modifiers in expected.items():
            with self.subTest(code=code):
                self.assertEqual(conditions[code].modifiers, modifiers)
                self.assertEqual(conditions[code].severity, "beneficial")
                self.assertTrue(conditions[code].label)

    def _dual_wield_rule(self):
        from world.rules.combat_modifiers import _RULES

        (rule,) = [
            rule for rule in _RULES if rule.id == "dual_wield_style_atk_phys_bonus"
        ]
        return rule

    def test_dual_wield_style_bonus_appears_only_while_dual_wielding(self):
        rule = self._dual_wield_rule()
        self.actor.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        self.actor.db.equipment = {
            "weapon_main": "left_blade",
            "weapon_off": "right_blade",
        }
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "dual_wield_style_atk_phys_bonus"
        )
        self.assertEqual(entry.modifiers, dict(rule.then))
        self.assertEqual(entry.severity, "beneficial")
        from .._equipment_rulebook_probes import display_label

        self.assertEqual(entry.label, display_label(rule.id))
        self.actor.db.equipment = {"weapon_main": "left_blade", "weapon_off": None}
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "dual_wield_style_atk_phys_bonus"
                for c in model.conditions
            )
        )

    def test_status_read_does_not_materialize_equipment_handler(self):
        rule = self._dual_wield_rule()
        self.actor.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        self.actor.db.equipment = {
            "weapon_main": "left_blade",
            "weapon_off": "right_blade",
        }
        self.assertNotIn("equipment", vars(self.actor))
        build_status_read_model(self.actor)
        self.assertNotIn("equipment", vars(self.actor))

    @covers_requirement(
        "webclient-status-presentation::status-presentation-has-no-mutation-side-effects"
    )
    def test_unmaterialized_sexual_baseline_remains_unmaterialized(self):
        self.actor.db.sexual = {
            "arousal": "平靜",
            "wetness": "乾燥",
            "shame": "無",
            "exposure": "遮蔽",
            "climax_phase": "未達",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        self.assertIsNone(self.actor.attributes.get("sexual_traits", category="traits"))
        build_status_read_model(self.actor)
        self.assertIsNone(
            self.actor.attributes.get("sexual_traits", category="traits"),
            "reading status must not materialize the sexual handler",
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_reflects_live_pleasure_on_materialized_entity(self):
        self.actor.sexual.pleasure.base = 61
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.label, "高度興奮敏捷與準度減損")
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_entry_disappears_when_pleasure_drops_below_the_band(self):
        self.actor.sexual.pleasure.base = 61
        first = build_status_read_model(self.actor)
        self.assertTrue(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in first.conditions
            )
        )
        self.actor.sexual.pleasure.base = 59
        second = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in second.conditions
            )
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_of_unmaterialized_entity_resolves_from_baseline_without_materializing(self):
        self.actor.db.sexual = {
            "arousal": "極限",
            "wetness": "乾燥",
            "shame": "無",
            "exposure": "極低",
            "climax_phase": "未達",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        self.assertIsNone(self.actor.attributes.get("sexual_traits", category="traits"))
        model = build_status_read_model(self.actor)
        entry = next(
            c for c in model.conditions if c.code == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(entry.modifiers, {"agility": "-20%", "accuracy": -15})
        self.assertIsNone(
            self.actor.attributes.get("sexual_traits", category="traits"),
            "status reads must not materialize the sexual handler",
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_tracks_a_ceilinged_stored_base(self):
        # CounterTrait.base's setter clamps writes into [0, 100]; the status
        # reader must resolve the stored base exactly as the live trait.value
        # read does, including at the ceiling.
        self.actor.sexual.pleasure.base = 95
        self.actor.sexual.pleasure.base += 14
        self.assertEqual(self.actor.sexual.pleasure.value, 100)
        model = build_status_read_model(self.actor)
        self.assertTrue(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in model.conditions
            )
        )

    @covers_requirement("webclient-status-presentation::the-no-create-status-read-model-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_status_panel_rejects_a_boolean_stored_base(self):
        self.actor.sexual.pleasure.base = 60
        raw = dict(self.actor.attributes.get("sexual_traits", category="traits"))
        raw["pleasure"] = dict(raw["pleasure"])
        raw["pleasure"]["base"] = True
        self.actor.attributes.add("sexual_traits", raw, category="traits")
        model = build_status_read_model(self.actor)
        self.assertFalse(
            any(
                c.code == "high_arousal_agility_accuracy_penalty"
                for c in model.conditions
            )
        )

    def test_malformed_buff_cache_and_entries_fail_closed(self):
        self.actor.attributes.add("buffs", "junk")
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)
        self.actor.attributes.add("buffs", None)
        model = build_status_read_model(self.actor)
        self.assertEqual(model.conditions, ())
        self.actor.attributes.add("buffs", {"bad": "junk"})
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

    def test_paused_zero_stack_and_expired_buff_entries_are_skipped(self):
        self.actor.attributes.add(
            "buffs",
            {
                "paused_one": {"definition_key": "poisoned", "stacks": 1, "paused": True},
                "zero_stacks": {"definition_key": "poisoned", "stacks": 0},
                "expired": {"definition_key": "poisoned", "stacks": 1, "remaining_seconds": 0},
            },
        )
        model = build_status_read_model(self.actor)
        self.assertEqual(model.conditions, ())

    def test_unknown_buff_definition_fails_closed(self):
        self.actor.attributes.add(
            "buffs", {"mystery": {"definition_key": "nope", "stacks": 1}}
        )
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

    def test_malformed_combat_record_fails_closed(self):
        for raw in ("junk", {"mode": "bandit", "rounds_elapsed": 1}):
            self.actor.attributes.add("active_combat", raw)
            with self.assertRaises(StatusQueryError):
                build_status_read_model(self.actor)
        self.actor.attributes.add(
            "active_combat", {"mode": "hostile", "rounds_elapsed": -1}
        )
        with self.assertRaises(StatusQueryError):
            build_status_read_model(self.actor)

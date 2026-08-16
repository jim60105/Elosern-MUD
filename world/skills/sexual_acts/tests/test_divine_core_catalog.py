"""Behaviour tests for the three C7a 神之秘法 acts.

Covers the delta spec's scenarios for the three hand-built acts — 絕頂律令
(AREA pleasure-ceiling), 時姦 (staged climax extensions), 神域搾取 (pleasure
drain into MP/SP/HP) — plus the race gate, the zero-counter ownership of a
divine-capable actor, the mastery-blanket exclusion (the design doc's "most
important test"), and the line-agnostic dispatch-table contract of the three
new effect prefixes.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.quests.catalog import register_catalog
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _handle_climax_extension_stage,
    _handle_divine_pleasure_max,
    _handle_sexual_drain,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.sexual_resist import ResistVerdict
from world.rules.sexual_state import climax_settlement_action
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts.divine import DIVINE_ACTS

_DIVINE_KEYS = ("divine_extreme_climax_command", "divine_timed_copulation", "divine_realm_drain")


def _verdict(resisted: bool) -> ResistVerdict:
    """One deterministic resist verdict for the elf-vs-human fixture.

    The elf caster's static stats far exceed the human target's, so a
    ``roll_d100`` patch cannot force a resist through the ordinary contest
    formula; the wiring tests establish the same direct-verdict pattern.
    """
    return ResistVerdict(
        resisted=resisted,
        auto_comply=False,
        roll=None,
        actor_score=100.0,
        resister_score=100.0,
    )


def _entity(key="divine catalog owner", race="human"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = race
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


class DivineActRegistrationTests(unittest.TestCase):
    """The three rows are hand-built pairs with the delta spec's shared fields."""

    @covers_requirement("sexual-catalog-divine-core::three-hand-built-acts-are-registered-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_three_acts_registered_with_shared_field_values(self):
        self.assertEqual(len(DIVINE_ACTS), 3)
        for skill, act in DIVINE_ACTS:
            with self.subTest(key=skill.key):
                self.assertIn(skill.key, _DIVINE_KEYS)
                self.assertEqual(skill.key, act.key)
                self.assertTrue(skill.requires_divine_arts)
                self.assertEqual(act.unlock, {})
                self.assertIsNone(act.target_part)
                self.assertTrue(act.resistible)
                self.assertEqual(act.actor_counters, ())
                self.assertEqual(act.participant_counters, ())
                self.assertIs(skill.category.value, "sexual_act")
                self.assertEqual(skill.group, "神之秘法")
                self.assertEqual(skill.cost, {})
                self.assertTrue(skill.usable_out_of_combat)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertEqual(
                    [effect for effect in skill.effects if effect.startswith("pleasure:")],
                    [],
                )

    @covers_requirement("sexual-catalog-divine-core::three-hand-built-acts-are-registered-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_each_act_declares_exactly_its_one_bespoke_effect(self):
        effects_by_key = {
            "divine_extreme_climax_command": ["divine_pleasure_max:絕頂律令"],
            "divine_timed_copulation": ["divine_climax_extension_stage:3"],
            "divine_realm_drain": ["divine_drain:神域搾取"],
        }
        for skill, act in DIVINE_ACTS:
            with self.subTest(key=skill.key):
                self.assertEqual(skill.effects, effects_by_key[skill.key])
                self.assertEqual(act.sexual_events, ())

    def test_placeholder_pleasure_fields_are_documented_not_read(self):
        for skill, act in DIVINE_ACTS:
            with self.subTest(key=skill.key):
                self.assertEqual(act.base_pleasure, 1)
                self.assertEqual(act.actor_pleasure_ratio, 0.0)
                self.assertIsNone(act.actor_part)


class DivineUnlockTests(EvenniaTest):
    """The race gate, zero-counter ownership, and mastery-blanket exclusion."""

    def setUp(self):
        super().setUp()
        self.actor = _entity("divine actor", race="elf")

    @covers_requirement("sexual-catalog-divine-core::three-hand-built-acts-are-registered-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_divine_capable_actor_with_zero_counters_owns_all_three(self):
        owned = set(self.actor.skills.owned_keys())
        for key in _DIVINE_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, owned)
                # Zero counters: no unlock threshold has ever been recorded.
                for counter in (
                    "masturbation_count",
                    "toy_use_count",
                    "exposure_act_count",
                    "watched_count",
                    "duo_act_count",
                    "group_act_count",
                    "hostile_act_count",
                    "restraint_count",
                    "interspecies_act_count",
                    "climax_count",
                    "climax_extension_count",
                ):
                    self.assertEqual(getattr(self.actor.sexual, counter), 0)

    @covers_requirement("sexual-catalog-divine-core::three-hand-built-acts-are-registered-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_mastery_only_non_divine_entity_owns_none_of_the_three(self):
        # The design doc's "most important test" (divine design §6): an entity
        # owning 性魔法主宰 has the full counter-gated catalogue in owned_keys()
        # but none of these three, absent a divine-capable race. reincarnation_
        # boon_yuna carries SexualMasteryEffect without requires_divine_arts,
        # so a human can legitimately own it.
        human = _entity("mastery holder")
        human.db.skills = {"active": ["reincarnation_boon_yuna"], "passive": []}
        owned = set(human.skills.owned_keys())
        counter_gated = [
            key
            for key, act in SEXUAL_ACT_REGISTRY.items()
            if act.unlock
        ]
        self.assertTrue(counter_gated)
        for key in counter_gated:
            with self.subTest(key=key):
                self.assertIn(key, owned)
        for key in _DIVINE_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(key, owned)


class DivineCastTests(EvenniaTest):
    """Casting the three acts through ActionResolver."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = _entity("divine caster", race="elf")
        self.actor.location = self.room1
        self.target = _entity("divine target")
        self.target.location = self.room1

    def _cast(self, act_key, targets, context=None):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                targets,
                context or RoomActionContext(self.actor.location, {}),
            )
        )

    @covers_requirement("sexual-catalog-divine-core::three-hand-built-acts-are-registered-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_non_divine_race_cannot_cast_any_of_the_three(self):
        human = _entity("human caster")
        human.location = self.room1
        for key in _DIVINE_KEYS:
            with self.subTest(key=key):
                with patch("world.rules.action.roll_d100", return_value=1):
                    result = ActionResolver.resolve(
                        ActionRequest(
                            human,
                            key,
                            [self.target],
                            RoomActionContext(human.location, {}),
                        )
                    )
                self.assertIs(result.reason, RejectReason.DIVINE_ARTS_FORBIDDEN)

    @covers_requirement("sexual-catalog-divine-core::絕頂律令-sets-every-target-s-pleasure-to-its-ceiling-and-walks-climax-phase-to-進行中-in-one-cast-never-touching-the-actor")
    def test_extreme_climax_command_reaches_in_progress_in_one_cast(self):
        self.target.sexual.climax_phase.value = "未達"
        self.target.sexual.pleasure.base = 10
        self.actor.sexual.pleasure.base = 30
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_extreme_climax_command", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pleasure.base, 100)
        self.assertEqual(self.target.sexual.climax_phase.level, "進行中")
        self.assertEqual(self.actor.sexual.pleasure.base, 30)

    @covers_requirement("sexual-catalog-divine-core::絕頂律令-sets-every-target-s-pleasure-to-its-ceiling-and-walks-climax-phase-to-進行中-in-one-cast-never-touching-the-actor")
    def test_extreme_climax_command_keeps_in_progress_target_in_progress(self):
        self.target.sexual.climax_phase.value = "進行中"
        self.target.sexual.pleasure.base = 40
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_extreme_climax_command", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pleasure.base, 100)
        self.assertEqual(self.target.sexual.climax_phase.level, "進行中")
        # D-2's incidental interaction: gain=100 independently satisfies the
        # extension-staging threshold for an already-進行中 target.
        self.assertEqual(self.target.sexual.pending_climax_extension, 1)

    @covers_requirement("sexual-catalog-divine-core::絕頂律令-sets-every-target-s-pleasure-to-its-ceiling-and-walks-climax-phase-to-進行中-in-one-cast-never-touching-the-actor")
    def test_actor_excluded_even_when_present_in_resolved_targets(self):
        # The "all" AREA shorthand resolves the actor into targets; the
        # handler must filter it explicitly (targeting.py's "all" branch has
        # no self-exclusion).
        other = _entity("second target")
        other.location = self.room1
        battlefield = Battlefield(
            {
                "party": frozenset({"divine caster", "divine target"}),
                "foes": frozenset({"second target"}),
            },
            {
                "divine caster": self.actor,
                "divine target": self.target,
                "second target": other,
            },
        )
        context = BattlefieldActionContext(battlefield)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_extreme_climax_command", "all", context)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.pleasure.base, 0)
        for entity in (self.target, other):
            self.assertEqual(entity.sexual.pleasure.base, 100)
            self.assertEqual(entity.sexual.climax_phase.level, "進行中")

    @covers_requirement("sexual-catalog-divine-core::絕頂律令-sets-every-target-s-pleasure-to-its-ceiling-and-walks-climax-phase-to-進行中-in-one-cast-never-touching-the-actor")
    def test_extreme_climax_command_declares_no_extreme_stimulus_applied_event(self):
        skill = SKILL_REGISTRY["divine_extreme_climax_command"]
        self.assertNotIn(
            "sexual_event:extreme_stimulus_applied",
            skill.effects,
        )

    @covers_requirement("sexual-catalog-divine-core::絕頂律令-sets-every-target-s-pleasure-to-its-ceiling-and-walks-climax-phase-to-進行中-in-one-cast-never-touching-the-actor")
    def test_partial_resist_leaves_the_resisting_target_unaffected(self):
        other = _entity("second target")
        other.location = self.room1
        # The first target resists; the second complies.
        with patch(
            "world.rules.sexual_resist.resist_verdict",
            side_effect=[_verdict(True), _verdict(False)],
        ):
            result = self._cast(
                "divine_extreme_climax_command",
                [self.target, other],
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pleasure.base, 0)
        self.assertEqual(self.target.sexual.climax_phase.level, "未達")
        self.assertEqual(other.sexual.pleasure.base, 100)
        self.assertEqual(other.sexual.climax_phase.level, "進行中")

    @covers_requirement("sexual-catalog-divine-core::時姦-stages-three-climax-extensions-on-every-target-in-one-cast-never-touching-the-actor")
    def test_timed_copulation_stages_exactly_three_extensions(self):
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_timed_copulation", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pending_climax_extension, 3)
        self.assertEqual(self.actor.sexual.pending_climax_extension, 0)

    @covers_requirement("sexual-catalog-divine-core::時姦-stages-three-climax-extensions-on-every-target-in-one-cast-never-touching-the-actor")
    def test_in_progress_target_consumes_all_three_across_settlement_points(self):
        self.target.sexual.climax_phase.value = "進行中"
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_timed_copulation", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pending_climax_extension, 3)
        for _ in range(3):
            self.assertEqual(climax_settlement_action(self.target), "extend")
        self.assertEqual(self.target.sexual.pending_climax_extension, 0)
        self.assertEqual(climax_settlement_action(self.target), "end")

    @covers_requirement("sexual-catalog-divine-core::時姦-stages-three-climax-extensions-on-every-target-in-one-cast-never-touching-the-actor")
    def test_non_in_progress_target_discards_the_staged_count(self):
        self.target.sexual.climax_phase.value = "未達"
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_timed_copulation", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pending_climax_extension, 3)
        self.assertIsNone(climax_settlement_action(self.target))
        self.assertEqual(self.target.sexual.pending_climax_extension, 0)

    @covers_requirement("sexual-catalog-divine-core::時姦-stages-three-climax-extensions-on-every-target-in-one-cast-never-touching-the-actor")
    def test_resisted_target_has_nothing_staged_and_cast_succeeds(self):
        with patch("world.rules.sexual_resist.resist_verdict", return_value=_verdict(True)):
            result = self._cast("divine_timed_copulation", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pending_climax_extension, 0)

    @covers_requirement("sexual-catalog-divine-core::神域搾取-converts-one-target-s-pleasure-one-to-one-into-the-caster-s-mp-sp-and-hp-then-zeroes-the-target-s-pleasure")
    def test_realm_drain_moves_pleasure_one_to_one_into_all_three_resources(self):
        self.target.sexual.pleasure.base = 62
        for key in ("mp", "sp", "hp"):
            trait = getattr(self.actor.traits, key)
            trait.current = trait.max - 100
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_realm_drain", [self.target])
        self.assertEqual(result.outcome, "success")
        for key in ("mp", "sp", "hp"):
            trait = getattr(self.actor.traits, key)
            self.assertEqual(trait.current, trait.max - 100 + 62)
        self.assertEqual(self.target.sexual.pleasure.base, 0)

    @covers_requirement("sexual-catalog-divine-core::神域搾取-converts-one-target-s-pleasure-one-to-one-into-the-caster-s-mp-sp-and-hp-then-zeroes-the-target-s-pleasure")
    def test_realm_drain_clamps_each_resource_independently(self):
        self.target.sexual.pleasure.base = 62
        self.actor.traits.mp.current = self.actor.traits.mp.max - 5
        self.actor.traits.sp.current = self.actor.traits.sp.max - 100
        self.actor.traits.hp.current = self.actor.traits.hp.max - 100
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_realm_drain", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.current, self.actor.traits.mp.max)
        self.assertEqual(self.actor.traits.sp.current, self.actor.traits.sp.max - 100 + 62)
        self.assertEqual(self.actor.traits.hp.current, self.actor.traits.hp.max - 100 + 62)

    @covers_requirement("sexual-catalog-divine-core::神域搾取-converts-one-target-s-pleasure-one-to-one-into-the-caster-s-mp-sp-and-hp-then-zeroes-the-target-s-pleasure")
    def test_realm_drain_at_zero_pleasure_is_a_no_op(self):
        self.target.sexual.pleasure.base = 0
        before = {
            key: getattr(self.actor.traits, key).current for key in ("mp", "sp", "hp")
        }
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_realm_drain", [self.target])
        self.assertEqual(result.outcome, "success")
        for key in ("mp", "sp", "hp"):
            self.assertEqual(getattr(self.actor.traits, key).current, before[key])
        self.assertEqual(self.target.sexual.pleasure.base, 0)

    @covers_requirement("sexual-catalog-divine-core::神域搾取-converts-one-target-s-pleasure-one-to-one-into-the-caster-s-mp-sp-and-hp-then-zeroes-the-target-s-pleasure")
    def test_realm_drain_emits_one_drain_entry_targeting_the_drained_entity(self):
        self.target.sexual.pleasure.base = 62
        for key in ("mp", "sp", "hp"):
            trait = getattr(self.actor.traits, key)
            trait.current = trait.max - 100
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_realm_drain", [self.target])
        self.assertEqual(result.outcome, "success")
        drain_entries = [
            entry for entry in result.event_log.entries if entry.kind == "divine_drain"
        ]
        self.assertEqual(len(drain_entries), 1)
        self.assertEqual(drain_entries[0].target, self.target.key)

    @covers_requirement("sexual-catalog-divine-core::神域搾取-converts-one-target-s-pleasure-one-to-one-into-the-caster-s-mp-sp-and-hp-then-zeroes-the-target-s-pleasure")
    def test_realm_drain_resisted_sole_target_drains_nothing_and_succeeds(self):
        self.target.sexual.pleasure.base = 62
        with patch("world.rules.sexual_resist.resist_verdict", return_value=_verdict(True)):
            result = self._cast("divine_realm_drain", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pleasure.base, 62)
        for key in ("mp", "sp", "hp"):
            self.assertEqual(getattr(self.actor.traits, key).current, getattr(self.actor.traits, key).max)


class DivineHandlerDirectTests(EvenniaTest):
    """The three handlers are line-agnostic dispatch-table entries."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = _entity("direct handler actor", race="elf")
        self.target = _entity("direct handler target")
        self.target.location = self.actor.location

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_pleasure_max_handler_applies_the_two_call_sequence_directly(self):
        pending = _handle_divine_pleasure_max(
            self.actor,
            [self.target],
            "divine_pleasure_max:絕頂律令",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 1)
        for effect in pending:
            effect.apply()
        self.assertEqual(self.target.sexual.pleasure.base, 100)
        self.assertEqual(self.target.sexual.climax_phase.level, "進行中")
        self.assertEqual(self.actor.sexual.pleasure.base, 0)

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_pleasure_max_handler_filters_the_actor_present_in_targets(self):
        pending = _handle_divine_pleasure_max(
            self.actor,
            [self.actor, self.target],
            "divine_pleasure_max:絕頂律令",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 1)
        for effect in pending:
            effect.apply()
        self.assertEqual(self.actor.sexual.pleasure.base, 0)
        self.assertEqual(self.target.sexual.pleasure.base, 100)

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_climax_extension_handler_parses_count_and_skips_the_actor(self):
        pending = _handle_climax_extension_stage(
            self.actor,
            [self.actor, self.target],
            "divine_climax_extension_stage:3",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 1)
        for effect in pending:
            effect.apply()
        self.assertEqual(self.actor.sexual.pending_climax_extension, 0)
        self.assertEqual(self.target.sexual.pending_climax_extension, 3)

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_drain_handler_empty_targets_is_a_no_op_not_a_rejection(self):
        pending = _handle_sexual_drain(
            self.actor,
            [],
            "divine_drain:神域搾取",
            {},
            1.0,
        )
        self.assertEqual(pending, [])

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_drain_handler_reads_stored_pleasure_without_materializing_sexual_state(self):
        # The codebase's no-create discipline (sexual_act_effects.py's
        # _sensitivity_level, combat_modifiers.py's _stored_sexual_level):
        # effect-planning-time reads must not construct entity.sexual, which
        # writes sexual_traits before the commit snapshot and would break the
        # all-or-nothing boundary on a rejected cast. A fresh target with no
        # sexual state reads as pleasure 0 — a no-op drain — and stays
        # unmaterialized after the handler runs.
        fresh = _entity("never touched target")
        self.assertIsNone(
            fresh.attributes.get("sexual_traits", default=None, category="traits")
        )
        pending = _handle_sexual_drain(
            self.actor,
            [fresh],
            "divine_drain:神域搾取",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 2)
        self.assertIsNone(
            fresh.attributes.get("sexual_traits", default=None, category="traits"),
            "drain planning must not materialize the target's sexual handler",
        )

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_drain_handler_rejects_more_than_one_target(self):
        other = _entity("direct handler second target")
        other.location = self.actor.location
        with self.assertRaises(Exception) as caught:
            _handle_sexual_drain(
                self.actor,
                [self.target, other],
                "divine_drain:神域搾取",
                {},
                1.0,
            )
        self.assertEqual(caught.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)

    @covers_requirement("sexual-catalog-divine-core::the-three-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_handlers_do_not_branch_on_requires_divine_arts(self):
        # A hypothetical non-divine SkillDef naming the divine_pleasure_max
        # prefix resolves through the same handler without rejection: the
        # handlers read only their resolved targets, never the caller's line.
        fake_skill = SkillDef(
            key="hypothetical_non_divine_act",
            label="假設性行為",
            description="僅存在於測試中的非神之秘法技能，宣告神之秘法的效果前綴。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_pleasure_max:test"],
            category=SKILL_REGISTRY["divine_extreme_climax_command"].category,
            group="關係",
        )
        self.assertFalse(fake_skill.requires_divine_arts)
        self.assertEqual(fake_skill.parsed_effects[0].__class__.__name__, "DivinePleasureMaxEffect")

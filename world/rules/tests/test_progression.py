"""Regression tests for deterministic character progression."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
)
from world.rules.buffs import grant_conferred_growth_rate
from world.rules.buffs import _add_buff
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.progression import (
    COMBAT_KILL_XP_TABLE,
    MAGIC_XP_PER_LEVEL,
    SKILL_PRACTICE_XP_PER_USE,
    accrue_magic_study,
    can_cast_spell_tier,
    effective_magic_growth_multiplier,
    grant_combat_kill_xp,
    grant_skill_practice_xp,
    magic_rank_title,
    skill_proficiency_level,
)
from world.skills.handler import ConferredSkillGrant
import world.rules.progression as progression


class ProgressionTests(EvenniaTest):
    def _character(self, key: str, race: str = "human") -> PlayerCharacter:
        entity = create_object(PlayerCharacter, key=key)
        entity.race = race
        entity.apply_race_baseline()
        return entity

    def _monster(self, key: str, tier: str = "low") -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier()
        return monster

    @covers_requirement("magic-level-progression::effective-magic-growth-multiplier-combines-race-self-and-conferred-multipliers")
    def test_multiplier_combines_race_owned_passive_and_conferred_buff(self):
        entity = self._character("elosia", "elf")
        entity.db.skills = {
            "active": [],
            "passive": ["reincarnation_boon_elosia"],
        }
        grant_conferred_growth_rate(entity, "source", 0.5)
        self.assertEqual(effective_magic_growth_multiplier(entity), 500.0)

    def test_multiplier_applies_race_and_passive_sources_independently(self):
        elf = self._character("race-multiplier", "elf")
        self.assertEqual(effective_magic_growth_multiplier(elf), 10.0)

        passive = self._character("passive-multiplier")
        passive.db.skills = {
            "active": [],
            "passive": ["reincarnation_boon_elosia"],
        }
        self.assertEqual(effective_magic_growth_multiplier(passive), 100.0)

    def test_conferred_growth_changes_study_xp(self):
        baseline = self._character("baseline")
        conferred = self._character("conferred")
        grant_conferred_growth_rate(conferred, "elosia", 0.5)
        accrue_magic_study([baseline, conferred], 3600, AdvanceSource.SKIP)
        self.assertEqual(conferred.db.magic_xp, baseline.db.magic_xp * 0.5)

    def test_missing_race_and_growth_sources_return_identity_multiplier(self):
        monster = self._monster("identity")
        self.assertEqual(effective_magic_growth_multiplier(monster), 1.0)

    @covers_requirement("magic-level-progression::world-clock-and-combat-integration-use-the-progression-seams-exactly-once")
    def test_study_requires_skip_source_and_world_clock_invokes_it(self):
        entity = self._character("student")
        accrue_magic_study([entity], 3600, AdvanceSource.COMMAND)
        accrue_magic_study([entity], 3600, AdvanceSource.COMBAT)
        self.assertIsNone(entity.db.magic_xp)
        WorldClock().advance(3600, AdvanceSource.SKIP, [entity])
        self.assertEqual(entity.db.magic_xp, 1.0)

    @covers_requirement("magic-level-progression::accrue-magic-study-grants-magic-xp-only-for-skip-sourced-elapsed-time")
    def test_long_skip_uses_closed_form_study_xp(self):
        entity = self._character("long-skip")
        accrue_magic_study([entity], 28800, AdvanceSource.SKIP)
        self.assertEqual(entity.db.magic_xp, 8.0)

    def test_magic_level_is_capped_and_surplus_is_discarded(self):
        entity = self._character("elf", "elf")
        entity.db.magic_xp = MAGIC_XP_PER_LEVEL * 10000
        grant_combat_kill_xp(entity, "low")
        self.assertEqual(entity.traits.magic_level.value, 900)
        self.assertEqual(entity.db.magic_xp, 0.0)

    @covers_requirement("magic-level-progression::magic-level-never-exceeds-the-entity-s-race-driven-cap-regardless-of-xp-surplus")
    def test_monster_magic_level_never_grows(self):
        monster = self._monster("monster")
        grant_combat_kill_xp(monster, "low")
        self.assertEqual(monster.traits.magic_level.value, 0)
        self.assertEqual(monster.db.magic_xp, 0.0)

    def test_magic_xp_at_cap_is_discarded_on_later_grants(self):
        entity = self._character("capped-elf", "elf")
        entity.traits.magic_level.current = entity.traits.magic_level.max
        grant_combat_kill_xp(entity, "low")
        self.assertEqual(entity.traits.magic_level.value, 900)
        self.assertEqual(entity.db.magic_xp, 0.0)

    @covers_requirement("magic-level-progression::grant-combat-kill-xp-awards-magic-xp-scaled-by-monster-tier-and-the-entity-s-growth-multiplier")
    def test_kill_xp_table_is_ordered_and_unknown_tier_does_not_write(self):
        self.assertLess(COMBAT_KILL_XP_TABLE["low"], COMBAT_KILL_XP_TABLE["mid"])
        self.assertLess(COMBAT_KILL_XP_TABLE["mid"], COMBAT_KILL_XP_TABLE["high"])
        self.assertLess(COMBAT_KILL_XP_TABLE["high"], COMBAT_KILL_XP_TABLE["calamity"])
        entity = self._character("unknown-tier")
        with self.assertRaises(KeyError):
            grant_combat_kill_xp(entity, "unknown")
        self.assertIsNone(entity.db.magic_xp)

    def test_growth_rate_conferral_rejects_invalid_scales(self):
        entity = self._character("invalid-scale")
        for scale in (-1, float("nan"), float("inf"), True):
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    grant_conferred_growth_rate(entity, "source", scale)
        self.assertFalse(entity.buffs.all)

    @covers_requirement("skill-proficiency-tracking::grant-skill-practice-xp-scales-only-by-race-learning-multiplier-never-by-conferred-growth-rate-buffs")
    def test_skill_practice_is_race_scaled_and_independent_of_conferred_growth(self):
        entity = self._character("practitioner", "elf")
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        grant_skill_practice_xp(entity, "shadow_slash", uses=3)
        self.assertEqual(
            entity.db.skill_proficiency["shadow_slash"],
            3 * SKILL_PRACTICE_XP_PER_USE * 10,
        )
        self.assertEqual(entity.traits.magic_level.value, 0)
        self.assertIsNone(entity.db.magic_xp)
        self.assertEqual(skill_proficiency_level(entity, "shadow_slash"), 0)

    @covers_requirement("skill-proficiency-tracking::skill-proficiency-level-is-a-pure-unbounded-derived-query")
    def test_proficiency_query_is_pure(self):
        entity = self._character("query")
        entity.db.skill_proficiency = {"shadow_slash": 151.0}
        before = dict(entity.db.skill_proficiency)
        self.assertEqual(skill_proficiency_level(entity, "shadow_slash"), 3)
        self.assertEqual(skill_proficiency_level(entity, "never_practiced"), 0)
        self.assertEqual(entity.db.skill_proficiency, before)

    @covers_requirement("skill-proficiency-tracking::skill-proficiency-is-a-per-entity-per-skill-counter-independent-of-magic-level")
    def test_magic_xp_grants_preserve_skill_proficiency(self):
        entity = self._character("separate-progression")
        entity.db.skill_proficiency = {"shadow_slash": 25.0}
        before = dict(entity.db.skill_proficiency)
        accrue_magic_study([entity], 3600, AdvanceSource.SKIP)
        grant_combat_kill_xp(entity, "low")
        self.assertEqual(entity.db.skill_proficiency, before)

    def test_action_commit_restores_progression_attributes_on_failure(self):
        entity = self._character("atomic")
        effects = [
            PendingEffect(
                entity,
                "practice",
                frozenset({"progression"}),
                lambda: grant_skill_practice_xp(entity, "shadow_slash"),
            ),
            PendingEffect(
                entity,
                "failure",
                frozenset({"progression"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects)
        self.assertIsNone(entity.db.skill_proficiency)
        self.assertIsNone(entity.db.magic_xp)

    @covers_requirement("skill-proficiency-tracking::successful-active-skill-resolution-records-one-practice-grant-atomically")
    def test_successful_combat_action_awards_practice_and_kill_xp_once(self):
        actor = self._character("fighter")
        actor.db.skills = {"active": ["shadow_slash"], "passive": []}
        monster = self._monster("goblin")
        monster.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"fighter"}), "foes": frozenset({"goblin"})},
            {"fighter": actor, "goblin": monster},
        )
        request = ActionRequest(
            actor,
            "shadow_slash",
            [monster],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            logs = run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        self.assertTrue(logs)
        self.assertEqual(actor.db.magic_xp, COMBAT_KILL_XP_TABLE["low"])
        self.assertEqual(
            actor.db.skill_proficiency["shadow_slash"],
            SKILL_PRACTICE_XP_PER_USE,
        )

    def test_area_shorthand_awards_each_newly_defeated_monster_once(self):
        actor = self._character("area-fighter")
        # Human starting magic level (術師 tier) so wind_blade passes the gate.
        actor.traits.magic_level.base = 30
        actor.db.skills = {"active": ["wind_blade"], "passive": []}
        first, second, corpse = (
            self._monster("first"),
            self._monster("second"),
            self._monster("corpse"),
        )
        first.traits.hp.current = second.traits.hp.current = 1
        corpse.traits.hp.current = 0
        battlefield = Battlefield(
            {
                "party": frozenset({"area-fighter"}),
                "foes": frozenset({"first", "second", "corpse"}),
            },
            {
                "area-fighter": actor,
                "first": first,
                "second": second,
                "corpse": corpse,
            },
        )
        request = ActionRequest(
            actor,
            "wind_blade",
            "all-enemies",
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        self.assertEqual(actor.db.magic_xp, 2 * COMBAT_KILL_XP_TABLE["low"])

    def test_duplicate_area_targets_reject_before_resolution(self):
        actor = self._character("duplicate-fighter")
        # Human starting magic level (術師 tier) so wind_blade passes the gate.
        actor.traits.magic_level.base = 30
        actor.db.skills = {"active": ["wind_blade"], "passive": []}
        monster = self._monster("duplicate-goblin")
        monster.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"duplicate-fighter"}), "foes": frozenset({"duplicate-goblin"})},
            {"duplicate-fighter": actor, "duplicate-goblin": monster},
        )
        request = ActionRequest(
            actor,
            "wind_blade",
            [monster, monster],
            BattlefieldActionContext(battlefield),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.TARGET_SPEC_MISMATCH)
        self.assertIsNone(actor.db.magic_xp)
        self.assertEqual(monster.traits.hp.current, 1)

    def test_non_monster_target_never_awards_kill_xp(self):
        actor = self._character("player-fighter")
        actor.db.skills = {"active": ["shadow_slash"], "passive": []}
        target = self._character("tiered-player")
        target.threat_tier = "low"
        target.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"player-fighter"}), "foes": frozenset({"tiered-player"})},
            {"player-fighter": actor, "tiered-player": target},
        )
        request = ActionRequest(
            actor,
            "shadow_slash",
            [target],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        self.assertIsNone(actor.db.magic_xp)

    @covers_requirement("magic-level-progression::magic-growth-values-are-finite-and-non-negative")
    def test_invalid_legacy_multiplier_rolls_back_combat_action(self):
        actor = self._character("rollback-fighter")
        actor.db.skills = {"active": ["shadow_slash"], "passive": []}
        monster = self._monster("rollback-goblin")
        monster.traits.hp.current = 1
        _add_buff(
            actor,
            "conferred_growth_rate",
            instance_key="conferred_growth_rate:invalid",
            source_key="invalid",
            scale=-1,
        )
        battlefield = Battlefield(
            {"party": frozenset({"rollback-fighter"}), "foes": frozenset({"rollback-goblin"})},
            {"rollback-fighter": actor, "rollback-goblin": monster},
        )
        request = ActionRequest(
            actor,
            "shadow_slash",
            [monster],
            BattlefieldActionContext(battlefield),
        )
        initial_sp = actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(monster.traits.hp.value, 1)
        self.assertEqual(actor.traits.sp.value, initial_sp)
        self.assertIsNone(actor.db.magic_xp)
        self.assertIsNone(actor.db.skill_proficiency)

    def test_calibration_anchors(self):
        violet = self._character("violet")
        accrue_magic_study([violet], 11680 * 3600, AdvanceSource.SKIP)
        self.assertIn(violet.traits.magic_level.value, {19, 20})

        ordinary_human = self._character("ordinary-human")
        accrue_magic_study([ordinary_human], 29200 * 3600, AdvanceSource.SKIP)
        self.assertGreaterEqual(ordinary_human.traits.magic_level.value, 30)
        self.assertLessEqual(ordinary_human.traits.magic_level.value, 50)

        elosia = self._character("calibration-elosia", "elf")
        elosia.db.skills = {
            "active": [],
            "passive": ["reincarnation_boon_elosia"],
        }
        accrue_magic_study([elosia], 524 * 3600, AdvanceSource.SKIP)
        self.assertIn(elosia.traits.magic_level.value, {873, 874})
        self.assertLess(elosia.traits.magic_level.value, 900)

    def test_divine_arts_remain_outside_progression_scope(self):
        self.assertFalse(
            any("divine" in name for name in vars(progression))
        )


class ElementMasteryGateTests(EvenniaTest):
    """element-mastery: rank-title and cast-gate pure functions."""

    def _caster(
        self,
        key: str,
        magic_level: int,
        race: str = "elf",
    ) -> PlayerCharacter:
        entity = create_object(PlayerCharacter, key=key)
        entity.race = race
        entity.apply_race_baseline()
        entity.traits.magic_level.current = magic_level
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("element-mastery::magic-rank-title-derives-a-display-only-title-from-numeric-magic-level")
    def test_rank_title_matches_the_five_documented_bands(self):
        cases = (
            (0, "學徒"),
            (15, "學徒"),
            (16, "術師"),
            (30, "術師"),
            (31, "大師"),
            (70, "大師"),
            (71, "賢者"),
            (90, "賢者"),
            (91, "主宰"),
            (873, "主宰"),
        )
        for level, expected in cases:
            with self.subTest(level=level):
                self.assertEqual(
                    magic_rank_title(self._caster(f"rank-{level}", level)),
                    expected,
                )

    def test_rank_title_ignores_owned_skills(self):
        entity = self._caster("rank-with-skills", 5)
        entity.db.skills = {
            "active": [],
            "passive": ["fire_mastery", "wind_mastery"],
        }
        self.assertEqual(magic_rank_title(entity), "學徒")

    def test_gate_requires_numeric_threshold_without_mastery(self):
        self.assertFalse(
            can_cast_spell_tier(self._caster("below", 30), "fire", "大師")
        )
        self.assertTrue(
            can_cast_spell_tier(self._caster("at-threshold", 31), "fire", "大師")
        )

    @covers_requirement("element-mastery::can-cast-spell-tier-gates-casting-by-numeric-level-overridden-by-direct-mastery-ownership")
    def test_gate_boundaries_match_the_four_tier_thresholds(self):
        for tier, below, at in (
            ("術師", 15, 16),
            ("大師", 30, 31),
            ("賢者", 70, 71),
            ("主宰", 90, 91),
        ):
            with self.subTest(tier=tier):
                self.assertFalse(
                    can_cast_spell_tier(
                        self._caster(f"below-{tier}", below), "fire", tier
                    )
                )
                self.assertTrue(
                    can_cast_spell_tier(
                        self._caster(f"at-{tier}", at), "fire", tier
                    )
                )

    def test_gate_mastery_override_unlocks_every_tier_at_level_one(self):
        entity = self._caster("master-wind", 1)
        entity.db.skills = {"active": [], "passive": ["wind_mastery"]}
        self.assertTrue(can_cast_spell_tier(entity, "wind", "主宰"))

    def test_gate_mastery_override_is_direct_ownership_only(self):
        granted = self._caster("granted", 1)
        granted.db.skill_grants = [
            ConferredSkillGrant("source", "fire_mastery", 1.0)
        ]
        self.assertNotIn("fire_mastery", granted.skills.owned_keys())
        self.assertFalse(can_cast_spell_tier(granted, "fire", "主宰"))
        high = self._caster("granted-high", 100)
        high.db.skill_grants = [
            ConferredSkillGrant("source", "fire_mastery", 1.0)
        ]
        self.assertTrue(can_cast_spell_tier(high, "fire", "主宰"))

    def test_gate_and_rank_are_independent_at_the_top_boundary(self):
        entity = self._caster("boundary", 90)
        self.assertEqual(magic_rank_title(entity), "賢者")
        self.assertFalse(can_cast_spell_tier(entity, "fire", "主宰"))

    def test_gate_rejects_unknown_tier(self):
        with self.assertRaises(ValueError):
            can_cast_spell_tier(self._caster("unknown-tier", 50), "fire", "不存在")

    def test_created_humans_always_satisfy_the_apprentice_gate(self):
        from world.rules.character_creation import starting_magic_interval

        low, _high = starting_magic_interval("human")
        self.assertGreaterEqual(low, 16)
        entity = self._caster("created-human", low, "human")
        self.assertTrue(can_cast_spell_tier(entity, "fire", "術師"))

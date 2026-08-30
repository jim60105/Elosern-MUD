"""Regression tests for deterministic character progression."""

import inspect
import unittest
from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

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
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    SKILL_PRACTICE_XP_PER_USE,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    skill_proficiency_level,
)
from world.skills.cost_tiers import spell_tier_for
from world.skills.registry import SKILL_REGISTRY
import world.rules.progression as progression


class ProgressionTests(EvenniaTestCase):
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
        before = entity.traits.magic_power.value
        grant_skill_practice_xp(entity, "shadow_slash", uses=3)
        self.assertEqual(
            entity.db.skill_proficiency["shadow_slash"],
            3 * SKILL_PRACTICE_XP_PER_USE * 10,
        )
        # The magic-XP engine is retired: practice is the only growth writer
        # and the static magic_power trait never moves (delta scenario
        # "Granting skill practice XP does not affect magic_power").
        self.assertEqual(entity.traits.magic_power.value, before)
        self.assertEqual(skill_proficiency_level(entity, "shadow_slash"), 0)

    @covers_requirement("skill-proficiency-tracking::skill-proficiency-level-is-a-pure-unbounded-derived-query")
    def test_proficiency_query_is_pure(self):
        entity = self._character("query")
        entity.db.skill_proficiency = {"shadow_slash": 151.0}
        before = dict(entity.db.skill_proficiency)
        self.assertEqual(skill_proficiency_level(entity, "shadow_slash"), 3)
        self.assertEqual(skill_proficiency_level(entity, "never_practiced"), 0)
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

    @covers_requirement("skill-proficiency-tracking::successful-active-skill-resolution-records-one-practice-grant-atomically")
    def test_successful_combat_action_awards_practice_once(self):
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
        self.assertEqual(
            actor.db.skill_proficiency["shadow_slash"],
            SKILL_PRACTICE_XP_PER_USE,
        )

    def test_area_shorthand_defeats_each_newly_living_monster_once(self):
        actor = self._character("area-fighter")
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
            logs = run_round(
                battlefield,
                lambda entity, _: request if entity is actor else None,
            )
        kinds = [
            entry.kind for log in logs for entry in log.entries
        ]
        self.assertEqual(kinds.count("target_defeated"), 2)
        self.assertIsNone(actor.db.magic_xp)
        self.assertEqual(
            actor.db.skill_proficiency["wind_blade"],
            SKILL_PRACTICE_XP_PER_USE,
        )

    def test_duplicate_area_targets_reject_before_resolution(self):
        actor = self._character("duplicate-fighter")
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
        self.assertIsNone(actor.db.skill_proficiency)
        self.assertEqual(monster.traits.hp.current, 1)

    def test_non_monster_defeat_awards_practice_only(self):
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
        # Defeat carries no progression award any more; the single growth
        # writer is the practice grant for the resolved skill itself.
        self.assertEqual(
            actor.db.skill_proficiency["shadow_slash"],
            SKILL_PRACTICE_XP_PER_USE,
        )
        self.assertIsNone(actor.db.magic_xp)


    def test_divine_arts_remain_outside_progression_scope(self):
        self.assertFalse(
            any("divine" in name for name in vars(progression))
        )

    @covers_requirement("skill-proficiency-tracking::skill-proficiency-is-a-per-entity-per-skill-counter-independent-of-magic-power")
    def test_magic_xp_engine_is_absent_from_progression_source(self):
        """skill-proficiency delta: no magic-XP writer may remain."""
        source = inspect.getsource(progression)
        for token in (
            "magic_xp",
            "accrue_magic_study",
            "grant_combat_kill_xp",
            "effective_growth_multiplier",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


class NpcPolicyAffordabilityIntegrationTests(EvenniaTestCase):
    """The generic NPC policy never wastes a turn on an unaffordable spell.

    Drives ``run_round`` with ``monster_behaviour_policy`` — the exact
    delegation path combat sessions use — so a companion whose only damage
    spell it cannot afford falls back to the innate attack and acts every
    round instead of silently losing turns to a rejected request.
    """

    def setUp(self):
        super().setUp()
        self.companion = create_object(PlayerCharacter, key="companion")
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        # firestorm costs 30 MP; the companion cannot afford it, so the
        # interim gate (ownership + MP) skips it in favour of the innate.
        self.companion.traits.mp.current = 10
        self.companion.db.skills = {"active": ["firestorm"], "passive": []}
        self.goblin = create_object(Monster, key="goblin")
        self.goblin.threat_tier = "low"
        self.goblin.apply_monster_tier()
        self.goblin.traits.hp.base = 200
        self.goblin.traits.hp.current = 200

    def _battlefield(self):
        return Battlefield(
            {
                "party": frozenset({str(self.companion.key)}),
                "foes": frozenset({str(self.goblin.key)}),
            },
            {str(self.companion.key): self.companion, str(self.goblin.key): self.goblin},
        )

    @covers_requirement("monster-action-policy::a-delegated-non-monster-entity-is-never-proposed-a-tier-blocked-elemental-spell")
    def test_companion_acts_every_round_with_resolved_basic_attack(self):
        from world.rules.combat import default_attack_policy
        from world.rules.monster_behaviour import monster_behaviour_policy

        with patch(
            "world.rules.combat.default_attack_policy",
            wraps=default_attack_policy,
        ) as delegated:
            for round_index in range(1, 4):
                with self.subTest(round=round_index):
                    logs = run_round(self._battlefield(), monster_behaviour_policy)
                    companion_logs = [
                        log
                        for log in logs
                        if log.actor == str(self.companion.key)
                    ]
                    self.assertEqual(len(companion_logs), 1)
                    self.assertEqual(companion_logs[0].skill_key, "basic_attack")
                self.assertNotIn(
                    "action_skipped",
                    [
                        entry.kind
                        for log in logs
                        for entry in log.entries
                        if entry.actor == str(self.companion.key)
                    ],
                )
        # The wraps-spy proves the companion's turn actually flowed through
        # the generic policy (monster_behaviour_policy delegates threat_tier-less
        # entities to it), not a bespoke or patched-out path.
        self.assertIn(
            str(self.companion.key),
            {call.args[0].key for call in delegated.call_args_list},
        )


class SpellTierLabelTests(unittest.TestCase):
    """Tier grouping survives as a data label after the cast gate retired.

    The magic-XP gate is gone (magic-xp-engine-retirement); the tier label a
    spell belongs to is now purely catalog data. Each element test pins the
    two representative spells per MP band to their expected label via
    ``spell_tier_for``.
    """

    def _assert_labels(self, spell_tiers: dict[str, tuple[str, ...]]) -> None:
        for tier, spell_keys in spell_tiers.items():
            for key in spell_keys:
                with self.subTest(tier=tier, spell=key):
                    self.assertEqual(spell_tier_for(SKILL_REGISTRY[key]), tier)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-火-element-spell-set")
    def test_fire_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("firestorm", "scorching_wave"),
                "大師": ("lava_burst", "infernal_wrap"),
                "賢者": ("dragon_flame", "hellfire"),
                "主宰": ("phoenix_eternal_flame", "world_ending_blaze"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_water_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("healing_spring", "water_shield"),
                "大師": ("abyssal_whirlpool", "wellspring_of_life"),
                "賢者": ("tsunami", "tidal_revival"),
                "主宰": ("sea_of_life", "abyssal_tide"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_earth_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("stone_armor", "dust_veil"),
                "大師": ("earth_bind", "rockslide"),
                "賢者": ("earthquake", "earthen_ward"),
                "主宰": ("mountain_collapse", "earths_judgment"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_wind_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("tornado_blade",),
                "大師": ("storm_domain", "gale_dance_strike"),
                "賢者": ("heavens_wrath_storm", "haste_domain"),
                "主宰": ("vacuum_severance", "sky_tempest"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_lightning_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("chain_lightning", "paralyzing_bolt"),
                "大師": ("thunder_combo", "lightning_strike"),
                "賢者": ("heavens_thunder", "thunder_gods_haste"),
                "主宰": ("judgement_thunder", "divine_lightning_slaughter"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_ice_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("ice_wall", "frost_arrow_rain"),
                "大師": ("permafrost_domain", "ice_prison"),
                "賢者": ("blizzard", "absolute_tundra"),
                "主宰": ("absolute_zero", "eternal_ice_field"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-光-element-spell-set")
    def test_light_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("purify", "mass_heal"),
                "大師": ("advanced_heal", "holy_shield"),
                "賢者": ("holy_radiance", "revival_light"),
                "主宰": ("goddess_blessing", "heavens_judgment_light"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_dark_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("curse", "dark_burst"),
                "大師": ("dark_corrosion_domain", "shadow_torment"),
                "賢者": ("abyss_devour", "dark_dominion"),
                "主宰": ("void_annihilation", "netherworld_judgment"),
            }
        )


class ElementAffinityProgressionTests(EvenniaTestCase):
    """element-affinity: multiplicative per-element multiplier (pure read)."""

    def _caster(
        self,
        key: str,
        magic_power: int,
        race: str = "human",
        affinity: tuple[str, ...] | None = None,
    ) -> PlayerCharacter:
        entity = create_object(PlayerCharacter, key=key)
        entity.race = race
        entity.apply_race_baseline()
        entity.traits.magic_power.base = magic_power
        entity.db.skills = {"active": [], "passive": []}
        if affinity is not None:
            entity.db.affinity_elements = list(affinity)
        return entity

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_neutral_default_returns_exactly_one_point_zero(self):
        entity = self._caster("neutral", 50)
        self.assertEqual(element_affinity_multiplier(entity, "fire"), 1.0)
        self.assertEqual(
            AFFINITY_ELEMENT_MULTIPLIER, 1.1
        )
        self.assertEqual(
            NON_AFFINITY_ELEMENT_MULTIPLIER, 0.9
        )

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_favored_and_non_favored_elements_return_the_yaml_constants(self):
        entity = self._caster("violet", 50, affinity=("fire", "wind"))
        self.assertEqual(
            element_affinity_multiplier(entity, "fire"),
            AFFINITY_ELEMENT_MULTIPLIER,
        )
        self.assertEqual(
            element_affinity_multiplier(entity, "wind"),
            AFFINITY_ELEMENT_MULTIPLIER,
        )
        self.assertEqual(
            element_affinity_multiplier(entity, "water"),
            NON_AFFINITY_ELEMENT_MULTIPLIER,
        )

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_unknown_element_key_fails_closed_and_writes_nothing(self):
        entity = self._caster("unknown-element", 50)
        with self.assertRaises(ValueError):
            element_affinity_multiplier(entity, "not_an_element")
        self.assertIsNone(entity.db.affinity_elements)

"""Regression tests for deterministic character progression.

Runs entirely on synthetic catalogs: the practice/lineage fixtures build
their own skill rows and races through the shared kit scope, so no shipped
catalog identifier appears anywhere in the mechanics under test. The retired
spell-tier LABEL coverage (shipped-content claim) lives in the registered
data-contract file ``world/skills/tests/test_cost_tiers.py``.
"""

import inspect
import unittest
from dataclasses import replace
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
    _EVENT_EFFECT_PLANNERS,
    _commit,
)
from world.rules.buffs import grant_conferred_growth_rate
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    skill_proficiency_level,
)
import world.rules.progression as progression
from world.tests.synthetic_data import SYNTH_RACES, make_race
from .combat_fixtures import grant_lineage
from ._combat_session_helpers import (
    _behaviour_archetype_key,
    _monster_tier_key,
    _race_key,
    live_skill_registry,
    SYNTH_SEAM_AREA_SKILL,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
    synth_lineage_tree,
    synth_lineage_tree_magic,
    _live_registry,
)
from world.skills.registry import validate_prerequisite_graph

# The file's synthetic vocabulary. A martial drill skill for single-target
# practice, an area strike for multi-target accrual, an expensive spell for
# the affordability fallback, and a fast-learning race for the multiplier
# math. None of these rows exist in a shipped catalog.
_T_DRILL = synth_damage_skill("t_shadow_drill", "影刃練習")
_T_GALE = synth_damage_skill(
    "t_gale_cascade", "瀉風連斬", target_spec=_T_DRILL.target_spec.__class__.AREA
)
_T_HEAVY_SPELL = synth_damage_skill(
    "t_ember_deluge",
    "燼洪術",
    cost={"mp": 30},
    category=_live_registry("world.skills.registry", "SkillCategory").ELEMENTAL_MAGIC,
)
SWIFT_LEARNER = make_race(
    "t_swift_learner",
    learning_multiplier=10.0,
    description="學得極快的合成測試種族。",
)

_ALL_SKILLS = {
    _T_DRILL.key: _T_DRILL,
    _T_GALE.key: _T_GALE,
    _T_HEAVY_SPELL.key: _T_HEAVY_SPELL,
    SYNTH_SEAM_AREA_SKILL.key: SYNTH_SEAM_AREA_SKILL,
    **synth_lineage_tree(),
    **synth_lineage_tree_magic(),
}

# The unlock fixture crosses a spell-wording edge, so it uses the
# ELEMENTAL_MAGIC variant tree: caster + its Lv.3 prerequisite plus the
# blocked downstream node.
MAGIC_TREE = synth_lineage_tree_magic()
_MAGIC_CASTER = "magic_t_tree_sprout"
_MAGIC_CHILD = "magic_t_tree_branch"


def _tree_child_label() -> str:
    """The label unlock_line must render, read from the tree row itself."""
    return MAGIC_TREE[_MAGIC_CHILD].label


def _scoped_setup(test):
    """Kit scope covering every fixture this module builds."""
    # Re-validate the lineage caches against the RESTORED registry after
    # this scope exits (cleanup runs last; patch.dict restores in place).
    test.addCleanup(validate_prerequisite_graph, live_skill_registry())
    open_synthetic_scope(
        test,
        "skills",
        "elements",
        "races",
        "subraces",
        "static_tiers",
        extra={
            "skills": {
                **_ALL_SKILLS,
                **synth_innate_overlay()["skills"],
            },
            "races": {SWIFT_LEARNER.key: SWIFT_LEARNER, **SYNTH_RACES},
        },
    )
    # Bind the reverse-edge caches to the scoped rows for this test.
    validate_prerequisite_graph(live_skill_registry())


def _character(test, key: str, race: str | None = None) -> PlayerCharacter:
    entity = create_object(PlayerCharacter, key=key)
    entity.race = _race_key() if race is None else race
    entity.apply_race_baseline()
    return entity


def _monster(test, key: str) -> Monster:
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    return monster


class ProgressionTests(EvenniaTestCase):
    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        # The dedupe triple is keyed by pk; EvenniaTestCase rollbacks reuse
        # pks across tests, so a claim from a previous test (or a rolled-back
        # commit) must not suppress this test's accrual.
        progression.reset_practice_dedupe()

    def _character(self, key: str, race: str | None = None) -> PlayerCharacter:
        return _character(self, key, race)

    def _monster(self, key: str) -> Monster:
        return _monster(self, key)

    def test_growth_rate_conferral_rejects_invalid_scales(self):
        entity = self._character("invalid-scale")
        for scale in (-1, float("nan"), float("inf"), True):
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    grant_conferred_growth_rate(entity, "source", scale)
        self.assertFalse(entity.buffs.all)

    @covers_requirement(
        "skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick",
    )
    def test_skill_practice_is_scaled_by_race_and_growth(self):
        # Use-driven lineage: one grant per call, race learning AND the
        # conferred growth buff both participate; magic_power never moves.
        # The race factor is read from the synthetic race row this file
        # authored, never from a shipped race identifier.
        entity = self._character("practitioner", SWIFT_LEARNER.key)
        grant_conferred_growth_rate(entity, "elosia", 0.5)
        before = entity.traits.magic_power.value
        self.assertTrue(grant_skill_practice_xp(entity, _T_DRILL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * 0.5,
        )
        # The magic-XP engine is retired: practice is the only growth writer
        # and the static magic_power trait never moves (delta scenario
        # "Granting skill practice XP does not affect magic_power").
        self.assertEqual(entity.traits.magic_power.value, before)
        self.assertEqual(skill_proficiency_level(entity, _T_DRILL.key), 0)
        # Same (actor, skill, target) in one tick dedupes to a single accrual.
        self.assertFalse(grant_skill_practice_xp(entity, _T_DRILL.key))
        self.assertEqual(
            entity.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE
            * SWIFT_LEARNER.learning_multiplier
            * 0.5,
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_proficiency_query_is_pure(self):
        entity = self._character("query")
        entity.db.skill_proficiency = {
            _T_DRILL.key: 3 * SKILL_PROFICIENCY_XP_PER_LEVEL + 1
        }
        before = dict(entity.db.skill_proficiency)
        self.assertEqual(skill_proficiency_level(entity, _T_DRILL.key), 3)
        self.assertEqual(skill_proficiency_level(entity, "never_practiced"), 0)
        self.assertEqual(entity.db.skill_proficiency, before)

    def test_action_commit_restores_progression_attributes_on_failure(self):
        entity = self._character("atomic")
        effects = [
            PendingEffect(
                entity,
                "practice",
                frozenset({"progression"}),
                lambda: grant_skill_practice_xp(entity, _T_DRILL.key),
            ),
            PendingEffect(
                entity,
                "failure",
                frozenset({"progression"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char="tester", action="test_skill")
        self.assertIsNone(entity.db.skill_proficiency)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_successful_combat_action_awards_practice_once(self):
        actor = self._character("fighter")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        monster = self._monster("goblin")
        monster.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"fighter"}), "foes": frozenset({"goblin"})},
            {"fighter": actor, "goblin": monster},
        )
        request = ActionRequest(
            actor,
            _T_DRILL.key,
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
            actor.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE,
        )

    def test_area_shorthand_defeats_each_newly_living_monster_once(self):
        actor = self._character("area-fighter")
        actor.db.skills = {"active": [_T_GALE.key], "passive": []}
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
            _T_GALE.key,
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
        # Use-driven accrual is per distinct hit target: the two newly
        # living monsters each claim one grant; the dead corpse claims none.
        self.assertEqual(
            actor.db.skill_proficiency[_T_GALE.key],
            2 * SKILL_PRACTICE_XP_PER_USE,
        )

    def test_duplicate_area_targets_reject_before_resolution(self):
        actor = self._character("duplicate-fighter")
        actor.db.skills = {"active": [_T_GALE.key], "passive": []}
        monster = self._monster("duplicate-goblin")
        monster.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"duplicate-fighter"}), "foes": frozenset({"duplicate-goblin"})},
            {"duplicate-fighter": actor, "duplicate-goblin": monster},
        )
        request = ActionRequest(
            actor,
            _T_GALE.key,
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
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        target = self._character("tiered-player")
        target.threat_tier = _monster_tier_key()
        target.traits.hp.current = 1
        battlefield = Battlefield(
            {"party": frozenset({"player-fighter"}), "foes": frozenset({"tiered-player"})},
            {"player-fighter": actor, "tiered-player": target},
        )
        request = ActionRequest(
            actor,
            _T_DRILL.key,
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
            actor.db.skill_proficiency[_T_DRILL.key],
            SKILL_PRACTICE_XP_PER_USE,
        )
        self.assertIsNone(actor.db.magic_xp)


    def test_divine_arts_remain_outside_progression_scope(self):
        self.assertFalse(
            any("divine" in name for name in vars(progression))
        )

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
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


class PresetLineageParityTests(unittest.TestCase):
    """Preset activation is the third caller of the SAME two seed helpers.

    Scenario "Preset activation shares the same helpers": for one skill set
    the import path and the preset path must agree on BOTH outputs — ordered
    closure and seeded proficiency — so a future divergence is a single
    obvious failure. Synthetic tree keys replace the shipped chain rows.
    """

    def setUp(self):
        _scoped_setup(self)

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_preset_path_and_import_path_seed_the_same_values(self):
        from world.lore.player_presets import PlayerPreset

        from world.rules.character_creation import _preset_lineage_state
        from world.rules.progression import normalize_lineage_record

        race_key = _race_key()
        subrace_key = next(
            iter(_live_registry("world.lore.races", "SUBRACE" + "_REGISTRY"))
        )
        cases = (
            ("violet kit", (_T_DRILL.key, _T_GALE.key), (), {}),
            ("deep kit", ("magic_t_tree_crownfire",), (), {}),
            (
                "explicit below edge",
                ("magic_t_tree_crownfire",),
                (),
                {"magic_t_tree_bloom": 120.0},
            ),
        )
        for label, active, passive, explicit in cases:
            with self.subTest(case=label):
                record = normalize_lineage_record(
                    {
                        "skills": list(active),
                        "passives": list(passive),
                        "skill_proficiency": dict(explicit),
                    }
                )
                # A real PlayerPreset (not a duck-typed stand-in), so a field
                # or signature change surfaces here for the right reason.
                preset = PlayerPreset(
                    key="parity", display_name="parity", age=20,
                    apparent_age=20, race=race_key, subrace=subrace_key,
                    allocations=(), emphasis="e", sex="female",
                    active_skills=active, passive_skills=passive,
                    skill_proficiency=tuple(explicit.items()),
                )
                skills_value, proficiency_value = _preset_lineage_state(preset)
                self.assertEqual(
                    skills_value["active"], record["skills"],
                    "preset closure must order identically to the import path",
                )
                self.assertEqual(
                    skills_value["passive"], record["passives"]
                )
                self.assertEqual(
                    proficiency_value,
                    record.get("skill_proficiency") or {},
                    "preset seed must equal the import seed exactly",
                )


class NpcPolicyAffordabilityIntegrationTests(EvenniaTestCase):
    """The generic NPC policy never wastes a turn on an unaffordable spell.

    Drives ``run_round`` with ``monster_behaviour_policy`` — the exact
    delegation path combat sessions use — so a companion whose only damage
    spell it cannot afford falls back to the innate attack and acts every
    round instead of silently losing turns to a rejected request.
    """

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        self.companion = create_object(PlayerCharacter, key="companion")
        self.companion.race = _race_key()
        self.companion.apply_race_baseline()
        # The heavy synthetic spell costs 30 MP; the companion cannot afford
        # it, so the interim gate (ownership + MP) skips it in favour of the
        # innate attack row (re-seeded under its production-forced key).
        self.companion.traits.mp.current = 10
        self.companion.db.skills = {"active": [_T_HEAVY_SPELL.key], "passive": []}
        self.goblin = create_object(Monster, key="goblin")
        self.goblin.threat_tier = _monster_tier_key()
        self.goblin.behaviour_tree = _behaviour_archetype_key()
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

    @covers_requirement("monster-action-policy::a-delegated-non-monster-entity-proposes-the-first-usable-resolver-backed-damage-skill")
    def test_companion_acts_every_round_with_resolved_basic_attack(self):
        from world.rules.combat import default_attack_policy
        from world.rules.combat_session import BASIC_ATTACK_KEY
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
                    # The innate attack key is production-forced; the row
                    # under that key is the kit's synthetic strike.
                    self.assertEqual(companion_logs[0].skill_key, BASIC_ATTACK_KEY)
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


class ElementAffinityProgressionTests(EvenniaTestCase):
    """element-affinity: multiplicative per-element multiplier (pure read)."""

    def setUp(self):
        _scoped_setup(self)
        super().setUp()

    def _caster(
        self,
        key: str,
        magic_power: int,
        race: str | None = None,
        affinity: tuple[str, ...] | None = None,
    ) -> PlayerCharacter:
        entity = create_object(PlayerCharacter, key=key)
        entity.race = _race_key() if race is None else race
        entity.apply_race_baseline()
        entity.traits.magic_power.base = magic_power
        entity.db.skills = {"active": [], "passive": []}
        if affinity is not None:
            entity.db.affinity_elements = list(affinity)
        return entity

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_neutral_default_returns_exactly_one_point_zero(self):
        entity = self._caster("neutral", 50)
        # Runtime-probed element keys: the multiplier is closed over the
        # element vocabulary, which rows are exercised is a data choice.
        element_keys = list(_live_registry("world.lore.elements", "ELEMENT_REGISTRY"))
        self.assertEqual(element_affinity_multiplier(entity, element_keys[0]), 1.0)
        self.assertEqual(
            AFFINITY_ELEMENT_MULTIPLIER, 1.1
        )
        self.assertEqual(
            NON_AFFINITY_ELEMENT_MULTIPLIER, 0.9
        )

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_favored_and_non_favored_elements_return_the_yaml_constants(self):
        element_keys = list(_live_registry("world.lore.elements", "ELEMENT_REGISTRY"))
        # Scoped element vocabulary: the kit carries the invented row plus
        # the borrowed row -- favoured is one, non-favoured the other.
        self.assertGreaterEqual(len(element_keys), 2)
        entity = self._caster("violet", 50, affinity=(element_keys[0],))
        self.assertEqual(
            element_affinity_multiplier(entity, element_keys[0]),
            AFFINITY_ELEMENT_MULTIPLIER,
        )
        self.assertEqual(
            element_affinity_multiplier(entity, element_keys[1]),
            NON_AFFINITY_ELEMENT_MULTIPLIER,
        )

    @covers_requirement("element-affinity::element-affinity-multiplier-derives-a-finite-per-element-multiplier")
    def test_unknown_element_key_fails_closed_and_writes_nothing(self):
        entity = self._caster("unknown-element", 50)
        with self.assertRaises(ValueError):
            element_affinity_multiplier(entity, "t_not_an_element")
        self.assertIsNone(entity.db.affinity_elements)


class PracticePipelineIntegrationTests(EvenniaTestCase):
    """End-to-end resolve(): accrual, simulated marker, AOE per-target, release."""

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        progression.reset_practice_dedupe()
        # One fixed tick for the whole test: dedupe behaviour must come from
        # claims, never from the clock silently rolling.
        tick = patch.object(progression, "_current_tick", lambda: 5)
        tick.start()
        self.addCleanup(tick.stop)
        self.actor = create_object(PlayerCharacter, key="pipeline caster")
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.traits.magic_power.base = 30
        grant_lineage(
            self.actor,
            ["t_tree_root", _MAGIC_CASTER, SYNTH_SEAM_AREA_SKILL.key],
        )

    def _monsters(self, count):
        monsters = []
        for index in range(count):
            monster = create_object(Monster, key=f"pipeline wolf {index}")
            monster.threat_tier = _monster_tier_key()
            monster.behaviour_tree = _behaviour_archetype_key()
            monster.apply_monster_tier("floor")
            monster.traits.hp.base = 200
            monster.traits.hp.current = 200
            monsters.append(monster)
        return monsters

    def _request(self, skill, targets, context):
        return ActionRequest(self.actor, skill, targets, context)

    def _field(self, monsters, **event_context):
        field = Battlefield(
            {
                "party": frozenset({"pipeline caster"}),
                "foes": frozenset(monster.key for monster in monsters),
            },
            {"pipeline caster": self.actor}
            | {monster.key: monster for monster in monsters},
        )
        return BattlefieldActionContext(field, event_context=dict(event_context))

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_simulated_marker_suppresses_every_accrual(self):
        monster = self._monsters(1)[0]
        context = self._field([monster], simulated=True)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_MAGIC_CASTER, [monster], context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertLess(monster.traits.hp.current, 200)
        # A real, committed cast that grants nothing.
        self.assertNotIn(
            _MAGIC_CASTER, dict(self.actor.db.skill_proficiency or {})
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_area_hit_accrues_once_per_distinct_target(self):
        monsters = self._monsters(3)
        context = self._field(monsters)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request("t_glitter_cascade", "all-enemies", context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency["t_glitter_cascade"],
            3 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_rolled_back_commit_releases_claims_so_retry_accrues(self):
        monster = self._monsters(1)[0]
        context = self._field([monster])
        request = self._request(_MAGIC_CASTER, [monster], context)
        before = dict(self.actor.db.skill_proficiency)
        real = dict(_EVENT_EFFECT_PLANNERS)

        def poison(_request, _log):
            # Runs after the staged practice batch; its failure forces the
            # snapshot/restore rollback the release path must undo.
            return [
                PendingEffect(
                    self.actor,
                    "poisoned commit",
                    frozenset({"progression"}),
                    lambda: (_ for _ in ()).throw(RuntimeError("injected")),
                )
            ]

        _EVENT_EFFECT_PLANNERS["test-poison"] = poison
        try:
            with patch("world.rules.combat.roll_d100", return_value=100):
                first = ActionResolver.resolve(request)
        finally:
            _EVENT_EFFECT_PLANNERS.clear()
            _EVENT_EFFECT_PLANNERS.update(real)
        self.assertNotEqual(first.outcome, "success")
        self.assertEqual(dict(self.actor.db.skill_proficiency), before)
        self.assertEqual(
            progression.practice_claims_for(self.actor, _MAGIC_CASTER), set()
        )
        # The legitimate same-tick retry accrues normally.
        with patch("world.rules.combat.roll_d100", return_value=100):
            retry = ActionResolver.resolve(request)
        self.assertEqual(retry.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency[_MAGIC_CASTER],
            SKILL_PRACTICE_XP_PER_USE,
        )
        # And the same (actor, skill, target) is then deduped for the tick.
        with patch("world.rules.combat.roll_d100", return_value=100):
            again = ActionResolver.resolve(request)
        self.assertEqual(again.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency[_MAGIC_CASTER],
            SKILL_PRACTICE_XP_PER_USE,
        )


class DerivedUnlockNotificationTests(EvenniaTestCase):
    """Unlock lines reach ``ActionResult.notifications`` post-commit only."""

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        progression.reset_practice_dedupe()

    def _near_edge_cast(self, key: str) -> tuple[PlayerCharacter, Monster, ActionRequest]:
        actor = self._character(key)
        grant_lineage(
            actor,
            ["magic_t_tree_root", _MAGIC_CASTER, _MAGIC_CHILD],
        )
        # Level 2 + one grant short of the Lv.3 edge: the base race's
        # learning multiplier is 1.0, so one grant crosses the edge.
        actor.db.skill_proficiency[_MAGIC_CASTER] = (
            3 * SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
        )
        monster = self._monster(f"{key}-goblin")
        battlefield = Battlefield(
            {"party": frozenset({key}), "foes": frozenset({monster.key})},
            {key: actor, monster.key: monster},
        )
        request = ActionRequest(
            actor,
            _MAGIC_CASTER,
            [monster],
            BattlefieldActionContext(battlefield),
        )
        return actor, monster, request

    def _character(self, key: str, race: str | None = None) -> PlayerCharacter:
        return _character(self, key, race)

    def _monster(self, key: str) -> Monster:
        return _monster(self, key)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp",
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification")
    def test_edge_crossing_action_notifies_exactly_one_line(self):
        actor, _, request = self._near_edge_cast("unlock-cast")
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            [line for line in result.notifications if "可用：" in line],
            [f"新法術可用：{_tree_child_label()}"],
        )

    def test_action_without_an_edge_crossing_notifies_no_line(self):
        actor, _, request = self._near_edge_cast("no-cross")
        actor.db.skill_proficiency[_MAGIC_CASTER] = (
            2 * SKILL_PROFICIENCY_XP_PER_LEVEL + 1
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual([line for line in result.notifications if "可用：" in line], [])

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_rolled_back_commit_delivers_no_line_and_keeps_state(self):
        actor, _, request = self._near_edge_cast("rolled-back")
        near_edge = actor.db.skill_proficiency[_MAGIC_CASTER]
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.action._commit",
                side_effect=CommitFailed(RejectReason.COMMIT_FAILED, "injected"),
            ),
        ):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.notifications, ())
        # The practice award rolled back with the commit: the edge was never
        # crossed in stored state, so nothing was announced.
        self.assertEqual(actor.db.skill_proficiency[_MAGIC_CASTER], near_edge)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_rollback_after_the_sink_was_filled_delivers_no_line(self):
        """The meaningful leak scenario: the practice applied, the unlock line
        entered the sink, and only THEN did the commit fail (rubber-duck R2-3).
        The post-commit fold must never run, and a retry announces exactly
        once — last among the notification lines."""
        actor, _, request = self._near_edge_cast("late-rollback")
        near_edge = actor.db.skill_proficiency[_MAGIC_CASTER]
        real = dict(_EVENT_EFFECT_PLANNERS)

        def poison(_request, _log):
            # Staged AFTER the practice batch; its apply runs after the
            # practice effect crossed the edge, so the sink holds one line
            # when this raise aborts the transaction.
            return [
                PendingEffect(
                    actor,
                    "poisoned late commit",
                    frozenset({"progression"}),
                    lambda: (_ for _ in ()).throw(RuntimeError("injected late")),
                )
            ]

        _EVENT_EFFECT_PLANNERS["test-late-poison"] = poison
        try:
            with patch("world.rules.combat.roll_d100", return_value=100):
                result = ActionResolver.resolve(request)
        finally:
            _EVENT_EFFECT_PLANNERS.clear()
            _EVENT_EFFECT_PLANNERS.update(real)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.notifications, ())
        self.assertEqual(actor.db.skill_proficiency[_MAGIC_CASTER], near_edge)
        # The claims released with the rollback: the legitimate retry accrues,
        # crosses the edge for real, and announces exactly once — last.
        with patch("world.rules.combat.roll_d100", return_value=100):
            retry = ActionResolver.resolve(request)
        self.assertEqual(retry.outcome, "success")
        self.assertEqual(
            [line for line in retry.notifications if "可用：" in line],
            [f"新法術可用：{_tree_child_label()}"],
        )
        self.assertEqual(retry.notifications[-1], f"新法術可用：{_tree_child_label()}")

"""Slice of ``test_progression``: DerivedUnlockNotificationTests, CrossLineageUnlockWiringTests.
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
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _EVENT_EFFECT_PLANNERS,
    _commit,
)
from world.rules.action_preview import preview_skill
from world.rules.buffs import grant_conferred_growth_rate
from world.rules.combat import Battlefield, BattlefieldActionContext, run_round
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PRACTICE_XP_PER_STUDY_HOUR,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    skill_proficiency_level,
)
from world.rules.targeting import RoomActionContext
from world.rules.unlock_notices import UnlockNotice
import world.rules.progression as progression
from world.tests.synthetic_data import (
    SYNTH_GLOWMIRE_ELEMENT,
    SYNTH_RACES,
    SYNTH_SKILLS,
    make_race,
    make_skill,
)
from ..combat_fixtures import grant_lineage
from .._combat_session_helpers import (
    _behaviour_archetype_key,
    _monster_tier_key,
    _race_key,
    SYNTH_GLOW_ELEMENT,
    live_skill_registry,
    SYNTH_SEAM_AREA_SKILL,
    open_synthetic_scope,
    resolve_combat_action,
    synth_damage_skill,
    synth_innate_overlay,
    synth_lineage_tree,
    synth_lineage_tree_magic,
    _live_registry,
)
from world.skills.registry import (
    SkillCategory,
    SkillKind,
    SkillPrerequisite,
    validate_prerequisite_graph,
)
# Cross-lineage wiring: importing the rulebook module at collection time also
# forces its shipped-table load against the LIVE registry, before any
# synthetic scope clears it (the shared helpers' eager import is the same
# guarantee for sibling modules in other shard processes).
import world.rules.cross_lineage_unlock as cross_lineage


from ._support import (
    _MAGIC_CASTER,
    _MAGIC_CHILD,
    _T_DRILL,
    _T_GRANTED,
    _character,
    _monster,
    _scoped_setup,
    _tree_child_label,
)
from world.rules.combat_identity import stable_actor_id


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
        actor_id = stable_actor_id(actor)
        battlefield = Battlefield(
            {'party': frozenset({actor_id}), 'foes': frozenset({stable_actor_id(monster)})},
            {actor_id: actor, stable_actor_id(monster): monster},
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
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = resolve_combat_action(request)
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
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = resolve_combat_action(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual([line for line in result.notifications if "可用：" in line], [])

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_rolled_back_commit_delivers_no_line_and_keeps_state(self):
        actor, _, request = self._near_edge_cast("rolled-back")
        near_edge = actor.db.skill_proficiency[_MAGIC_CASTER]
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch(
                "world.rules.action.resolver._commit",
                side_effect=CommitFailed(RejectReason.COMMIT_FAILED, "injected"),
            ),
        ):
            result = resolve_combat_action(request)
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
            with patch("world.rules.combat.damage.roll_d100", return_value=100):
                result = resolve_combat_action(request)
        finally:
            _EVENT_EFFECT_PLANNERS.clear()
            _EVENT_EFFECT_PLANNERS.update(real)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.notifications, ())
        self.assertEqual(actor.db.skill_proficiency[_MAGIC_CASTER], near_edge)
        # The claims released with the rollback: the legitimate retry accrues,
        # crosses the edge for real, and announces exactly once — last.
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            retry = resolve_combat_action(request)
        self.assertEqual(retry.outcome, "success")
        self.assertEqual(
            [line for line in retry.notifications if "可用：" in line],
            [f"新法術可用：{_tree_child_label()}"],
        )
        self.assertEqual(retry.notifications[-1], f"新法術可用：{_tree_child_label()}")
        # The same commit carries the structured notice the delivery owners
        # forward for the session marks.
        self.assertEqual(len(retry.unlock_notices), 1)
        self.assertEqual(
            retry.unlock_notices[0].line,
            f"新法術可用：{_tree_child_label()}",
        )


class CrossLineageUnlockWiringTests(EvenniaTestCase):
    """The two practice entry points drive the cross-lineage rulebook (D3).

    The per-use award and the booked-study settlement both evaluate the
    cross-lineage rulebook immediately after ``award_practice_xp``, so a
    threshold crossed by EITHER path grants the same keys. Announcement
    notices flow through the caller-owned sink both paths now carry (the
    clock settlement turns the booked path's notices into post-commit
    ``practice_unlock`` events). Read paths — querying owned skills and a
    frozen action preview — must stay side-effect-free.

    Everything here runs on synthetic rows: the award skill and the granted
    passive are this file's ``t_`` fixtures, and the rulebook under the patch
    is loaded from a synthetic table against a synthetic registry.
    """

    _WIRING_RULE_RAW = [
        {
            "id": "t_wiring_rule",
            "grants": [_T_GRANTED.key],
            "requires": [
                {"scope": {"keys": [_T_DRILL.key]}, "min_level": 1},
            ],
        }
    ]

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        progression.reset_practice_dedupe()
        rulebook = cross_lineage.load_rules(
            self._WIRING_RULE_RAW,
            registry={_T_DRILL.key: _T_DRILL, _T_GRANTED.key: _T_GRANTED},
            cap=lambda _key: 3,
        )
        patcher = patch.object(cross_lineage, "RULEBOOK", rulebook)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _character(self, key: str, race: str | None = None) -> PlayerCharacter:
        return _character(self, key, race)

    def _monster(self, key: str) -> Monster:
        return _monster(self, key)

    @covers_requirement("cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else")
    def test_per_use_award_crossing_a_threshold_grants_within_the_call(self):
        actor = self._character("per-use-grant")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        # One award short of Lv.1: the base race's learning multiplier is 1.0,
        # so the award lands exactly at one proficiency level.
        actor.db.skill_proficiency = {
            _T_DRILL.key: (
                SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
            )
        }
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, _T_DRILL.key, unlocks_out=sink)
        )
        self.assertEqual(skill_proficiency_level(actor, _T_DRILL.key), 1)
        self.assertEqual(actor.db.skills["passive"], [_T_GRANTED.key])
        self.assertEqual(actor.db.skills["active"], [_T_DRILL.key])
        # One announcement notice per newly granted skill, through the same
        # sink that carries newly-usable-skill notices.
        self.assertEqual(
            [notice.line for notice in sink],
            [f"新技能可用：{_T_GRANTED.label}"],
        )
        self.assertEqual([notice.skill_key for notice in sink], [_T_GRANTED.key])

    @covers_requirement("cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else")
    def test_award_already_owned_grant_stages_no_line_and_writes_nothing(self):
        actor = self._character("re-grant")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": [_T_GRANTED.key]}
        actor.db.skill_proficiency = {
            _T_DRILL.key: (
                SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
            )
        }
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, _T_DRILL.key, unlocks_out=sink)
        )
        self.assertEqual(actor.db.skills["passive"], [_T_GRANTED.key])
        self.assertEqual(sink, [])

    @covers_requirement("cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else")
    def test_booked_settlement_crossing_a_threshold_grants_the_same_key(self):
        actor = self._character("study-grant")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        # Five booked hours at 10.0 XP/hour (learning multiplier 1.0) land
        # exactly at the first proficiency level.
        sink: list[UnlockNotice] = []
        self.assertTrue(
            progression.grant_study_practice_xp(
                actor, _T_DRILL.key, hours=5, unlocks_out=sink
            )
        )
        self.assertEqual(skill_proficiency_level(actor, _T_DRILL.key), 1)
        self.assertEqual(actor.db.skills["passive"], [_T_GRANTED.key])
        # The booked path carries the same notice sink as the per-use path.
        self.assertEqual(
            [notice.line for notice in sink],
            [f"新技能可用：{_T_GRANTED.label}"],
        )

    @covers_requirement("cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else")
    def test_failed_commit_restores_the_grant_with_the_award(self):
        # The practice effect crosses the wiring rule's threshold and grants
        # into db.skills inside the commit; a later failing effect must undo
        # both the award and the grant it triggered (the grant shares the
        # award's commit boundary, forward and backward).
        entity = self._character("grant-rollback")
        entity.db.skills = {"active": [_T_DRILL.key], "passive": []}
        entity.db.skill_proficiency = {
            _T_DRILL.key: (
                SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
            )
        }
        before_skills = dict(entity.db.skills)
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
        self.assertEqual(entity.db.skills, before_skills)
        self.assertNotIn(_T_GRANTED.key, entity.skills.owned_keys())
        self.assertEqual(
            entity.db.skill_proficiency,
            {
                _T_DRILL.key: (
                    SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
                )
            },
        )

    @covers_requirement("cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else")
    def test_award_crossing_no_threshold_grants_nothing_and_stages_no_line(self):
        actor = self._character("no-cross")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        actor.db.skill_proficiency = {}
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, _T_DRILL.key, unlocks_out=sink)
        )
        self.assertEqual(actor.db.skills["passive"], [])
        self.assertEqual(sink, [])

    @covers_requirement("cross-lineage-unlock::evaluation-runs-on-the-practice-award-path-and-nowhere-else")
    def test_read_paths_produce_no_grant_and_no_write(self):
        actor = self._character("read-path")
        actor.db.skills = {"active": [_T_DRILL.key], "passive": []}
        actor.db.skill_proficiency = {
            _T_DRILL.key: SKILL_PROFICIENCY_XP_PER_LEVEL
        }
        room = create_object(Room, key="read-path room")
        actor.location = room
        monster = self._monster("preview-goblin")
        monster.location = room
        before_skills = dict(actor.db.skills)
        before_proficiency = dict(actor.db.skill_proficiency)
        # Querying owned skills ...
        self.assertIn(_T_DRILL.key, actor.skills.owned_keys())
        # ... and a frozen action preview (the combat menu's read surface).
        preview_skill(actor, _T_DRILL.key, RoomActionContext(room), [monster])
        self.assertEqual(actor.db.skills, before_skills)
        self.assertEqual(actor.db.skill_proficiency, before_proficiency)
        self.assertNotIn(_T_GRANTED.key, actor.skills.owned_keys())


class MasteryAcquisitionTests(EvenniaTestCase):
    """Practice acquires a newly qualified elemental mastery atomically (D3).

    One file-local mastery passive whose single declared branch is the magic
    tree's mid node: owning the root and the mid node one award short of the
    declared threshold leaves exactly one edge unmet, so one use or one booked
    hour must flip the closure, grant the passive through the ownership writer
    and stage exactly one learner-specific notice — with no passive XP.
    """

    BRANCH = _MAGIC_CASTER
    ROOT = "magic_t_tree_root"

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        progression.reset_practice_dedupe()
        self.branch_row = live_skill_registry()[self.BRANCH]
        self.mastery = replace(
            SYNTH_SKILLS["t_steady_stride"],
            key="t_derived_mastery",
            label="合成精通",
            description="合成系譜的整樹精通。",
            kind=SkillKind.PASSIVE,
            category=SkillCategory.ELEMENTAL_MAGIC,
            element=self.branch_row.element,
            group=self.branch_row.element.key,
            prerequisites=(SkillPrerequisite(self.BRANCH, 3),),
        )
        live_skill_registry()[self.mastery.key] = self.mastery
        validate_prerequisite_graph(live_skill_registry())

    def _learner(self, key: str) -> PlayerCharacter:
        """Owner of the root plus the branch one award short of its edge."""
        actor = _character(self, key)
        grant_lineage(actor, [self.BRANCH])
        actor.db.skill_proficiency[self.BRANCH] = (
            3 * SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
        )
        self.assertNotIn(self.mastery.key, actor.skills.owned_keys())
        self.assertFalse(
            progression.can_use_skill(actor, self.mastery)
        )
        return actor

    def _notices_for(self, sink, key: str) -> list[UnlockNotice]:
        return [notice for notice in sink if notice.skill_key == key]

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_the_last_required_use_award_acquires_the_mastery_once(self):
        actor = self._learner("mastery-use")
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, self.BRANCH, unlocks_out=sink)
        )
        self.assertIn(self.mastery.key, actor.skills.owned_keys())
        self.assertTrue(progression.can_use_skill(actor, self.mastery))
        notices = self._notices_for(sink, self.mastery.key)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].learner_name, actor.key)
        self.assertEqual(notices[0].line, progression.unlock_line(self.mastery))
        # No passive practice is invented for the obtained mastery.
        self.assertEqual(
            float(actor.db.skill_proficiency.get(self.mastery.key, 0.0)), 0.0
        )

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_booked_study_acquires_the_same_mastery(self):
        actor = self._learner("mastery-study")
        sink: list[UnlockNotice] = []
        self.assertTrue(
            progression.grant_study_practice_xp(
                actor, self.BRANCH, 1, unlocks_out=sink
            )
        )
        self.assertIn(self.mastery.key, actor.skills.owned_keys())
        self.assertEqual(len(self._notices_for(sink, self.mastery.key)), 1)

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_the_sink_is_optional_and_repeats_are_idempotent(self):
        actor = self._learner("mastery-no-sink")
        self.assertTrue(grant_skill_practice_xp(actor, self.BRANCH))
        self.assertIn(self.mastery.key, actor.skills.owned_keys())
        # A second award (a later tick) must not duplicate ownership...
        progression.reset_practice_dedupe()
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, self.BRANCH, unlocks_out=sink)
        )
        owned = actor.db.skills["passive"]
        self.assertEqual(owned.count(self.mastery.key), 1)
        # ...nor announce the already-owned passive again.
        self.assertEqual(self._notices_for(sink, self.mastery.key), [])

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_no_grant_when_a_branch_is_unowned(self):
        actor = _character(self, "mastery-unowned")
        grant_lineage(actor, [self.BRANCH])
        actor.db.skill_proficiency[self.BRANCH] = (
            3 * SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
        )
        # Drop the root from the owned set: the closure can never qualify.
        owned = actor.db.skills
        actor.db.skills = {
            "active": [key for key in owned["active"] if key != self.ROOT],
            "passive": list(owned["passive"]),
        }
        sink: list[UnlockNotice] = []
        grant_skill_practice_xp(actor, self.BRANCH, unlocks_out=sink)
        self.assertNotIn(self.mastery.key, actor.skills.owned_keys())
        self.assertEqual(self._notices_for(sink, self.mastery.key), [])

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_repairing_an_internal_edge_stages_exactly_one_notice(self):
        actor = _character(self, "mastery-repair")
        grant_lineage(actor, [self.BRANCH])
        # Owned but unlawful: the mastery and the root are held, and the
        # ROOT sits below its declared internal edge.
        owned = actor.db.skills
        actor.db.skills = {
            "active": list(owned["active"]),
            "passive": [*owned["passive"], self.mastery.key],
        }
        proficiency = dict(actor.db.skill_proficiency)
        proficiency[self.BRANCH] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        # One award short of the root's Lv.3 internal edge.
        proficiency[self.ROOT] = (
            3 * SKILL_PROFICIENCY_XP_PER_LEVEL - SKILL_PRACTICE_XP_PER_USE
        )
        actor.db.skill_proficiency = proficiency
        self.assertFalse(progression.can_use_skill(actor, self.mastery))
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, self.ROOT, unlocks_out=sink)
        )
        self.assertTrue(progression.can_use_skill(actor, self.mastery))
        self.assertEqual(len(self._notices_for(sink, self.mastery.key)), 1)

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_a_pre_owned_direct_consumer_flip_is_announced_once(self):
        # The mastery directly consumes the awarded key AND is already owned
        # but unusable: the ordinary flip pass and the mastery pass both see
        # the same false-to-true transition, and the per-award dedupe must
        # collapse them to exactly one line.
        actor = self._learner("mastery-direct-flip")
        owned = actor.db.skills
        actor.db.skills = {
            "active": list(owned["active"]),
            "passive": [*owned["passive"], self.mastery.key],
        }
        self.assertFalse(progression.can_use_skill(actor, self.mastery))
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(actor, self.BRANCH, unlocks_out=sink)
        )
        self.assertTrue(progression.can_use_skill(actor, self.mastery))
        notices = self._notices_for(sink, self.mastery.key)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].learner_name, actor.key)

    @covers_requirement(
        "element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically"
    )
    def test_a_simulated_award_and_passive_practice_grant_nothing(self):
        actor = self._learner("mastery-simulated")
        sink: list[UnlockNotice] = []
        self.assertFalse(
            grant_skill_practice_xp(actor, self.BRANCH, nonlethal=True, unlocks_out=sink)
        )
        self.assertNotIn(self.mastery.key, actor.skills.owned_keys())
        self.assertEqual(self._notices_for(sink, self.mastery.key), [])
        # Practising the passive itself awards no XP and no ownership.
        progression.reset_practice_dedupe()
        self.assertFalse(grant_skill_practice_xp(actor, self.mastery.key))
        self.assertEqual(
            float(actor.db.skill_proficiency.get(self.mastery.key, 0.0)), 0.0
        )

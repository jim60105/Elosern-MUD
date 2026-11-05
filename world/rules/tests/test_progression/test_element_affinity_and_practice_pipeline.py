"""Slice of ``test_progression``: ElementAffinityProgressionTests, PracticePipelineIntegrationTests.
"""
import inspect
import unittest
from dataclasses import replace
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.objects.models import ObjectDB
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
from world.rules.clock import get_world_clock
from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PRACTICE_XP_PER_STUDY_HOUR,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    grant_study_practice_xp,
    skill_proficiency_level,
)
from world.rules.targeting import RoomActionContext
from world.lore.elements import Element
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
    TargetSpec,
    validate_prerequisite_graph,
)
from world.skills.handler import ConferredSkillGrant
# Cross-lineage wiring: importing the rulebook module at collection time also
# forces its shipped-table load against the LIVE registry, before any
# synthetic scope clears it (the shared helpers' eager import is the same
# guarantee for sibling modules in other shard processes).
import world.rules.cross_lineage_unlock as cross_lineage


from ._support import (
    _MAGIC_CASTER,
    _character,
    _monster,
    _scoped_setup,
)
from world.rules.combat_identity import stable_actor_id


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
        actor_id = stable_actor_id(self.actor)
        field = Battlefield(
            {
                'party': frozenset({actor_id}),
                'foes': frozenset(stable_actor_id(monster) for monster in monsters),
            },
            {actor_id: self.actor}
            | {stable_actor_id(monster): monster for monster in monsters},
        )
        return BattlefieldActionContext(field, event_context=dict(event_context))

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_simulated_marker_suppresses_every_accrual(self):
        monster = self._monsters(1)[0]
        context = self._field([monster], simulated=True)
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = resolve_combat_action(self._request(_MAGIC_CASTER, [monster], context))
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
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = resolve_combat_action(self._request("t_glitter_cascade", "all-enemies", context))
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency["t_glitter_cascade"],
            3 * SKILL_PRACTICE_XP_PER_USE,
        )

    @covers_requirement("skill-lineage::each-actor-skill-target-accrues-once-per-world-clock-tick")
    def test_rolled_back_commit_releases_claims_so_retry_accrues(self):
        registry = live_skill_registry()
        paid_skill = replace(registry[_MAGIC_CASTER], cost={"mp": 10})
        cost_scope = patch.dict(registry, {_MAGIC_CASTER: paid_skill})
        cost_scope.start()
        self.addCleanup(cost_scope.stop)
        monster = self._monsters(1)[0]
        context = self._field([monster])
        request = self._request(_MAGIC_CASTER, [monster], context)
        before = dict(self.actor.db.skill_proficiency)
        before_mp = self.actor.traits.mp.current
        before_hp = monster.traits.hp.current
        clock = get_world_clock()
        before_tick = clock.tick
        fault_observations = []
        real = dict(_EVENT_EFFECT_PLANNERS)

        def fail_after_claim():
            # Observe the acquired claim and completed writes at the fault.
            fault_observations.append((
                dict(self.actor.db.skill_proficiency),
                progression.practice_claims_for(self.actor, _MAGIC_CASTER),
                self.actor.traits.mp.current,
                monster.traits.hp.current,
            ))
            raise RuntimeError("injected after practice claim")

        def poison(_request, _log):
            # Runs after the staged practice batch; its failure forces the
            # snapshot/restore rollback the release path must undo.
            return [
                PendingEffect(
                    self.actor,
                    "poisoned commit",
                    frozenset({"progression"}),
                    fail_after_claim,
                )
            ]

        _EVENT_EFFECT_PLANNERS["test-poison"] = poison
        try:
            with patch("world.rules.combat.damage.roll_d100", return_value=100):
                first = resolve_combat_action(request)
        finally:
            _EVENT_EFFECT_PLANNERS.clear()
            _EVENT_EFFECT_PLANNERS.update(real)
        self.assertNotEqual(first.outcome, "success")
        self.assertIsNone(first.event_log)
        self.assertIsNone(first.time_cost_seconds)
        self.assertEqual(first.notifications, ())
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(len(fault_observations), 1)
        written_practice, claims, paid_mp, damaged_hp = fault_observations[0]
        self.assertNotEqual(written_practice, before)
        self.assertTrue(claims)
        self.assertLess(paid_mp, before_mp)
        self.assertLess(damaged_hp, before_hp)
        self.assertEqual(dict(self.actor.db.skill_proficiency), before)
        self.assertEqual(self.actor.traits.mp.current, before_mp)
        self.assertEqual(monster.traits.hp.current, before_hp)
        reloaded_actor = ObjectDB.objects.get(pk=self.actor.pk)
        reloaded_monster = ObjectDB.objects.get(pk=monster.pk)
        self.assertEqual(dict(reloaded_actor.db.skill_proficiency), before)
        self.assertEqual(reloaded_actor.traits.mp.current, before_mp)
        self.assertEqual(reloaded_monster.traits.hp.current, before_hp)
        self.assertEqual(
            progression.practice_claims_for(self.actor, _MAGIC_CASTER), set()
        )
        # The legitimate same-tick retry accrues normally.
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            retry = resolve_combat_action(request)
        self.assertEqual(retry.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency[_MAGIC_CASTER],
            SKILL_PRACTICE_XP_PER_USE,
        )
        # And the same (actor, skill, target) is then deduped for the tick.
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            again = resolve_combat_action(request)
        self.assertEqual(again.outcome, "success")
        self.assertEqual(
            self.actor.db.skill_proficiency[_MAGIC_CASTER],
            SKILL_PRACTICE_XP_PER_USE,
        )


# --- Elemental learning eligibility (design D1/D2/D3) -----------------------
#
# File-local synthetic rows, built inside the synthetic scope: ACTIVE
# elemental spells of every effect shape (damage, heal, self-buff, control,
# mixed) plus an element-tagged PHYSICAL martial row, a PASSIVE enhancement,
# an elementless action, and two PASSIVE scoped ``growth_rate`` rows (one
# matching the practised element, one not). Every fixture key is a ``t_``
# token; no shipped identifier is named.

_ELEMENT = SYNTH_SKILLS["t_ember_burst"].element.key
_OTHER_ELEMENT = SYNTH_GLOW_ELEMENT

_DAMAGE = "t_elig_damage"
_MEND = "t_elig_mend"
_VEIL = "t_elig_veil"
_DAZE = "t_elig_daze"
_MIXED = "t_elig_mixed"
_MARTIAL = "t_elig_martial"
_PLAIN = "t_elig_plain"
_PASSIVE = "t_elig_passive"
_ELEMENTLESS_SPELL = "t_elig_elementless_spell"
_UNREGISTERED_SPELL = "t_elig_unregistered_spell"
_GROWTH = "t_elig_growth"
_GROWTH_OTHER = "t_elig_growth_other"
_PAIR_DAMAGE = "t_elig_pair_damage"
_PAIR_MEND = "t_elig_pair_mend"

# An Element instance the scoped registry does not carry: the classifier's
# registered-element guard, not the element-presence guard.
_UNREGISTERED_ELEMENT = Element("t_elig_unknown", "未登錄", "synthetic element")


def _growth_row(key: str, label: str, multiplier: int, scope: str):
    """One synthetic PASSIVE scoped ``growth_rate`` row (no element)."""
    return replace(
        synth_damage_skill(
            key,
            label,
            effects=(f"growth_rate:practice:{multiplier}:{scope}",),
            kind=SkillKind.PASSIVE,
            category=SkillCategory.ENHANCEMENT,
        ),
        element=None,
    )


def _practice_rows() -> dict:
    """The synthetic rows the eligibility cases register in one scope."""
    rows = (
        synth_damage_skill(
            _DAMAGE,
            "灼燼擊",
            effects=(f"damage:{_ELEMENT}:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
        ),
        synth_damage_skill(
            _MEND,
            "燼息癒合",
            effects=("heal:single",),
            category=SkillCategory.ELEMENTAL_MAGIC,
        ),
        synth_damage_skill(
            _VEIL,
            "燼幕",
            effects=("self_buff_apply:t_elig_veil_buff",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            target_spec=TargetSpec.SELF,
        ),
        synth_damage_skill(
            _DAZE,
            "燼惑",
            effects=("buff_apply:t_elig_daze_buff",),
            category=SkillCategory.ELEMENTAL_MAGIC,
        ),
        synth_damage_skill(
            _MIXED,
            "灼光癒合",
            effects=(f"damage:{_ELEMENT}:magic", "heal:single"),
            category=SkillCategory.ELEMENTAL_MAGIC,
        ),
        synth_damage_skill(
            _MARTIAL,
            "燼刃",
            effects=(f"damage:{_ELEMENT}:physical",),
            category=SkillCategory.MARTIAL_ARTS,
        ),
        make_skill(_PLAIN),
        synth_damage_skill(
            _PASSIVE,
            "燼之韻",
            effects=(),
            kind=SkillKind.PASSIVE,
            category=SkillCategory.ENHANCEMENT,
        ),
        replace(
            synth_damage_skill(
                _ELEMENTLESS_SPELL,
                "無屬癒合",
                effects=("heal:single",),
                category=SkillCategory.ELEMENTAL_MAGIC,
            ),
            element=None,
        ),
        replace(
            synth_damage_skill(
                _UNREGISTERED_SPELL,
                "幻元素癒合",
                effects=("heal:single",),
                category=SkillCategory.ELEMENTAL_MAGIC,
            ),
            element=_UNREGISTERED_ELEMENT,
        ),
        _growth_row(_GROWTH, "燼成長", 3, _ELEMENT),
        _growth_row(_GROWTH_OTHER, "異成長", 7, _OTHER_ELEMENT),
        synth_damage_skill(
            _PAIR_DAMAGE,
            "對照灼擊",
            effects=(f"damage:{_ELEMENT}:magic",),
            cost={"mp": 10},
            category=SkillCategory.ELEMENTAL_MAGIC,
        ),
        synth_damage_skill(
            _PAIR_MEND,
            "對照癒合",
            effects=("heal:single",),
            cost={"mp": 10},
            category=SkillCategory.ELEMENTAL_MAGIC,
        ),
    )
    return {row.key: row for row in rows}


class ElementalLearningEligibilityTests(EvenniaTestCase):
    """skill-lineage: elemental learning eligibility on both award paths.

    Formula inputs are pinned to fixed synthetic values, so every expected XP
    total below is derived by hand from base x race x affinity x conferred x
    owned -- never by calling the calculator under test.
    """

    def setUp(self):
        _scoped_setup(self)
        super().setUp()
        progression.reset_practice_dedupe()
        scope = patch.dict(live_skill_registry(), _practice_rows(), clear=False)
        scope.start()
        self.addCleanup(scope.stop)

    def _patch_formula(self):
        """Pin base XP 2, study-hour XP 7, race 2, affinity 1.25 / 0.75."""
        for target, value in (
            ("world.rules.progression._practice.SKILL_PRACTICE_XP_PER_USE", 2.0),
            ("world.rules.progression.PRACTICE_XP_PER_STUDY_HOUR", 7.0),
            (
                "world.rules.progression._scaling.AFFINITY_ELEMENT_MULTIPLIER",
                1.25,
            ),
            (
                "world.rules.progression._scaling.NON_AFFINITY_ELEMENT_MULTIPLIER",
                0.75,
            ),
        ):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        race = patch(
            "world.rules.progression._practice._race_learning_multiplier",
            lambda entity: 2.0,
        )
        race.start()
        self.addCleanup(race.stop)

    def _learner(
        self,
        key: str,
        *,
        affinity=(),
        owned=(),
        passives=(),
        conferred=None,
        skill_grants=(),
    ) -> PlayerCharacter:
        """One synthetic learner owning ``owned`` and ``passives``."""
        entity = _character(self, key)
        entity.db.skills = {"active": list(owned), "passive": list(passives)}
        entity.db.skill_proficiency = {}
        if affinity:
            entity.db.affinity_elements = list(affinity)
        if conferred is not None:
            grant_conferred_growth_rate(entity, "t_practice_source", conferred)
        if skill_grants:
            entity.db.skill_grants = list(skill_grants)
        return entity

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_damage_free_shapes_share_both_award_paths(self):
        self._patch_formula()
        for key in (_DAMAGE, _MEND, _VEIL, _DAZE, _MIXED):
            learner = self._learner(
                f"shape {key}",
                affinity=(_ELEMENT,),
                owned=(key,),
                passives=(_GROWTH,),
                conferred=1.5,
            )
            self.assertTrue(grant_skill_practice_xp(learner, key))
            # 2 base x 2 race x 1.25 favored x 1.5 conferred x 3 owned.
            self.assertEqual(learner.db.skill_proficiency[key], 22.5)
            self.assertTrue(grant_study_practice_xp(learner, key, 1))
            # One booked hour: 7 x (2 x 1.25 x 1.5 x 3), on top of the use.
            self.assertEqual(learner.db.skill_proficiency[key], 22.5 + 78.75)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_use_and_study_award_the_fixed_affinity_numbers(self):
        self._patch_formula()
        for affinity, use, study in (
            ((_ELEMENT,), 22.5, 78.75),
            ((_OTHER_ELEMENT,), 13.5, 47.25),
            ((), 18.0, 63.0),
        ):
            learner = self._learner(
                f"affinity {affinity!r}",
                affinity=affinity,
                owned=(_MEND,),
                passives=(_GROWTH,),
                conferred=1.5,
            )
            self.assertTrue(grant_skill_practice_xp(learner, _MEND))
            self.assertEqual(learner.db.skill_proficiency[_MEND], use)
            self.assertTrue(grant_study_practice_xp(learner, _MEND, 1))
            self.assertEqual(learner.db.skill_proficiency[_MEND], use + study)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_elemental_physical_and_elementless_stay_neutral(self):
        self._patch_formula()
        # The last two are ACTIVE ELEMENTAL_MAGIC rows that still fail the
        # catalog predicate: one declares no element, one a key the registry
        # does not carry.
        for key in (_MARTIAL, _PLAIN, _ELEMENTLESS_SPELL, _UNREGISTERED_SPELL):
            learner = self._learner(
                f"neutral {key}",
                affinity=(_ELEMENT,),
                owned=(key,),
                passives=(_GROWTH,),
                conferred=1.5,
            )
            # Neutral affinity and a neutral owned factor: 2 x 2 x 1 x 1.5.
            self.assertTrue(grant_skill_practice_xp(learner, key))
            self.assertEqual(learner.db.skill_proficiency[key], 6.0)
            self.assertTrue(grant_study_practice_xp(learner, key, 1))
            self.assertEqual(learner.db.skill_proficiency[key], 6.0 + 21.0)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_owned_scope_and_ownership_controls(self):
        self._patch_formula()
        mismatch = self._learner(
            "mismatched scope",
            affinity=(_ELEMENT,),
            owned=(_MEND,),
            passives=(_GROWTH_OTHER,),
            conferred=1.5,
        )
        granted = self._learner(
            "conferred ownership",
            affinity=(_ELEMENT,),
            owned=(_MEND,),
            conferred=1.5,
            skill_grants=(
                ConferredSkillGrant("t_practice_source", _GROWTH, 1.0),
            ),
        )
        bare = self._learner(
            "no growth source",
            affinity=(_ELEMENT,),
            owned=(_MEND,),
        )
        for learner, use, study in (
            (mismatch, 7.5, 26.25),
            (granted, 7.5, 26.25),
            (bare, 5.0, 17.5),
        ):
            self.assertTrue(grant_skill_practice_xp(learner, _MEND))
            self.assertEqual(learner.db.skill_proficiency[_MEND], use)
            self.assertTrue(grant_study_practice_xp(learner, _MEND, 1))
            self.assertEqual(learner.db.skill_proficiency[_MEND], use + study)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_passive_requests_write_nothing(self):
        self._patch_formula()
        learner = self._learner(
            "passive owner",
            owned=(_MEND,),
            passives=(_PASSIVE, _GROWTH),
            conferred=1.5,
        )
        self.assertFalse(grant_skill_practice_xp(learner, _PASSIVE))
        self.assertFalse(grant_study_practice_xp(learner, _PASSIVE, 1))
        self.assertEqual(dict(learner.db.skill_proficiency), {})

    def _caster(self, key: str, room, *, affinity=(), mp: int = 100):
        """One combat caster owning the paired damage/heal fixtures."""
        entity = create_object(PlayerCharacter, key=key)
        entity.location = room
        entity.race = _race_key()
        entity.apply_race_baseline()
        entity.traits.magic_power.base = 30
        entity.traits.hp.base = 300
        entity.traits.hp.current = 300
        entity.traits.mp.base = mp
        entity.traits.mp.current = mp
        entity.db.skills = {"active": [_PAIR_DAMAGE, _PAIR_MEND], "passive": []}
        entity.db.skill_proficiency = {}
        if affinity:
            entity.db.affinity_elements = list(affinity)
        return entity

    def _patient(self, key: str, room):
        """One unskilled party recipient at a partially depleted HP pool."""
        entity = create_object(PlayerCharacter, key=key)
        entity.location = room
        entity.race = _race_key()
        entity.apply_race_baseline()
        entity.traits.hp.base = 300
        entity.traits.hp.current = 100
        entity.db.skills = {"active": [], "passive": []}
        entity.db.skill_proficiency = {}
        return entity

    def _battlefield(self, party, foes):
        entities = {
            stable_actor_id(entity): entity for entity in (*party, *foes)
        }
        return Battlefield(
            {
                'party': frozenset(stable_actor_id(entity) for entity in party),
                'foes': frozenset(stable_actor_id(entity) for entity in foes),
            },
            entities,
        )

    def _resolve(self, caster, skill_key, target, battlefield):
        request = ActionRequest(
            caster, skill_key, [target], BattlefieldActionContext(battlefield)
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            return resolve_combat_action(request)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_learning_factors_change_practice_xp_alone(self):
        room = create_object(Room, key="eligibility arena")
        favored = self._caster("eligibility favored", room, affinity=(_ELEMENT,))
        unfavored = self._caster(
            "eligibility unfavored", room, affinity=(_OTHER_ELEMENT,)
        )
        bystander = self._patient("eligibility bystander", room)
        bystander_state = (
            bystander.traits.hp.current,
            bystander.traits.mp.current,
            dict(bystander.db.skill_proficiency),
        )
        results = []
        for caster, wolf_key, ally_key in (
            (favored, "favored wolf", "favored ally"),
            (unfavored, "unfavored wolf", "unfavored ally"),
        ):
            wolf = _monster(self, wolf_key)
            wolf.traits.hp.base = 500
            wolf.traits.hp.current = 500
            ally = self._patient(ally_key, room)
            battlefield = self._battlefield((caster, ally, bystander), (wolf,))
            bases_before = (
                caster.traits.magic_power.base,
                caster.traits.atk_phys.base,
            )
            mp_before = caster.traits.mp.current
            wolf_before = wolf.traits.hp.current
            ally_before = ally.traits.hp.current
            damage = self._resolve(caster, _PAIR_DAMAGE, wolf, battlefield)
            self.assertEqual(damage.outcome, "success")
            mend = self._resolve(caster, _PAIR_MEND, ally, battlefield)
            self.assertEqual(mend.outcome, "success")
            # The raw innate bases are untouched by either resolution.
            self.assertEqual(
                (caster.traits.magic_power.base, caster.traits.atk_phys.base),
                bases_before,
            )
            results.append(
                (
                    mp_before - caster.traits.mp.current,
                    wolf_before - wolf.traits.hp.current,
                    ally.traits.hp.current - ally_before,
                    caster.traits.magic_power.base,
                    caster.traits.atk_phys.base,
                    caster.db.skill_proficiency[_PAIR_DAMAGE],
                    caster.db.skill_proficiency[_PAIR_MEND],
                )
            )
        favored_run, unfavored_run = results
        # Identical stats, resources and outputs across the learning variants.
        self.assertGreater(favored_run[1], 0)
        self.assertGreater(favored_run[2], 0)
        self.assertEqual(favored_run[0], 20)
        self.assertEqual(favored_run[0], unfavored_run[0])
        self.assertEqual(favored_run[1], unfavored_run[1])
        self.assertEqual(favored_run[2], unfavored_run[2])
        self.assertEqual(favored_run[3], unfavored_run[3])
        self.assertEqual(favored_run[4], unfavored_run[4])
        # Only the learner's practice XP differs, by the elemental factor.
        for index in (5, 6):
            self.assertGreater(favored_run[index], 0)
            self.assertGreater(unfavored_run[index], 0)
            self.assertAlmostEqual(
                favored_run[index] / unfavored_run[index],
                AFFINITY_ELEMENT_MULTIPLIER / NON_AFFINITY_ELEMENT_MULTIPLIER,
            )
        # The untouched party member is byte-identical after both rounds.
        self.assertEqual(
            (
                bystander.traits.hp.current,
                bystander.traits.mp.current,
                dict(bystander.db.skill_proficiency),
            ),
            bystander_state,
        )

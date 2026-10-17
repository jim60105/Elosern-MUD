"""Synthetic mechanism suite: timed monster effects, recipients and lifetime.

Independent synthetic coverage for the generic timed-effect contract: an
enemy hit-rider reaches only the hit-qualified selected enemies, a
hit-independent self effect reaches only the caster on a valid affordable
resolved attempt, refresh replaces lifetime without accumulating magnitude,
expiry removes the contribution, and neither narrative prose nor forged
environment context changes an outcome.

Every decisive input here is synthetic: file-local ``t_`` skills and buffs
built from the shared kit and registered for this module only, so no shipped
content identity is read and no expected value is copied from a registry.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    active_stack_count,
    entity_active_buffs,
    has_positional_marker,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import COMBAT_YAML, Battlefield, BattlefieldActionContext
from world.rules.monster_individual import construct_species_individual
from world.lore.monster_species import MonsterCombatProfile
from world.skills.effects import EffectAudience, EffectPolicy
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import (
    make_buff,
    make_monster_species,
    make_monster_variant,
    make_skill,
    synthetic_registries,
)

RIDER_BUFF = "t_synth_rider_mark"
GUARD_BUFF = "t_synth_guard_shell"
RIDER_SKILL = "t_synth_rider_kit"
GUARD_SKILL = "t_synth_guard_kit"


def _rider_skill() -> object:
    """One synthetic enemy hit-rider kit: physical damage plus a rider buff."""
    return make_skill(
        RIDER_SKILL,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 4, "sp": 2},
        effects=["damage:fire:physical", f"buff_apply:{RIDER_BUFF}"],
        effect_policies=(
            EffectPolicy(audience=EffectAudience.ENEMIES),
            EffectPolicy(audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    )


def _guard_skill() -> object:
    """One synthetic hit-independent self-guard kit."""
    return make_skill(
        GUARD_SKILL,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 4, "sp": 2},
        effects=["damage:fire:physical", f"self_buff_apply:{GUARD_BUFF}"],
        effect_policies=(
            EffectPolicy(audience=EffectAudience.ENEMIES),
            EffectPolicy(audience=EffectAudience.SELF),
        ),
    )


class TimedMonsterEffectMechanismTests(EvenniaTestCase):
    """Requirement: declared recipients, hit dependency and lifetime."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="t_timed_room")
        self.caster = self._character("t_timed_caster", agility=20, attack=50)
        self.enemy = self._character("t_timed_enemy", agility=10, defense=10)
        self.ally = self._character("t_timed_ally", agility=10, defense=10)
        self.control = self._character("t_timed_control", agility=10, defense=10)
        self.battlefield = Battlefield(
            roster={
                "t_timed_caster": self.caster,
                "t_timed_enemy": self.enemy,
                "t_timed_ally": self.ally,
                "t_timed_control": self.control,
            },
            teams={
                "party": {"t_timed_caster", "t_timed_ally"},
                "foes": {"t_timed_enemy", "t_timed_control"},
            },
        )
        self.context = BattlefieldActionContext(self.battlefield)
        for key, template in (
            (RIDER_BUFF, make_buff(RIDER_BUFF, duration=30, stacking="refresh")),
            (GUARD_BUFF, make_buff(GUARD_BUFF, duration=30, stacking="refresh")),
        ):
            BUFF_DEFINITIONS[key] = template
            self.addCleanup(BUFF_DEFINITIONS.pop, key, None)

    def _character(self, key: str, *, agility: int = 10, defense: int = 5, attack: int = 5):
        character = create_object(PlayerCharacter, key=key, location=self.room)
        character.race = "human"
        character.apply_race_baseline()
        character.db.skills = {"active": [], "passive": []}
        character.traits.hp.base = 100
        character.traits.hp.current = 100
        character.traits.mp.base = 100
        character.traits.mp.current = 100
        character.traits.sp.base = 100
        character.traits.sp.current = 100
        character.traits.agility.base = agility
        character.traits.defense.base = defense
        character.traits.atk_phys.base = attack
        return character

    def _own(self, character, skill) -> None:
        """Grant one synthetic skill to the actor's lineage.

        The skill itself is registered only for the duration of each resolution
        (``patch.dict``), so this fixture never mutates the shared registry.
        """
        from world.rules.tests.combat_fixtures import grant_lineage

        grant_lineage(character, [skill.key])

    def _resolve(self, skill, targets, *, roll: int, context=None):
        request = ActionRequest(
            self.caster, skill.key, targets, context or self.context
        )
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
            with patch("world.rules.combat.damage.roll_d100", return_value=roll):
                return ActionResolver.resolve(request)

    def _gauges(self, *characters) -> tuple[tuple[int, int, int], ...]:
        return tuple(
            (character.traits.hp.current, character.traits.mp.current,
             character.traits.sp.current)
            for character in characters
        )

    @covers_requirement(
        "monster-resource-abilities::timed-monster-effects-follow-declared-recipients-and-lifetime"
    )
    def test_enemy_rider_reaches_only_the_hit_qualified_enemy(self):
        """Scenario: Rider routing.

        The rider is hit-qualified: a miss grants nothing anywhere, a hit
        grants exactly one instance to the hit enemy, and a hit whose committed
        HP loss is the damage floor (defense swallows the attack) still grants
        it, because qualification is the hit and never the HP delta. The caster
        and the untargeted ally/foe controls stay untouched throughout.
        """
        skill = _rider_skill()
        self._own(self.caster, skill)
        # Ratio mitigation retains ``k / (k + defense)``: only a defense that
        # dominates the attack drives the retained hit under the damage floor.
        self.enemy.traits.defense.base = 10000
        controls = (self.caster, self.ally, self.control)

        missed = self._resolve(skill, [self.enemy], roll=1)
        self.assertEqual(missed.outcome, "success")
        for entity in (self.enemy, *controls):
            self.assertNotIn(RIDER_BUFF, entity_active_buffs(entity))
        self.assertEqual(self.enemy.traits.hp.current, 100)

        absorbed = self._resolve(skill, [self.enemy], roll=80)
        self.assertEqual(absorbed.outcome, "success")
        # The committed loss is the rulebook's damage floor: the defense
        # swallowed the attack entirely, and the rider still landed.
        self.assertEqual(
            100 - self.enemy.traits.hp.current, int(COMBAT_YAML["damage"]["floor"])
        )
        self.assertEqual(active_stack_count(self.enemy, RIDER_BUFF), 1)
        for entity in controls:
            self.assertNotIn(RIDER_BUFF, entity_active_buffs(entity))

        # A second hit refreshes the same single contribution rather than
        # accumulating a second one.
        self.assertEqual(self._resolve(skill, [self.enemy], roll=80).outcome, "success")
        self.assertEqual(active_stack_count(self.enemy, RIDER_BUFF), 1)

    @covers_requirement(
        "monster-resource-abilities::timed-monster-effects-follow-declared-recipients-and-lifetime",
        "monster-resource-abilities::monster-effects-and-payments-share-the-ordinary-atomic-action",
    )
    def test_hit_independent_self_guard_grants_the_caster_only(self):
        """Scenario: Self routing.

        The guard is not hit-dependent: a valid affordable attempt grants it to
        the caster even when the strike misses, and it never reaches the
        targeted enemy or the ally. A rejected request writes nothing at all,
        and an invalid or absent target is rejected with its own reason.
        """
        skill = _guard_skill()
        self._own(self.caster, skill)
        controls = (self.enemy, self.ally, self.control)

        missed = self._resolve(skill, [self.enemy], roll=1)
        self.assertEqual(missed.outcome, "success")
        self.assertEqual(self.enemy.traits.hp.current, 100)
        self.assertEqual(active_stack_count(self.caster, GUARD_BUFF), 1)
        for entity in controls:
            self.assertNotIn(GUARD_BUFF, entity_active_buffs(entity))

        # Either resource short: rejected before dice or writes.
        self.caster.traits.mp.current = 3
        before = self._gauges(self.caster, self.enemy, self.ally, self.control)
        with patch("world.rules.combat.damage.roll_d100") as roller:
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                rejected = ActionResolver.resolve(
                    ActionRequest(self.caster, skill.key, [self.enemy], self.context)
                )
        self.assertEqual(rejected.outcome, "rejected")
        self.assertEqual(rejected.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(roller.call_count, 0)
        self.assertEqual(self._gauges(self.caster, self.enemy, self.ally, self.control), before)
        self.assertEqual(active_stack_count(self.caster, GUARD_BUFF), 1)

        # Restore resources: an empty target list and an absent target are
        # rejected by the resolver's own gates and still grant nothing.
        self.caster.traits.mp.current = 100
        empty = self._resolve(skill, [], roll=80)
        self.assertEqual(empty.outcome, "rejected")
        self.assertEqual(empty.reason, RejectReason.TARGET_SPEC_MISMATCH)
        absent = create_object(PlayerCharacter, key="t_timed_absent", location=self.room)
        absent.race = "human"
        absent.apply_race_baseline()
        outside = self._resolve(skill, [absent], roll=80)
        self.assertEqual(outside.outcome, "rejected")
        self.assertEqual(outside.reason, RejectReason.TARGET_NOT_PRESENT)
        self.assertNotIn(GUARD_BUFF, entity_active_buffs(absent))
        self.assertEqual(active_stack_count(self.caster, GUARD_BUFF), 1)

    @covers_requirement(
        "monster-resource-abilities::timed-monster-effects-follow-declared-recipients-and-lifetime"
    )
    def test_refresh_replaces_lifetime_and_expiry_removes_the_contribution(self):
        """Scenario: Lifetime.

        An aged instance is refreshed back to its full declared lifetime as one
        same-key contribution, and crossing the refreshed expiry removes it and
        leaves no undeclared residue behind.
        """
        skill = _guard_skill()
        self._own(self.caster, skill)
        definition = BUFF_DEFINITIONS[GUARD_BUFF]
        clock = WorldClock()

        self.assertEqual(self._resolve(skill, [self.enemy], roll=80).outcome, "success")
        self.assertEqual(active_stack_count(self.caster, GUARD_BUFF), 1)
        clock.advance(3, AdvanceSource.COMMAND, (self.caster,))
        aged = self.caster.buffs.all[GUARD_BUFF]
        self.assertEqual(aged.remaining_seconds, definition.duration - 3)

        self.assertEqual(self._resolve(skill, [self.enemy], roll=80).outcome, "success")
        self.assertEqual(active_stack_count(self.caster, GUARD_BUFF), 1)
        refreshed = self.caster.buffs.all[GUARD_BUFF]
        self.assertEqual(refreshed.remaining_seconds, definition.duration)
        self.assertEqual(len([b for b in self.caster.buffs.all.values()
                              if b.definition_key == GUARD_BUFF]), 1)

        hp_before = self.caster.traits.hp.current
        clock.advance(definition.duration, AdvanceSource.COMMAND, (self.caster,))
        self.assertNotIn(GUARD_BUFF, entity_active_buffs(self.caster))
        self.assertEqual(active_stack_count(self.caster, GUARD_BUFF), 0)
        self.assertFalse(has_positional_marker(self.caster))
        self.assertEqual(self.caster.traits.hp.current, hp_before)

    @covers_requirement(
        "monster-resource-abilities::timed-monster-effects-follow-declared-recipients-and-lifetime",
        "monster-resource-abilities::monster-effects-and-payments-share-the-ordinary-atomic-action",
    )
    def test_narrative_prose_and_forged_environment_change_nothing(self):
        """Scenario: Environment remains prose; narrative grants no effect.

        Two declared variants differ only in their narrative strings and still
        produce byte-identical results through real construction and
        resolution, and attaching forged environment facts to the action
        context changes nothing either.
        """
        skill = _rider_skill()
        species_keys = ("t_prose_species_a", "t_prose_species_b")
        species = {}
        variants = {}
        for index, species_key in enumerate(species_keys):
            variant_key = f"t_prose_variant_{index}"
            species[species_key] = make_monster_species(
                species_key,
                default_variant_key=variant_key,
                published_ecology_zh=f"合成生態敘述 {index}。",
                published_description_zh=f"合成外觀敘述 {index}。",
            )
            variants[variant_key] = make_monster_variant(
                variant_key,
                species_key=species_key,
                description_zh=f"合成變體敘述 {index}。",
                combat_profile=MonsterCombatProfile(
                    hp=100, mp=100, sp=100, atk_phys=5,
                    agility=1, defense=0, magic_power=0,
                ),
                active_skill_keys=(skill.key,),
            )
        observed = []
        with synthetic_registries(
            "monster_species",
            "monster_variants",
            "monster_tiers",
            extra={"monster_species": species, "monster_variants": variants},
        ):
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}):
                for index, species_key in enumerate(species_keys):
                    actor = construct_species_individual(
                        species_key, f"t_prose_variant_{index}"
                    )
                    victim = create_object(
                        PlayerCharacter, key=f"t_prose_victim_{index}", location=self.room
                    )
                    victim.race = "human"
                    victim.apply_race_baseline()
                    victim.traits.hp.current = 100
                    victim.traits.mp.current = 100
                    victim.traits.defense.base = 10
                    victim.traits.agility.base = 10
                    actor.location = self.room
                    field = Battlefield(
                        {"party": frozenset({victim.key}),
                         "foes": frozenset({actor.key})},
                        {victim.key: victim, actor.key: actor},
                    )
                    self.assertIn(skill.key, actor.db.skills["active"])
                    request = ActionRequest(
                        actor, skill.key, [victim], BattlefieldActionContext(field)
                    )
                    with patch("world.rules.combat.damage.roll_d100", return_value=80):
                        result = ActionResolver.resolve(request)
                    self.assertEqual(result.outcome, "success")
                    observed.append(
                        (
                            victim.traits.hp.current,
                            active_stack_count(victim, RIDER_BUFF),
                            actor.traits.mp.current,
                            actor.traits.sp.current,
                        )
                    )
        # The two declarations really differ in prose...
        self.assertNotEqual(
            species[species_keys[0]].published_ecology_zh,
            species[species_keys[1]].published_ecology_zh,
        )
        self.assertNotEqual(
            variants["t_prose_variant_0"].description_zh,
            variants["t_prose_variant_1"].description_zh,
        )
        # ...and yet the mechanics are identical.
        self.assertEqual(len(observed), 2)
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[0][1], 1)
        self.assertLess(observed[0][0], 100)

        # Forged environment facts on an ordinary synthetic exchange change
        # neither the outcome nor the resulting state.
        plain = _guard_skill()
        self._own(self.caster, plain)
        forged = BattlefieldActionContext(
            self.battlefield,
            event_context={
                "battlefield": self.battlefield,
                "ecology_prose": "偽造生態敘述",
                "environment": {"weather": "fog", "terrain": "cliff"},
            },
        )
        self.assertIn("ecology_prose", forged.event_context)
        self.assertNotIn("ecology_prose", self.context.event_context)

        def deltas(before, after):
            return tuple(
                tuple(later - earlier for earlier, later in zip(start, end))
                for start, end in zip(before, after)
            )

        before_first = self._gauges(self.caster, self.enemy)
        first = self._resolve(plain, [self.enemy], roll=80)
        after_first = self._gauges(self.caster, self.enemy)
        before_second = self._gauges(self.caster, self.enemy)
        second = self._resolve(plain, [self.enemy], roll=80, context=forged)
        after_second = self._gauges(self.caster, self.enemy)
        self.assertEqual(first.outcome, "success")
        self.assertEqual(second.outcome, "success")
        self.assertEqual(
            deltas(before_first, after_first),
            deltas(before_second, after_second),
        )
        self.assertNotEqual(deltas(before_first, after_first), ((0, 0, 0), (0, 0, 0)))

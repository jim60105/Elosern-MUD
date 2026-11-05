"""Data-contract test: slime representative-composition production smoke over the generic self-support/lifetime contracts

The stable-key-ordered representative of the hit-independent self-support
composition shape is constructed for real and observed through one committed
session: the shipped utility binding offers a self-only guard plan with a
positive defensive value, settlement pays its SP once and mounts the guard on
the caster only, an aged mount refreshes to one contribution, expiry removes
it, an exhausted pool falls back to the innate attack, and a committed reload
keeps the spent pool, the remaining lifetime, the kit and the binding. Shared
synthetic suites own payment ordering, formula and rollback vectors.

``SelfSupportGroupMemberTests`` derives that composition group from the shipped
declarations instead of naming its members, so every variant that joins the
shape is exercised on its own authored axis.
"""

from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import BUFF_DEFINITIONS, entity_active_buffs
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    combat_provenance,
)
from world.rules.combat_identity import stable_actor_id
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.monster_individual import construct_species_individual
from world.rules.rulebook.schema import load_rules
from world.rules.tests._combat_session_helpers import engagement_provenance
from world.rules.tests.test_monster_composition_coverage import (
    composition_groups,
    variant_signature,
)
from world.skills.registry import SKILL_REGISTRY

# The representative the composition-coverage check derives for this group.
REPRESENTATIVE_VARIANT = "mudbank_dweller"
REPRESENTATIVE_ROW = MONSTER_VARIANT_REGISTRY[REPRESENTATIVE_VARIANT]
SKILL_KEY = REPRESENTATIVE_ROW.active_skill_keys[0]
BEHAVIOUR_KEY = REPRESENTATIVE_ROW.behaviour_profile_key

_MOUNTED_PREFIXES = ("buff_apply:", "self_buff_apply:")


def _mounted_buff_key(skill) -> str:
    """The timed effect key one representative kit actually mounts."""
    for effect in skill.effects:
        for prefix in _MOUNTED_PREFIXES:
            if effect.startswith(prefix):
                return effect[len(prefix):]
    raise AssertionError("the representative kit mounts no timed effect")


BUFF_KEY = _mounted_buff_key(SKILL_REGISTRY[SKILL_KEY])

# The live combat-modifier row the mounted effect is valued and settled by.
_MODIFIER_RULE = next(
    rule
    for rule in load_rules(
        Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
    )
    if rule.when.get("buff_active") == BUFF_KEY
)
MODIFIER_AXIS, MODIFIER_MAGNITUDE = next(iter(_MODIFIER_RULE.then.items()))


def _buff_instances(entity):
    return [buff for buff in entity.buffs.all.values() if buff.definition_key == BUFF_KEY]


def _control_ally():
    """One constructed same-composition individual used as a recipient control."""
    return construct_species_individual(
        REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
    )


def _field(caster, opponent, ally):
    return Battlefield(
        {
            "party": frozenset({stable_actor_id(opponent)}),
            "foes": frozenset({stable_actor_id(caster), stable_actor_id(ally)}),
        },
        {
            stable_actor_id(opponent): opponent,
            stable_actor_id(caster): caster,
            stable_actor_id(ally): ally,
        },
    )


class MudfilmSlimeResourceSkillSmokeTests(EvenniaTestCase):
    def _opponent(self, room, key):
        player = create_object(PlayerCharacter, key=key, location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        return player

    def _modifier(self, entity):
        return evaluate_combat_modifiers(entity).get(MODIFIER_AXIS, 0)

    def test_production_self_support_candidacy_payment_lifetime_and_reload(self):
        """Detect a legacy binding, recipient routing, stale refresh or lost durable source."""
        slime = construct_species_individual(
            REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
        )
        room = create_object(Room, key="t_mudfilm_smoke_room")
        opponent = self._opponent(room, "t_mudfilm_smoke_target")
        ally = _control_ally()
        slime.location = room
        ally.location = room
        field = _field(slime, opponent, ally)
        context = BattlefieldActionContext(field)
        skill = SKILL_REGISTRY[SKILL_KEY]
        baseline = self._modifier(slime)
        controls = {
            entity.pk: (
                entity.traits.hp.current,
                entity.traits.mp.current,
                entity.traits.sp.current,
                dict(evaluate_combat_modifiers(entity)),
            )
            for entity in (opponent, ally)
        }
        before_sp = slime.traits.sp.current

        # Candidacy: the shipped utility binding offers the guard as a plan
        # with the implicit SELF binding and a positive defensive value,
        # whatever else the selector may choose.
        trace = []
        request = monster_behaviour_policy(slime, field, context=context, trace=trace)
        self.assertIsNotNone(request)
        plans = [plan for plan in trace[-1].plans if plan.skill_key == SKILL_KEY]
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertIsNone(plan.shorthand)
        self.assertEqual(plan.target_ids, ())
        self.assertGreater(plan.control, 0)

        # Settlement: the plan's implicit request pays the SP once, mounts the
        # guard on the caster only, and changes the live modifier axis by its
        # authored magnitude. The opponent and ally are untouched controls.
        guard_request = ActionRequest(slime, SKILL_KEY, [], context)
        with combat_provenance(engagement_provenance().at_slot(0)):
            result = ActionResolver.resolve(guard_request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(slime.traits.sp.current, before_sp - skill.cost["sp"])
        self.assertIn(BUFF_KEY, entity_active_buffs(slime))
        self.assertEqual(
            self._modifier(slime), baseline + MODIFIER_MAGNITUDE
        )
        for entity in (opponent, ally):
            self.assertNotIn(BUFF_KEY, entity_active_buffs(entity))
            self.assertEqual(
                (
                    entity.traits.hp.current,
                    entity.traits.mp.current,
                    entity.traits.sp.current,
                    dict(evaluate_combat_modifiers(entity)),
                ),
                controls[entity.pk],
            )
        duration = BUFF_DEFINITIONS[BUFF_KEY].duration
        self.assertEqual(_buff_instances(slime)[0].remaining_seconds, duration)

        # Aging then a committed reload: the spent pool and the remaining
        # lifetime are durable, and the kit/binding come from the fresh row.
        clock = WorldClock()
        age = max(1, duration // 2)
        clock.advance(age, AdvanceSource.COMMAND, (slime,))
        self.assertEqual(_buff_instances(slime)[0].remaining_seconds, duration - age)
        spent_sp = slime.traits.sp.current
        slime.flush_cached_instance(slime)
        reloaded = Monster.objects.get(pk=slime.pk)
        self.assertIsNot(reloaded, slime)
        self.assertEqual(reloaded.species_key, slime.species_key)
        self.assertEqual(reloaded.variant_key, slime.variant_key)
        self.assertEqual(reloaded.traits.sp.current, spent_sp)
        self.assertEqual(reloaded.db.skills["active"], [SKILL_KEY])
        self.assertEqual(reloaded.db.behaviour_tree, BEHAVIOUR_KEY)
        self.assertIn(BUFF_KEY, entity_active_buffs(reloaded))
        self.assertEqual(
            _buff_instances(reloaded)[0].remaining_seconds, duration - age
        )

        # Refresh: a recast through the reloaded row replaces the aged mount
        # with one fresh contribution, never a second one.
        field = _field(reloaded, opponent, ally)
        context = BattlefieldActionContext(field)
        reloaded.traits.sp.current = reloaded.traits.sp.max
        paid_before = reloaded.traits.sp.current
        with combat_provenance(engagement_provenance().at_slot(0)):
            refreshed = ActionResolver.resolve(
                ActionRequest(reloaded, SKILL_KEY, [], context)
            )
        self.assertEqual(refreshed.outcome, "success")
        self.assertEqual(len(_buff_instances(reloaded)), 1)
        self.assertEqual(_buff_instances(reloaded)[0].remaining_seconds, duration)
        self.assertEqual(
            self._modifier(reloaded), baseline + MODIFIER_MAGNITUDE
        )
        self.assertEqual(
            reloaded.traits.sp.current, paid_before - skill.cost["sp"]
        )

        # Expiry removes the contribution.
        clock.advance(duration, AdvanceSource.COMMAND, (reloaded,))
        self.assertNotIn(BUFF_KEY, entity_active_buffs(reloaded))
        self.assertEqual(self._modifier(reloaded), baseline)

        # An exhausted pool removes the guard from the candidate set: the
        # ordinary innate attack remains the only candidate, and a forced
        # guard request is rejected without payment.
        reloaded.traits.sp.current = skill.cost["sp"] - 1
        trace = []
        exhausted = monster_behaviour_policy(
            reloaded, field, context=context, trace=trace
        )
        self.assertEqual(exhausted.skill_key, "basic_attack")
        self.assertEqual(
            [plan for plan in trace[-1].plans if plan.skill_key == SKILL_KEY], []
        )
        unpaid = reloaded.traits.sp.current
        with combat_provenance(engagement_provenance().at_slot(0)):
            forced = ActionResolver.resolve(
                ActionRequest(reloaded, SKILL_KEY, [], context)
            )
        self.assertEqual(forced.outcome, "rejected")
        self.assertIs(forced.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(reloaded.traits.sp.current, unpaid)


class SelfSupportGroupMemberTests(EvenniaTestCase):
    """Every derived member of the hit-independent self-support group.

    The smoke above exercises the group's stable-key-ordered representative;
    this check derives the whole group from the shipped declarations (no key
    list) and repeats the observable contract on each member: its shipped
    utility binding offers its own kit skill as a self-only plan with positive
    value, settlement pays the declared cost once, the declared effect mounts
    on the caster only, and the live modifier row that names that effect moves
    the caster's bundle on its own declared axis.
    """

    def _opponent(self, room, key):
        player = create_object(PlayerCharacter, key=key, location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        return player

    def _control_state(self, entity):
        return (
            entity.traits.hp.current,
            entity.traits.mp.current,
            entity.traits.sp.current,
            dict(evaluate_combat_modifiers(entity)),
        )

    def test_every_group_member_selects_pays_and_mounts_its_own_kit(self):
        signature = variant_signature(REPRESENTATIVE_ROW, SKILL_REGISTRY)
        members = composition_groups(MONSTER_VARIANT_REGISTRY, SKILL_REGISTRY)[signature]
        self.assertIn(REPRESENTATIVE_VARIANT, members)
        for position, variant_key in enumerate(members):
            with self.subTest(variant=variant_key):
                row = MONSTER_VARIANT_REGISTRY[variant_key]
                skill_key = row.active_skill_keys[0]
                skill = SKILL_REGISTRY[skill_key]
                buff_key = _mounted_buff_key(skill)
                rule = next(
                    rule
                    for rule in load_rules(
                        Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
                    )
                    if rule.when.get("buff_active") == buff_key
                )
                axis, magnitude = next(iter(rule.then.items()))
                caster = construct_species_individual(row.species_key, variant_key)
                room = create_object(Room, key=f"t_self_support_room_{position}")
                caster.location = room
                opponent = self._opponent(room, f"t_self_support_target_{position}")
                ally = construct_species_individual(row.species_key, variant_key)
                ally.location = room
                field = _field(caster, opponent, ally)
                context = BattlefieldActionContext(field)
                baseline = evaluate_combat_modifiers(caster).get(axis, 0)
                controls = {
                    entity.pk: self._control_state(entity)
                    for entity in (opponent, ally)
                }
                before_sp = caster.traits.sp.current

                # Candidacy: the shipped utility binding offers this member's
                # own kit as an implicit SELF plan with positive value, even
                # though the selector may choose the innate attack instead.
                trace = []
                request = monster_behaviour_policy(
                    caster, field, context=context, trace=trace
                )
                self.assertIsNotNone(request)
                plans = [plan for plan in trace[-1].plans if plan.skill_key == skill_key]
                self.assertEqual(len(plans), 1)
                plan = plans[0]
                self.assertIsNone(plan.shorthand)
                self.assertEqual(plan.target_ids, ())
                self.assertGreater(plan.control, 0)

                # Settlement: this member's own kit pays its declared cost
                # exactly once, mounts its effect on the caster only and moves
                # the live modifier row's own axis by its authored magnitude.
                with combat_provenance(engagement_provenance().at_slot(0)):
                    result = ActionResolver.resolve(
                        ActionRequest(caster, skill_key, [], context)
                    )
                self.assertEqual(result.outcome, "success")
                self.assertEqual(
                    caster.traits.sp.current, before_sp - skill.cost["sp"]
                )
                self.assertIn(buff_key, entity_active_buffs(caster))
                self.assertEqual(
                    evaluate_combat_modifiers(caster).get(axis, 0),
                    baseline + magnitude,
                )
                for entity in (opponent, ally):
                    self.assertNotIn(buff_key, entity_active_buffs(entity))
                    self.assertEqual(
                        self._control_state(entity), controls[entity.pk]
                    )

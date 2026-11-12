"""Data-contract test: sparrow representative-composition production smoke over the generic rider/lifetime contracts

The stable-key-ordered representative of the enemy hit-rider composition shape
is constructed for real and observed through one committed session: authored
selection, resolver payment, mounted rider delivery to the hit enemy only,
aged refresh and expiry on the representative's own declared lifetime, ordinary
fallback on its exhausted SP axis, the inclusive flee edge, a late-target
rejection and a committed reload. Shared synthetic suites own the hit,
recipient-control, rollback and lifetime mechanism vectors.

``EnemyRiderGroupMemberTests`` derives that composition group from the shipped
declarations instead of naming its members, so every variant that joins the
shape is exercised on its own rider axis through a landed hit, a miss and a
committed reload.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.tests._combat_session_helpers import (
    engagement_provenance,
    resolve_combat_action,
)
from world.rules.buffs import BUFF_DEFINITIONS, entity_active_buffs
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    combat_provenance,
)
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.combat_session.lifecycle import engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import (
    DecisionMode,
    monster_behaviour_policy,
    resolve_behaviour_profile,
    resolve_monster_ai,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.tests.combat_fixtures import flee_edge
from world.rules.tests.test_monster_composition_coverage import (
    composition_groups,
    variant_signature,
)
from world.skills.registry import SKILL_REGISTRY
from world.rules.combat_identity import stable_actor_id

# The representative the composition-coverage check derives for this group.
REPRESENTATIVE_VARIANT = "cliff_stepper"
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


def _linked_modifier_axis_and_delta(buff_key: str) -> tuple[str, int]:
    """The single stat axis and contribution declared for this representative's mount."""
    matching = [
        rule for rule in _RULES if rule.when.get("buff_active") == buff_key
    ]
    if len(matching) != 1 or len(matching[0].then) != 1:
        raise AssertionError(
            f"expected exactly one single-axis modifier rule for buff {buff_key!r}, found {matching!r}"
        )
    axis, delta = next(iter(matching[0].then.items()))
    return str(axis), int(delta)


MODIFIER_AXIS, MODIFIER_DELTA = _linked_modifier_axis_and_delta(BUFF_KEY)


def _buff_instances(entity, buff_key=BUFF_KEY):
    return [buff for buff in entity.buffs.all.values() if buff.definition_key == buff_key]


class SwayWhistleSparrowResourceSkillSmokeTests(EvenniaTestCase):
    @covers_requirement(
        "monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-resource-abilities::timed-monster-effects-follow-declared-recipients-and-lifetime",
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence",
        "test-data-independence::representative-production-smoke-proves-real-consumer-integration-proportionally",
    )
    def test_production_enemy_rider_payment_refresh_controls_and_reload(self):
        """Detect rider delivery to the caster/control, stale lifetime or lost payment."""
        pecker = construct_species_individual(
            REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
        )
        room = create_object(Room, key="t_rider_smoke_room")
        player = create_object(PlayerCharacter, key="t_rider_smoke_target", location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        control = create_object(PlayerCharacter, key="t_rider_smoke_control", location=room)
        control.race = "human"
        control.apply_race_baseline()
        controls = (control.traits.hp.current, control.traits.mp.current)
        pecker.location = room
        engage(player, pecker)
        record = read_session(player)
        field = Battlefield(
            {'party': frozenset({stable_actor_id(player)}), 'foes': frozenset({stable_actor_id(pecker)})},
            {stable_actor_id(player): player, stable_actor_id(pecker): pecker},
        )
        skill = SKILL_REGISTRY[SKILL_KEY]
        baseline_modifier = evaluate_combat_modifiers(player).get(MODIFIER_AXIS, 0)
        request = _enemy_policy(pecker, field, record)
        self.assertEqual(request.skill_key, SKILL_KEY)
        self.assertEqual(request.targets, [player])
        before = (pecker.traits.mp.current, pecker.traits.sp.current)
        with patch(
            "world.rules.combat.damage.roll_d100", return_value=80
        ), combat_provenance(engagement_provenance().at_slot(0)):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertLess(player.traits.hp.current, 10000)
        self.assertEqual(
            (pecker.traits.mp.current, pecker.traits.sp.current),
            (before[0] - skill.cost["mp"], before[1] - skill.cost["sp"]),
        )
        self.assertIn(BUFF_KEY, entity_active_buffs(player))
        self.assertNotIn(BUFF_KEY, entity_active_buffs(pecker))
        self.assertNotIn(BUFF_KEY, entity_active_buffs(control))
        self.assertEqual((control.traits.hp.current, control.traits.mp.current), controls)
        self.assertEqual(
            evaluate_combat_modifiers(player).get(MODIFIER_AXIS, 0),
            baseline_modifier + MODIFIER_DELTA,
        )
        duration = BUFF_DEFINITIONS[BUFF_KEY].duration
        instance = _buff_instances(player)[0]
        self.assertEqual(instance.remaining_seconds, duration)
        clock = WorldClock()
        # A one-second authored mount has no integer pre-expiry aging instant;
        # fixed synthetic lifecycle tests own that edge and the refresh formula.
        if duration > 1:
            age = max(1, duration // 2)
            clock.advance(age, AdvanceSource.COMMAND, (player,))
            self.assertEqual(_buff_instances(player)[0].remaining_seconds, duration - age)
            modifier_before = evaluate_combat_modifiers(player).get(MODIFIER_AXIS, 0)
            pecker.traits.mp.current = pecker.traits.mp.max
            pecker.traits.sp.current = pecker.traits.sp.max
            refresh_request = _enemy_policy(pecker, field, record)
            self.assertEqual(refresh_request.skill_key, SKILL_KEY)
            with patch(
                "world.rules.combat.damage.roll_d100", return_value=80
            ), combat_provenance(engagement_provenance().at_slot(0)):
                self.assertEqual(
                    ActionResolver.resolve(refresh_request).outcome, "success"
                )
            refreshed = _buff_instances(player)
            self.assertEqual(len(refreshed), 1)
            self.assertEqual(refreshed[0].remaining_seconds, duration)
            self.assertEqual(
                evaluate_combat_modifiers(player).get(MODIFIER_AXIS, 0), modifier_before
            )
        clock.advance(duration, AdvanceSource.COMMAND, (player,))
        self.assertNotIn(BUFF_KEY, entity_active_buffs(player))
        self.assertEqual(
            evaluate_combat_modifiers(player).get(MODIFIER_AXIS, 0), baseline_modifier
        )

        # SP-axis exhaustion: the ordinary attack takes over through the same
        # selection boundary, so the other payable axis is real evidence too.
        pecker.traits.sp.current = 0
        depleted_mp = pecker.traits.mp.current
        fallback = _enemy_policy(pecker, field, record)
        self.assertEqual(fallback.skill_key, "basic_attack")
        with patch(
            "world.rules.combat.damage.roll_d100", return_value=80
        ), combat_provenance(engagement_provenance().at_slot(0)):
            self.assertEqual(ActionResolver.resolve(fallback).outcome, "success")
        reloaded = Monster.objects.get(pk=pecker.pk)
        self.assertEqual(reloaded.species_key, pecker.species_key)
        self.assertEqual(reloaded.variant_key, pecker.variant_key)
        self.assertEqual(reloaded.traits.mp.current, depleted_mp)
        self.assertEqual(reloaded.traits.sp.current, 0)
        self.assertEqual(reloaded.db.skills["active"], [SKILL_KEY])
        self.assertEqual(reloaded.db.behaviour_tree, BEHAVIOUR_KEY)

        # Late-target gate: the policy's own request, taken at full health so
        # the kit is the selection, is resolved after its target died.
        reloaded.traits.sp.current = reloaded.traits.sp.max
        reloaded.traits.mp.current = reloaded.traits.mp.max
        reloaded.traits.hp.current = reloaded.traits.hp.max
        strike = _enemy_policy(reloaded, field, record)
        self.assertEqual(strike.skill_key, SKILL_KEY)
        paid_before = (reloaded.traits.mp.current, reloaded.traits.sp.current)
        practice_before = dict(reloaded.db.skill_proficiency or {})
        player_hp = player.traits.hp.current
        player.traits.hp.current = 0
        with combat_provenance(engagement_provenance().at_slot(0)):
            late = ActionResolver.resolve(strike)
        self.assertEqual(late.outcome, "rejected")
        self.assertEqual(late.reason, RejectReason.TARGET_DEAD)
        self.assertEqual(
            (reloaded.traits.mp.current, reloaded.traits.sp.current), paid_before
        )
        self.assertEqual(dict(reloaded.db.skill_proficiency or {}), practice_before)
        # Restore the victim so the flee-boundary probe below still has a
        # living enemy to select against.
        player.traits.hp.current = player_hp

        # Inclusive flee edge, located with the engine's own comparison.
        maximum = reloaded.traits.hp.max
        threshold = resolve_behaviour_profile(reloaded).flee_hp_fraction
        self.assertIsNotNone(threshold)
        edge = flee_edge(maximum, threshold)
        self.assertGreater(edge, 0)
        reloaded.traits.hp.current = edge
        self.assertEqual(_enemy_policy(reloaded, field, record).skill_key, FLEE_SKILL_KEY)
        if edge < maximum:
            reloaded.traits.hp.current = edge + 1
            self.assertEqual(_enemy_policy(reloaded, field, record).skill_key, SKILL_KEY)


class EnemyRiderGroupMemberTests(EvenniaTestCase):
    """Every derived member of the enemy hit-rider composition group.

    The smoke above exercises the group's stable-key-ordered representative;
    this check derives the whole group from the shipped declarations (no key
    list) and repeats the rider contract on each member: the member's own
    decision mode offers its owned kit against the lone enemy, settlement
    pays the declared cost once on a miss and on a hit, a landed hit mounts
    the member's own rider on the struck enemy only and moves that enemy's
    declared modifier axis, a miss leaves every recipient untouched, and a
    committed reload keeps both spent pools and the mounted rider. Movement
    and flee availability stay with the shared rider and flee suites.
    """

    _TARGET_AGILITY = 10

    def _opponent(self, room, key):
        """One real target that survives either attempt and adds no defense."""
        player = create_object(PlayerCharacter, key=key, location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.defense.base = 0
        player.traits.agility.base = self._TARGET_AGILITY
        return player

    @staticmethod
    def _gauges(entity):
        return (entity.traits.hp.current, entity.traits.mp.current, entity.traits.sp.current)

    @staticmethod
    def _paid_once(member, skill, before):
        """The declared cost left the member's own pools exactly once."""
        return (
            member.traits.mp.current == before[0] - skill.cost.get("mp", 0),
            member.traits.sp.current == before[1] - skill.cost.get("sp", 0),
        )

    def test_every_group_member_lands_its_own_rider_and_misses_clean(self):
        signature = variant_signature(REPRESENTATIVE_ROW, SKILL_REGISTRY)
        members = composition_groups(MONSTER_VARIANT_REGISTRY, SKILL_REGISTRY)[signature]
        self.assertIn(REPRESENTATIVE_VARIANT, members)
        for position, variant_key in enumerate(members):
            with self.subTest(variant=variant_key):
                row = MONSTER_VARIANT_REGISTRY[variant_key]
                skill_key = row.active_skill_keys[0]
                skill = SKILL_REGISTRY[skill_key]
                buff_key = _mounted_buff_key(skill)
                axis, magnitude = _linked_modifier_axis_and_delta(buff_key)
                definition = BUFF_DEFINITIONS[buff_key]
                self.assertIs(type(definition.duration), int)
                self.assertGreater(definition.duration, 0)
                self.assertEqual(definition.stacking, "refresh")

                member = construct_species_individual(row.species_key, variant_key)
                room = create_object(Room, key=f"t_rider_member_room_{position}")
                member.location = room
                opponent = self._opponent(room, f"t_rider_member_target_{position}")
                ally = construct_species_individual(row.species_key, variant_key)
                ally.location = room
                field = Battlefield(
                    {
                        "party": frozenset({stable_actor_id(opponent)}),
                        "foes": frozenset(
                            {stable_actor_id(member), stable_actor_id(ally)}
                        ),
                    },
                    {
                        stable_actor_id(opponent): opponent,
                        stable_actor_id(member): member,
                        stable_actor_id(ally): ally,
                    },
                )
                context = BattlefieldActionContext(field)
                target_state = (
                    *self._gauges(opponent),
                    dict(evaluate_combat_modifiers(opponent)),
                )
                ally_state = (
                    *self._gauges(ally),
                    dict(evaluate_combat_modifiers(ally)),
                )

                # Candidacy: a reflex member's own decision returns its kit
                # against the lone enemy; a utility member offers the same kit
                # as a scored plan aimed at it, whatever else it may choose.
                trace = []
                request = monster_behaviour_policy(
                    member, field, context=context, trace=trace
                )
                self.assertIsNotNone(request)
                if resolve_monster_ai(member).mode is DecisionMode.REFLEX:
                    self.assertEqual(request.skill_key, skill_key)
                    self.assertEqual(request.targets, [opponent])
                else:
                    plans = [
                        plan for plan in trace[-1].plans if plan.skill_key == skill_key
                    ]
                    self.assertEqual(len(plans), 1)
                    self.assertEqual(
                        plans[0].target_ids, (stable_actor_id(opponent),)
                    )
                    self.assertGreater(plans[0].damage, 0)

                # A miss still pays the declared cost and grants nothing to
                # any recipient: the rider is hit-qualified.
                before = (member.traits.mp.current, member.traits.sp.current)
                with patch("world.rules.combat.damage.roll_d100", return_value=1):
                    missed = resolve_combat_action(
                        ActionRequest(member, skill_key, [opponent], context)
                    )
                self.assertEqual(missed.outcome, "success")
                self.assertEqual(self._paid_once(member, skill, before), (True, True))
                for entity in (opponent, ally, member):
                    self.assertNotIn(buff_key, entity_active_buffs(entity))
                self.assertEqual(
                    (*self._gauges(opponent), dict(evaluate_combat_modifiers(opponent))),
                    target_state,
                )

                # A landed hit mounts the member's own rider on the struck
                # enemy only and moves that enemy's declared axis by the
                # member's authored magnitude. Restoring both pools keeps the
                # hit probe independent of which pools the kit spends.
                member.traits.mp.current = member.traits.mp.max
                member.traits.sp.current = member.traits.sp.max
                before = (member.traits.mp.current, member.traits.sp.current)
                with patch("world.rules.combat.damage.roll_d100", return_value=80):
                    landed = resolve_combat_action(
                        ActionRequest(member, skill_key, [opponent], context)
                    )
                self.assertEqual(landed.outcome, "success")
                self.assertEqual(self._paid_once(member, skill, before), (True, True))
                self.assertLess(opponent.traits.hp.current, target_state[0])
                self.assertIn(buff_key, entity_active_buffs(opponent))
                self.assertNotIn(buff_key, entity_active_buffs(member))
                self.assertNotIn(buff_key, entity_active_buffs(ally))
                self.assertEqual(
                    evaluate_combat_modifiers(opponent).get(axis, 0),
                    target_state[3].get(axis, 0) + magnitude,
                )
                self.assertEqual(
                    (*self._gauges(ally), dict(evaluate_combat_modifiers(ally))),
                    ally_state,
                )

                # Committed reload: the mounted rider, its remaining lifetime,
                # the recipient's moved axis and both spent pools are durable.
                remaining = _buff_instances(opponent, buff_key)[0].remaining_seconds
                self.assertGreater(remaining, 0)
                self.assertLessEqual(remaining, definition.duration)
                spent = (member.traits.mp.current, member.traits.sp.current)
                opponent.flush_cached_instance(opponent)
                member.flush_cached_instance(member)
                flush_cache()
                reloaded_target = PlayerCharacter.objects.get(pk=opponent.pk)
                reloaded_member = Monster.objects.get(pk=member.pk)
                self.assertIsNot(reloaded_target, opponent)
                self.assertIsNot(reloaded_member, member)
                self.assertIn(buff_key, entity_active_buffs(reloaded_target))
                self.assertEqual(
                    evaluate_combat_modifiers(reloaded_target).get(axis, 0),
                    target_state[3].get(axis, 0) + magnitude,
                )
                self.assertEqual(
                    (
                        reloaded_member.traits.mp.current,
                        reloaded_member.traits.sp.current,
                    ),
                    spent,
                )

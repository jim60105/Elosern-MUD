"""Data-contract test: sparrow representative-composition production smoke over the generic rider/lifetime contracts

The stable-key-ordered representative of the enemy hit-rider composition shape
is constructed for real and observed through one committed session: authored
selection, resolver payment, mounted rider delivery to the hit enemy only,
aged refresh and expiry on the representative's own declared lifetime, ordinary
fallback on its exhausted SP axis, the inclusive flee edge, a late-target
rejection and a committed reload. Shared synthetic suites own the hit,
recipient-control, rollback and lifetime mechanism vectors.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.rules.action import ActionResolver, RejectReason
from world.rules.buffs import BUFF_DEFINITIONS, entity_active_buffs
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import Battlefield
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.combat_session.lifecycle import engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import resolve_behaviour_profile
from world.rules.monster_individual import construct_species_individual
from world.rules.tests.combat_fixtures import flee_edge
from world.skills.registry import SKILL_REGISTRY

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


def _buff_instances(entity):
    return [buff for buff in entity.buffs.all.values() if buff.definition_key == BUFF_KEY]


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
            {"party": frozenset({player.key}), "foes": frozenset({pecker.key})},
            {player.key: player, pecker.key: pecker},
        )
        skill = SKILL_REGISTRY[SKILL_KEY]
        baseline_modifier = evaluate_combat_modifiers(player).get(MODIFIER_AXIS, 0)
        request = _enemy_policy(pecker, field, record)
        self.assertEqual(request.skill_key, SKILL_KEY)
        self.assertEqual(request.targets, [player])
        before = (pecker.traits.mp.current, pecker.traits.sp.current)
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
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
            with patch("world.rules.combat.damage.roll_d100", return_value=80):
                self.assertEqual(ActionResolver.resolve(refresh_request).outcome, "success")
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
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
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

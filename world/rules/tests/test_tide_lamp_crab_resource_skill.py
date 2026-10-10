"""Data-contract test: crab resource skill production combat smoke contract

One real session proves hit-independent self-guard routing, nominal payment,
aged ally-attempt refresh and durable depletion. Shared synthetic tests own
formula, rejection, hit-evidence and rollback vectors.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver
from world.rules.buffs import BUFF_DEFINITIONS, entity_active_buffs
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.combat_session.lifecycle import engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.monster_individual import construct_species_individual
from world.skills.registry import SKILL_REGISTRY

SKILL_KEY = "lamp_carapace_claw"
BUFF_KEY = "lamp_carapace_guard"


def _buff_instances(entity):
    return [buff for buff in entity.buffs.all.values() if buff.definition_key == BUFF_KEY]


class TideLampCrabResourceSkillSmokeTests(EvenniaTestCase):
    def _opponent(self, room, key):
        player = create_object(PlayerCharacter, key=key, location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        return player

    @covers_requirement(
        "monster-action-policy::潮燈蟹-contact-kit-uses-existing-first-owned-policy-and-fallback",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-resource-abilities::潮燈蟹-timed-modifier-follows-its-authored-recipient-and-lifetime",
        "test-data-independence::representative-production-smoke-proves-real-consumer-integration-proportionally",
    )
    def test_production_self_guard_miss_ally_refresh_payment_and_reload(self):
        """Detect hit-gated guard, role swap, stale refresh or lost durable source."""
        crab = construct_species_individual("tide_lamp_crab", "shore_walker")
        room = create_object(Room, key="t_guard_smoke_room")
        player = self._opponent(room, "t_guard_smoke_target")
        ally = self._opponent(room, "t_guard_smoke_ally")
        crab.location = room
        engage(player, crab)
        record = read_session(player)
        field = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({crab.key, ally.key})},
            {player.key: player, crab.key: crab, ally.key: ally},
        )
        skill = SKILL_REGISTRY[SKILL_KEY]
        baseline_defense = evaluate_combat_modifiers(crab).get("defense", 0)
        before = (crab.traits.mp.current, crab.traits.sp.current)
        controls = {entity.pk: (entity.traits.hp.current, entity.traits.mp.current) for entity in (player, ally)}
        request = _enemy_policy(crab, field, record)
        self.assertEqual(request.skill_key, SKILL_KEY)
        self.assertEqual(request.targets, [player])
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            (crab.traits.mp.current, crab.traits.sp.current),
            (before[0] - skill.cost["mp"], before[1] - skill.cost["sp"]),
        )
        self.assertIn(BUFF_KEY, entity_active_buffs(crab))
        self.assertGreater(evaluate_combat_modifiers(crab)["defense"], baseline_defense)
        for entity in (player, ally):
            self.assertNotIn(BUFF_KEY, entity_active_buffs(entity))
            self.assertEqual((entity.traits.hp.current, entity.traits.mp.current), controls[entity.pk])
        duration = BUFF_DEFINITIONS[BUFF_KEY].duration
        self.assertEqual(_buff_instances(crab)[0].remaining_seconds, duration)
        clock = WorldClock()
        # A duration of one second has no integer pre-expiry aging instant.
        # Shared synthetic fixtures retain the exact refresh-edge mechanism.
        if duration > 1:
            age = max(1, duration // 2)
            clock.advance(age, AdvanceSource.COMMAND, (crab,))
            self.assertEqual(_buff_instances(crab)[0].remaining_seconds, duration - age)
            modifier_before = evaluate_combat_modifiers(crab)["defense"]
            crab.traits.mp.current = crab.traits.mp.max
            crab.traits.sp.current = crab.traits.sp.max
            ally_before = (ally.traits.hp.current, ally.traits.mp.current)
            paid_before = (crab.traits.mp.current, crab.traits.sp.current)
            with patch("world.rules.combat.damage.roll_d100", return_value=80):
                refreshed = ActionResolver.resolve(ActionRequest(
                    crab, SKILL_KEY, [ally], BattlefieldActionContext(field),
                ))
            self.assertEqual(refreshed.outcome, "success")
            self.assertEqual((ally.traits.hp.current, ally.traits.mp.current), ally_before)
            self.assertNotIn(BUFF_KEY, entity_active_buffs(ally))
            self.assertEqual(len(_buff_instances(crab)), 1)
            self.assertEqual(_buff_instances(crab)[0].remaining_seconds, duration)
            self.assertEqual(evaluate_combat_modifiers(crab)["defense"], modifier_before)
            self.assertEqual(
                (crab.traits.mp.current, crab.traits.sp.current),
                (paid_before[0] - skill.cost["mp"], paid_before[1] - skill.cost["sp"]),
            )
        # Reload while the guard remains mounted, before observing expiry.
        depleted_sp = crab.traits.sp.current
        crab.traits.mp.current = 0
        reloaded = Monster.objects.get(pk=crab.pk)
        self.assertEqual(reloaded.species_key, "tide_lamp_crab")
        self.assertEqual(reloaded.variant_key, "shore_walker")
        self.assertEqual(reloaded.traits.mp.current, 0)
        self.assertEqual(reloaded.traits.sp.current, depleted_sp)
        self.assertEqual(reloaded.db.skills["active"], [SKILL_KEY])
        self.assertEqual(reloaded.db.behaviour_tree, "instinctive")
        self.assertIn(BUFF_KEY, entity_active_buffs(reloaded))
        self.assertEqual(_buff_instances(reloaded)[0].remaining_seconds, duration)
        fallback = _enemy_policy(reloaded, field, record)
        self.assertEqual(fallback.skill_key, "basic_attack")
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            self.assertEqual(ActionResolver.resolve(fallback).outcome, "success")
        self.assertEqual(reloaded.traits.mp.current, 0)
        self.assertEqual(reloaded.traits.sp.current, depleted_sp)
        clock.advance(duration, AdvanceSource.COMMAND, (reloaded,))
        self.assertNotIn(BUFF_KEY, entity_active_buffs(reloaded))
        self.assertEqual(evaluate_combat_modifiers(reloaded).get("defense", 0), baseline_defense)

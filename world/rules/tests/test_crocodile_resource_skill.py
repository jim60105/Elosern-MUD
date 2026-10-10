"""Data-contract test: crocodile resource skill production combat smoke contract

One real session composition observes selection, payment, recipient controls
and durable depletion. Shared synthetic suites own transfer arithmetic and
hit/rollback vectors; generic content checks own both variant profiles.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import ActionResolver
from world.rules.combat import Battlefield
from world.rules.combat_session.lifecycle import engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.monster_individual import construct_species_individual
from world.skills.registry import SKILL_REGISTRY


class CrocodileResourceSkillSmokeTests(EvenniaTestCase):
    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
        "monster-action-policy::authored-crocodile-behavior-uses-the-existing-first-owned-strategy",
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-resource-abilities::production-crocodile-delivery-includes-real-combat-and-persistence-evidence",
        "test-data-independence::representative-production-smoke-proves-real-consumer-integration-proportionally",
    )
    def test_production_drain_session_payment_controls_and_reload(self):
        """Detect wrong selection, recipient, missing payment or startup refill."""
        crocodile = construct_species_individual("tide_devouring_crocodile", "bank_lurker")
        room = create_object(Room, key="t_drain_smoke_room")
        player = create_object(PlayerCharacter, key="t_drain_smoke_target", location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.mp.base = 100
        player.traits.mp.current = 100
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        crocodile.location = room
        control = create_object(PlayerCharacter, key="t_drain_smoke_control", location=room)
        control.race = "human"
        control.apply_race_baseline()
        control_before = (control.traits.hp.current, control.traits.mp.current)
        engage(player, crocodile)
        record = read_session(player)
        field = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({crocodile.key})},
            {player.key: player, crocodile.key: crocodile},
        )
        action = _enemy_policy(crocodile, field, record)
        self.assertIsNotNone(action)
        self.assertEqual(action.skill_key, "tide_devouring_bite")
        self.assertEqual(action.targets, [player])
        skill = SKILL_REGISTRY[action.skill_key]
        before_mp = crocodile.traits.mp.current
        before_sp = crocodile.traits.sp.current
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            result = ActionResolver.resolve(action)
        self.assertEqual(result.outcome, "success")
        self.assertLess(player.traits.hp.current, 10000)
        self.assertLess(player.traits.mp.current, 100)
        # This observes authored payment reaching the real settlement boundary.
        # Calculation correctness and full-cap ordering remain synthetic properties.
        self.assertEqual(crocodile.traits.mp.current, before_mp - skill.cost["mp"])
        self.assertEqual(crocodile.traits.sp.current, before_sp - skill.cost["sp"])
        self.assertEqual((control.traits.hp.current, control.traits.mp.current), control_before)
        crocodile.traits.mp.current = 0
        depleted_sp = crocodile.traits.sp.current
        fallback = _enemy_policy(crocodile, field, record)
        self.assertEqual(fallback.skill_key, "basic_attack")
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            self.assertEqual(ActionResolver.resolve(fallback).outcome, "success")
        reloaded = Monster.objects.get(pk=crocodile.pk)
        self.assertEqual(reloaded.species_key, "tide_devouring_crocodile")
        self.assertEqual(reloaded.variant_key, "bank_lurker")
        self.assertEqual(reloaded.traits.mp.current, 0)
        self.assertEqual(reloaded.traits.sp.current, depleted_sp)
        self.assertEqual(reloaded.db.skills["active"], [skill.key])
        self.assertEqual(reloaded.db.behaviour_tree, "ambush_predator")
        target = PlayerCharacter.objects.get(pk=player.pk)
        self.assertEqual(target.traits.hp.current, player.traits.hp.current)
        self.assertEqual(target.traits.mp.current, player.traits.mp.current)

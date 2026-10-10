"""Data-contract test: crocodile representative-composition production smoke over the generic transfer/policy contracts

The stable-key-ordered representative of the transfer/drain composition shape
is constructed for real and observed through one committed session: authored
selection, resolver payment, untouched controls, ordinary fallback on its
exhausted MP axis, the inclusive flee edge, a late-target rejection and a
committed reload. Shared synthetic suites own the transfer arithmetic, the
hit/miss/absorbed vectors and the post-write rollback.
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
from world.rules.combat import Battlefield
from world.rules.combat_session.lifecycle import engage
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import read_session
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import resolve_behaviour_profile
from world.rules.monster_individual import construct_species_individual
from world.skills.registry import SKILL_REGISTRY

# The representative the composition-coverage check derives for this group.
REPRESENTATIVE_VARIANT = "bank_lurker"
REPRESENTATIVE_ROW = MONSTER_VARIANT_REGISTRY[REPRESENTATIVE_VARIANT]
SKILL_KEY = REPRESENTATIVE_ROW.active_skill_keys[0]
BEHAVIOUR_KEY = REPRESENTATIVE_ROW.behaviour_profile_key


class CrocodileResourceSkillSmokeTests(EvenniaTestCase):
    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
        "monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback",
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence",
        "test-data-independence::representative-production-smoke-proves-real-consumer-integration-proportionally",
    )
    def test_production_drain_session_payment_controls_and_reload(self):
        """Detect wrong selection, recipient, missing payment or startup refill."""
        crocodile = construct_species_individual(
            REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
        )
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
        self.assertEqual(action.skill_key, SKILL_KEY)
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

        # MP-axis exhaustion: the ordinary attack takes over, still through the
        # same selection boundary and the same per-axis affordability rule.
        crocodile.traits.mp.current = 0
        depleted_sp = crocodile.traits.sp.current
        fallback = _enemy_policy(crocodile, field, record)
        self.assertEqual(fallback.skill_key, "basic_attack")
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            self.assertEqual(ActionResolver.resolve(fallback).outcome, "success")
        reloaded = Monster.objects.get(pk=crocodile.pk)
        self.assertEqual(reloaded.species_key, crocodile.species_key)
        self.assertEqual(reloaded.variant_key, crocodile.variant_key)
        self.assertEqual(reloaded.traits.mp.current, 0)
        self.assertEqual(reloaded.traits.sp.current, depleted_sp)
        self.assertEqual(reloaded.db.skills["active"], [skill.key])
        self.assertEqual(reloaded.db.behaviour_tree, BEHAVIOUR_KEY)
        target = PlayerCharacter.objects.get(pk=player.pk)
        self.assertEqual(target.traits.hp.current, player.traits.hp.current)
        self.assertEqual(target.traits.mp.current, player.traits.mp.current)

        # Inclusive flee edge on this representative's own declared threshold,
        # then a target that dies between selection and resolution.
        reloaded.traits.mp.current = reloaded.traits.mp.max
        threshold = resolve_behaviour_profile(reloaded).flee_hp_fraction
        self.assertIsNotNone(threshold)
        edge = int(reloaded.traits.hp.max * threshold)
        reloaded.traits.hp.current = edge
        self.assertEqual(_enemy_policy(reloaded, field, record).skill_key, FLEE_SKILL_KEY)
        reloaded.traits.hp.current = edge + 1
        strike = _enemy_policy(reloaded, field, record)
        self.assertEqual(strike.skill_key, SKILL_KEY)

        paid_before = (reloaded.traits.mp.current, reloaded.traits.sp.current)
        practice_before = dict(reloaded.db.skill_proficiency or {})
        player.traits.hp.current = 0
        late = ActionResolver.resolve(strike)
        self.assertEqual(late.outcome, "rejected")
        self.assertEqual(late.reason, RejectReason.TARGET_DEAD)
        self.assertEqual(
            (reloaded.traits.mp.current, reloaded.traits.sp.current), paid_before
        )
        self.assertEqual(dict(reloaded.db.skill_proficiency or {}), practice_before)

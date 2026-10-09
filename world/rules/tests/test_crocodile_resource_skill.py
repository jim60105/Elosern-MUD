"""Data-contract test: crocodile resource skill production combat smoke contract

Exercises both formally constructed crocodile variants (bank_lurker and bay_warden)
through real resolver-backed combat sessions with deterministic hit, miss,
and resource exhaustion falling back to basic_attack, verifying MP/SP payment,
drain, recovery, persistence reload, and no generative/image service calls.
"""

from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    run_round,
)
from world.rules.combat_session.policies import (
    _enemy_policy,
)
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.combat_session.lifecycle import engage
from world.rules.combat_session.lifecycle import clear_session
from world.rules.combat_session.records import read_session
from world.rules.combat_session.battlefield import _context_for
from world.rules.action import (
    ActionRequest,
    ActionResolver,
)
from world.rules.monster_individual import construct_species_individual
from world.skills.registry import SKILL_REGISTRY


class CrocodileResourceSkillSmokeTests(EvenniaTestCase):
    """Production combat smoke test for crocodile resource skills."""

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals",
        "skill-effect-model::dependent-recipients-intersect-ordinary-audiences-with-source-hits",
        "skill-effect-model::dependent-effects-retain-normal-settlement-and-rollback",
    )
    def test_production_crocodile_variants_combat_exhaustion_and_reload(self):
        # 1. Formally construct BOTH variants through the production entry point
        croc_bank = construct_species_individual("tide_devouring_crocodile", "bank_lurker")
        croc_bay = construct_species_individual("tide_devouring_crocodile", "bay_warden")

        self.assertEqual(croc_bank.variant_key, "bank_lurker")
        self.assertEqual(croc_bay.variant_key, "bay_warden")
        self.assertEqual(croc_bank.traits.hp.current, 140)
        self.assertEqual(croc_bank.traits.mp.current, 30)
        self.assertEqual(croc_bank.traits.sp.current, 40)
        self.assertEqual(croc_bay.traits.hp.current, 210)
        self.assertEqual(croc_bay.traits.mp.current, 50)
        self.assertEqual(croc_bay.traits.sp.current, 60)
        self.assertEqual(croc_bank.db.skills["active"], ["tide_devouring_bite"])
        self.assertEqual(croc_bay.db.skills["active"], ["tide_devouring_bite"])
        self.assertEqual(croc_bank.db.behaviour_tree, "ambush_predator")
        self.assertEqual(croc_bay.db.behaviour_tree, "ambush_predator")

        # 2. Opponent setup: valid controlled PlayerCharacter
        room = create_object(Room, key="river_bank")
        player = create_object(PlayerCharacter, key="target_hero")
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.current = 500
        player.traits.hp.base = 500
        player.traits.mp.current = 100
        player.traits.mp.base = 100
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        player.location = room
        croc_bank.location = room

        engage_res = engage(player, croc_bank)
        record = read_session(player)

        battlefield = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({croc_bank.key})},
            {player.key: player, croc_bank.key: croc_bank},
        )

        # 3. Step A: Policy selects tide_devouring_bite for bank_lurker
        action_1 = _enemy_policy(croc_bank, battlefield, record)
        self.assertIsNotNone(action_1)
        self.assertEqual(action_1.skill_key, "tide_devouring_bite")
        self.assertEqual(action_1.targets, [player])

        # Execute deterministic hit
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            res_hit = ActionResolver.resolve(action_1)
        self.assertEqual(res_hit.outcome, "success")
        # Target lost damage and 10 MP
        self.assertLess(player.traits.hp.current, 500)
        self.assertEqual(player.traits.mp.current, 90)
        # Croc started at 30 MP, 40 SP: recovered 10 MP (clamped at 30), paid 10 MP / 5 SP -> 20 MP, 35 SP
        self.assertEqual(croc_bank.traits.mp.current, 20)
        self.assertEqual(croc_bank.traits.sp.current, 35)

        # 4. Step B: Deterministic miss
        action_2 = _enemy_policy(croc_bank, battlefield, record)
        self.assertEqual(action_2.skill_key, "tide_devouring_bite")
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            res_miss = ActionResolver.resolve(action_2)
        self.assertEqual(res_miss.outcome, "success")
        # Miss: 0 damage, 0 drain -> player stays at 90 MP
        self.assertEqual(player.traits.mp.current, 90)
        # Croc paid 10 MP, 5 SP -> 10 MP, 30 SP
        self.assertEqual(croc_bank.traits.mp.current, 10)
        self.assertEqual(croc_bank.traits.sp.current, 30)

        # 5. Step C: Hit from 10 MP -> recovers 10 to 20, pays 10 to 10 MP, pays 5 SP to 25 SP
        action_3 = _enemy_policy(croc_bank, battlefield, record)
        self.assertEqual(action_3.skill_key, "tide_devouring_bite")
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            res_hit_2 = ActionResolver.resolve(action_3)
        self.assertEqual(res_hit_2.outcome, "success")
        self.assertEqual(player.traits.mp.current, 80)
        self.assertEqual(croc_bank.traits.mp.current, 10)
        self.assertEqual(croc_bank.traits.sp.current, 25)

        # 6. Step D: Exhaustion -> deplete MP to 0 so bite is unaffordable
        croc_bank.traits.mp.current = 0
        action_exhausted = _enemy_policy(croc_bank, battlefield, record)
        self.assertIsNotNone(action_exhausted)
        # Policy falls back to basic_attack!
        self.assertEqual(action_exhausted.skill_key, "basic_attack")
        self.assertEqual(action_exhausted.targets, [player])

        # Resolve basic_attack
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            res_basic = ActionResolver.resolve(action_exhausted)
        self.assertEqual(res_basic.outcome, "success")
        # basic_attack costs 0 MP / 0 SP, deals physical damage
        self.assertEqual(croc_bank.traits.mp.current, 0)
        self.assertEqual(croc_bank.traits.sp.current, 25)

        # 7. Persistence reload of depleted participants
        reloaded_croc = Monster.objects.get(pk=croc_bank.pk)
        self.assertEqual(reloaded_croc.species_key, "tide_devouring_crocodile")
        self.assertEqual(reloaded_croc.variant_key, "bank_lurker")
        self.assertEqual(reloaded_croc.traits.mp.current, 0)
        self.assertEqual(reloaded_croc.traits.sp.current, 25)
        self.assertEqual(reloaded_croc.db.skills["active"], ["tide_devouring_bite"])
        self.assertEqual(reloaded_croc.db.behaviour_tree, "ambush_predator")

        reloaded_player = PlayerCharacter.objects.get(pk=player.pk)
        self.assertEqual(reloaded_player.traits.hp.current, player.traits.hp.current)
        self.assertEqual(reloaded_player.traits.mp.current, 80)

        # 8. Bay warden combat resolution smoke
        clear_session(player)
        croc_bay.location = room
        engage(player, croc_bay)
        record_bay = read_session(player)
        battlefield_bay = Battlefield(
            {"party": frozenset({player.key}), "foes": frozenset({croc_bay.key})},
            {player.key: player, croc_bay.key: croc_bay},
        )
        action_bay = _enemy_policy(croc_bay, battlefield_bay, record_bay)
        self.assertEqual(action_bay.skill_key, "tide_devouring_bite")
        # Bay warden starts at 50 MP, 60 SP. Hit from 50 clamps at 50, pays 10 MP -> 40 MP, pays 5 SP -> 55 SP
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            res_bay = ActionResolver.resolve(action_bay)
        self.assertEqual(res_bay.outcome, "success")
        self.assertEqual(croc_bay.traits.mp.current, 40)
        self.assertEqual(croc_bay.traits.sp.current, 55)
        self.assertEqual(player.traits.mp.current, 70)

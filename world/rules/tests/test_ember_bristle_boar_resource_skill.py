"""Data-contract test: boar two-strike representative-composition production smoke over the generic area/single damage and payment contracts

The stable-key-ordered representative of the two-strike composition shape is
constructed for real and observed through real policy selection and resolver
settlement: one opponent selects the single-target charge, a party of two
selects the area sweep, the sweep reaches every living enemy with its own hit
and defense outcome while an allied control stays untouched, both resources are
paid once per cast, either exhausted resource falls back to the innate attack,
freeform scaling stays unreachable, and a committed reload preserves the spent
pools, kit and behaviour binding. Shared synthetic suites own the damage
arithmetic, the hit/miss vectors and the post-write rollback.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.rules.action import ActionResolver
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    combat_provenance,
)
from world.rules.combat_identity import stable_actor_id
from world.rules.combat_session.policies import BASIC_ATTACK_KEY
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.monster_individual import construct_species_individual
from world.rules.progression import freeform_scales_for
from world.rules.tests._combat_session_helpers import engagement_provenance
from world.skills.registry import SKILL_REGISTRY

# The representative the composition-coverage check derives for this group.
REPRESENTATIVE_VARIANT = "warm_den_boar"
REPRESENTATIVE_ROW = MONSTER_VARIANT_REGISTRY[REPRESENTATIVE_VARIANT]
CHARGE_KEY, SWEEP_KEY = REPRESENTATIVE_ROW.active_skill_keys
CHARGE = SKILL_REGISTRY[CHARGE_KEY]
SWEEP = SKILL_REGISTRY[SWEEP_KEY]
BEHAVIOUR_KEY = REPRESENTATIVE_ROW.behaviour_profile_key

#: Below the cheapest kit cost of one resource, no kit skill is affordable.
MINIMUM_KIT_MP = min(skill.cost["mp"] for skill in (CHARGE, SWEEP))
MINIMUM_KIT_SP = min(skill.cost["sp"] for skill in (CHARGE, SWEEP))


def _opponent(room, key, *, defense):
    """One real player combatant whose defense is its own authored value."""
    player = create_object(PlayerCharacter, key=key, location=room)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.hp.base = 10000
    player.traits.hp.current = 10000
    player.traits.defense.base = defense
    player.traits.agility.base = 10
    return player


def _field(boar, ally, enemies):
    """One battlefield whose roster keeps the enemies in authored order."""
    roster = {
        stable_actor_id(entity): entity for entity in (*enemies, boar, ally)
    }
    return Battlefield(
        {
            "party": frozenset(stable_actor_id(enemy) for enemy in enemies),
            "foes": frozenset({stable_actor_id(boar), stable_actor_id(ally)}),
        },
        roster,
    )


def _resources(entity):
    """The observable pools and hit points of one control recipient."""
    return (
        entity.traits.hp.current,
        entity.traits.mp.current,
        entity.traits.sp.current,
    )


class EmberBristleBoarResourceSkillSmokeTests(EvenniaTestCase):
    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
        "monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback",
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-individual-construction::constructed-kits-and-depleted-resources-survive-reload-without-registry-resets",
        "monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence",
        "test-data-independence::representative-production-smoke-proves-real-consumer-integration-proportionally",
    )
    def test_production_two_strike_selection_recipients_payment_and_reload(self):
        """Detect wrong selection, recipient set, payment or lost durable kit."""
        boar = construct_species_individual(
            REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
        )
        ally = construct_species_individual(
            REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
        )
        room = create_object(Room, key="t_ember_boar_smoke_room")
        boar.location = room
        ally.location = room
        front = _opponent(room, "t_ember_boar_smoke_front", defense=0)
        rear = _opponent(room, "t_ember_boar_smoke_rear", defense=20)

        # Selection: one opponent selects the single-target charge, while two
        # opponents select the area sweep. The legacy body scores the charge
        # and the innate attack equally (both are physical), so its tie-break
        # die is pinned to the even branch that keeps the owned kit first.
        single_field = _field(boar, ally, (front,))
        single_context = BattlefieldActionContext(single_field)
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100", return_value=100
        ):
            single = monster_behaviour_policy(
                boar, single_field, context=single_context
            )
        self.assertIsNotNone(single)
        self.assertEqual(single.skill_key, CHARGE_KEY)
        self.assertEqual(single.targets, [front])

        pair_field = _field(boar, ally, (front, rear))
        pair_context = BattlefieldActionContext(pair_field)
        pair = monster_behaviour_policy(boar, pair_field, context=pair_context)
        self.assertIsNotNone(pair)
        self.assertEqual(pair.skill_key, SWEEP_KEY)
        self.assertEqual(pair.targets, "all-enemies")

        # The single-target strike reaches its chosen enemy, pays both costs
        # once, and leaves the allied control untouched.
        ally_control = _resources(ally)
        front_before = front.traits.hp.current
        paid_mp = boar.traits.mp.current
        paid_sp = boar.traits.sp.current
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            combat_provenance(engagement_provenance().at_slot(0)),
        ):
            charged = ActionResolver.resolve(single)
        self.assertEqual(charged.outcome, "success")
        self.assertLess(front.traits.hp.current, front_before)
        self.assertEqual(boar.traits.mp.current, paid_mp - CHARGE.cost["mp"])
        self.assertEqual(boar.traits.sp.current, paid_sp - CHARGE.cost["sp"])
        self.assertEqual(_resources(ally), ally_control)

        # First sweep: one recipient lands and the other misses, so the two
        # hit outcomes are recorded separately, and the cast pays once.
        boar.traits.mp.current = boar.traits.mp.max
        boar.traits.sp.current = boar.traits.sp.max
        front_before = front.traits.hp.current
        rear_before = rear.traits.hp.current
        paid_mp = boar.traits.mp.current
        paid_sp = boar.traits.sp.current
        ally_control = _resources(ally)
        with (
            patch(
                "world.rules.combat.damage.roll_d100", side_effect=[100, 1]
            ),
            combat_provenance(engagement_provenance().at_slot(0)),
        ):
            swept = ActionResolver.resolve(pair)
        self.assertEqual(swept.outcome, "success")
        self.assertLess(front.traits.hp.current, front_before)
        self.assertEqual(rear.traits.hp.current, rear_before)
        self.assertEqual(boar.traits.mp.current, paid_mp - SWEEP.cost["mp"])
        self.assertEqual(boar.traits.sp.current, paid_sp - SWEEP.cost["sp"])
        self.assertEqual(_resources(ally), ally_control)

        # Second sweep: both recipients land, and each strike is mitigated by
        # that recipient's own defense, so the per-cast losses differ.
        front_before = front.traits.hp.current
        rear_before = rear.traits.hp.current
        paid_mp = boar.traits.mp.current
        paid_sp = boar.traits.sp.current
        with (
            patch(
                "world.rules.combat.damage.roll_d100", side_effect=[100, 100]
            ),
            combat_provenance(engagement_provenance().at_slot(0)),
        ):
            swept_again = ActionResolver.resolve(pair)
        self.assertEqual(swept_again.outcome, "success")
        front_loss = front_before - front.traits.hp.current
        rear_loss = rear_before - rear.traits.hp.current
        self.assertGreater(front_loss, 0)
        self.assertGreater(rear_loss, 0)
        self.assertGreater(front_loss, rear_loss)
        self.assertEqual(boar.traits.mp.current, paid_mp - SWEEP.cost["mp"])
        self.assertEqual(boar.traits.sp.current, paid_sp - SWEEP.cost["sp"])

        # Either exhausted resource removes the whole kit from the affordable
        # set, and the innate attack takes over through the same boundary.
        boar.traits.mp.current = boar.traits.mp.max
        boar.traits.sp.current = boar.traits.sp.max
        boar.traits.mp.current = MINIMUM_KIT_MP - 1
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100", return_value=100
        ):
            exhausted_mp = monster_behaviour_policy(
                boar, single_field, context=single_context
            )
        self.assertIsNotNone(exhausted_mp)
        self.assertEqual(exhausted_mp.skill_key, BASIC_ATTACK_KEY)

        boar.traits.mp.current = boar.traits.mp.max
        boar.traits.sp.current = MINIMUM_KIT_SP - 1
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100", return_value=100
        ):
            exhausted_sp = monster_behaviour_policy(
                boar, single_field, context=single_context
            )
        self.assertIsNotNone(exhausted_sp)
        self.assertEqual(exhausted_sp.skill_key, BASIC_ATTACK_KEY)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            combat_provenance(engagement_provenance().at_slot(0)),
        ):
            fallback = ActionResolver.resolve(exhausted_sp)
        self.assertEqual(fallback.outcome, "success")

        # Shape eligibility alone never grants freeform scaling: the element's
        # mastery passive is not owned by the kit.
        for skill_key in REPRESENTATIVE_ROW.active_skill_keys:
            with self.subTest(skill=skill_key):
                self.assertEqual(
                    freeform_scales_for(boar, SKILL_REGISTRY[skill_key]), ()
                )

        # A committed reload keeps the spent pools, the kit and the binding.
        boar.traits.mp.current = 7
        boar.traits.sp.current = 3
        boar.flush_cached_instance(boar)
        reloaded = Monster.objects.get(pk=boar.pk)
        self.assertIsNot(reloaded, boar)
        self.assertEqual(reloaded.species_key, REPRESENTATIVE_ROW.species_key)
        self.assertEqual(reloaded.variant_key, REPRESENTATIVE_VARIANT)
        self.assertEqual(reloaded.traits.mp.current, 7)
        self.assertEqual(reloaded.traits.sp.current, 3)
        self.assertEqual(
            reloaded.db.skills["active"],
            list(REPRESENTATIVE_ROW.active_skill_keys),
        )
        self.assertEqual(reloaded.db.behaviour_tree, BEHAVIOUR_KEY)

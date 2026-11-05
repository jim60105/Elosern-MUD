"""Data-contract test: crocodile drain-and-guard representative-composition production smoke over the generic transfer/self-support/lifetime contracts

The stable-key-ordered representative of the drain-plus-self-support
composition shape is constructed for real and observed through one committed
session: the shipped utility binding offers plans for both kit skills, an
explicit guard cast pays its own MP once and mounts the film on the caster
only, an explicit bite on a hit drains the opponent's actual current MP and
credits the caster before the bite's own costs are deducted, an aged mount
refreshes to one contribution and expires cleanly, an insufficient pool
removes the guard from the candidate set and a forced guard request is
rejected without payment, and a committed reload keeps the spent pools, the
remaining lifetime, the kit and the binding. Shared synthetic suites own the
transfer arithmetic, the hit/miss/absorbed vectors and the post-write
rollback.
"""

from pathlib import Path
from unittest.mock import patch

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
from world.skills.effects import parse_effect
from world.skills.registry import SKILL_REGISTRY

# The representative the composition-coverage check derives for this group.
REPRESENTATIVE_VARIANT = "reservoir_warden"
REPRESENTATIVE_ROW = MONSTER_VARIANT_REGISTRY[REPRESENTATIVE_VARIANT]
BITE_KEY, GUARD_KEY = REPRESENTATIVE_ROW.active_skill_keys
BITE = SKILL_REGISTRY[BITE_KEY]
GUARD = SKILL_REGISTRY[GUARD_KEY]
BEHAVIOUR_KEY = REPRESENTATIVE_ROW.behaviour_profile_key

_MOUNTED_PREFIXES = ("buff_apply:", "self_buff_apply:")


def _mounted_buff_key(skill) -> str:
    """The timed effect key one kit skill actually mounts."""
    for effect in skill.effects:
        for prefix in _MOUNTED_PREFIXES:
            if effect.startswith(prefix):
                return effect[len(prefix):]
    raise AssertionError("the guard skill mounts no timed effect")


BUFF_KEY = _mounted_buff_key(GUARD)

# The declared drain shape one bite carries, read from the declaration itself.
_TRANSFER = next(
    parse_effect(effect)
    for effect in BITE.effects
    if effect.startswith("gauge_transfer:")
)
DECLARED_DRAIN = int(_TRANSFER.magnitude)

# The live combat-modifier row the mounted film is valued and settled by.
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


class ReservoirWardenResourceSkillSmokeTests(EvenniaTestCase):
    def _opponent(self, room, key):
        player = create_object(PlayerCharacter, key=key, location=room)
        player.race = "human"
        player.apply_race_baseline()
        player.traits.hp.base = 10000
        player.traits.hp.current = 10000
        player.traits.mp.base = 100
        player.traits.mp.current = 100
        player.traits.defense.base = 0
        player.traits.agility.base = 10
        return player

    def _modifier(self, entity):
        return evaluate_combat_modifiers(entity).get(MODIFIER_AXIS, 0)

    def test_production_drain_and_guard_candidacy_payment_lifetime_and_reload(self):
        """Detect wrong selection, recipient, payment, credit or lost durable source."""
        crocodile = construct_species_individual(
            REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT
        )
        room = create_object(Room, key="t_reservoir_smoke_room")
        opponent = self._opponent(room, "t_reservoir_smoke_target")
        ally = _control_ally()
        crocodile.location = room
        ally.location = room
        field = _field(crocodile, opponent, ally)
        context = BattlefieldActionContext(field)
        baseline = self._modifier(crocodile)

        # Candidacy: the shipped utility binding offers both kit skills as
        # scored plans, the guard with the implicit SELF binding, and the
        # guard's defensive projection is a positive control value.
        trace = []
        request = monster_behaviour_policy(crocodile, field, context=context, trace=trace)
        self.assertIsNotNone(request)
        plans = {plan.skill_key: plan for plan in trace[-1].plans}
        self.assertIn(GUARD_KEY, plans)
        self.assertIn(BITE_KEY, plans)
        guard_plan = plans[GUARD_KEY]
        bite_plan = plans[BITE_KEY]
        self.assertIsNone(guard_plan.shorthand)
        self.assertEqual(guard_plan.target_ids, ())
        self.assertGreater(guard_plan.control, 0)
        self.assertEqual(bite_plan.target_ids, (stable_actor_id(opponent),))
        self.assertGreater(bite_plan.damage, 0)

        # Guard settlement: the plan's implicit request pays the MP once,
        # mounts the film on the caster only, and changes the live modifier
        # axis by its authored magnitude. The opponent and ally are untouched.
        controls = {
            entity.pk: (
                entity.traits.hp.current,
                entity.traits.mp.current,
                entity.traits.sp.current,
                dict(evaluate_combat_modifiers(entity)),
            )
            for entity in (opponent, ally)
        }
        before_mp = crocodile.traits.mp.current
        before_sp = crocodile.traits.sp.current
        with combat_provenance(engagement_provenance().at_slot(0)):
            guarded = ActionResolver.resolve(
                ActionRequest(crocodile, GUARD_KEY, [], context)
            )
        self.assertEqual(guarded.outcome, "success")
        self.assertEqual(crocodile.traits.mp.current, before_mp - GUARD.cost["mp"])
        self.assertEqual(crocodile.traits.sp.current, before_sp)
        self.assertIn(BUFF_KEY, entity_active_buffs(crocodile))
        self.assertEqual(self._modifier(crocodile), baseline + MODIFIER_MAGNITUDE)
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
        self.assertEqual(_buff_instances(crocodile)[0].remaining_seconds, duration)

        # Bite settlement on a hit: the opponent loses exactly the MP it
        # actually had below the declared fixed drain, and the caster is
        # credited that actual amount. After the guard payment there is
        # headroom below the maximum, so this uncapped credit distinguishes the
        # actual amount from both no credit and the declared nominal amount.
        removed = DECLARED_DRAIN - 3
        self.assertGreater(removed, 0)
        self.assertLess(removed, DECLARED_DRAIN)
        opponent.traits.mp.current = removed
        bite_mp_before = crocodile.traits.mp.current
        self.assertLessEqual(bite_mp_before + removed, crocodile.traits.mp.max)
        bite_sp_before = crocodile.traits.sp.current
        with patch(
            "world.rules.combat.damage.roll_d100", return_value=80
        ), combat_provenance(engagement_provenance().at_slot(0)):
            bitten = ActionResolver.resolve(
                ActionRequest(crocodile, BITE_KEY, [opponent], context)
            )
        self.assertEqual(bitten.outcome, "success")
        self.assertEqual(opponent.traits.mp.current, 0)
        expected_mp = bite_mp_before + removed - BITE.cost["mp"]
        self.assertEqual(crocodile.traits.mp.current, expected_mp)
        self.assertEqual(
            crocodile.traits.sp.current, bite_sp_before - BITE.cost["sp"]
        )

        # A second hit with the credit reaching the pool's ceiling: the credit
        # is capped at the maximum and still precedes the bite's own costs.
        opponent.traits.mp.current = removed
        crocodile.traits.mp.current = crocodile.traits.mp.max - 2
        bite_mp_before = crocodile.traits.mp.current
        with patch(
            "world.rules.combat.damage.roll_d100", return_value=80
        ), combat_provenance(engagement_provenance().at_slot(0)):
            capped = ActionResolver.resolve(
                ActionRequest(crocodile, BITE_KEY, [opponent], context)
            )
        self.assertEqual(capped.outcome, "success")
        self.assertEqual(opponent.traits.mp.current, 0)
        self.assertEqual(
            crocodile.traits.mp.current,
            crocodile.traits.mp.max - BITE.cost["mp"],
        )

        # Aging then a committed reload: the spent pools, the remaining
        # lifetime, the kit and the binding are durable.
        clock = WorldClock()
        age = max(1, duration // 2)
        clock.advance(age, AdvanceSource.COMMAND, (crocodile,))
        self.assertEqual(
            _buff_instances(crocodile)[0].remaining_seconds, duration - age
        )
        spent_mp = crocodile.traits.mp.current
        spent_sp = crocodile.traits.sp.current
        crocodile.flush_cached_instance(crocodile)
        reloaded = Monster.objects.get(pk=crocodile.pk)
        self.assertIsNot(reloaded, crocodile)
        self.assertEqual(reloaded.species_key, crocodile.species_key)
        self.assertEqual(reloaded.variant_key, crocodile.variant_key)
        self.assertEqual(reloaded.traits.mp.current, spent_mp)
        self.assertEqual(reloaded.traits.sp.current, spent_sp)
        self.assertEqual(reloaded.db.skills["active"], [BITE_KEY, GUARD_KEY])
        self.assertEqual(reloaded.db.behaviour_tree, BEHAVIOUR_KEY)
        self.assertIn(BUFF_KEY, entity_active_buffs(reloaded))
        self.assertEqual(
            _buff_instances(reloaded)[0].remaining_seconds, duration - age
        )

        # Refresh: a recast through the reloaded row replaces the aged mount
        # with one fresh contribution, never a second one.
        field = _field(reloaded, opponent, ally)
        context = BattlefieldActionContext(field)
        reloaded.traits.mp.current = reloaded.traits.mp.max
        paid_before = reloaded.traits.mp.current
        with combat_provenance(engagement_provenance().at_slot(0)):
            refreshed = ActionResolver.resolve(
                ActionRequest(reloaded, GUARD_KEY, [], context)
            )
        self.assertEqual(refreshed.outcome, "success")
        self.assertEqual(len(_buff_instances(reloaded)), 1)
        self.assertEqual(_buff_instances(reloaded)[0].remaining_seconds, duration)
        self.assertEqual(self._modifier(reloaded), baseline + MODIFIER_MAGNITUDE)
        self.assertEqual(reloaded.traits.mp.current, paid_before - GUARD.cost["mp"])

        # Expiry removes the contribution.
        clock.advance(duration, AdvanceSource.COMMAND, (reloaded,))
        self.assertNotIn(BUFF_KEY, entity_active_buffs(reloaded))
        self.assertEqual(self._modifier(reloaded), baseline)

        # An insufficient pool removes the guard from the candidate set while
        # the bite remains affordable: a forced guard request is rejected
        # without payment or a fabricated mount.
        reloaded.traits.mp.current = GUARD.cost["mp"] - 1
        self.assertGreater(reloaded.traits.mp.current, 0)
        trace = []
        monster_behaviour_policy(
            reloaded, field, context=context, trace=trace
        )
        self.assertIn(
            BITE_KEY, [plan.skill_key for plan in trace[-1].plans]
        )
        self.assertEqual(
            [plan for plan in trace[-1].plans if plan.skill_key == GUARD_KEY], []
        )
        unpaid = reloaded.traits.mp.current
        mounts_before = len(_buff_instances(reloaded))
        with combat_provenance(engagement_provenance().at_slot(0)):
            forced = ActionResolver.resolve(
                ActionRequest(reloaded, GUARD_KEY, [], context)
            )
        self.assertEqual(forced.outcome, "rejected")
        self.assertIs(forced.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(reloaded.traits.mp.current, unpaid)
        self.assertEqual(len(_buff_instances(reloaded)), mounts_before)
        self.assertNotIn(BUFF_KEY, entity_active_buffs(reloaded))

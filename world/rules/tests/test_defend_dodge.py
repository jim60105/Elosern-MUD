"""Round-start Defend and Dodge: shared scalar arithmetic (party-combat-defend-dodge).

Pure ``unittest.TestCase``: the scalar settlement/estimation boundary, the
damage handler's per-recipient tactical application (including the bypass and
zero-defense cases and per-recipient AREA resolution), and ``run_round``'s
round execution context (activation before ordinary actions and expiry at
round end). No database, no settings, no live skill resolution.
"""

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.rules.combat import Battlefield, RoundTactical, run_round
from world.rules.combat.damage import _handle_damage
from world.rules.combat.scalars import hit_margin, strike_amount, strike_lands
from world.skills.effects import DamagePolicy, EffectPolicy, ResolvedEffect

from .combat_fixtures import FakeEntity


def _damage_residual(pending) -> int:
    """Return the staged residual encoded in one pending damage description."""
    return int(pending.description.rsplit("|", 1)[1])


class DefendScalarTests(unittest.TestCase):
    @covers_requirement("combat-resolution::defend-reduces-eligible-final-scaled-direct-damage")
    def test_defend_reduces_the_final_scaled_amount_after_scale_and_floors_it(self):
        # Ordinary scaled damage 40 with reduction 0.35 -> 26 (the spec example).
        self.assertEqual(
            strike_amount(
                attack=40.0, multiplier=1.0, coefficient=1.0, defense=0.0,
                defending=True,
            ),
            26,
        )
        # The same strike with no declaration is unchanged.
        self.assertEqual(
            strike_amount(
                attack=40.0, multiplier=1.0, coefficient=1.0, defense=0.0,
            ),
            40,
        )
        # The floor is applied to the reduced result, not scaled away.
        self.assertEqual(
            strike_amount(
                attack=1.0, multiplier=1.0, coefficient=1.0, defense=0.0,
                defending=True,
            ),
            1,
        )


class DodgeScalarTests(unittest.TestCase):
    @covers_requirement(
        "combat-resolution::dodge-affects-only-shared-hit-checks-and-their-margins"
    )
    def test_dodge_subtracts_the_rulebook_threshold_bonus_from_the_margin(self):
        base = hit_margin(
            60, attacker_agility=5.0, attacker_accuracy=2.0, defender_agility=8.0
        )
        dodging = hit_margin(
            60,
            attacker_agility=5.0,
            attacker_accuracy=2.0,
            defender_agility=8.0,
            defender_dodging=True,
        )
        self.assertEqual(base - dodging, 25.0)
        self.assertEqual(dodging, base - 25.0)

    @covers_requirement(
        "combat-resolution::dodge-affects-only-shared-hit-checks-and-their-margins"
    )
    def test_a_raw_100_critical_still_requires_landing_through_dodge(self):
        # defender agility 30: threshold 81, so raw 100 (margin 19) lands
        # without dodge; the +25 dodge threshold (106) turns raw 100 into a
        # miss, and the critical multiplier is never reached.
        without = hit_margin(100, attacker_agility=0.0, attacker_accuracy=0.0, defender_agility=30.0)
        with_dodge = hit_margin(
            100, attacker_agility=0.0, attacker_accuracy=0.0, defender_agility=30.0,
            defender_dodging=True,
        )
        self.assertTrue(strike_lands(without))
        self.assertFalse(strike_lands(with_dodge))


class DamageHandlerTacticalTests(unittest.TestCase):
    def _strike(self, battlefield, targets, *, roll=60, event_context=None):
        with patch("world.rules.combat.damage.roll_d100", return_value=roll):
            return _handle_damage(
                battlefield.roster["hero"],
                targets,
                "damage:dark:physical",
                {"battlefield": battlefield} if event_context is None else event_context,
                1.0,
            )

    @covers_requirement("combat-resolution::defend-reduces-eligible-final-scaled-direct-damage")
    def test_defend_is_the_recipients_declaration_and_bypass_is_exempt(self):
        hero = FakeEntity("hero", atk_phys=40, agility=10, defense=0)
        defended = FakeEntity("defended", hp=100, max_hp=100, defense=0, agility=10)
        plain = FakeEntity("plain", hp=100, max_hp=100, defense=0, agility=10)
        battlefield = Battlefield(
            {"hero": frozenset({"hero"}), "foe": frozenset({"defended", "plain"})},
            {"hero": hero, "defended": defended, "plain": plain},
        )
        battlefield.tactical = RoundTactical({"defended": "defend"})

        pending = self._strike(battlefield, [defended, plain])
        self.assertEqual(_damage_residual(pending[0]), 26)
        self.assertEqual(_damage_residual(pending[1]), 40)

        # An explicitly defense-bypassing occurrence skips Defend entirely,
        # even against a declared defender with zero defense.
        resolved = ResolvedEffect(
            policy=EffectPolicy(damage=DamagePolicy(unconditional_defense_bypass=True))
        )
        bypassed = self._strike(
            battlefield,
            [defended],
            event_context={"battlefield": battlefield, "resolved_effect": resolved},
        )
        self.assertEqual(_damage_residual(bypassed[0]), 40)

    @covers_requirement(
        "combat-resolution::dodge-affects-only-shared-hit-checks-and-their-margins"
    )
    def test_dodge_is_applied_per_recipient_and_raw_100_never_overrides_it(self):
        hero = FakeEntity("hero", atk_phys=40, agility=0, defense=0)
        dodging = FakeEntity("dodging", hp=100, max_hp=100, defense=0, agility=30)
        standing = FakeEntity("standing", hp=100, max_hp=100, defense=0, agility=30)
        battlefield = Battlefield(
            {"hero": frozenset({"hero"}), "foe": frozenset({"dodging", "standing"})},
            {"hero": hero, "dodging": dodging, "standing": standing},
        )
        battlefield.tactical = RoundTactical({"dodging": "dodge"})

        pending = self._strike(battlefield, [dodging, standing], roll=100)
        # Raw 100 lands the standing recipient (margin 19) but the dodging
        # recipient's +25 threshold saturated it to a miss: no invented roll,
        # no critical, zero staged damage.
        self.assertEqual(_damage_residual(pending[0]), 0)
        self.assertEqual(_damage_residual(pending[1]), 80)


class RoundTacticalScopeTests(unittest.TestCase):
    @covers_requirement(
        "combat-resolution::defend-and-dodge-consume-one-zero-resource-round-start-action"
    )
    def test_run_round_activates_declarations_for_the_whole_round_then_expires(self):
        slow = FakeEntity("slow", hp=100, agility=1)
        fast = FakeEntity("fast", hp=100, agility=99)
        battlefield = Battlefield(
            {"ally": frozenset({"slow"}), "enemy": frozenset({"fast"})},
            {"slow": slow, "fast": fast},
        )
        seen: list[tuple[str, str | None]] = []

        def provider(entity, field):
            seen.append((str(entity.key), None if field.tactical is None else field.tactical.tactic_for("slow")))
            return None

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.tick_buffs", return_value=()),
            patch("world.rules.combat.rounds.decay_tick"),
            patch("world.rules.combat.rounds.climax_settlement_action", return_value=None),
        ):
            run_round(battlefield, provider, tactical_declarations={"slow": "defend"})
        # The declaration was active before the fast enemy's first turn.
        self.assertEqual(seen[0], ("fast", "defend"))
        self.assertIn(("slow", "defend"), seen)
        # Round ended: the transient context expired and cannot stack.
        self.assertIsNone(battlefield.tactical)

        seen.clear()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.tick_buffs", return_value=()),
            patch("world.rules.combat.rounds.decay_tick"),
            patch("world.rules.combat.rounds.climax_settlement_action", return_value=None),
        ):
            run_round(battlefield, provider)
        self.assertTrue(seen)
        self.assertTrue(all(tactic is None for _key, tactic in seen))
        self.assertIsNone(battlefield.tactical)

    @covers_requirement(
        "combat-resolution::defend-and-dodge-consume-one-zero-resource-round-start-action"
    )
    def test_run_round_clears_declarations_when_the_round_raises(self):
        slow = FakeEntity("slow", hp=100, agility=1)
        fast = FakeEntity("fast", hp=100, agility=99)
        battlefield = Battlefield(
            {"ally": frozenset({"slow"}), "enemy": frozenset({"fast"})},
            {"slow": slow, "fast": fast},
        )

        def exploding_provider(entity, field):
            raise RuntimeError("technical failure")

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=90),
            patch("world.rules.combat.rounds.roll_d100", return_value=90),
            self.assertRaises(RuntimeError),
        ):
            run_round(battlefield, exploding_provider, tactical_declarations={"slow": "dodge"})
        self.assertIsNone(battlefield.tactical)


class EnemyUnavailableTests(unittest.TestCase):
    @covers_requirement(
        "combat-resolution::defend-and-dodge-consume-one-zero-resource-round-start-action"
    )
    def test_declarations_are_scoped_to_the_named_roster_key_only(self):
        tactical = RoundTactical({"slow": "defend"})
        self.assertTrue(tactical.is_defending("slow"))
        self.assertFalse(tactical.is_defending("fast"))
        self.assertFalse(tactical.is_dodging("fast"))
        self.assertIsNone(tactical.tactic_for("fast"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

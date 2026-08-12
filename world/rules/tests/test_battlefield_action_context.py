"""Battlefield context and shorthand integration tests."""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.targeting import ActionContext, Relation, expand_target_shorthand

from .combat_fixtures import FakeEntity


class BattlefieldActionContextTests(unittest.TestCase):
    def setUp(self):
        self.actor = FakeEntity("actor")
        self.ally = FakeEntity("ally")
        self.enemy = FakeEntity("enemy")
        self.battlefield = Battlefield(
            {"party": frozenset({"actor", "ally"}), "foes": frozenset({"enemy"})},
            {"actor": self.actor, "ally": self.ally, "enemy": self.enemy},
        )
        self.context = BattlefieldActionContext(self.battlefield)

    @covers_requirement("battlefield-action-context::battlefieldactioncontext-conforms-to-change-8-s-actioncontext-protocol")
    @covers_requirement("targeting-validation::actioncontext-is-a-shared-protocol-implemented-differently-by-combat-and-non-combat")
    def test_protocol_and_relation_truth_table(self):
        self.assertIsInstance(self.context, ActionContext)
        self.assertIs(self.context.relation_to(self.actor, self.actor), Relation.SELF)
        self.assertIs(self.context.relation_to(self.actor, self.ally), Relation.ALLY)
        self.assertIs(self.context.relation_to(self.actor, self.enemy), Relation.ENEMY)

    @covers_requirement("battlefield-action-context::is-in-range-checks-fled-status-melee-versus-ranged-is-explicitly-not-built", "battlefield-action-context::is-present-checks-canonical-battlefield-roster-membership")
    @covers_requirement("disengage-action::a-fled-entity-is-immediately-excluded-from-targeting-turn-order-and-team-power")
    def test_fled_entity_is_absent_and_out_of_range(self):
        self.battlefield.fled.add("enemy")
        self.assertTrue(self.context.is_present(self.actor, self.enemy))
        self.assertFalse(self.context.is_in_range(self.actor, self.enemy, object()))

    @covers_requirement("battlefield-action-context::relation-to-is-derived-from-two-team-membership-not-a-stored-relation-field")
    def test_event_context_cannot_reference_a_different_battlefield(self):
        other = Battlefield(
            {"a": frozenset({"actor"}), "b": frozenset({"enemy"})},
            {"actor": self.actor, "enemy": self.enemy},
        )
        with self.assertRaisesRegex(ValueError, "must match"):
            BattlefieldActionContext(
                self.battlefield,
                event_context={"battlefield": other},
            )

    @covers_requirement("battlefield-action-context::combat-shortcuts-read-the-two-team-roster-with-no-separate-expansion-path", "targeting-validation::combat-shortcuts-are-convenience-ui-not-permission-boundaries")
    def test_shorthand_expands_mapping_values(self):
        self.assertEqual(
            expand_target_shorthand(self.actor, self.context, "all-enemies"),
            [self.enemy],
        )
        self.assertCountEqual(
            expand_target_shorthand(self.actor, self.context, "all-allies"),
            [self.actor, self.ally],
        )

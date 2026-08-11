"""Canonical mode derivation tests (foundation section 3.4)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.context import PresentationContext
from .combat_fixtures import BattlefieldIsolation


class ModeDerivationTests(BattlefieldIsolation, EvenniaTest):
    def _actor(self):
        actor = create_object(PlayerCharacter, key="mode actor")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.location = self.room1
        return actor

    @covers_requirement(
        "webclient-status-presentation::snapshot-mode-is-derived-from-canonical-puppet-state"
    )
    def test_pending_creation_takes_creation_mode(self):
        actor = self._actor()
        actor.creation_pending = True
        context = PresentationContext(actor=actor, protocol_version=1)
        self.assertEqual(PresentationCoordinator.mode_for(context), "creation")

    @covers_requirement(
        "webclient-status-presentation::snapshot-mode-is-derived-from-canonical-puppet-state"
    )
    def test_active_combat_reports_combat_mode(self):
        from world.rules.combat_session import engage

        actor = self._actor()
        monster = create_object(Monster, key="wolf", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier()
        engage(actor, monster)
        context = PresentationContext(actor=actor, protocol_version=1)
        self.assertEqual(PresentationCoordinator.mode_for(context), "combat")

    @covers_requirement(
        "webclient-status-presentation::snapshot-mode-is-derived-from-canonical-puppet-state"
    )
    def test_ordinary_puppet_receives_exploration_mode(self):
        actor = self._actor()
        context = PresentationContext(actor=actor, protocol_version=1)
        self.assertEqual(PresentationCoordinator.mode_for(context), "exploration")

    @covers_requirement(
        "webclient-status-presentation::snapshot-mode-is-derived-from-canonical-puppet-state"
    )
    def test_malformed_combat_record_falls_back_to_exploration(self):
        actor = self._actor()
        actor.db.active_combat = {"not": "a valid record"}
        context = PresentationContext(actor=actor, protocol_version=1)
        self.assertEqual(PresentationCoordinator.mode_for(context), "exploration")


if __name__ == "__main__":
    unittest.main()

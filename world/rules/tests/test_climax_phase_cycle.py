"""Tests for guarded climax-phase transitions."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.sexual_state import (
    _VALID_CLIMAX_TRANSITIONS,
    _apply_climax_phase_set,
)


class ClimaxPhaseCycleTests(EvenniaTest):
    def _entity_at(self, level):
        entity = create_object(PlayerCharacter, key=f"phase {level}")
        entity.sexual.climax_phase.value = level
        return entity

    @covers_requirement("sexual-state-handler::climax-phase-can-only-move-along-its-valid-cycle-enforced-by-one-guarded-function")
    def test_every_declared_edge_applies(self):
        for source, targets in _VALID_CLIMAX_TRANSITIONS.items():
            for target in targets:
                with self.subTest(source=source, target=target):
                    entity = self._entity_at(source)
                    self.assertEqual(_apply_climax_phase_set(entity, target), "cycle")
                    self.assertEqual(entity.sexual.climax_phase.level, target)

    def test_invalid_edge_is_a_noop(self):
        entity = self._entity_at("進行中")
        self.assertIsNone(_apply_climax_phase_set(entity, "接近"))
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")

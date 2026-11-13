"""Behavior tests for the per-character entered-archetype record.

Every scene key and prose value is invented with the reserved ``t_`` prefix, so
no test names shipped content. The scene-ensure half of the room-entry seam
belongs to the art capability and never runs here: it is replaced with an
off-seam mock so these tests observe only the record half of the same hook.
"""

from __future__ import annotations

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom, InstanceRoom
from world.rules.scene_visits import (
    ENTERED_ARCHETYPES_ATTRIBUTE,
    SCHEMA_VERSION,
    entered_archetypes,
)
from world.tests.synthetic_data import make_archetype, synthetic_registries

#: The kit's first synthetic scene archetype.
BAZAAR = "t_synth_bazaar"
#: The kit's second synthetic scene archetype.
LODGE = "t_synth_lodge"
#: A file-local archetype one scope declares, absent from the kit.
ZETA = "t_scene_zeta"
#: A second file-local archetype, declared after ``ZETA`` in registry order.
ALPHA = "t_scene_alpha"
#: An archetype key no scope declares.
UNDECLARED = "t_scene_undeclared"


def _local(*keys: str) -> dict[str, object]:
    """File-local synthetic archetypes, kept in the given registry order."""

    return {key: make_archetype(key) for key in keys}


class EnteredArchetypeRecordTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.enterContext(patch("world.art.service.ensure_scene_asset"))

    def _grid_room(self, archetype, x):
        room, errors = AnchorRoom.create(key="t-scene-grid", xyz=(x, 1, "test_map"))
        self.assertEqual(errors, [])
        room.scene_archetype = archetype
        return room

    def _instance_room(self, archetype):
        room, errors = InstanceRoom.create(key="t-scene-instance")
        self.assertEqual(errors, [])
        room.scene_archetype = archetype
        return room

    def _stored(self, character=None):
        return (character or self.char1).attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE)

    def test_entering_rooms_records_each_archetype_once(self):
        with synthetic_registries("archetypes"), patch(
            "world.rules.scene_visits.log_info"
        ) as info:
            first = self._grid_room(BAZAAR, 1)
            second = self._grid_room(BAZAAR, 2)
            elsewhere = self._instance_room(LODGE)
            self.char1.move_to(first, quiet=True)
            self.char1.move_to(second, quiet=True)
            self.char1.move_to(elsewhere, quiet=True)

            self.assertEqual(entered_archetypes(self.char1), (BAZAAR, LODGE))
            self.assertEqual(
                self._stored(),
                {"schema_version": SCHEMA_VERSION, "archetypes": [BAZAAR, LODGE]},
            )
            self.assertEqual(
                [call.args[0] for call in info.call_args_list],
                ["scene_entry_recorded", "scene_entry_recorded"],
            )

    def test_another_characters_entries_are_separate(self):
        twin = create_object(
            PlayerCharacter, key="t-scene-twin", location=self.room1, home=self.room1
        )
        twin.account = self.account
        with synthetic_registries("archetypes"):
            self.char1.move_to(self._grid_room(BAZAAR, 1), quiet=True)

            self.assertEqual(entered_archetypes(self.char1), (BAZAAR,))
            self.assertEqual(entered_archetypes(twin), ())
            self.assertIsNone(self._stored(twin))

    def test_an_unresolvable_archetype_records_nothing(self):
        with synthetic_registries("archetypes"):
            self.char1.move_to(self._grid_room(BAZAAR, 1), quiet=True)
            recorded = self._stored()
            missing = self._grid_room(None, 2)
            undeclared = self._instance_room(UNDECLARED)

            self.char1.move_to(missing, quiet=True)
            self.assertEqual(self.char1.location, missing)
            self.char1.move_to(undeclared, quiet=True)
            self.assertEqual(self.char1.location, undeclared)
            self.assertEqual(entered_archetypes(self.char1), (BAZAAR,))
            self.assertEqual(self._stored(), recorded)

    def test_a_failing_write_never_blocks_the_move(self):
        with synthetic_registries("archetypes"):
            room = self._grid_room(BAZAAR, 1)
            with patch(
                "world.rules.scene_visits._write_record",
                side_effect=RuntimeError("record boom"),
            ), patch("world.rules.scene_visits.log_warn") as warn:
                self.char1.move_to(room, quiet=True)

            self.assertEqual(self.char1.location, room)
            self.assertIsNone(self._stored())
            self.assertEqual(
                [call.args[0] for call in warn.call_args_list],
                ["scene_entry_record_failed"],
            )
            self.assertIsInstance(warn.call_args.kwargs["exc"], RuntimeError)

    def test_read_returns_registry_order_not_stored_order(self):
        with synthetic_registries("archetypes", extra={"archetypes": _local(ZETA, ALPHA)}):
            self.char1.move_to(self._grid_room(ZETA, 1), quiet=True)
            self.char1.move_to(self._grid_room(ALPHA, 2), quiet=True)

            # Storage is canonical (sorted); the read follows registry order.
            self.assertEqual(self._stored()["archetypes"], sorted([ALPHA, ZETA]))
            self.assertEqual(entered_archetypes(self.char1), (ZETA, ALPHA))

    def test_a_removed_archetype_is_not_returned(self):
        with synthetic_registries("archetypes", extra={"archetypes": _local(ZETA)}):
            self.char1.move_to(self._grid_room(BAZAAR, 1), quiet=True)
            self.char1.move_to(self._grid_room(ZETA, 2), quiet=True)
            self.assertEqual(entered_archetypes(self.char1), (BAZAAR, ZETA))
            recorded = self._stored()

        with synthetic_registries("archetypes"):
            self.assertEqual(entered_archetypes(self.char1), (BAZAAR,))
            self.assertEqual(self._stored(), recorded)
            self.assertIn(ZETA, recorded["archetypes"])


if __name__ == "__main__":
    import unittest

    unittest.main()

"""Map-knowledge journeys (pruning)."""

from ._support import _node_ids
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.rooms import InstanceRoom
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.map_knowledge import KnowledgeError, parse_knowledge, prune_reclaimed_room


class MapKnowledgePruneTests(EvenniaTest):
    """Reclaimed-room pruning (design D4) through the instance reclaim seam."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room1.save()

    def _knowledge_of(self, character):
        try:
            return parse_knowledge(character)
        except KnowledgeError:
            return []

    @covers_requirement("map-knowledge::reclaimed-room-knowledge-is-pruned-transactionally-with-the-room-deletion")
    def test_prune_removes_target_node_only_from_affected_players(self):
        room = create_object(InstanceRoom, key="ephemeral")
        affected = self.char1
        unaffected = self.char2
        affected.attributes.add(
            "map_knowledge",
            {
                "schema_version": 2,
                "wilderness": {},
                "visited": {
                    f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
                },
            },
        )
        unaffected.attributes.add(
            "map_knowledge",
            {
                "schema_version": 2,
                "wilderness": {},
                "visited": {
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30}
                },
            },
        )
        prune_reclaimed_room(room.id)
        self.assertNotIn(f"room:{room.id}", _node_ids(affected))
        self.assertIn(f"room:{self.room1.id}", _node_ids(affected))
        self.assertIn(f"room:{self.room1.id}", _node_ids(unaffected))

    @covers_requirement(
        "wilderness-knowledge-chunks::wilderness-observations-are-chunk-addressed"
    )
    def test_prune_reclaimed_room_preserves_wilderness_chunks(self):
        room = create_object(InstanceRoom, key="prune_with_wild")
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 2,
                "visited": {
                    f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
                },
                "wilderness": {
                    WILDERNESS_NAME: {
                        "0:0": {"65": {"first_seen_tick": 5, "last_seen_tick": 8, "sight": 4}}
                    }
                },
            },
        )
        prune_reclaimed_room(room.id)
        stored = self.char1.attributes.get("map_knowledge")
        self.assertEqual(
            stored,
            {
                "schema_version": 2,
                "visited": {f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30}},
                "wilderness": {
                    WILDERNESS_NAME: {
                        "0:0": {"65": {"first_seen_tick": 5, "last_seen_tick": 8, "sight": 4}}
                    }
                },
            },
        )

    def test_player_without_attribute_gets_none_by_pruning(self):
        room = create_object(InstanceRoom, key="never_visited")
        self.assertFalse(self.char1.attributes.has("map_knowledge"))
        prune_reclaimed_room(room.id)
        self.assertFalse(self.char1.attributes.has("map_knowledge"))

    def test_prune_skips_a_corrupt_record_with_a_diagnostic(self):
        room = create_object(InstanceRoom, key="corrupt_owner")
        self.char1.attributes.add(
            "map_knowledge", {"schema_version": 99, "visited": {}}
        )
        from world.rules.map_knowledge import log_warn as _log_warn

        with patch("world.rules.map_knowledge.log_warn") as log_warn:
            prune_reclaimed_room(room.id)
            log_warn.assert_called()
        # The corrupt record is left untouched, not reset or rewritten.
        self.assertEqual(
            self.char1.attributes.get("map_knowledge"),
            {"schema_version": 99, "visited": {}},
        )

    @covers_requirement("map-knowledge::reclaimed-room-knowledge-is-pruned-transactionally-with-the-room-deletion")
    def test_prune_write_failure_restores_snapshots(self):
        room = create_object(InstanceRoom, key="failure_room")
        before = {
            "schema_version": 2,
            "visited": {
                f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
            },
            "wilderness": {},
        }
        self.char1.attributes.add("map_knowledge", before)
        self.char2.attributes.add(
            "map_knowledge",
            {
                "schema_version": 2,
                "wilderness": {},
                "visited": {f"room:{room.id}": {"first_seen_tick": 5, "last_seen_tick": 5}},
            },
        )
        from world.rules.map_knowledge import KnowledgePruneError

        target = f"room:{room.id}"

        def failing_prune_write(character, record):
            visited = record.get("visited", {})
            if target in visited:
                # A snapshot restore write carries the target node back; let it
                # through so the module's own rollback can run.
                character.attributes.add("map_knowledge", record)
                return
            raise RuntimeError("disk full")

        with patch(
            "world.rules.map_knowledge._write_knowledge",
            side_effect=failing_prune_write,
        ):
            with self.assertRaises(KnowledgePruneError):
                prune_reclaimed_room(room.id)
        # The failing write never committed, so the stored values are restored
        # to their prior snapshots via the real restore path.
        self.assertEqual(self.char1.attributes.get("map_knowledge"), before)
        self.assertEqual(
            self.char2.attributes.get("map_knowledge"),
            {
                "schema_version": 2,
                "wilderness": {},
                "visited": {f"room:{room.id}": {"first_seen_tick": 5, "last_seen_tick": 5}},
            },
        )

    def test_prune_restore_failure_is_best_effort_and_still_raises(self):
        # A persistence failure on the prune write, with the restore write also
        # failing, must not raise out of the module except as the dedicated
        # error (the inner restore failure is swallowed as best-effort).
        room = create_object(InstanceRoom, key="restore_failure")
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 2,
                "wilderness": {},
                "visited": {f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20}},
            },
        )
        from world.rules.map_knowledge import KnowledgePruneError

        target = f"room:{room.id}"

        def always_fail(character, record):
            raise RuntimeError("disk full")

        with patch(
            "world.rules.map_knowledge._write_knowledge",
            side_effect=always_fail,
        ):
            with self.assertRaises(KnowledgePruneError):
                prune_reclaimed_room(room.id)


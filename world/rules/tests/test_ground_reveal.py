"""Ground observation writes and the bounded reveal projection.

Synthetic schema-2 records, synthetic district ownership and fixed radii keep
every expectation independent of shipped content. Arrival and explicit-skip
settlement are exercised through the real clock owners with injected sight
radii and fault injection after the observation write.
"""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.maps import wilderness_provider
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.tests.geography_fixture import publish_shipped_geography
from world.rules.clock import AdvanceSource, WorldClock, _EVENT_SOURCES, get_world_clock
from world.rules.fatigue import SleepPosture, read_fatigue_state, write_fatigue_state
from world.rules.map_knowledge import (
    CHUNK_CELLS,
    KNOWLEDGE_ATTR,
    is_revealed,
    parse_knowledge,
    record_ground_observation,
    revealed_in_bounds,
)
from world.rules.skip_safety import SkipRejectReason
from world.rules.sleep_receipt import read_sleep_receipt
from world.tests.raw_attributes import raw_attribute_value
from world.rules.time_skip import (
    MODE_DURATION,
    SkipRefused,
    advance_wait,
    continue_sleep,
    enter_party_sleep,
    enter_sleep,
)

publish_shipped_geography()

CELL = (12, 34)


def _offset(x, y):
    return (y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS)


def _chunk_key(x, y):
    return f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}"


def _record(chunks=None, visited=None):
    return {
        "schema_version": 2,
        "visited": dict(visited or {}),
        "wilderness": {wilderness_provider.WILDERNESS_NAME: dict(chunks or {})},
    }


def _wild_node(x, y):
    return f"wild:{wilderness_provider.WILDERNESS_NAME}:{x}:{y}"


class _Attributes:
    """A read-only attribute surface that fails on any write attempt."""

    def __init__(self, record):
        self.record = record
        self.writes = []

    def get(self, key, default=None):
        return self.record

    def add(self, *args, **kwargs):
        self.writes.append((args, kwargs))
        raise AssertionError("a read projection must never write")

    def remove(self, *args, **kwargs):
        self.writes.append((args, kwargs))
        raise AssertionError("a read projection must never write")


class _Character:
    def __init__(self, record=None):
        self.attributes = _Attributes(record)


class GroundRevealProjectionTests(unittest.TestCase):
    def _reveal(self, record, bounds, *, landmarks=None, owners=None):
        character = _Character(record)
        with patch(
            "world.lore.map_districts.landmark_node_ids",
            return_value=dict(landmarks or {}),
        ), patch(
            "world.maps.district_partition.district_at",
            side_effect=lambda cell: (owners or {}).get(tuple(cell)),
        ):
            revealed = revealed_in_bounds(character, bounds)
        self.assertEqual(character.attributes.writes, [])
        return revealed

    def test_union_spans_chunk_edges_without_reading_distant_chunks(self):
        # Two visits one cell either side of the 64-cell chunk seam, each with
        # radius 1: a manually known 5x3 union.
        record = _record(
            {
                "0:0": {
                    str(_offset(63, 63)): {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 1,
                    }
                },
                "1:0": {
                    str(_offset(65, 63)): {
                        "first_seen_tick": 2,
                        "last_seen_tick": 2,
                        "sight": 1,
                    }
                },
                # A distant corrupt chunk whose bytes must never be decoded for
                # this window.
                "9:9": {
                    "0": {
                        "first_seen_tick": 3,
                        "last_seen_tick": 3,
                        "sight": 99,
                    }
                },
            },
            visited={},
        )
        decoded = []

        from world.rules import map_knowledge as knowledge

        real_decode = knowledge._decode_chunk_entries

        def recording_decode(chunk_key, chunk_data):
            decoded.append(chunk_key)
            return real_decode(chunk_key, chunk_data)

        with patch.object(knowledge, "_decode_chunk_entries", side_effect=recording_decode):
            revealed = self._reveal(record, (60, 60, 70, 66))
        self.assertEqual(
            revealed,
            {(x, y) for x in range(62, 67) for y in range(62, 65)},
        )
        self.assertEqual(set(decoded), {"0:0", "1:0"})

    def test_lit_district_shortcut_reveals_ownership_and_landmark_chunks_only(self):
        record = _record(
            {
                "0:0": {
                    str(_offset(63, 63)): {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 1,
                    }
                },
                "1:0": {
                    str(_offset(65, 63)): {
                        "first_seen_tick": 2,
                        "last_seen_tick": 2,
                        "sight": 1,
                    }
                },
            },
            visited={},
        )
        decoded = []

        from world.rules import map_knowledge as knowledge

        real_decode = knowledge._decode_chunk_entries

        def recording_decode(chunk_key, chunk_data):
            decoded.append(chunk_key)
            return real_decode(chunk_key, chunk_data)

        with patch.object(knowledge, "_decode_chunk_entries", side_effect=recording_decode):
            revealed = self._reveal(
                record,
                (60, 60, 70, 66),
                landmarks={"harbour": _wild_node(65, 63)},
                owners={(70, 66): "harbour"},
            )
        self.assertIn((70, 66), revealed, "the whole lit district is revealed")
        self.assertIn((63, 63), revealed)
        # Membership decodes the landmark's chunk; the window decodes only its
        # two expanded observation chunks. Nothing else is touched.
        self.assertEqual(set(decoded), {"0:0", "1:0"})

    def test_corrupt_selected_chunk_keeps_lit_reveal_and_preserves_bytes(self):
        record = _record(
            {
                "0:0": {
                    str(_offset(60, 60)): {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 1,
                    }
                },
                "1:0": {
                    # Invalid sight: this selected chunk is corrupt.
                    "0": {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 99,
                    }
                },
            },
            visited={},
        )
        before = repr(record)
        with patch("world.rules.map_knowledge.log_warn") as log_warn:
            revealed = self._reveal(
                record,
                (60, 60, 70, 66),
                landmarks={"harbour": _wild_node(60, 60)},
                owners={(70, 66): "harbour"},
            )
        self.assertEqual(revealed, {(70, 66)})
        self.assertNotIn((61, 61), revealed, "a corrupt selected chunk drops the disc union")
        self.assertEqual(repr(record), before, "corruption retains the record bytes")
        log_warn.assert_called()

    def test_invalid_envelope_reveals_nothing(self):
        record = {"schema_version": 1, "visited": {}, "wilderness": {}}
        with patch("world.rules.map_knowledge.log_warn") as log_warn:
            self.assertEqual(self._reveal(record, (0, 0, 10, 10)), frozenset())
        log_warn.assert_called()
        self.assertEqual(record, {"schema_version": 1, "visited": {}, "wilderness": {}})

    def test_query_is_cropped_to_the_wilderness_frame(self):
        record = _record(
            {
                "0:0": {
                    "0": {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 0,
                    }
                }
            }
        )
        self.assertEqual(self._reveal(record, (-5, -5, 2, 2)), {(0, 0)})
        self.assertEqual(
            self._reveal(record, (
                wilderness_provider.WILDERNESS_MAX_X + 5,
                0,
                wilderness_provider.WILDERNESS_MAX_X + 9,
                9,
            )),
            frozenset(),
        )

    def test_is_revealed_matches_the_bounded_projection(self):
        record = _record(
            {
                "0:0": {
                    "0": {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 0,
                    }
                }
            }
        )
        character = _Character(record)
        with patch("world.lore.map_districts.landmark_node_ids", return_value={}), patch(
            "world.maps.district_partition.district_at", return_value=None
        ):
            self.assertTrue(is_revealed(character, (0, 0)))
            self.assertFalse(is_revealed(character, (1, 0)))
        self.assertEqual(character.attributes.writes, [])

    def test_hidden_terrain_reveals_without_location_identity(self):
        # (61, 61) lies inside the disc of the visited (60, 60) but has never
        # been visited: its terrain reveals while the exact-visit gate stays
        # false, and the projection emits coordinates only.
        from world.rules.map_knowledge import has_visited

        record = _record(
            {
                "0:0": {
                    str(_offset(60, 60)): {
                        "first_seen_tick": 1,
                        "last_seen_tick": 1,
                        "sight": 1,
                    }
                }
            }
        )
        character = _Character(record)
        with patch("world.lore.map_districts.landmark_node_ids", return_value={}), patch(
            "world.maps.district_partition.district_at", return_value=None
        ):
            self.assertIn((61, 61), revealed_in_bounds(character, (55, 55, 65, 65)))
            self.assertFalse(has_visited(character, _wild_node(61, 61)))
            self.assertTrue(has_visited(character, _wild_node(60, 60)))


class GroundObservationWriterTests(EvenniaTest):
    @covers_requirement(
        "map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record"
    )
    def test_observation_keeps_first_tick_and_maximum_sight(self):
        record_ground_observation(self.char1, CELL, 100, 3)
        record_ground_observation(self.char1, CELL, 200, 2)
        record_ground_observation(self.char1, CELL, 50, 7)
        visits = {visit.node_id: visit for visit in parse_knowledge(self.char1)}
        visit = visits[_wild_node(*CELL)]
        self.assertEqual((visit.first_seen_tick, visit.last_seen_tick, visit.sight), (100, 200, 7))

    @covers_requirement(
        "map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record"
    )
    def test_tick_zero_is_a_real_preserved_first_observation(self):
        record_ground_observation(self.char1, CELL, 0, 1)
        record_ground_observation(self.char1, CELL, 10, 2)
        visit = {v.node_id: v for v in parse_knowledge(self.char1)}[_wild_node(*CELL)]
        self.assertEqual((visit.first_seen_tick, visit.last_seen_tick, visit.sight), (0, 10, 2))

    def test_non_player_and_corrupt_records_are_never_written(self):
        npc = create_object(NPC, key="ground-npc", location=self.room1)
        record_ground_observation(npc, CELL, 1, 5)
        self.assertIsNone(npc.attributes.get(KNOWLEDGE_ATTR))

        corrupt = {"schema_version": 99, "visited": {}}
        self.char1.attributes.add(KNOWLEDGE_ATTR, corrupt)
        with patch("world.rules.map_knowledge.log_warn") as log_warn:
            record_ground_observation(self.char1, CELL, 1, 5)
        self.assertEqual(self.char1.attributes.get(KNOWLEDGE_ATTR), corrupt)
        log_warn.assert_called()


class SkipObservationTests(EvenniaTest):
    """Successful explicit skips observe once; excluded paths never do."""

    def setUp(self):
        super().setUp()
        self._event_sources = dict(_EVENT_SOURCES)
        _EVENT_SOURCES.clear()
        self.addCleanup(_EVENT_SOURCES.update, self._event_sources)
        self.addCleanup(_EVENT_SOURCES.clear)
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from typeclasses.rooms import Room

        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.cell = self._valid_cell()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.assertTrue(
            enter_wilderness(
                self.player,
                coordinates=self.cell,
                name=wilderness_provider.WILDERNESS_NAME,
            )
        )
        self.terrain = self.player.location
        self.cell = self.terrain.coordinates
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        # These cases establish the observation contract, not the shared
        # safety gate; ambient wilderness occupants must not refuse the skip.
        self._safety = patch(
            "world.rules.time_skip.evaluate_skip_safety", return_value=None
        )
        self._safety.start()
        self.addCleanup(self._safety.stop)

    @staticmethod
    def _valid_cell():
        from world.maps import wilderness_provider as provider

        max_x = provider.WILDERNESS_MAX_X
        max_y = provider.WILDERNESS_MAX_Y
        for offset in range(200):
            candidate = (max_x // 2 + offset, max_y // 2)
            if provider.is_valid_wilderness_cell(candidate):
                return candidate
        raise AssertionError("no valid wilderness cell near the frame centre")

    def _observe(self):
        real = record_ground_observation
        return patch(
            "world.rules.map_knowledge.record_ground_observation",
            wraps=real,
        )

    def _visit(self):
        return {v.node_id: v for v in parse_knowledge(self.player)}[_wild_node(*self.cell)]

    def test_positive_wait_observes_the_final_cell_once(self):
        before = get_world_clock().tick
        with patch("world.rules.sight.ground_radius_at", return_value=5), self._observe() as observe:
            result = advance_wait(self.player, 60)
        self.assertEqual(result.elapsed_seconds, 60)
        observe.assert_called_once()
        self.assertEqual(observe.call_args.args[0], self.player)
        self.assertEqual(observe.call_args.args[1], self.cell)
        self.assertEqual(observe.call_args.args[2], before + 60)
        visit = self._visit()
        self.assertEqual((visit.last_seen_tick, visit.sight), (before + 60, 5))

        # Same cell, later waits: a smaller sight never lowers the maximum and
        # a larger one raises it at the new final tick.
        middle = get_world_clock().tick
        with patch("world.rules.sight.ground_radius_at", return_value=2), self._observe():
            advance_wait(self.player, 60)
        self.assertEqual(self._visit().sight, 5)
        self.assertEqual(self._visit().last_seen_tick, middle + 60)
        with patch("world.rules.sight.ground_radius_at", return_value=7), self._observe():
            advance_wait(self.player, 60)
        final = self._visit()
        self.assertEqual(
            (final.first_seen_tick, final.last_seen_tick, final.sight),
            (before + 60, middle + 120, 7),
        )

    def test_truncated_wait_observes_its_actual_end(self):
        companion = create_object(NPC, key="forced-sleeper", location=self.terrain)
        companion.race = "human"
        companion.apply_race_baseline()
        from world.rules.party import join_party

        join_party(companion, self.player)
        write_fatigue_state(companion, 0, SleepPosture.FORCED)
        before = get_world_clock().tick
        with patch("world.rules.sight.ground_radius_at", return_value=4), self._observe() as observe:
            result = advance_wait(self.player, 10000)
        self.assertEqual(result.elapsed_seconds, 6000)
        observe.assert_called_once()
        self.assertEqual(observe.call_args.args[2], before + 6000)
        self.assertEqual(self._visit().last_seen_tick, before + 6000)

    def test_zero_and_replayed_waits_never_observe(self):
        with patch("world.rules.sight.ground_radius_at", return_value=3), self._observe() as observe:
            advance_wait(self.player, 0)
            self.assertEqual(observe.call_count, 0)
            advance_wait(self.player, 60, operation_id="synthetic-ground-once")
            self.assertEqual(observe.call_count, 1)
            advance_wait(self.player, 60, operation_id="synthetic-ground-once")
            self.assertEqual(observe.call_count, 1)

    def test_refused_wait_never_observes(self):
        with patch("world.rules.sight.ground_radius_at", return_value=3), patch(
            "world.rules.time_skip.evaluate_skip_safety",
            return_value=SkipRejectReason.IN_COMBAT,
        ), self._observe() as observe:
            with self.assertRaises(SkipRefused):
                advance_wait(self.player, 60)
        self.assertEqual(observe.call_count, 0)
        self.assertIsNone(self.player.attributes.get(KNOWLEDGE_ATTR))

    def test_self_sleep_continuation_observes_once(self):
        entry = enter_sleep(self.player, mode=MODE_DURATION, seconds=600)
        with patch("world.rules.sight.ground_radius_at", return_value=6), self._observe() as observe:
            continue_sleep(self.player, entry)
        observe.assert_called_once()
        self.assertEqual(self._visit().sight, 6)

    def test_party_sleep_continuation_observes_once(self):
        enter_party_sleep(self.player, mode=MODE_DURATION, seconds=600)
        with patch("world.rules.sight.ground_radius_at", return_value=2), self._observe() as observe:
            continue_sleep(self.player)
        observe.assert_called_once()
        self.assertEqual(self._visit().sight, 2)

    def test_forced_sleep_continuation_observes_once(self):
        write_fatigue_state(self.player, 2400, SleepPosture.AWAKE)
        advance_wait(self.player, 1200)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.FORCED)
        self.assertIsNotNone(read_sleep_receipt(self.player))
        self.player.attributes.remove(KNOWLEDGE_ATTR)
        with patch("world.rules.sight.ground_radius_at", return_value=1), self._observe() as observe:
            continue_sleep(self.player)
        observe.assert_called_once()
        self.assertEqual(self._visit().sight, 1)

    def test_non_skip_advance_never_observes(self):
        with patch("world.rules.sight.ground_radius_at", return_value=3), self._observe() as observe:
            WorldClock(get_world_clock().tick).advance(60, AdvanceSource.COMMAND, [self.player])
        self.assertEqual(observe.call_count, 0)
        self.assertIsNone(self.player.attributes.get(KNOWLEDGE_ATTR))

    def test_writer_persistence_failure_keeps_history_and_commits_the_skip(self):
        before = get_world_clock().tick
        record_ground_observation(self.player, self.cell, before, 2)
        prior = self.player.attributes.get(KNOWLEDGE_ATTR)

        from world.rules import map_knowledge as knowledge

        real_write = knowledge._write_knowledge

        def fail_after_write(character, record):
            real_write(character, record)
            raise RuntimeError("synthetic writer persistence failure")

        with patch(
            "world.rules.sight.ground_radius_at", return_value=7
        ), patch.object(
            knowledge, "_write_knowledge", side_effect=fail_after_write
        ), patch.object(knowledge, "log_warn") as log_warn:
            result = advance_wait(self.player, 60)

        self.assertEqual(result.elapsed_seconds, 60)
        self.assertEqual(int(get_world_clock().tick), before + 60)
        self.assertEqual(self.player.attributes.get(KNOWLEDGE_ATTR), prior)
        self.assertEqual(raw_attribute_value(self.player, KNOWLEDGE_ATTR), prior)
        self.assertIn(
            "map_knowledge_record_ground_observation_write_failed",
            [call.args[0] for call in log_warn.call_args_list],
        )


if __name__ == "__main__":
    unittest.main()

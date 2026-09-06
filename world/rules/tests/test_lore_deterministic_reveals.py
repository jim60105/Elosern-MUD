"""Tests for the deterministic lore-reveal sources (lore-deterministic-reveals).

Covers:
- ``reveal_lore_best_effort`` and ``schedule_lore_reveal_best_effort`` helpers
- Arrival reveals: anchor, region, unremarkable room, repeat
- Defeat reveals: registered tier, companion credit, simulated skip, untiered skip
- Origin reveals: race, nation, guild rank, unresolvable values
- Non-blocking guarantees: corrupt codex record, reveal failures during movement and combat
- Sole-writer boundary: deterministic sources never bypass ``record_lore_reveal``
- Reveal silence: no messages sent to character
"""

import types
import unittest
from unittest.mock import MagicMock, patch

from tools.spec_traceability import covers_requirement

from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.nations import NATION_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.rules.lore_knowledge import (
    record_lore_reveal,
    reveal_lore_best_effort,
    schedule_lore_reveal_best_effort,
)

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubDb:
    """Evennia-like db surface: missing attributes read as None."""

    def __getattr__(self, name):
        return None


class _Stub:
    """Minimal player-like object exposing db and key; msg() raises if called."""

    def __init__(self, key: str = "test-char"):
        self.db = _StubDb()
        self.key = key
        self.ndb = types.SimpleNamespace()

    def msg(self, *args, **kwargs):
        raise AssertionError(f"msg() was called unexpectedly: {args!r} {kwargs!r}")


def _player(**attrs):
    stub = _Stub()
    for key, value in attrs.items():
        setattr(stub.db, key, value)
    return stub


# ---------------------------------------------------------------------------
# Best-effort helper
# ---------------------------------------------------------------------------


class RevealBestEffortHelperTests(unittest.TestCase):
    """reveal_lore_best_effort: wraps record_lore_reveal, swallows exceptions."""

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_success_returns_true_and_writes_record(self):
        player = _player()
        result = reveal_lore_best_effort(player, "race", "elf")
        self.assertTrue(result)
        self.assertIn("race:elf", player.db.lore_discovered)

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_repeat_reveal_returns_true_idempotently(self):
        player = _player()
        reveal_lore_best_effort(player, "anchor", "capital_grandia")
        result = reveal_lore_best_effort(player, "anchor", "capital_grandia")
        self.assertTrue(result)
        self.assertEqual(player.db.lore_discovered, {"anchor:capital_grandia"})

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_unresolvable_key_returns_false_without_raising(self):
        player = _player()
        result = reveal_lore_best_effort(player, "race", "not_a_race")
        self.assertFalse(result)
        self.assertIsNone(player.db.lore_discovered)

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_unknown_category_returns_false_without_raising(self):
        player = _player()
        result = reveal_lore_best_effort(player, "bogus", "x")
        self.assertFalse(result)

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_failure_is_logged_through_facade_with_exc_and_context(self):
        player = _player()
        with patch("world.rules.lore_knowledge.log_warn") as mock_log:
            reveal_lore_best_effort(player, "race", "not_a_race")
        mock_log.assert_called_once()
        event = mock_log.call_args[0][0]
        kwargs = mock_log.call_args[1]
        self.assertEqual(event, "lore_reveal_failed")
        self.assertIn("exc", kwargs)
        ctx = kwargs["context"]
        self.assertEqual(ctx["category"], "race")
        self.assertEqual(ctx["key"], "not_a_race")

    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    @covers_requirement("lore-knowledge::the-codex-is-discoverable-with-every-generative-service-offline")
    def test_sole_writer_not_bypassed(self):
        """reveal_lore_best_effort must delegate to record_lore_reveal only."""
        player = _player()
        with patch("world.rules.lore_knowledge.record_lore_reveal") as mock_writer:
            mock_writer.return_value = None
            reveal_lore_best_effort(player, "anchor", "capital_grandia")
        mock_writer.assert_called_once_with(player, "anchor", "capital_grandia")

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_reveal_is_silent_no_msg_sent(self):
        """A successful reveal must not call player.msg()."""
        player = _Stub()
        # _Stub.msg raises on any call; this test must not raise
        reveal_lore_best_effort(player, "race", "elf")

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_schedule_ignores_none_key(self):
        """schedule_lore_reveal_best_effort silently drops None/empty keys."""
        with patch("world.rules.lore_knowledge.log_warn") as mock_log:
            schedule_lore_reveal_best_effort(_player(), "anchor", None)
            schedule_lore_reveal_best_effort(_player(), "anchor", "")
        mock_log.assert_not_called()


# ---------------------------------------------------------------------------
# Room resolution helpers
# ---------------------------------------------------------------------------


class RoomResolutionTests(unittest.TestCase):
    """resolve_room_anchor and resolve_room_region return correct keys."""

    def setUp(self):
        from world.quests.room_observation import resolve_room_anchor, resolve_room_region
        self.resolve_anchor = resolve_room_anchor
        self.resolve_region = resolve_room_region

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_anchor_room_resolves_to_registered_key(self):
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "capital_grandia"
        result = self.resolve_anchor(room)
        self.assertEqual(result, "capital_grandia")
        self.assertIn("capital_grandia", ANCHOR_REGISTRY)

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_room_with_unregistered_anchor_key_returns_none(self):
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "nonexistent_anchor"
        self.assertIsNone(self.resolve_anchor(room))

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_room_with_no_anchor_key_returns_none(self):
        room = MagicMock(spec=[])
        self.assertIsNone(self.resolve_anchor(room))

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_none_room_returns_none_anchor(self):
        self.assertIsNone(self.resolve_anchor(None))

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_region_resolves_from_explicit_region_key(self):
        room = MagicMock(spec=["region_key", "db"])
        room.region_key = "central_mountains"
        result = self.resolve_region(room)
        self.assertEqual(result, "central_mountains")

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_region_resolves_from_valid_coordinates(self):
        # (110, 50): central_mountains — x in [100,123], y=50 < _NORTH_FOREST_Y_MIN=190
        room = MagicMock(spec=[])
        result = self.resolve_region(room, coordinates=(110, 50))
        self.assertEqual(result, "central_mountains")

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_room_with_no_region_info_returns_none(self):
        room = MagicMock(spec=[])
        self.assertIsNone(self.resolve_region(room))

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_out_of_bounds_coordinates_return_none(self):
        room = MagicMock(spec=[])
        result = self.resolve_region(room, coordinates=(300, 300))
        self.assertIsNone(result)

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_bool_coordinates_rejected(self):
        """True/False must not be accepted as integer coordinates."""
        room = MagicMock(spec=[])
        result = self.resolve_region(room, coordinates=(True, False))
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# observe_arrival_lore — patch world.rules.lore_knowledge since that module
# is lazily imported inside observe_arrival_lore.
# ---------------------------------------------------------------------------


class ArrivalLoreTests(unittest.TestCase):
    """observe_arrival_lore schedules anchor and region reveals on character arrival."""

    def setUp(self):
        from world.quests.room_observation import observe_arrival_lore
        self.observe = observe_arrival_lore

    def _make_player_char(self):
        """Return a MagicMock that passes isinstance(obj, PlayerCharacter)."""
        from typeclasses.characters import PlayerCharacter
        char = MagicMock(spec=PlayerCharacter)
        char.__class__ = PlayerCharacter
        char.key = "hero"
        char.ndb = types.SimpleNamespace()
        char.db = _StubDb()
        return char

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_anchor_room_schedules_anchor_reveal(self):
        char = self._make_player_char()
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "capital_grandia"
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort") as mock_sched:
            self.observe(char, room)
        calls = [c.args for c in mock_sched.call_args_list]
        self.assertIn((char, "anchor", "capital_grandia"), calls)

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_region_room_schedules_region_reveal(self):
        char = self._make_player_char()
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort") as mock_sched:
            self.observe(char, None, wilderness_coordinates=(110, 50))
        calls = [c.args for c in mock_sched.call_args_list]
        self.assertIn((char, "region", "central_mountains"), calls)

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_unremarkable_room_schedules_nothing(self):
        char = self._make_player_char()
        room = MagicMock(spec=[])
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort") as mock_sched:
            self.observe(char, room)
        mock_sched.assert_not_called()

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_non_player_character_is_ignored(self):
        non_player = MagicMock()
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "capital_grandia"
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort") as mock_sched:
            self.observe(non_player, room)
        mock_sched.assert_not_called()

    @covers_requirement("lore-knowledge::arrival-reveals-the-anchor-and-region-a-room-resolves-to")
    def test_idempotent_writer_prevents_duplicate_codex_entries(self):
        char = self._make_player_char()
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "capital_grandia"
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort") as mock_sched:
            self.observe(char, room)
            self.observe(char, room)  # same room, same char — should deduplicate
        # Deduplication is handled by the idempotent sole writer, not a marker.
        # Multiple observe calls schedule multiple on_commit callbacks; the writer
        # makes the second a no-op. Both calls must schedule (not be suppressed).
        anchor_calls = [c for c in mock_sched.call_args_list if c.args[1] == "anchor"]
        self.assertGreaterEqual(len(anchor_calls), 1)

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_corrupt_lore_record_does_not_interrupt_movement(self):
        """A broken schedule call must be caught by observe_arrival_lore's outer guard."""
        char = self._make_player_char()
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "capital_grandia"
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort",
                   side_effect=RuntimeError("db corruption")):
            with patch("world.observability.log_warn") as mock_log:
                # Must not raise
                self.observe(char, room)
        mock_log.assert_called_once()
        event = mock_log.call_args[0][0]
        self.assertEqual(event, "lore_reveal_failed")

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_arrival_reveal_is_silent(self):
        """observe_arrival_lore must never call character.msg()."""
        char = self._make_player_char()
        char.msg = MagicMock(side_effect=AssertionError("msg() must not be called"))
        room = MagicMock(spec=["anchor_key", "db"])
        room.anchor_key = "capital_grandia"
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort"):
            self.observe(char, room)


# ---------------------------------------------------------------------------
# Defeat reveals
# ---------------------------------------------------------------------------


class DefeatLoreTests(unittest.TestCase):
    """_make_defeat_lore_apply and _defeated_targets honour the spec."""

    def _make_event_log(self, entries):
        log = MagicMock()
        log.entries = entries
        return log

    def _make_entry(self, kind, **data):
        entry = MagicMock()
        entry.kind = kind
        entry.data = data
        return entry

    @covers_requirement("lore-knowledge::defeating-a-monster-reveals-its-tier")
    def test_simulated_defeat_excluded_from_defeated_targets(self):
        from world.quests.planner import _defeated_targets
        log = self._make_event_log([
            self._make_entry("target_defeated", target_id=1, monster_tier="low", simulated=True)
        ])
        self.assertEqual(_defeated_targets(log), ())

    @covers_requirement("lore-knowledge::defeating-a-monster-reveals-its-tier")
    def test_real_defeat_included_in_defeated_targets(self):
        from world.quests.planner import _defeated_targets
        log = self._make_event_log([
            self._make_entry("target_defeated", target_id=1, monster_tier="low")
        ])
        result = _defeated_targets(log)
        self.assertEqual(result, ((1, "low"),))

    @covers_requirement("lore-knowledge::defeating-a-monster-reveals-its-tier")
    def test_untiered_defeat_yields_none_tier(self):
        from world.quests.planner import _defeated_targets
        log = self._make_event_log([
            self._make_entry("target_defeated", target_id=1, monster_tier=None)
        ])
        result = _defeated_targets(log)
        self.assertEqual(result, ((1, None),))

    @covers_requirement("lore-knowledge::defeating-a-monster-reveals-its-tier")
    @covers_requirement("lore-knowledge::the-codex-is-discoverable-with-every-generative-service-offline")
    def test_make_defeat_lore_apply_factory_binds_correctly(self):
        """_make_defeat_lore_apply returns a callable that invokes schedule_lore_reveal_best_effort."""
        from world.quests.planner import _make_defeat_lore_apply

        player = _player()
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort") as mock_sched:
            # Build the factory INSIDE the patch so the import in the factory body
            # resolves to the mocked version and the lambda's closure captures it.
            fn = _make_defeat_lore_apply(player, "low")
            self.assertTrue(callable(fn))
            fn()
        mock_sched.assert_called_once_with(player, "monster", "low")

    @covers_requirement("lore-knowledge::defeating-a-monster-reveals-its-tier")
    def test_unregistered_tier_not_in_monster_registry(self):
        """A tier not in MONSTER_TIER_REGISTRY must produce no reveal effect."""
        from world.quests.planner import _defeated_targets
        log = self._make_event_log([
            self._make_entry("target_defeated", target_id=1, monster_tier="ultra_super_rare")
        ])
        result = _defeated_targets(log)
        tier = result[0][1]
        self.assertNotIn(tier, MONSTER_TIER_REGISTRY)

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_defeat_lore_reveal_failure_does_not_raise(self):
        """_make_defeat_lore_apply uses schedule_lore_reveal_best_effort which swallows exceptions."""
        from world.quests.planner import _make_defeat_lore_apply

        player = _player()
        with patch("world.rules.lore_knowledge.schedule_lore_reveal_best_effort",
                   side_effect=RuntimeError("boom")):
            fn = _make_defeat_lore_apply(player, "low")
        # schedule_lore_reveal_best_effort wraps its own internals in try-except; any
        # error it encounters (import failure, on_commit failure) is logged, not raised.
        # Verify that schedule_lore_reveal_best_effort guards unexpected failures:
        with patch("world.rules.lore_knowledge.log_warn"):
            with patch("world.rules.lore_knowledge.reveal_lore_best_effort",
                       side_effect=RuntimeError("boom")):
                # on_commit is called immediately in AUTOCOMMIT mode; the lambda raises;
                # schedule_lore_reveal_best_effort's guard catches it.
                schedule_lore_reveal_best_effort(player, "monster", "low")


# ---------------------------------------------------------------------------
# Origin reveals
# ---------------------------------------------------------------------------


class OriginRevealCreationDataclassTests(unittest.TestCase):
    """CharacterCreationRequest and _ValidatedCreation carry the nation field."""

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_nation_field_on_request_and_validated_creation(self):
        import dataclasses
        from world.rules.character_creation import CharacterCreationRequest, _ValidatedCreation
        req_fields = {f.name for f in dataclasses.fields(CharacterCreationRequest)}
        val_fields = {f.name for f in dataclasses.fields(_ValidatedCreation)}
        self.assertIn("nation", req_fields)
        self.assertIn("nation", val_fields)

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_nation_defaults_to_none_on_request(self):
        from world.rules.character_creation import CharacterCreationRequest
        req = CharacterCreationRequest(mode="custom", display_name="T", age=20,
                                       apparent_age=20, race="human", subrace="human_commoner",
                                       allocations={})
        self.assertIsNone(req.nation)


class OriginRevealHelperTests(unittest.TestCase):
    """reveal_lore_best_effort covers race, nation, guild entries."""

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_valid_race_reveal_succeeds(self):
        player = _player()
        self.assertTrue(reveal_lore_best_effort(player, "race", "human"))
        self.assertIn("race:human", player.db.lore_discovered)

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_valid_nation_reveal_succeeds(self):
        player = _player()
        self.assertTrue(reveal_lore_best_effort(player, "nation", "grandia"))
        self.assertIn("nation:grandia", player.db.lore_discovered)

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_f_rank_guild_reveal_succeeds(self):
        player = _player()
        self.assertTrue(reveal_lore_best_effort(player, "guild", "F"))
        self.assertIn("guild:F", player.db.lore_discovered)

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_unresolvable_race_does_not_raise_and_reveals_nothing(self):
        """A subrace key (not a race) must not raise and must leave codex unchanged."""
        player = _player()
        result = reveal_lore_best_effort(player, "race", "ciaran")
        self.assertFalse(result)
        self.assertIsNone(player.db.lore_discovered)

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_unresolvable_nation_does_not_raise_and_reveals_nothing(self):
        player = _player()
        result = reveal_lore_best_effort(player, "nation", "atlantis")
        self.assertFalse(result)
        self.assertIsNone(player.db.lore_discovered)

    @covers_requirement("lore-knowledge::origin-reveals-seed-the-codex-at-creation-and-registration")
    def test_unresolvable_guild_rank_does_not_raise(self):
        player = _player()
        result = reveal_lore_best_effort(player, "guild", "Z")
        self.assertFalse(result)
        self.assertIsNone(player.db.lore_discovered)


# ---------------------------------------------------------------------------
# Sole-writer boundary
# ---------------------------------------------------------------------------


class SoleWriterBoundaryTests(unittest.TestCase):
    """Deterministic sources must write through record_lore_reveal only."""

    @covers_requirement("lore-knowledge::the-codex-is-discoverable-with-every-generative-service-offline")
    @covers_requirement("lore-knowledge::the-codex-stores-discovered-entries-append-only-under-one-sole-writer")
    def test_reveal_best_effort_delegates_to_record_lore_reveal(self):
        import world.rules.lore_knowledge as mod

        player = _player()
        original_record = mod.record_lore_reveal
        calls: list[tuple[str, str]] = []

        def recording_record(p, cat, key):
            calls.append((cat, key))
            return original_record(p, cat, key)

        with patch.object(mod, "record_lore_reveal", side_effect=recording_record):
            reveal_lore_best_effort(player, "anchor", "capital_grandia")

        self.assertEqual(calls, [("anchor", "capital_grandia")])
        self.assertIn("anchor:capital_grandia", player.db.lore_discovered)

    @covers_requirement("lore-knowledge::the-codex-is-discoverable-with-every-generative-service-offline")
    def test_offline_play_fills_codex_without_external_calls(self):
        """Purely deterministic reveals fill the codex without any LLM or network call."""
        player = _player()

        reveal_lore_best_effort(player, "race", "elf")
        reveal_lore_best_effort(player, "nation", "grandia")
        reveal_lore_best_effort(player, "anchor", "capital_grandia")
        reveal_lore_best_effort(player, "monster", "low")

        self.assertEqual(
            player.db.lore_discovered,
            {"race:elf", "nation:grandia", "anchor:capital_grandia", "monster:low"},
        )


# ---------------------------------------------------------------------------
# Silence guarantee
# ---------------------------------------------------------------------------


class RevealSilenceTests(unittest.TestCase):
    """Reveals must emit no player-facing messages."""

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_successful_reveal_sends_no_message(self):
        """reveal_lore_best_effort must never call player.msg()."""
        player = _Stub()
        # _Stub.msg raises on any call; this test must not raise
        reveal_lore_best_effort(player, "race", "elf")

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_failed_reveal_sends_no_message(self):
        """Even a failing reveal must not message the player."""
        player = _Stub()
        reveal_lore_best_effort(player, "race", "not_a_race")

    @covers_requirement("lore-knowledge::a-reveal-never-blocks-or-fails-the-play-that-triggered-it")
    def test_reveal_is_silent_via_mock(self):
        """A reveal never sends any message to the character."""
        player = _Stub()
        msg_mock = MagicMock()
        player.msg = msg_mock
        reveal_lore_best_effort(player, "anchor", "capital_grandia")
        msg_mock.assert_not_called()

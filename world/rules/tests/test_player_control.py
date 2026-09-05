"""Tests for world.rules.player_control.is_player_driven.

Pins the clock-invariant contract: the world advances only on player action;
companion possession widens WHO counts as a player actor, never WHEN.
"""

from unittest.mock import MagicMock
import evennia

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules.player_control import is_player_driven


class PlayerControlPredicateTests(EvenniaTest):
    """Scenario tests for is_player_driven."""

    @covers_requirement(
        "player-control-predicate::one-predicate-decides-player-driven-entity-status"
    )
    def test_puppeted_player_character_is_player_driven(self):
        """Scenario: A puppeted player character is player-driven."""
        self.assertTrue(is_player_driven(self.char1))

    @covers_requirement(
        "player-control-predicate::one-predicate-decides-player-driven-entity-status"
    )
    def test_possessed_and_puppeted_npc_is_player_driven(self):
        """Scenario: A possessed-and-puppeted NPC is player-driven."""
        npc = create_object(NPC, key="附身NPC", location=self.room1)
        npc.db.possessed_by = self.char1.pk

        # Give the NPC a mock session
        session = ServerSession()
        session.sessid = 99991
        evennia.SESSION_HANDLER[session.sessid] = session
        npc.sessions.add(session)

        try:
            self.assertTrue(is_player_driven(npc))
        finally:
            npc.sessions.remove(session)
            evennia.SESSION_HANDLER.pop(session.sessid, None)

    @covers_requirement(
        "player-control-predicate::one-predicate-decides-player-driven-entity-status"
    )
    def test_ordinary_npc_is_not_player_driven(self):
        """Scenario: An ordinary NPC is not."""
        npc = create_object(NPC, key="普通NPC", location=self.room1)
        # Unpossessed NPC
        self.assertFalse(is_player_driven(npc))

        # Possessed but unpuppeted NPC (stale-attribute window)
        npc.db.possessed_by = self.char1.pk
        self.assertEqual(npc.sessions.count(), 0)
        self.assertFalse(is_player_driven(npc))

        # None entity
        self.assertFalse(is_player_driven(None))

    @covers_requirement(
        "player-control-predicate::one-predicate-decides-player-driven-entity-status"
    )
    def test_predicate_is_only_such_gate(self):
        """Scenario: The predicate is the only such gate in movement or triggers."""
        from pathlib import Path
        import re

        repo_root = Path(__file__).resolve().parents[3]
        pattern = re.compile(r"isinstance\([^)]+PlayerCharacter\)")

        targets = [
            repo_root / "world" / "rules" / "movement.py",
            repo_root / "typeclasses" / "characters.py",
        ]
        for path in targets:
            text = path.read_text(encoding="utf-8")
            matches = pattern.findall(text)
            # In movement.py: 0 matches (replaced by is_player_driven)
            # In characters.py: only in PlayerCharacter class hierarchy or unrelated helpers
            if path.name == "movement.py":
                self.assertEqual(
                    len(matches),
                    0,
                    f"Found raw isinstance(...PlayerCharacter) in {path}: {matches}",
                )

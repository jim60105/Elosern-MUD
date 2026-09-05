"""Command tests for possess (附身) and unpossess (歸位).

Pins the localized command surface and handback-first dismissal guard
(companion-possession-core capability).
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.leave import CmdLeave
from commands.possess import CmdPossess, CmdUnpossess
from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.quests.catalog import register_catalog
from world.rules.party import (
    HANDBACK_FIRST_MESSAGE,
    is_companion,
    join_party,
)
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_ALREADY_POSSESSING,
    REASON_NOT_BOUND,
    UNPOSSESS_RELEASED_MESSAGE,
    current_possession,
)


class PossessCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """Scenario tests for possess and unpossess commands."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(NPC, key="艾洛希雅", location=self.room1)
        self.char1.location = self.room1

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    def test_possess_missing_target_reports_usage(self):
        """Scenario: The command pair resolves targets and reports gate lines (missing target)."""
        output = self.call(CmdPossess(), "")
        self.assertIn("你想附身誰？請指定一個同伴", output)
        self.assertIsNone(current_possession(self.char1))

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    def test_possess_unbound_target_reports_error(self):
        """Scenario: The command pair resolves targets and reports gate lines (unbound target)."""
        output = self.call(CmdPossess(), "艾洛希雅")
        self.assertIn(POSSESSION_REJECTION_MESSAGES[REASON_NOT_BOUND], output)
        self.assertIsNone(current_possession(self.char1))

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    def test_possess_bound_companion_succeeds(self):
        """Possess enters possession and notifies the caller."""
        join_party(self.npc, self.char1)
        output = self.call(CmdPossess(), "艾洛希雅")
        self.assertIn("你附身到了艾洛希雅身上。", output)
        self.assertIsNotNone(current_possession(self.char1))
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    def test_possess_already_possessing_reports_error(self):
        """Possess when already possessing reports gate line."""
        join_party(self.npc, self.char1)
        self.call(CmdPossess(), "艾洛希雅")

        output = self.call(CmdPossess(), "艾洛希雅")
        self.assertIn(POSSESSION_REJECTION_MESSAGES[REASON_ALREADY_POSSESSING], output)

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    def test_unpossess_without_possession_reports_error(self):
        """Unpossess without possession reports idle state."""
        output = self.call(CmdUnpossess(), "")
        self.assertIn("你目前並未附身在任何同伴身上。", output)

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    def test_unpossess_releases_possession(self):
        """Scenario: 歸位 releases the current possession."""
        join_party(self.npc, self.char1)
        self.call(CmdPossess(), "艾洛希雅")
        self.assertIsNotNone(current_possession(self.char1))

        output = self.call(CmdUnpossess(), "")
        self.assertIn(UNPOSSESS_RELEASED_MESSAGE, output)
        self.assertIsNone(current_possession(self.char1))
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "party-system::the-leave-command-dismisses-a-companion-without-affinity-change"
    )
    def test_leave_on_possessed_companion_refuses_handback_first(self):
        """Scenario: A possessed companion refuses dismissal via the leave command."""
        join_party(self.npc, self.char1)
        self.call(CmdPossess(), "艾洛希雅")

        output = self.call(CmdLeave(), "艾洛希雅")
        self.assertIn(HANDBACK_FIRST_MESSAGE, output)

        # Still bound and possessed!
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertIsNotNone(current_possession(self.char1))
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))

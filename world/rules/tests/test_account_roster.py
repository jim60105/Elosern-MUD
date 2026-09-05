"""Tests for the deterministic account roster read model (webclient-character-roster)."""

from unittest.mock import PropertyMock, patch

from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.account_roster import (
    MAX_ROSTER_ROWS,
    ROSTER_LOCK_REASON,
    AccountRosterError,
    AccountRosterView,
    RosterCharacterView,
    build_account_roster,
)


class AccountRosterTests(EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.characters.add(self.char1)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_ordering_by_identity(self):
        """Characters are ordered by ascending numeric identity."""
        self.account.create_character(key="Beta")
        self.account.create_character(key="Gamma")

        view = build_account_roster(self.char1)
        identities = [c.identity for c in view.characters]
        self.assertEqual(identities, sorted(identities))
        self.assertEqual(len(view.characters), 3)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_current_flag_identification(self):
        """Exactly the rendered actor has current: True, others have current: False."""
        char_b, _ = self.account.create_character(key="Beta")
        view1 = build_account_roster(self.char1)
        current_1 = [c for c in view1.characters if c.current]
        self.assertEqual(len(current_1), 1)
        self.assertEqual(current_1[0].identity, int(self.char1.pk))

        self.account.puppet_object(self.session, char_b)
        view2 = build_account_roster(char_b)
        current_2 = [c for c in view2.characters if c.current]
        self.assertEqual(len(current_2), 1)
        self.assertEqual(current_2[0].identity, int(char_b.pk))

        # Switch back to char1 for subsequent tests
        self.account.puppet_object(self.session, self.char1)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_pending_flag_identification(self):
        """creation_pending marker is reported truthfully per character."""
        self.char1.db.creation_pending = False
        char_b, _ = self.account.create_character(key="PendingHero")
        self.assertTrue(getattr(char_b, "creation_pending", False))

        view = build_account_roster(self.char1)
        rows_by_id = {c.identity: c for c in view.characters}
        self.assertFalse(rows_by_id[int(self.char1.pk)].pending)
        self.assertTrue(rows_by_id[int(char_b.pk)].pending)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts",
        "webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only",
    )
    def test_foreign_account_characters_excluded(self):
        """Characters belonging to other accounts never appear in the roster."""
        self.account2.characters.add(self.char2)
        view = build_account_roster(self.char1)
        character_ids = {c.identity for c in view.characters}
        self.assertIn(int(self.char1.pk), character_ids)
        self.assertNotIn(int(self.char2.pk), character_ids)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_max_roster_rows_bound(self):
        """The roster truncates to MAX_ROSTER_ROWS (10) even if an account owns more."""
        fake_chars = [self.char1]
        for i in range(2, 13):
            fake_char = create.create_object(
                self.character_typeclass,
                key=f"Extra_{i}",
            )
            fake_char.account = self.account
            fake_chars.append(fake_char)

        with patch.object(Account, "characters", new_callable=PropertyMock) as mock_chars:
            mock_chars.return_value = fake_chars
            view = build_account_roster(self.char1)
            self.assertEqual(len(view.characters), MAX_ROSTER_ROWS)
            self.assertEqual(view.max_characters, 5)
            self.assertFalse(view.can_create)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_max_roster_rows_bound_preserves_active_puppet_with_high_identity(self):
        """When an account owns >10 characters and the active actor has the highest PK,
        the bounded roster always includes the active actor and remains sorted ascending.
        """
        fake_chars = [self.char1]
        for i in range(2, 13):
            fake_char = create.create_object(
                self.character_typeclass,
                key=f"Extra_{i}",
            )
            fake_char.account = self.account
            fake_chars.append(fake_char)

        # Let the 12th character (highest PK) be the active actor
        active_actor = fake_chars[-1]

        with patch.object(Account, "characters", new_callable=PropertyMock) as mock_chars:
            mock_chars.return_value = fake_chars
            view = build_account_roster(active_actor)
            self.assertEqual(len(view.characters), MAX_ROSTER_ROWS)
            current_rows = [c for c in view.characters if c.current]
            self.assertEqual(len(current_rows), 1)
            self.assertEqual(current_rows[0].identity, int(active_actor.pk))
            identities = [c.identity for c in view.characters]
            self.assertEqual(identities, sorted(identities))

    @covers_requirement(
        "webclient-character-roster::the-roster-carries-the-account-s-capacity-and-switch-lock-facts"
    )
    def test_capacity_and_can_create_at_and_below_cap(self):
        """can_create is True when count < MAX_NR_CHARACTERS, False when count >= MAX_NR_CHARACTERS."""
        with override_settings(MAX_NR_CHARACTERS=2):
            view_below = build_account_roster(self.char1)
            self.assertEqual(view_below.max_characters, 2)
            self.assertTrue(view_below.can_create)

            self.account.create_character(key="Second")
            view_at_cap = build_account_roster(self.char1)
            self.assertEqual(view_at_cap.max_characters, 2)
            self.assertFalse(view_at_cap.can_create)

    @covers_requirement(
        "webclient-character-roster::the-roster-carries-the-account-s-capacity-and-switch-lock-facts"
    )
    def test_switch_locked_in_and_out_of_combat(self):
        """switch_locked is True and lock_reason is set in combat; cleared out of combat."""
        with patch("world.rules.account_roster.is_in_active_session", return_value=False):
            view_peace = build_account_roster(self.char1)
            self.assertFalse(view_peace.switch_locked)
            self.assertIsNone(view_peace.lock_reason)

        with patch("world.rules.account_roster.is_in_active_session", return_value=True):
            view_combat = build_account_roster(self.char1)
            self.assertTrue(view_combat.switch_locked)
            self.assertEqual(view_combat.lock_reason, ROSTER_LOCK_REASON)

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode"
    )
    def test_account_roster_error_when_actor_none(self):
        """build_account_roster(None) raises AccountRosterError."""
        with self.assertRaises(AccountRosterError):
            build_account_roster(None)

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode"
    )
    def test_account_roster_error_when_account_none(self):
        """An actor with no resolvable account raises AccountRosterError."""
        orphan_char = create.create_object(self.character_typeclass, key="Orphan")
        self.assertIsNone(getattr(orphan_char, "account", None))
        with self.assertRaises(AccountRosterError):
            build_account_roster(orphan_char)

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode"
    )
    def test_account_roster_error_when_characters_handler_raises(self):
        """A characters collection that raises an exception translates to AccountRosterError."""
        with patch.object(Account, "characters", new_callable=PropertyMock) as mock_chars:
            mock_chars.side_effect = RuntimeError("database failure")
            with self.assertRaises(AccountRosterError):
                build_account_roster(self.char1)

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_account_roster_error_when_actor_not_in_characters(self):
        """An actor not in the account's characters list raises AccountRosterError (0 current rows)."""
        char_other = create.create_object(self.character_typeclass, key="Other")
        char_other.account = self.account

        with patch.object(Account, "characters", new_callable=PropertyMock) as mock_chars:
            mock_chars.return_value = [char_other]
            with self.assertRaises(AccountRosterError) as ctx:
                build_account_roster(self.char1)
            self.assertIn("roster must have exactly one current character", str(ctx.exception))

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts"
    )
    def test_account_roster_error_when_actor_not_in_characters_large_roster(self):
        """When account owns 11+ characters and the actor is not in that list, raises AccountRosterError."""
        fake_chars = []
        for i in range(1, 13):
            c = create.create_object(self.character_typeclass, key=f"Other_{i}")
            c.account = self.account
            fake_chars.append(c)

        with patch.object(Account, "characters", new_callable=PropertyMock) as mock_chars:
            mock_chars.return_value = fake_chars
            with self.assertRaises(AccountRosterError) as ctx:
                build_account_roster(self.char1)
            self.assertIn("roster must have exactly one current character", str(ctx.exception))

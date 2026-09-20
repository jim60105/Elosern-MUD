"""The account.character.create adapter and its transition rechecks."""
from web.webclient.actions.account_actions import (
    ALREADY_CURRENT_CODE,
    ALREADY_CURRENT_MESSAGE,
    AFFECTED_PANELS,
    AccountActionError,
    CHARACTER_SLOTS_FULL_CODE,
    CHARACTER_SLOTS_FULL_MESSAGE,
    CREATE_FAILED_MESSAGE,
    CREATE_IN_COMBAT_MESSAGE,
    CREATE_SUCCESS_CODE,
    CREATE_SUCCESS_MESSAGE,
    IN_COMBAT_CODE,
    IN_COMBAT_MESSAGE,
    INVALID_CHARACTER_CODE,
    INVALID_CHARACTER_MESSAGE,
    NO_ACTIVE_SESSION_CODE,
    NO_ACTIVE_SESSION_MESSAGE,
    RECOVERY_FAILED_MESSAGE,
    RECOVERY_RESTORED_TEMPLATE,
    RECOVERY_RETAINED_TEMPLATE,
    SUCCESS_CODE,
    SUCCESS_MESSAGE,
    TRANSITION_PENDING_CODE,
    TRANSITION_PENDING_MESSAGE,
    _account_character_create_adapter,
    _account_character_switch_adapter,
    _attach_puppet,
    _perform_create,
    _perform_switch,
    _clear_transition_pending,
    _recover_transition,
    _transition_pending,
    set_clock_for_testing,
    validate_account_character_create_payload,
    validate_account_character_switch_payload,
)
from twisted.internet.task import Clock
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from types import SimpleNamespace
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.registry import build_production_registry
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.clock import get_world_clock
from unittest.mock import MagicMock, patch
import unittest


class AccountActionsIntegrationTests(EvenniaTest):
    """Integration tests for account.character.switch against real Evennia state."""

    def setUp(self):
        super().setUp()
        get_world_clock()

        # Injected deterministic clock
        self.clock = Clock()
        set_clock_for_testing(self.clock)

        # Set up characters on self.account
        self.account.characters.add(self.char1)
        self.char1.account = self.account

        self.char2 = create_object(
            PlayerCharacter,
            key="SecondChar",
            location=self.room1,
            home=self.room1,
        )
        self.char2.account = self.account
        self.account.characters.add(self.char2)

        self.char3 = create_object(
            PlayerCharacter,
            key="ThirdChar",
            location=self.room1,
            home=self.room1,
        )
        self.char3.account = self.account
        self.account.characters.add(self.char3)

        # Foreign character owned by self.account2
        self.foreign_char = self.char2_from_account2 if hasattr(self, "char2_from_account2") else create_object(
            PlayerCharacter,
            key="ForeignChar",
            location=self.room1,
            home=self.room1,
        )
        self.foreign_char.account = self.account2
        self.account2.characters.add(self.foreign_char)

        # Registries
        self.action_registry = build_production_action_registry()
        self.presentation_registry = build_production_registry()

        # Configure self.session (the real ServerSession created by EvenniaTest)
        self.session.puppet = self.char1
        self.session.puid = self.char1.id
        self.session.protocol_key = "websocket"
        self.session.sent = []

        def recording_msg(*args, **kwargs):
            self.session.sent.append(kwargs)
        self.session.msg = recording_msg

        self.char1.sessions.add(self.session)
        self.coordinator = attach_coordinator(self.session, self.presentation_registry)


    def tearDown(self):
        set_clock_for_testing(None)
        super().tearDown()


    def _envelope(self, payload, request_id="r1", epoch=None, base_revision=None):
        if epoch is None:
            epoch = self.coordinator.epoch
        if base_revision is None:
            base_revision = self.coordinator.revision
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": request_id,
            "base_revision": base_revision,
            "action_id": "account.character.switch",
            "payload": payload,
        }



    # -------------------------------------------------------------------------
    # MC4: Character Create Action Tests
    # -------------------------------------------------------------------------
    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    def test_create_rejected_at_capacity(self):
        """Creating when account is at MAX_NR_CHARACTERS capacity is rejected synchronously."""
        # Account already holds char1, char2, char3 (3 characters)
        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 3):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], CHARACTER_SLOTS_FULL_CODE)
        self.assertEqual(result["message"], CHARACTER_SLOTS_FULL_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # Nothing was scheduled and session puppet is untouched
        self.assertEqual(len(self.clock.getDelayedCalls()), 0)
        self.assertIs(self.session.puppet, self.char1)
        self.assertEqual(len(self.account.characters), 3)


    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    def test_create_rejected_when_currently_in_combat(self):
        """Creating while in active combat is blocked synchronously."""
        with patch(
            "web.webclient.actions.account_actions.is_in_active_session",
            return_value=True,
        ):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], IN_COMBAT_CODE)
        self.assertEqual(result["message"], CREATE_IN_COMBAT_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # Nothing was scheduled
        self.assertEqual(len(self.clock.getDelayedCalls()), 0)
        self.assertIs(self.session.puppet, self.char1)


    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    def test_create_rejected_for_actor_without_account(self):
        """Creating from an actor with no account returns no_active_session."""
        fake_actor = SimpleNamespace(account=None)
        result = _account_character_create_adapter(
            fake_actor,
            {},
            session=self.session,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], NO_ACTIVE_SESSION_CODE)
        self.assertEqual(result["message"], NO_ACTIVE_SESSION_MESSAGE)
        self.assertTrue(result["no_presentation"])


    @covers_requirement(
        "webclient-character-roster::a-newly-created-character-enters-the-existing-wizard-and-never-resends-the-world-introduction"
    )
    def test_create_acceptance_and_clock_advance(self):
        """Accepting create returns success result; advancing clock creates and attaches shell in creation mode."""
        account_msgs = []
        def fake_msg(text=None, *args, **kwargs):
            if text is not None:
                account_msgs.append(text)
            elif args:
                account_msgs.append(args[0])
        self.account.msg = fake_msg

        initial_epoch = self.coordinator.epoch
        initial_char_count = len(self.account.characters)

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], CREATE_SUCCESS_CODE)
        self.assertEqual(result["message"], CREATE_SUCCESS_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # Puppet before reactor advance is still char1
        self.assertIs(self.session.puppet, self.char1)
        self.assertEqual(len(self.clock.getDelayedCalls()), 1)

        # Advance clock to execute scheduled _perform_create
        self.clock.advance(0)

        # Session is now puppeting the newly created shell
        new_shell = self.session.puppet
        self.assertIsNotNone(new_shell)
        self.assertIsNot(new_shell, self.char1)
        self.assertIn(new_shell, self.account.characters)
        self.assertEqual(len(self.account.characters), initial_char_count + 1)
        self.assertTrue(getattr(new_shell, "creation_pending", False))
        self.assertEqual(new_shell.key, self.account.key)
        self.assertIs(self.account.db._last_puppet, new_shell)

        # Mode resolves to creation with a bumped epoch in the published snapshot
        snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
        self.assertTrue(snapshots)
        snapshot_envelope = snapshots[-1]["ui_snapshot"][0][0]
        self.assertEqual(snapshot_envelope["mode"], "creation")
        self.assertNotEqual(snapshot_envelope["presentation_epoch"], initial_epoch)

        # creation_start_screen was delivered; WORLD_INTRODUCTION was not
        self.assertTrue(any("你站在伊洛瑟恩大陸的門口" in m for m in account_msgs))
        self.assertFalse(any("這是一個充斥著魔力" in m for m in account_msgs))


    @covers_requirement(
        "webclient-character-roster::the-new-character-shell-is-created-before-the-current-character-is-left"
    )
    def test_create_late_capacity_failure_costs_nothing(self):
        """Capacity check failure at transition time leaves session completely untouched."""
        account_msgs = []
        def fake_msg(text=None, *args, **kwargs):
            if text is not None:
                account_msgs.append(text)
            elif args:
                account_msgs.append(args[0])
        self.account.msg = fake_msg

        initial_epoch = self.coordinator.epoch
        initial_chars = list(self.account.characters)

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

            # Simulate capacity failure reported by create_character returning (None, errors)
            with patch.object(
                self.account,
                "create_character",
                return_value=(None, ["Slots full"]),
            ), patch(
                "web.webclient.actions.account_actions.log_warn"
            ) as mock_warn:
                self.clock.advance(0)
                mock_warn.assert_called()
                self.assertEqual(mock_warn.call_args[0][0], "char_create_rejected")

        # Session still holds char1 with epoch intact
        self.assertIs(self.session.puppet, self.char1)
        self.assertEqual(self.coordinator.epoch, initial_epoch)
        self.assertEqual(list(self.account.characters), initial_chars)
        self.assertTrue(any(CREATE_FAILED_MESSAGE in m for m in account_msgs))


    @covers_requirement(
        "webclient-character-roster::the-new-character-shell-is-created-before-the-current-character-is-left"
    )
    def test_create_late_exception_costs_nothing(self):
        """Exception raised during create_character leaves session completely untouched."""
        account_msgs = []
        def fake_msg(text=None, *args, **kwargs):
            if text is not None:
                account_msgs.append(text)
            elif args:
                account_msgs.append(args[0])
        self.account.msg = fake_msg

        initial_epoch = self.coordinator.epoch
        initial_chars = list(self.account.characters)

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

            with patch.object(
                self.account,
                "create_character",
                side_effect=RuntimeError("Storage failure"),
            ), patch(
                "web.webclient.actions.account_actions.log_warn"
            ) as mock_warn:
                self.clock.advance(0)
                mock_warn.assert_called()
                self.assertEqual(mock_warn.call_args[0][0], "char_create_call_failed")

        # Session still holds char1 with epoch intact
        self.assertIs(self.session.puppet, self.char1)
        self.assertEqual(self.coordinator.epoch, initial_epoch)
        self.assertEqual(list(self.account.characters), initial_chars)
        self.assertTrue(any(CREATE_FAILED_MESSAGE in m for m in account_msgs))


    @covers_requirement(
        "webclient-character-roster::the-new-character-shell-is-created-before-the-current-character-is-left"
    )
    def test_create_transition_capacity_recheck_cancels(self):
        """If account hits capacity after admission before transition runs, transition cancels safely."""
        account_msgs = []
        def fake_msg(text=None, *args, **kwargs):
            if text is not None:
                account_msgs.append(text)
            elif args:
                account_msgs.append(args[0])
        self.account.msg = fake_msg

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

        # Before clock advance, reduce MAX_NR_CHARACTERS to 2 (account has char1, char2, char3 -> 3 >= 2)
        with patch(
            "web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 2
        ), patch.object(
            self.account, "create_character"
        ) as mock_create, patch(
            "web.webclient.actions.account_actions.log_warn"
        ) as mock_warn:
            self.clock.advance(0)
            mock_create.assert_not_called()
            mock_warn.assert_called()
            self.assertEqual(mock_warn.call_args[0][0], "char_create_capacity_reached")

        self.assertIs(self.session.puppet, self.char1)
        self.assertTrue(any(CHARACTER_SLOTS_FULL_MESSAGE in m for m in account_msgs))

        # MC6: the cancelled create cleared the marker; a fresh request is admitted
        self.assertFalse(_transition_pending(self.session))
        next_result = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char3.pk)}, session=self.session
        )
        self.assertEqual(next_result["outcome"], "success")
        self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    def test_create_transition_combat_recheck_cancels(self):
        """If character enters combat after admission before transition runs, transition cancels safely."""
        account_msgs = []
        def fake_msg(text=None, *args, **kwargs):
            if text is not None:
                account_msgs.append(text)
            elif args:
                account_msgs.append(args[0])
        self.account.msg = fake_msg

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

        # Before clock advance, puppet enters combat
        with patch(
            "web.webclient.actions.account_actions.is_in_active_session",
            return_value=True,
        ), patch.object(
            self.account, "create_character"
        ) as mock_create, patch(
            "web.webclient.actions.account_actions.log_warn"
        ) as mock_warn:
            self.clock.advance(0)
            mock_create.assert_not_called()
            mock_warn.assert_called()
            self.assertEqual(mock_warn.call_args[0][0], "char_create_entered_combat")

        self.assertIs(self.session.puppet, self.char1)
        self.assertTrue(any(CREATE_IN_COMBAT_MESSAGE in m for m in account_msgs))

        # MC6: the cancelled create cleared the marker; a fresh request is admitted
        self.assertFalse(_transition_pending(self.session))
        next_result = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char3.pk)}, session=self.session
        )
        self.assertEqual(next_result["outcome"], "success")
        self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


    def test_create_stale_puppet_cancels_before_transition(self):
        """If session puppet changed before scheduled create callback executes, callback cancels."""
        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

            # Simulate puppet switch before clock advances
            self.session.puppet = self.char2

            with patch.object(self.account, "create_character") as mock_create:
                self.clock.advance(0)
                mock_create.assert_not_called()

        self.assertIs(self.session.puppet, self.char2)

        # MC6: the cancelled create cleared the marker; a fresh request is admitted
        self.assertFalse(_transition_pending(self.session))
        next_result = _account_character_switch_adapter(
            self.char2, {"character_id": int(self.char1.pk)}, session=self.session
        )
        self.assertEqual(next_result["outcome"], "success")
        self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


    @covers_requirement(
        "webclient-character-roster::the-new-character-shell-is-created-before-the-current-character-is-left"
    )
    def test_create_failed_attach_retains_previous_and_preserves_orphan(self):
        """If attach fails silently while previous puppet is retained, orphan shell is preserved in roster."""
        chars_before = list(self.account.characters)

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

            # Attach fails, but session still holds char1 (rung 1)
            with patch(
                "web.webclient.actions.account_actions._attach_puppet",
                return_value=False,
            ):
                self.clock.advance(0)

        # Session still holds char1
        self.assertIs(self.session.puppet, self.char1)
        self.assertIs(self.account.db._last_puppet, self.char1)

        # Orphaned shell is NOT deleted: it exists, belongs to account, and has creation_pending=True
        new_shells = [c for c in self.account.characters if c not in chars_before]
        self.assertEqual(len(new_shells), 1)
        orphan = new_shells[0]
        self.assertTrue(getattr(orphan, "creation_pending", False))


    @covers_requirement(
        "webclient-character-roster::the-new-character-shell-is-created-before-the-current-character-is-left"
    )
    def test_create_failed_attach_repairs_previous_and_preserves_orphan(self):
        """If initial attach fails after detach, rung 2 repairs previous and orphan shell is preserved."""
        chars_before = list(self.account.characters)

        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

            call_count = 0
            def mock_attach(session, account, target):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: attaching the new shell fails and detaches session
                    session.puppet = None
                    return False
                # Second call: recovery ladder re-attaching char1 succeeds
                session.puppet = target
                return True

            with patch(
                "web.webclient.actions.account_actions._attach_puppet",
                side_effect=mock_attach,
            ):
                self.clock.advance(0)

        # Repaired to char1
        self.assertIs(self.session.puppet, self.char1)
        self.assertIs(self.account.db._last_puppet, self.char1)

        # Orphaned shell is preserved in account.characters
        new_shells = [c for c in self.account.characters if c not in chars_before]
        self.assertEqual(len(new_shells), 1)
        orphan = new_shells[0]
        self.assertTrue(getattr(orphan, "creation_pending", False))


    @covers_requirement(
        "webclient-character-roster::a-newly-created-character-enters-the-existing-wizard-and-never-resends-the-world-introduction"
    )
    def test_create_abandoned_shell_round_trip(self):
        """Creating B, saving draft, switching to A, and switching back to B preserves draft and creation mode."""
        with patch("web.webclient.actions.account_actions.settings.MAX_NR_CHARACTERS", 10):
            # 1. Create character B
            result = _account_character_create_adapter(
                self.char1,
                {},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")
            self.clock.advance(0)

            char_b = self.session.puppet
            self.assertIsNot(char_b, self.char1)
            self.assertTrue(getattr(char_b, "creation_pending", False))

            # 2. Player saves some draft data on char_b
            char_b.db.creation_draft = {"concept": "wizard", "race": "elf"}

            # 3. Switch back to char1
            result_switch_a = _account_character_switch_adapter(
                char_b,
                {"character_id": int(self.char1.pk)},
                session=self.session,
            )
            self.assertEqual(result_switch_a["outcome"], "success")
            self.clock.advance(0)
            self.assertIs(self.session.puppet, self.char1)

            # 4. Switch forward back to char_b
            result_switch_b = _account_character_switch_adapter(
                self.char1,
                {"character_id": int(char_b.pk)},
                session=self.session,
            )
            self.assertEqual(result_switch_b["outcome"], "success")
            self.clock.advance(0)
            self.assertIs(self.session.puppet, char_b)

            # Draft is preserved and snapshot mode resolves to creation
            self.assertEqual(char_b.db.creation_draft, {"concept": "wizard", "race": "elf"})
            snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
            self.assertTrue(snapshots)
            snapshot_envelope = snapshots[-1]["ui_snapshot"][0][0]
            self.assertEqual(snapshot_envelope["mode"], "creation")

if __name__ == "__main__":
    unittest.main()

"""Tests for account character capacity and slot enforcement (multichar-01-account-capacity)."""

from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import (
    CharacterCreationRequest,
    activate_player_character,
)


class AccountCapacityTests(EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    @covers_requirement(
        "player-character-creation::an-account-owns-up-to-a-configured-number-of-independently-created-characters"
    )
    def test_account_holds_characters_up_to_capacity(self):
        account = create.create_account(
            "MultiCharAcct1",
            email="mc1@example.com",
            password="testpassword",
            typeclass=self.account_typeclass,
            permissions=["Player"],
        )
        for i in range(1, 6):
            char, errs = account.create_character(key=f"Hero_{i}")
            self.assertIsNotNone(char, f"Character {i} should be created successfully")
            self.assertFalse(errs)
            self.assertIn(char, account.characters)
            self.assertTrue(
                getattr(char, "creation_pending", False),
                f"Character {i} should be marked creation_pending",
            )
        self.assertEqual(len(account.characters), 5)

    @covers_requirement(
        "player-character-creation::an-account-owns-up-to-a-configured-number-of-independently-created-characters"
    )
    def test_capacity_refusal_without_side_effects(self):
        account = create.create_account(
            "MultiCharAcct2",
            email="mc2@example.com",
            password="testpassword",
            typeclass=self.account_typeclass,
            permissions=["Player"],
        )
        for i in range(1, 6):
            char, errs = account.create_character(key=f"Hero_{i}")
            self.assertIsNotNone(char)
            self.assertFalse(errs)

        chars_before = list(account.characters)
        total_objects_before = PlayerCharacter.objects.count()

        char_extra, errs = account.create_character(key="Hero_Extra")
        self.assertIsNone(char_extra)
        self.assertTrue(errs)
        self.assertIn("You may only have a maximum of 5 characters.", errs[0])
        self.assertEqual(list(account.characters), chars_before)
        self.assertEqual(PlayerCharacter.objects.count(), total_objects_before)

    @covers_requirement(
        "player-character-creation::an-account-owns-up-to-a-configured-number-of-independently-created-characters"
    )
    def test_developer_account_also_enforces_capacity(self):
        """Evennia stock allows Developer/superuser to bypass slots; Elosern enforces for all."""
        account = create.create_account(
            "MultiCharDev",
            email="mcdev@example.com",
            password="testpassword",
            typeclass=self.account_typeclass,
            permissions=["Developer"],
        )
        for i in range(1, 6):
            char, errs = account.create_character(key=f"DevHero_{i}")
            self.assertIsNotNone(char)
            self.assertFalse(errs)

        chars_before = list(account.characters)
        total_objects_before = PlayerCharacter.objects.count()

        char_extra, errs = account.create_character(key="DevHero_Extra")
        self.assertIsNone(char_extra)
        self.assertTrue(errs)
        self.assertIn("You may only have a maximum of 5 characters.", errs[0])
        self.assertEqual(list(account.characters), chars_before)
        self.assertEqual(PlayerCharacter.objects.count(), total_objects_before)

    @covers_requirement(
        "player-character-creation::an-account-owns-up-to-a-configured-number-of-independently-created-characters"
    )
    def test_activation_is_per_character(self):
        account = create.create_account(
            "MultiCharAcct3",
            email="mc3@example.com",
            password="testpassword",
            typeclass=self.account_typeclass,
            permissions=["Player"],
        )
        char1, _ = account.create_character(key="Pending1")
        char2, _ = account.create_character(key="Pending2")
        self.assertTrue(char1.creation_pending)
        self.assertTrue(char2.creation_pending)

        activate_player_character(
            account,
            char1,
            CharacterCreationRequest(mode="preset", preset_key="human_wanderer"),
        )
        self.assertFalse(char1.creation_pending)
        self.assertTrue(char2.creation_pending)

    @covers_requirement(
        "player-character-creation::an-account-owns-up-to-a-configured-number-of-independently-created-characters"
    )
    def test_capacity_knob_overridable(self):
        with override_settings(MAX_NR_CHARACTERS=2):
            account = create.create_account(
                "MultiCharAcct4",
                email="mc4@example.com",
                password="testpassword",
                typeclass=self.account_typeclass,
                permissions=["Player"],
            )
            char1, errs1 = account.create_character(key="Hero1")
            self.assertIsNotNone(char1)
            char2, errs2 = account.create_character(key="Hero2")
            self.assertIsNotNone(char2)

            char3, errs3 = account.create_character(key="Hero3")
            self.assertIsNone(char3)
            self.assertTrue(errs3)
            self.assertIn("You may only have a maximum of 2 characters.", errs3[0])

    @covers_requirement(
        "player-character-creation::an-account-owns-up-to-a-configured-number-of-independently-created-characters"
    )
    def test_registration_shell_plus_creations_reaches_capacity(self):
        """A registered account has 1 auto-created shell, so 4 more creations fill the cap of 5."""
        account = create.create_account(
            "RegAccount",
            email="reg@example.com",
            password="testpassword",
            typeclass=self.account_typeclass,
            permissions=["Player"],
        )
        first_shell, errs0 = account.create_character(key=account.key)
        self.assertIsNotNone(first_shell)
        self.assertFalse(errs0)
        self.assertEqual(len(account.characters), 1)

        for i in range(1, 5):
            char, errs = account.create_character(key=f"Sibling_{i}")
            self.assertIsNotNone(char)
            self.assertFalse(errs)

        self.assertEqual(len(account.characters), 5)

        total_objects_before = PlayerCharacter.objects.count()
        char_extra, errs = account.create_character(key="Sibling_Overflow")
        self.assertIsNone(char_extra)
        self.assertTrue(errs)
        self.assertIn("You may only have a maximum of 5 characters.", errs[0])
        self.assertEqual(len(account.characters), 5)
        self.assertEqual(PlayerCharacter.objects.count(), total_objects_before)

    @covers_requirement("game-command-docs::accurate-command-details")
    def test_developer_can_charcreate_and_player_is_refused(self):
        """Developer can charcreate and switch, Player is refused by lock."""
        from commands.default_cmdsets import AccountCmdSet

        account_cmdset = AccountCmdSet()
        charcreate_cmd = account_cmdset.get("charcreate")

        # 1. Player account is refused access to charcreate
        player_account = self.account2
        self.assertFalse(charcreate_cmd.access(player_account, "cmd"))

        # 2. Developer account is granted access to charcreate
        dev_account = self.account
        self.assertTrue(charcreate_cmd.access(dev_account, "cmd"))

        # 3. Developer creates a second shell
        created_char, errs = dev_account.create_character(key="DevSecondHero")
        self.assertIsNotNone(created_char)
        self.assertFalse(errs)
        self.assertIn(created_char, dev_account.characters)

        # 4. Switch between them
        dev_account.puppet_object(self.session, created_char)
        self.assertEqual(dev_account.get_puppet(self.session), created_char)

        dev_account.puppet_object(self.session, self.char1)
        self.assertEqual(dev_account.get_puppet(self.session), self.char1)

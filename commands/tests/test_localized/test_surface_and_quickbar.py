"""Slice of ``test_localized``: LocalizedCommandSurfaceTests, QuickbarLetterPinningTests.
"""
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from django.test import override_settings
from evennia import default_cmds
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from commands.default_cmdsets import AccountCmdSet, CharacterCmdSet
from commands.localized import (
    CmdDrop,
    CmdGet,
    CmdGive,
    CmdGoto,
    CmdHelp,
    CmdHome,
    CmdIC,
    CmdLook,
    CmdMap,
    CmdNick,
    CmdOOC,
    CmdOOCLook,
    CmdOption,
    CmdPage,
    CmdPassword,
    CmdPose,
    CmdQuell,
    CmdQuit,
    CmdSay,
    CmdSessions,
    CmdSetDesc,
    CmdStyle,
    CmdWhisper,
    CmdWho,
    CmdColorTest,
    LOCALIZED_DEFAULT_KEYS,
)
from typeclasses.rooms import InstanceRoom
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire,
    deliver,
    quest,
    register,
)
from world.rules.combat_session import engage
from world.rules.quest_delivery import active_deliveries_for_recipient
from world.rules.tests._combat_session_helpers import _monster
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import make_item, synthetic_registries


class LocalizedCommandSurfaceTests(EvenniaTestCase):
    """The merged player cmdsets never expose a stock localized default."""

    def test_merged_cmdsets_expose_no_stock_localized_defaults(self):
        stock_classes = {
            default_cmds.CmdLook,
            default_cmds.CmdHelp,
            default_cmds.CmdSay,
            default_cmds.CmdPose,
            default_cmds.CmdGet,
            default_cmds.CmdDrop,
            default_cmds.CmdGive,
            default_cmds.CmdHome,
            default_cmds.CmdWhisper,
            default_cmds.CmdNick,
            default_cmds.CmdSetDesc,
            default_cmds.CmdQuit,
            default_cmds.CmdWho,
            default_cmds.CmdOOC,
            default_cmds.CmdIC,
            default_cmds.CmdPage,
            default_cmds.CmdPassword,
            default_cmds.CmdOption,
            default_cmds.CmdSessions,
            default_cmds.CmdColorTest,
            default_cmds.CmdStyle,
            default_cmds.CmdQuell,
        }
        for cmdset in (CharacterCmdSet(), AccountCmdSet()):
            for command in cmdset.commands:
                self.assertNotIn(type(command), stock_classes)

    def test_all_localized_keys_are_mounted(self):
        merged = {c.key for c in CharacterCmdSet().commands}
        merged.update({c.key for c in AccountCmdSet().commands})
        self.assertTrue(LOCALIZED_DEFAULT_KEYS.issubset(merged))


class QuickbarLetterPinningTests(EvenniaTestCase):
    """The webclient quickbar's bound letters are installed command words.

    The draft's chip badges double as keybindings, and the client contract
    requires every badge letter to be a literal command the server accepts on
    every transport (webclient-contextual-hud: quick-word chips + the pinned
    bound-letters requirement). This pins the six letters against the merged
    player cmdsets so the chip table cannot drift from the command surface.
    """

    # letter -> the command key the webclient chip pins it to.
    BOUND_LETTERS = {
        "l": "看",
        "g": "拿",
        "s": "說",
        "t": "talk",
        "w": "wait",
        "c": "cast",
    }

    def _letter_owners(self):
        # ``CmdSet.add`` flattens nested cmdsets (the XYZGrid grid commands
        # ride in via a sub-cmdset) into ``commands`` at mount time, so the
        # top-level cmdsets' ``commands`` cover the full installed surface.
        # Every installed key AND alias is enumerated — that is what makes
        # the collision check robust against an upstream default claiming a
        # letter rather than merely trusting a source audit.
        owners: dict[str, set[str]] = {}
        for cmdset in (CharacterCmdSet(), AccountCmdSet()):
            for command in cmdset.commands:
                for name in [command.key, *command.aliases]:
                    if isinstance(name, str):
                        owners.setdefault(name, set()).add(command.key)
        return owners

    @covers_requirement(
        "webclient-contextual-hud::bound-quickbar-letters-are-pinned-against-the-installed-player-cmdset"
    )
    def test_bound_letters_resolve_to_their_pinned_commands(self):
        owners = self._letter_owners()
        for letter, pinned_key in self.BOUND_LETTERS.items():
            with self.subTest(letter=letter):
                # Exactly one mounted command claims the letter, and it is the
                # pinned one — no collision against any other installed key
                # or alias in either player cmdset.
                self.assertEqual(owners.get(letter), {pinned_key})

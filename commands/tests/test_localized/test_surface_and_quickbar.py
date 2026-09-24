"""Slice of ``test_localized``: LocalizedCommandSurfaceTests.
"""
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

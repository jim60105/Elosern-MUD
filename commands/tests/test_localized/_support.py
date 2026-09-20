"""File-local kit item keys for the ``test_localized`` slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
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


# Kit item keys used as opaque registry keys in the inventory/give paths: the
# localized commands move whatever key the caller carries, so invented rows
# exercise the same seams as the shipped catalogue.
_POTION = "t_ember_spray"


_FLASK = "t_huskapple"


# The kit slotted weapon row for the equipped-item refusal.
_BLADE = "t_thorn_knife"


# A kit consumable row carried through the containment/key-list sync seams.
_MEAL = make_item("t_packed_meal")


_MEAL_KEY = _MEAL.key



"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds

from commands.action import CmdCast
from commands.art import CmdArtRequeue, CmdArtRetry, CmdArtRun, CmdArtStatus
from commands.combat import (
    CmdCombatActions,
    CmdCombatForfeit,
    CmdEngage,
    CmdGuildExam,
)
from commands.economy import CmdBuy, CmdInventory, CmdSell, CmdShopStock
from commands.guild import (
    CmdGuildAbandon,
    CmdGuildAccept,
    CmdGuildList,
    CmdGuildLog,
    CmdGuildMerit,
    CmdGuildRegister,
    CmdGuildRequest,
    CmdGuildShow,
    CmdGuildTurnIn,
)
from commands.invite import CmdInvite
from commands.leave import CmdLeave
from commands.lore import CmdLore
from commands.localized import (
    CmdColorTest,
    CmdDrop,
    CmdGet,
    CmdGive,
    CmdHelp,
    CmdHome,
    CmdIC,
    CmdLook,
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
    ProjectXYZGridCmdSet,
)
from commands.scene import CmdEnterScene
from commands.skip import CmdRest, CmdSleep, CmdWaitUntil
from commands.talk import CmdsTalk

# The stock Evennia default keys replaced by the localized zh-tw wrappers
# (commands/localized/). After ``super().at_cmdset_creation()`` the originals
# are removed so no English-keyed variant ever matches in normal play.
_LOCALIZED_ORIGINALS = (
    "look",
    "help",
    "say",
    "pose",
    "get",
    "drop",
    "give",
    "home",
    "whisper",
    "nick",
    "setdesc",
    "quit",
    "who",
    "ooc",
    "ic",
    "page",
    "password",
    "option",
    "sessions",
    "color",
    "style",
    "quell",
)

_LOCALIZED_CHARACTER_WRAPPERS = (
    CmdLook,
    CmdHelp,
    CmdSay,
    CmdPose,
    CmdGet,
    CmdDrop,
    CmdGive,
    CmdHome,
    CmdWhisper,
    CmdNick,
    CmdSetDesc,
)

_LOCALIZED_ACCOUNT_WRAPPERS = (
    CmdOOCLook,
    CmdHelp,
    CmdQuit,
    CmdWho,
    CmdOOC,
    CmdIC,
    CmdPage,
    CmdPassword,
    CmdOption,
    CmdSessions,
    CmdColorTest,
    CmdStyle,
    CmdQuell,
    CmdNick,
)


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        for key in _LOCALIZED_ORIGINALS:
            self.remove(key)
        for wrapper in _LOCALIZED_CHARACTER_WRAPPERS:
            self.add(wrapper)
        self.add(CmdCast)
        self.add(CmdArtStatus)
        self.add(CmdArtRun)
        self.add(CmdArtRetry)
        self.add(CmdArtRequeue)
        self.add(CmdRest)
        self.add(CmdSleep)
        self.add(CmdWaitUntil)
        self.add(CmdEngage)
        self.add(CmdCombatForfeit)
        self.add(CmdCombatActions)
        self.add(CmdGuildExam)
        self.add(CmdGuildRegister)
        self.add(CmdGuildList)
        self.add(CmdGuildAccept)
        self.add(CmdGuildLog)
        self.add(CmdGuildShow)
        self.add(CmdGuildAbandon)
        self.add(CmdGuildTurnIn)
        self.add(CmdGuildMerit)
        self.add(CmdGuildRequest)
        self.add(CmdEnterScene)
        self.add(CmdShopStock)
        self.add(CmdBuy)
        self.add(CmdSell)
        self.add(CmdInventory)
        self.add(CmdsTalk)
        self.add(CmdInvite)
        self.add(CmdLeave)
        self.add(CmdLore)
        self.add(ProjectXYZGridCmdSet)


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        for key in _LOCALIZED_ORIGINALS:
            self.remove(key)
        for wrapper in _LOCALIZED_ACCOUNT_WRAPPERS:
            self.add(wrapper)


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #

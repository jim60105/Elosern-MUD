"""Localized zh-tw wrappers of Evennia's default commands (localize-limbo-zhtw).

Every class here replaces one stock Evennia default in the merged player
cmdsets; the stock commands are removed from ``commands/default_cmdsets.py``.
``LOCALIZED_DEFAULT_KEYS`` is the canonical key set used by the cmdsets and by
the command-docs contract test.
"""

from .account import (
    CmdColorTest,
    CmdIC,
    CmdOOC,
    CmdOOCLook,
    CmdOption,
    CmdPage,
    CmdPassword,
    CmdQuell,
    CmdQuit,
    CmdSessions,
    CmdStyle,
    CmdWho,
)
from .general import (
    CmdDrop,
    CmdGet,
    CmdGive,
    CmdHome,
    CmdLook,
    CmdNick,
    CmdPose,
    CmdSay,
    CmdSetDesc,
    CmdWhisper,
)
from .help import CmdHelp
from .xyzgrid import CmdGoto, CmdMap, ProjectXYZGridCmdSet

__all__ = [
    "CmdColorTest",
    "CmdDrop",
    "CmdGet",
    "CmdGive",
    "CmdGoto",
    "CmdHelp",
    "CmdHome",
    "CmdIC",
    "CmdLook",
    "CmdMap",
    "CmdNick",
    "CmdOOC",
    "CmdOOCLook",
    "CmdOption",
    "CmdPage",
    "CmdPassword",
    "CmdPose",
    "CmdQuell",
    "CmdQuit",
    "CmdSay",
    "CmdSessions",
    "CmdSetDesc",
    "CmdStyle",
    "CmdWhisper",
    "CmdWho",
    "ProjectXYZGridCmdSet",
    "LOCALIZED_DEFAULT_KEYS",
]

# The zh-tw primary keys of every localized default command, grouped by the
# cmdset that mounts them. The keys are the contract for the reference docs
# and for the removal step in commands/default_cmdsets.py.
LOCALIZED_CHARACTER_KEYS = (
    "看",
    "說明",
    "說",
    "動作",
    "拿",
    "丟",
    "給",
    "回家",
    "耳語",
    "暱稱",
    "設定描述",
)
LOCALIZED_ACCOUNT_KEYS = (
    "看",
    "說明",
    "登出",
    "在線",
    "離開角色",
    "進入世界",
    "傳訊",
    "密碼",
    "選項",
    "連線",
    "色彩",
    "樣式",
    "降權",
)
LOCALIZED_XYZGRID_KEYS = ("地圖", "前往")

LOCALIZED_DEFAULT_KEYS = frozenset(
    LOCALIZED_CHARACTER_KEYS + LOCALIZED_ACCOUNT_KEYS + LOCALIZED_XYZGRID_KEYS
)

# The English original keys replaced by the wrappers (commands/localized/
# general.py and account.py mount them by these keys in the merged cmdsets).
LOCALIZED_ORIGINAL_KEYS = frozenset(
    (
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
)

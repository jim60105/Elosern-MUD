"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
    {
        "key": "新手引導",
        "aliases": ["onboarding", "新手指引"],
        "category": "General",
        "text": """
            你從南門踏入聖潔王都時，城門的守衛會向你說明下一步。

            # 抵達

            初來乍到時，先用 look 看看四周。守衛會引導你沿南大道往北，
            穿過中央廣場，抵達冒險者公會。

            # 守衛

            你可以用 talk 與守衛交談，並詢問關鍵字（公會、冒險、危險、再見）
            取得他對王都與冒險的解說。

            # 第一天

            到冒險者公會註冊成為冒險者（guild register），
            從任務板接取討伐低階魔物，前往北門外的荒野討伐目標，
            然後回到公會回報（guild turnin），完成你的第一天。

        """,
    },
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "locks": "read:perm(Developer)",
        "text": """
            Evennia is a MU-game server and framework written in Python. You can read more
            on https://www.evennia.com.

            # subtopics

            ## Installation

            You'll find installation instructions on https://www.evennia.com.

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discussions

            The Discussions forum is found at https://github.com/evennia/evennia/discussions.

            ### Discord

            There is also a discord channel for chatting - connect using the
            following link: https://discord.gg/AJJpcRUhtF

        """,
    },
]

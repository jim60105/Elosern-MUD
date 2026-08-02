# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

CONNECTION_SCREEN = """
|b==============================================================|n
        |g伊洛瑟恩大陸|n —— 一個等待英雄的廣闊世界。

 如果你已有帳號，請輸入：
     |wconnect <帳號> <密碼>|n
 如果你是新玩家，請輸入：
     |wcreate <帳號> <密碼>|n

 新帳號必須建立一個成年角色，才能踏入這個世界。
 登入後使用 |wcharacter|n 選擇預設角色或開始自訂角色。

 若帳號名稱包含空格，請用引號括起來。
 輸入 |whelp|n 取得更多資訊，|wlook|n 重新顯示此畫面。
|b==============================================================|n"""

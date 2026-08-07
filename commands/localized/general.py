"""Localized zh-tw wrappers of Evennia's default character commands
(localize-limbo-zhtw D-5).

Every wrapper keeps the upstream class's full alias set and locks, carries a
zh-tw help docstring, and ports the command body with zh-tw output. Bodies
branch on ``self.cmdstring`` (not the key) where an alias has different
upstream semantics. No stock English command remains reachable: the merged
player cmdsets remove the originals (commands/default_cmdsets.py).
"""

from evennia.commands.default.general import (
    CmdDrop as _CmdDrop,
    CmdGet as _CmdGet,
    CmdGive as _CmdGive,
    CmdHome as _CmdHome,
    CmdLook as _CmdLook,
    CmdNick as _CmdNick,
    CmdPose as _CmdPose,
    CmdSay as _CmdSay,
    CmdSetDesc as _CmdSetDesc,
    CmdWhisper as _CmdWhisper,
)
from evennia.commands.default.general import NumberedTargetCommand as _NumberedTargetCommand
from evennia.typeclasses.attributes import NickTemplateInvalid
from evennia.utils import utils


class NumberedTargetCommand(_NumberedTargetCommand):
    """Numbered-target parse that also accepts the zh-tw classifier 「個」.

    The appearance layer displays a group as ``{count} 個 {name}``; this parse
    strips a leading 「個」 after the count so the displayed form is directly
    typeable (``拿 2 個 銅幣`` searches 銅幣 with stacked=2).
    """

    def parse(self):
        super().parse()
        if self.number and self.args.startswith("個"):
            self.args = self.args[1:].lstrip()


class CmdLook(_CmdLook):
    """查看目前位置或對象

    用法：
      看
      看 <對象>
      看 *<帳號>

    觀察你所在的位置，或附近的對象。
    """

    key = "看"
    aliases = ["look", "l", "ls"]

    def func(self):
        """執行查看。"""
        caller = self.caller
        if not self.args:
            target = caller.location
            if not target:
                caller.msg("你沒有可以查看的地方！")
                return
        else:
            target = caller.search(self.args)
            if not target:
                return
        desc = caller.at_look(target)
        # 與上游相同：以 type=look 的 outputfunc 輸出，方便客戶端區分。
        self.msg(text=(desc, {"type": "look"}), options=None)


class CmdSay(_CmdSay):
    """以角色身分說話

    用法：
      說 <訊息>

    對目前位置的人說話。
    """

    key = "說"
    aliases = ["say", '"', "'"]
    arg_regex = None

    def func(self):
        """執行說話。"""
        caller = self.caller
        if not self.args:
            caller.msg("要說什麼？")
            return
        speech = self.args
        speech = caller.at_pre_say(speech)
        if not speech:
            return
        caller.at_say(speech, msg_self=True)


class CmdPose(_CmdPose):
    """做一個動作

    用法：
      動作 <動作描述>
      動作的 <動作描述>

    範例：
      動作 靠著牆壁微笑。
      -> 其他人會看到：
      湯姆靠著牆壁微笑。

    描述一個正在進行的動作；動作描述會自動以你的名字開頭。
    """

    key = "動作"
    aliases = ["pose", ":", "emote"]
    arg_regex = None

    def parse(self):
        args = self.args
        if args and not args[0] in ["'", ",", ":"]:
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        if not self.args:
            self.msg("你想做什麼？")
        else:
            msg = f"{self.caller.name}{self.args}"
            self.caller.location.msg_contents(
                text=(msg, {"type": "pose"}), from_obj=self.caller
            )


class CmdGet(_CmdGet, NumberedTargetCommand):
    """撿起物品

    用法：
      拿 <物品>

    從你所在的位置撿起一個物品，放進背包。
    """

    key = "拿"
    aliases = ["get", "grab"]

    def func(self):
        """執行撿取。"""
        caller = self.caller
        if not self.args:
            self.msg("要拿什麼？")
            return
        objs = caller.search(self.args, location=caller.location, stacked=self.number)
        if not objs:
            return
        objs = utils.make_iter(objs)

        if len(objs) == 1 and caller == objs[0]:
            self.msg("你不能拿自己。")
            return

        for obj in objs:
            if not obj.access(caller, "get"):
                if obj.db.get_err_msg:
                    self.msg(obj.db.get_err_msg)
                else:
                    self.msg("你不能拿那個。")
                return
            if not obj.at_pre_get(caller):
                return

        moved = []
        for obj in objs:
            if obj.move_to(caller, quiet=True, move_type="get"):
                moved.append(obj)
                obj.at_get(caller)

        if not moved:
            self.msg("那個撿不起來。")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.msg(f"你撿起了{obj_name}。")
            caller.location.msg_contents(
                f"{caller.key} 撿起了{obj_name}。", exclude=[caller]
            )


class CmdDrop(_CmdDrop, NumberedTargetCommand):
    """丟下物品

    用法：
      丟 <物品>

    把背包中的一個物品丟到你目前所在的位置。
    """

    key = "丟"
    aliases = ["drop"]

    def func(self):
        """執行丟棄。"""
        caller = self.caller
        if not self.args:
            caller.msg("要丟什麼？")
            return

        objs = caller.search(
            self.args,
            location=caller,
            nofound_string=f"你沒有帶著 {self.args}。",
            multimatch_string=f"你帶著不只一個 {self.args}：",
            stacked=self.number,
        )
        if not objs:
            return
        objs = utils.make_iter(objs)

        for obj in objs:
            if not obj.at_pre_drop(caller):
                return

        moved = []
        for obj in objs:
            if obj.move_to(caller.location, quiet=True, move_type="drop"):
                moved.append(obj)
                obj.at_drop(caller)

        if not moved:
            self.msg("那個丟不掉。")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.msg(f"你丟下了{obj_name}。")
            caller.location.msg_contents(
                f"{caller.key} 丟下了{obj_name}。", exclude=[caller]
            )


class CmdGive(_CmdGive, NumberedTargetCommand):
    """把物品交給別人

    用法：
      給 <背包中的物品> = <目標>

    把你背包中的物品交給另一個人，放進對方的背包。
    """

    key = "給"
    aliases = ["give"]
    rhs_split = ("=", " to ")

    def func(self):
        """執行交付。"""
        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("用法：給 <背包中的物品> = <目標>")
            return
        to_give = caller.search(
            self.lhs,
            location=caller,
            nofound_string=f"你沒有帶著 {self.lhs}。",
            multimatch_string=f"你帶著不只一個 {self.lhs}：",
            stacked=self.number,
        )
        if not to_give:
            return
        target = caller.search(self.rhs)
        if not target:
            return

        to_give = utils.make_iter(to_give)

        singular, plural = to_give[0].get_numbered_name(len(to_give), caller)
        if target == caller:
            caller.msg(f"你把{plural if len(to_give) > 1 else singular}留給了自己。")
            return

        for obj in to_give:
            if not obj.at_pre_give(caller, target):
                return

        moved = []
        for obj in to_give:
            if obj.move_to(target, quiet=True, move_type="give"):
                moved.append(obj)
                obj.at_give(caller, target)

        if not moved:
            caller.msg(
                f"你無法把物品交給 {target.get_display_name(caller)}。"
            )
        else:
            obj_name = to_give[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.msg(f"你把{obj_name}交給了 {target.get_display_name(caller)}。")
            target.msg(f"{caller.get_display_name(target)} 把{obj_name}交給了你。")


class CmdHome(_CmdHome):
    """回到角色的重生點

    用法：
      回家

    將你傳送回重生點。
    """

    key = "回家"
    aliases = ["home"]
    arg_regex = r"$"

    def func(self):
        """執行回家。"""
        caller = self.caller
        home = caller.home
        if not home:
            caller.msg("你沒有家！")
        elif home == caller.location:
            caller.msg("你已經在家了！")
        else:
            caller.msg("還是家最溫暖……")
            caller.move_to(home, move_type="teleport")


class CmdWhisper(_CmdWhisper):
    """對另一個人悄聲說話

    用法：
      耳語 <角色> = <訊息>
      耳語 <角色一>, <角色二> = <訊息>

    對你目前位置中的一個或多個角色私下說話，房間裡的其他人都不知道。
    """

    key = "耳語"
    aliases = ["whisper"]

    def func(self):
        """執行悄聲說話。"""
        caller = self.caller
        if not self.lhs or not self.rhs:
            caller.msg("用法：耳語 <角色> = <訊息>")
            return

        receivers = [recv.strip() for recv in self.lhs.split(",")]
        receivers = [caller.search(receiver) for receiver in set(receivers)]
        receivers = [recv for recv in receivers if recv]

        speech = self.rhs
        if not speech or not receivers:
            return

        speech = caller.at_pre_say(speech, whisper=True, receivers=receivers)
        msg_self = None if caller in receivers else True
        caller.at_say(speech, msg_self=msg_self, receivers=receivers, whisper=True)


class CmdNick(_CmdNick):
    """建立個人暱稱

    用法：
      暱稱[/切換] <字串> = [<替換字串>]
      暱稱/delete <字串> 或 <編號>
      暱稱/list（等同 nicks）

    切換：
      inputline - 替換輸入行（預設）
      object    - 替換對象搜尋
      account   - 替換帳號搜尋
      list      - 顯示所有已定義的暱稱（也可以用 nicks）
      delete    - 依 /list 的編號刪除暱稱
      clearall  - 清除所有暱稱

    範例：
      暱稱 hi = 說 你好，我是莎拉！
      暱稱/object tom = 那個高個子男人
      暱稱 tm?$1 = page tallman=$1

    個人暱稱是只在你自己輸入時生效的字串替換。此指令不會更改任何物件。
    """

    key = "暱稱"
    aliases = ["nick", "nickname", "nicks"]

    def func(self):
        """執行暱稱管理（上游邏輯，zh-tw 訊息）。"""
        caller = self.caller
        account = caller.account
        nicktypes = []
        specified_nicktype = False

        if "object" in self.switches:
            nicktypes.append("object")
            specified_nicktype = True
        if "account" in self.switches:
            nicktypes.append("account")
            specified_nicktype = True
        if "inputline" in self.switches:
            nicktypes.append("inputline")
            specified_nicktype = True
        if "list" in self.switches or self.cmdstring == "nicks":
            nicktypes.append("object")
            nicktypes.append("inputline")
            nicktypes.append("account")
            specified_nicktype = True

        if not nicktypes:
            # 與上游相同：未指定切換時只操作 inputline 暱稱。
            nicktypes = ["inputline"]

        if "clearall" in self.switches:
            for nicktype in nicktypes:
                if nicktype == "account":
                    caller.account.nicks.clear(category=nicktype)
                else:
                    caller.nicks.clear(category=nicktype)
            self.msg("已清除所有暱稱。")
            return

        if "delete" in self.switches:
            nicklist = []
            for nicktype in nicktypes:
                if nicktype == "account":
                    obj = account
                else:
                    obj = caller
                nicks = obj.nicks.get(category=nicktype, return_obj=True)
                if isinstance(nicks, list):
                    nicklist.extend(nicks)
                elif nicks:
                    nicklist.append(nicks)
            if not self.args:
                self.msg("用法：暱稱/delete <暱稱> 或 <編號>（輸入 nicks 查看清單）")
                return
            self.args = self.args.lstrip("#")
            oldnicks = []
            if self.args.isdigit():
                delindex = int(self.args)
                if 0 < delindex <= len(nicklist):
                    oldnicks.append(nicklist[delindex - 1])
                else:
                    caller.msg("無效的暱稱編號。請輸入 nicks 查看清單。")
                    return
            else:
                if not specified_nicktype:
                    nicktypes = ("object", "account", "inputline")
                for nicktype in nicktypes:
                    oldnicks.append(
                        caller.nicks.get(self.args, category=nicktype, return_obj=True)
                    )

            oldnicks = [oldnick for oldnick in oldnicks if oldnick]
            if oldnicks:
                for oldnick in oldnicks:
                    nicktype = oldnick.category
                    nicktypestr = "%s-nick" % nicktype.capitalize()
                    _, _, old_nickstring, old_replstring = oldnick.value
                    caller.nicks.remove(old_nickstring, category=nicktype)
                    caller.msg(
                        f"{nicktypestr} 已移除：'|w{old_nickstring}|n' -> |w{old_replstring}|n。"
                    )
            else:
                caller.msg("沒有符合的暱稱可以移除。")
            return

        if not self.rhs and self.lhs:
            strings = []
            if not specified_nicktype:
                nicktypes = ("object", "account", "inputline")
            for nicktype in nicktypes:
                obj = account if nicktype == "account" else caller
                nicks = [
                    nick
                    for nick in utils.make_iter(obj.nicks.get(category=nicktype, return_obj=True))
                    if nick
                ]
                for nick in nicks:
                    _, _, nick, repl = nick.value
                    if nick.startswith(self.lhs):
                        strings.append(f"{nicktype.capitalize()}-nick: '{nick}' -> '{repl}'")
            if strings:
                caller.msg("\n".join(strings))
            else:
                caller.msg(f"找不到以 '{self.lhs}' 開頭的暱稱。")
            return

        if not self.args or not self.lhs:
            caller.msg("用法：暱稱[/切換] 暱稱 = [真實字串]")
            return

        nickstring = self.lhs
        replstring = self.rhs

        if replstring == nickstring:
            caller.msg("把暱稱設成和要替換的字串一樣沒有意義……")
            return

        errstring = ""
        string = ""
        for nicktype in nicktypes:
            nicktypestr = f"{nicktype.capitalize()}-nick"
            old_nickstring = None
            old_replstring = None

            oldnick = caller.nicks.get(key=nickstring, category=nicktype, return_obj=True)
            if oldnick:
                _, _, old_nickstring, old_replstring = oldnick.value
            if replstring:
                errstring = ""
                if oldnick:
                    if replstring == old_replstring:
                        string += f"\n已經設有一模一樣的 {nicktypestr.lower()}。"
                    else:
                        string += (
                            f"\n{nicktypestr} '|w{old_nickstring}|n' 已更新為"
                            f" 對應 '|w{replstring}|n'。"
                        )
                else:
                    string += f"\n{nicktypestr} '|w{nickstring}|n' 對應到 '|w{replstring}|n'。"
                try:
                    caller.nicks.add(nickstring, replstring, category=nicktype)
                except NickTemplateInvalid:
                    caller.msg(
                        "暱稱與替換字串中必須使用相同的 $-標記。"
                    )
                    return
            elif old_nickstring and old_replstring:
                string += f"\n{nicktypestr} '|w{old_nickstring}|n' 對應到 '|w{old_replstring}|n'。"
                errstring = ""
        string = errstring if errstring else string
        caller.msg(string)


class CmdSetDesc(_CmdSetDesc):
    """設定你自己的描述

    用法：
      設定描述 <描述>

    為自己加上一段描述；別人查看你時會看到它。
    """

    key = "設定描述"
    aliases = ["setdesc"]
    arg_regex = r"\s|$"

    def func(self):
        """設定描述。"""
        if not self.args:
            self.msg("你必須加上一段描述。")
            return
        self.caller.db.desc = self.args.strip()
        self.msg("你已設定你的描述。")

"""Localized zh-tw wrappers of Evennia's default account commands
(localize-limbo-zhtw D-5).

Same rules as ``commands/localized/general.py``: full alias sets and locks
retained, zh-tw docstrings, zh-tw output, ``cmdstring``-based branching where
an alias has distinct upstream semantics (e.g. ``doing``).
"""

import time
from codecs import lookup as codecs_lookup

from django.conf import settings

import evennia
from evennia.commands.default.account import (
    CmdColorTest as _CmdColorTest,
    CmdIC as _CmdIC,
    CmdOOC as _CmdOOC,
    CmdOOCLook as _CmdOOCLook,
    CmdOption as _CmdOption,
    CmdPassword as _CmdPassword,
    CmdQuell as _CmdQuell,
    CmdQuit as _CmdQuit,
    CmdSessions as _CmdSessions,
    CmdStyle as _CmdStyle,
    CmdWho as _CmdWho,
    MuxAccountLookCommand,
)
from evennia.commands.default.comms import CmdPage as _CmdPage
from evennia.utils import create, search, utils

class CmdOOCLook(_CmdOOCLook):
    """在離開角色（OOC）狀態下查看

    用法：
      看

    在 OOC 狀態下查看。
    """

    key = "看"
    aliases = ["look", "l", "ls"]
    help_category = "General"

    def func(self):
        """執行 OOC 查看。"""
        if self.session.puppet:
            self.msg("你目前沒有能力查看四周。")
            return

        self.msg(self.account.at_look(target=self.playable, session=self.session))


class CmdIC(_CmdIC):
    """進入遊戲世界（附身角色）

    用法：
      進入世界 <角色>

    進入角色（IC）狀態，附身為指定的角色。未指定角色時，回到上次附身的角色。
    """

    key = "進入世界"
    aliases = ["ic", "puppet"]
    help_category = "General"

    def func(self):
        """執行附身。"""
        account = self.account
        session = self.session

        new_character = None
        character_candidates = []

        if not self.args:
            character_candidates = [account.db._last_puppet] if account.db._last_puppet else []
            if not character_candidates:
                self.msg("用法：進入世界 <角色>")
                return
        else:
            if playables := account.characters:
                character_candidates.extend(
                    utils.make_iter(
                        account.search(
                            self.args,
                            candidates=playables,
                            search_object=True,
                            quiet=True,
                        )
                    )
                )

            if account.locks.check_lockstring(account, "perm(Builder)"):
                if session.puppet:
                    character_candidates = [
                        char
                        for char in session.puppet.search(self.args, quiet=True)
                        if char.access(account, "puppet")
                    ]
                if not character_candidates:
                    character_candidates.extend(
                        [
                            char
                            for char in search.object_search(self.args)
                            if char.access(account, "puppet")
                        ]
                    )

        if not character_candidates:
            self.msg("那不是一個有效的角色。")
            return
        if len(character_candidates) > 1:
            self.msg(
                "多個同名目標：\n %s"
                % ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in character_candidates)
            )
            return
        else:
            new_character = character_candidates[0]

        try:
            account.puppet_object(session, new_character)
            account.db._last_puppet = new_character
        except RuntimeError as exc:
            self.msg(f"|r你無法附身 |C{new_character.name}|n：{exc}")


class CmdOOC(_CmdOOC):
    """停止附身，離開角色（OOC）

    用法：
      離開角色

    離開你目前的角色，進入無形體的 OOC 狀態。
    """

    key = "離開角色"
    aliases = ["ooc", "unpuppet"]
    help_category = "General"

    def func(self):
        """執行離開角色。"""
        account = self.account
        session = self.session

        old_char = account.get_puppet(session)
        if not old_char:
            self.msg("你已經在 OOC 狀態了。")
            return

        account.db._last_puppet = old_char

        try:
            account.unpuppet_object(session)
            # WebClient: tell the browser to clear character panels and lock
            # mutations, then retire the presentation/dispatch sequence so any
            # puppet (even the same character) starts a fresh epoch and
            # request cache.
            from web.webclient.presentation.ingress import (
                reset_client_sequence,
                send_unpuppet_transition,
            )

            send_unpuppet_transition(session)
            from web.webclient.actions.dispatcher import retire_sequence

            retire_sequence(session)
            reset_client_sequence(session)
            self.msg("\n|G你已離開角色（OOC）。|n\n")

            self.msg(account.at_look(target=self.playable, session=session))

        except RuntimeError as exc:
            self.msg(f"|r無法離開角色 |c{old_char}|n：{exc}")


class CmdSessions(_CmdSessions):
    """查看你目前的連線

    用法：
      連線

    列出目前連接到你帳號的所有連線。
    """

    key = "連線"
    aliases = ["sessions"]
    help_category = "General"

    def func(self):
        """執行連線列表。"""
        account = self.account
        sessions = account.sessions.all()
        table = self.styled_table(
            "|w連線編號", "|w協定", "|w主機", "|w附身角色", "|w位置"
        )
        for sess in sorted(sessions, key=lambda x: x.sessid):
            char = account.get_puppet(sess)
            table.add_row(
                str(sess.sessid),
                str(sess.protocol_key),
                isinstance(sess.address, tuple) and sess.address[0] or sess.address,
                char and str(char) or "無",
                char and str(char.location) or "—",
            )
        self.msg(f"|w你目前的連線：|n\n{table}")


class CmdWho(_CmdWho):
    """列出目前在線的玩家

    用法：
      在線
      doing

    顯示目前在線的玩家。doing 是別名，會對所有人隱藏進階資訊。
    """

    key = "在線"
    aliases = ["who", "doing"]

    def func(self):
        """執行在線列表。"""
        account = self.account
        session_list = evennia.SESSION_HANDLER.get_sessions()

        session_list = sorted(session_list, key=lambda o: o.account.key)

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = account.check_permstring("Developer") or account.check_permstring(
                "Admins"
            )

        naccounts = evennia.SESSION_HANDLER.account_count()
        if show_session_data:
            table = self.styled_table(
                "|w帳號名稱",
                "|w在線時間",
                "|w閒置",
                "|w附身角色",
                "|w位置",
                "|w指令數",
                "|w協定",
                "|w主機",
            )
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                session_account = session.get_account()
                puppet = session.get_puppet()
                location = puppet.location.key if puppet and puppet.location else "無"
                table.add_row(
                    utils.crop(session_account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                    utils.crop(puppet.get_display_name(account) if puppet else "無", width=25),
                    utils.crop(location, width=25),
                    session.cmd_total,
                    session.protocol_key,
                    isinstance(session.address, tuple) and session.address[0] or session.address,
                )
        else:
            table = self.styled_table("|w帳號名稱", "|w在線時間", "|w閒置")
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                session_account = session.get_account()
                table.add_row(
                    utils.crop(session_account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                )
        self.msg(
            "|w在線帳號：|n\n%s\n共 %s 個帳號在線。"
            % (table, naccounts)
        )


class CmdOption(_CmdOption):
    """設定帳號選項

    用法：
      選項[/save] [名稱 = 數值]

    切換：
      save - 儲存目前的選項設定，供日後登入使用。
      clear - 清除已儲存的選項。

    查看與設定客戶端介面設定。
    """

    key = "選項"
    aliases = ["option", "options"]
    switch_options = ("save", "clear")

    def func(self):
        """執行選項設定（上游邏輯，zh-tw 訊息）。"""
        if self.session is None:
            return

        flags = self.session.protocol_flags

        if not self.args:
            if "save" in self.switches:
                self.caller.db._saved_protocol_flags = flags
                self.msg("|g已儲存所有選項。使用 選項/clear 移除。|n")
            if "clear" in self.switches:
                self.caller.db._saved_protocol_flags = {}
                self.msg("|g已清除所有已儲存的選項。")

            options = dict(flags)
            saved_options = dict(self.caller.attributes.get("_saved_protocol_flags", default={}))

            if "SCREENWIDTH" in options:
                if len(options["SCREENWIDTH"]) == 1:
                    options["SCREENWIDTH"] = options["SCREENWIDTH"][0]
                else:
                    options["SCREENWIDTH"] = "  \n".join(
                        "%s : %s" % (screenid, size)
                        for screenid, size in options["SCREENWIDTH"].items()
                    )
            if "SCREENHEIGHT" in options:
                if len(options["SCREENHEIGHT"]) == 1:
                    options["SCREENHEIGHT"] = options["SCREENHEIGHT"][0]
                else:
                    options["SCREENHEIGHT"] = "  \n".join(
                        "%s : %s" % (screenid, size)
                        for screenid, size in options["SCREENHEIGHT"].items()
                    )
            options.pop("TTYPE", None)

            header = ("名稱", "數值", "已儲存") if saved_options else ("名稱", "數值")
            table = self.styled_table(*header)
            for key in sorted(options):
                row = [key, options[key]]
                if saved_options:
                    saved = " |Y是|n" if key in saved_options else ""
                    changed = (
                        "|y*|n" if key in saved_options and flags[key] != saved_options[key] else ""
                    )
                    row.append("%s%s" % (saved, changed))
                table.add_row(*row)
            self.msg(f"|w客戶端設定（{self.session.protocol_key}）：|n\n{table}|n")
            return

        if not self.rhs:
            self.msg("用法：選項 [名稱 = [數值]]")
            return

        def validate_encoding(new_encoding):
            try:
                codecs_lookup(new_encoding)
            except LookupError:
                raise RuntimeError(f"編碼 '|w{new_encoding}|n' 無效。")
            return val

        def validate_size(new_size):
            return {0: int(new_size)}

        def validate_bool(new_bool):
            return True if new_bool.lower() in ("true", "on", "1") else False

        def update(new_name, new_val, validator):
            try:
                old_val = flags.get(new_name, False)
                new_val = validator(new_val)
                if old_val == new_val:
                    self.msg(f"選項 |w{new_name}|n 保持為 '|w{old_val}|n'。")
                else:
                    flags[new_name] = new_val
                    if new_name in ["SCREENWIDTH", "SCREENHEIGHT"]:
                        flags["AUTORESIZE"] = False
                    self.msg(
                        f"選項 |w{new_name}|n 已從 '|w{old_val}|n' 改為 '|w{new_val}|n'。"
                    )
                return {new_name: new_val}
            except Exception as err:
                self.msg(f"|r無法設定選項 |w{new_name}|r：|n {err}")
                return False

        validators = {
            "ANSI": validate_bool,
            "CLIENTNAME": utils.to_str,
            "ENCODING": validate_encoding,
            "MCCP": validate_bool,
            "NOGOAHEAD": validate_bool,
            "NOPROMPTGOAHEAD": validate_bool,
            "MXP": validate_bool,
            "NOCOLOR": validate_bool,
            "NOPKEEPALIVE": validate_bool,
            "OOB": validate_bool,
            "RAW": validate_bool,
            "SCREENHEIGHT": validate_size,
            "SCREENWIDTH": validate_size,
            "AUTORESIZE": validate_bool,
            "SCREENREADER": validate_bool,
            "TERM": utils.to_str,
            "UTF-8": validate_bool,
            "XTERM256": validate_bool,
            "INPUTDEBUG": validate_bool,
            "FORCEDENDLINE": validate_bool,
            "LOCALECHO": validate_bool,
            "TRUECOLOR": validate_bool,
            "ISTYPING": validate_bool,
        }

        name = self.lhs.upper()
        val = self.rhs.strip()
        optiondict = False
        if val and name in validators:
            optiondict = update(name, val, validators[name])
        else:
            self.msg("|r沒有名為 '|w%s|r' 的選項。" % name)
        if optiondict:
            if "save" in self.switches:
                saved_options = self.account.attributes.get("_saved_protocol_flags", default={})
                saved_options.update(optiondict)
                self.account.attributes.add("_saved_protocol_flags", saved_options)
                for key in optiondict:
                    self.msg(f"|g已儲存選項 {key}。|n")
            if "clear" in self.switches:
                for key in optiondict:
                    self.account.attributes.get("_saved_protocol_flags", {}).pop(key, None)
                    self.msg(f"|g已清除已儲存的 {key}。")
            self.session.update_flags(**optiondict)


class CmdPassword(_CmdPassword):
    """變更你的密碼

    用法：
      密碼 <舊密碼> = <新密碼>

    變更你的密碼。請務必選擇安全的密碼。
    """

    key = "密碼"
    aliases = ["password"]

    def func(self):
        """執行變更密碼。"""
        account = self.account
        if not self.rhs:
            self.msg("用法：密碼 <舊密碼> = <新密碼>")
            return
        oldpass = self.lhslist[0]
        newpass = self.rhslist[0]

        validated, error = account.validate_password(newpass)

        if not account.check_password(oldpass):
            self.msg("舊密碼不正確。")
        elif not validated:
            errors = [e for suberror in error.messages for e in error.messages]
            self.msg("\n".join(errors))
        else:
            account.set_password(newpass)
            account.save()
            self.msg("密碼已變更。")


class CmdQuit(_CmdQuit):
    """登出遊戲

    用法：
      登出

    切換：
      all - 中斷所有已連線的 session

    從遊戲中登出目前的連線。使用 /all 可中斷所有連線。
    """

    key = "登出"
    aliases = ["quit"]
    switch_options = ("all",)

    def func(self):
        """執行登出。"""
        account = self.account

        if "all" in self.switches:
            account.msg(
                "|R登出|n 所有連線。期待很快再見到你。", session=self.session
            )
            reason = "quit/all"
            for session in account.sessions.all():
                account.disconnect_session_from_account(session, reason)
        else:
            nsess = len(account.sessions.all())
            reason = "quit"
            if nsess == 2:
                account.msg("|R登出|n。還有一條連線保持連接。", session=self.session)
            elif nsess > 2:
                account.msg(
                    "|R登出|n。還有 %i 條連線保持連接。" % (nsess - 1),
                    session=self.session,
                )
            else:
                account.msg("|R登出|n。期待很快再見到你。", session=self.session)
            account.disconnect_session_from_account(self.session, reason)


class CmdColorTest(_CmdColorTest):
    """測試你的客戶端支援哪些色彩

    用法：
      色彩 ansi | xterm256 | truecolor

    印出色彩對照表與遊戲內可用的色彩程式碼，並測試你的客戶端支援程度。
    """

    key = "色彩"
    aliases = ["color", "colour"]
    help_category = "General"

    def func(self):
        """執行色彩測試（上游邏輯，zh-tw 說明文字）。"""
        if self.args.startswith("a"):
            from evennia.utils import ansi

            ap = ansi.ANSI_PARSER
            bright_fg = [
                "%s%s|n" % (code, code.replace("|", "||"))
                for code, _ in ap.ansi_map[self.slice_bright_fg]
            ]
            dark_fg = [
                "%s%s|n" % (code, code.replace("|", "||"))
                for code, _ in ap.ansi_map[self.slice_dark_fg]
            ]
            dark_bg = [
                "%s%s|n" % (code.replace("\\", ""), code.replace("|", "||").replace("\\", ""))
                for code, _ in ap.ansi_map[self.slice_dark_bg]
            ]
            bright_bg = [
                "%s%s|n" % (code.replace("\\", ""), code.replace("|", "||").replace("\\", ""))
                for code, _ in ap.ansi_xterm256_bright_bg_map[self.slice_bright_bg]
            ]
            dark_fg.extend(["" for _ in range(len(bright_fg) - len(dark_fg))])
            table = utils.format_table([bright_fg, dark_fg, bright_bg, dark_bg])
            string = "ANSI 色彩："
            for row in table:
                string += "\n " + " ".join(row)
            self.msg(string)
            self.msg(
                "||X : 黑色。||/ : 換行，||- : 定位，||_ : 空格，||* : 反白，||u : 底線\n"
                "要組合背景與前景色，請在最後加上背景標記，例如 ||r||[B。\n"
                "注意：亮色背景（如 ||[r）需要你的客戶端支援 Xterm256 色彩。"
            )
        elif self.args.startswith("x"):
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ir in range(6):
                for ig in range(6):
                    for ib in range(6):
                        table[ir].append("|%i%i%i%s|n" % (ir, ig, ib, "||%i%i%i" % (ir, ig, ib)))
                        table[6 + ir].append(
                            "|%i%i%i|[%i%i%i%s|n"
                            % (5 - ir, 5 - ig, 5 - ib, ir, ig, ib, "||[%i%i%i" % (ir, ig, ib))
                        )
            table = self.table_format(table)
            string = (
                "Xterm256 色彩（如果沒有顯示所有色階，你的客戶端可能不支援 xterm256）："
            )
            string += "\n" + "\n".join("".join(row) for row in table)
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ibatch in range(4):
                for igray in range(6):
                    letter = chr(97 + (ibatch * 6 + igray))
                    inverse = chr(122 - (ibatch * 6 + igray))
                    table[0 + igray].append("|=%s%s |n" % (letter, "||=%s" % letter))
                    table[6 + igray].append("|=%s|[=%s%s |n" % (inverse, letter, "||[=%s" % letter))
            for igray in range(6):
                if igray < 2:
                    letter = chr(121 + igray)
                    inverse = chr(98 - igray)
                    fg = "|=%s%s |n" % (letter, "||=%s" % letter)
                    bg = "|=%s|[=%s%s |n" % (inverse, letter, "||[=%s" % letter)
                else:
                    fg, bg = " ", " "
                table[0 + igray].append(fg)
                table[6 + igray].append(bg)
            table = self.table_format(table)
            string += "\n" + "\n".join("".join(row) for row in table)
            self.msg(string)
        elif self.args.startswith("t"):
            string = (
                "\n"
                "真彩色（如果這不是平滑的彩虹漸層，你的客戶端可能不支援 truecolor）：\n"
            )
            display_width = self.client_width()
            num_colors = display_width * 1
            color_block = [
                f"|[{self.make_hex_color_from_column(i, num_colors)} " for i in range(num_colors)
            ]
            color_block = [
                "".join(color_block[iline : iline + display_width])
                for iline in range(0, num_colors, display_width)
            ]
            string += "\n".join(color_block)
            string += (
                "\n|n前景：|#FF0000||#FF0000|n (|#F00||#F00|n) 到 |#0000FF||#0000FF|n (|#00F||#00F|n)"
                "\n|n背景：|[#FF0000||[#FF0000|n (|[#F00||[#F00|n) 到 |n|[#0000FF||[#0000FF |n(|[#00F||[#00F|n)"
            )
            self.msg(string)
        else:
            self.msg("用法：色彩 ansi || xterm256 || truecolor")


class CmdQuell(_CmdQuell):
    """以角色的權限取代帳號的權限

    用法：
      降權
      取消降權

    通常附身角色時使用帳號的權限層級。此指令會切換為使用角色的權限。
    主要用於測試。使用「取消降權」指令回復正常運作。
    """

    key = "降權"
    aliases = ["quell", "unquell"]
    help_category = "General"

    def _recache_locks(self, account):
        if self.session:
            char = self.session.puppet
            if char:
                char.locks.reset()
        account.locks.reset()

    def func(self):
        """執行降權。"""
        account = self.account
        permstr = (
            account.is_superuser and "(superuser)" or "(%s)" % ", ".join(account.permissions.all())
        )
        if self.cmdstring in ("unquell", "取消降權"):
            if not account.attributes.get("_quell"):
                self.msg(f"目前已經使用正常的帳號權限 {permstr}。")
            else:
                account.attributes.remove("_quell")
                self.msg(f"已回復帳號權限 {permstr}。")
        else:
            if account.attributes.get("_quell"):
                self.msg(f"已經在降權中使用帳號權限 {permstr}。")
                return
            account.attributes.add("_quell", True)
            puppet = self.session.puppet if self.session else None
            if puppet:
                cpermstr = "(%s)" % ", ".join(puppet.permissions.all())
                cpermstr = f"降權為目前角色的權限 {cpermstr}。"
                cpermstr += (
                    f"\n（注意：如果這高於帳號權限 {permstr}，將取兩者中較低者。）"
                )
                cpermstr += "\n使用「取消降權」回復正常權限。"
                self.msg(cpermstr)
            else:
                self.msg(f"降權帳號權限 {permstr}。使用「取消降權」取回。")
        self._recache_locks(account)


class CmdStyle(_CmdStyle):
    """遊戲內樣式選項

    用法：
      樣式
      樣式 <選項> = <數值>

    設定遊戲內顯示元素的樣式（表格邊框、說明文字等）。不帶參數時列出所有選項。
    """

    key = "樣式"
    aliases = ["style"]
    switch_options = ["clear"]

    def func(self):
        if not self.args:
            self.list_styles()
            return
        self.set()

    def list_styles(self):
        table = self.styled_table("選項", "說明", "類型", "數值", width=78)
        for op_key in self.account.options.options_dict.keys():
            op_found = self.account.options.get(op_key, return_obj=True)
            table.add_row(
                op_key, op_found.description, op_found.__class__.__name__, op_found.display()
            )
        self.msg(str(table))

    def set(self):
        try:
            result = self.account.options.set(self.lhs, self.rhs)
        except ValueError as e:
            self.msg(str(e))
            return
        self.msg(f"樣式 {result.key} 已設為 {result.display()}")


class CmdPage(_CmdPage):
    """傳送私人訊息給另一個帳號

    用法：
      傳訊 <帳號> <訊息>
      傳訊[/切換] [<帳號>,<帳號>,... = <訊息>]
      傳訊 <編號>

    切換：
      last - 顯示你最後一次傳訊的對象
      list - 顯示你最近的 <編號> 筆傳訊（預設）

    傳送訊息給在線的目標帳號。多個目標或對象名稱含有空格時需要使用 = 分隔。
    """

    key = "傳訊"
    aliases = ["page", "tell"]
    switch_options = ("last", "list")
    help_category = "Comms"

    def func(self):
        """執行傳訊（上游邏輯，zh-tw 訊息）。"""
        from django.db.models import Q

        from evennia.comms.models import Msg

        caller = self.caller

        pages_we_sent = Msg.objects.get_messages_by_sender(caller).order_by("-db_date_created")
        pages_we_sent = pages_we_sent.filter(
            Q(db_tags__db_key__iexact="page", db_tags__db_category__iexact="comms")
            | Q(db_tags__isnull=True)
        )
        pages_we_sent = [msg for msg in pages_we_sent if msg.access(caller, "read", default=True)]

        pages_we_got = Msg.objects.get_messages_by_receiver(caller).order_by("-db_date_created")
        pages_we_got = pages_we_got.filter(
            Q(db_tags__db_key__iexact="page", db_tags__db_category__iexact="comms")
            | Q(db_tags__isnull=True)
        )
        pages_we_got = [msg for msg in pages_we_got if msg.access(caller, "read", default=True)]

        targets, message, number = [], None, None

        if "last" in self.switches:
            if pages_we_sent:
                recv = ",".join(obj.key for obj in pages_we_sent[0].receivers)
                self.msg(f"你最後傳訊給 |c{recv}|n：{pages_we_sent[0].message}")
                return
            else:
                self.msg("你還沒有傳訊給任何人。")
                return

        if self.args:
            if self.rhs:
                for target in self.lhslist:
                    target_obj = self.caller.search(target)
                    if not target_obj:
                        return
                    targets.append(target_obj)
                message = self.rhs.strip()
            else:
                target, *message = self.args.split(" ", 1)
                if target and target.isnumeric():
                    number = int(target)
                elif message:
                    target_obj = self.caller.search(target, quiet=True)
                    if target_obj:
                        targets = [target_obj[0]]
                        message = message[0].strip()
                    else:
                        message = self.args.strip()
                else:
                    message = self.args.strip()

        pages = list(pages_we_sent) + list(pages_we_got)
        pages = sorted(pages, key=lambda page: page.date_created)

        if message:
            if not targets:
                if pages_we_sent:
                    targets = pages_we_sent[0].receivers
                else:
                    self.msg("要傳訊給誰？")
                    return

            header = f"|w帳號|n |c{caller.key}|n |w傳訊：|n"
            if message.startswith(":"):
                message = f"{caller.key} {message.strip(':').strip()}"

            target_perms = " or ".join([f"id({target.id})" for target in targets + [caller]])
            create.create_message(
                caller,
                message,
                receivers=targets,
                locks=(
                    f"read:{target_perms} or perm(Admin);"
                    f"delete:id({caller.id}) or perm(Admin);"
                    f"edit:id({caller.id}) or perm(Admin)"
                ),
                tags=[("page", "comms")],
            )

            received = []
            rstrings = []
            for target in targets:
                if not target.access(caller, "msg"):
                    rstrings.append(f"你不能傳訊給 {target}。")
                    continue
                target.msg(f"{header} {message}")
                if hasattr(target, "sessions") and not target.sessions.count():
                    received.append(f"|C{target.name}|n")
                    rstrings.append(
                        f"{received[-1]} 目前離線。他之後查看傳訊記錄時會看到這則訊息。"
                    )
                else:
                    received.append(f"|c{target.name}|n")
            if rstrings:
                self.msg("\n".join(rstrings))
            self.msg("你已傳訊給 %s：「%s」。" % (", ".join(received), message))
            return

        else:
            if number is not None and len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages
            to_template = "|w{date}{clr} {sender}|n寄給{clr}{receiver}|n:> {message}"
            from_template = "|w{date}{clr} {receiver}|n來自{clr}{sender}|n:< {message}"
            listing = []
            prev_selfsend = False
            for page in lastpages:
                multi_send = len(page.senders) > 1
                multi_recv = len(page.receivers) > 1
                sending = self.caller in page.senders
                selfsend = sending and self.caller in page.receivers
                if selfsend:
                    if prev_selfsend:
                        sending = False
                        prev_selfsend = False
                    else:
                        prev_selfsend = True

                clr = "|c" if sending else "|g"

                sender = f"|n,{clr}".join(obj.key for obj in page.senders)
                receiver = f"|n,{clr}".join([obj.name for obj in page.receivers])
                if sending:
                    template = to_template
                    sender = f"{sender} " if multi_send else ""
                    receiver = f" {receiver}" if multi_recv else f" {receiver}"
                else:
                    template = from_template
                    receiver = f"{receiver} " if multi_recv else ""
                    sender = f" {sender} " if multi_send else f" {sender}"

                listing.append(
                    template.format(
                        date=utils.datetime_format(page.date_created),
                        clr=clr,
                        sender=sender,
                        receiver=receiver,
                        message=page.message,
                    )
                )
            lastpages = "\n ".join(listing)

            if lastpages:
                string = f"你最近的傳訊：\n {lastpages}"
            else:
                string = "你還沒有傳送或接收任何傳訊。"
            self.msg(string)
            return

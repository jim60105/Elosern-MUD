"""Letter-only text counterpart to the server-authorized browser surface."""

import time

from commands.command import Command
from world.narrative import player_correspondence as letters
from world.observability import log_info


class CmdLetters(Command):
    """List collected letters, send/collect at a branch, or open a letter anywhere.

    Usage: 信件 [寄 <recipient>=<body>|領取|讀 <source_id>|更多 <cursor>]
    """

    key = "信件"
    aliases = ["letters"]
    locks = "cmd:all()"
    help_category = "一般"

    def at_pre_cmd(self):
        """Log the bounded arguments like every other command."""
        self._observability_started = time.perf_counter()
        log_info("cmd_in", context={"char": self.caller.pk, "cmd": self.key,
                                    "args": self.args or ""})

    def func(self):
        args = (self.args or "").lstrip()
        try:
            if not args or args.startswith("更多 "):
                after = 0
                if args:
                    cursor = args[3:].strip()
                    if not cursor.isdigit():
                        raise letters.CorrespondenceError("請使用信件清單提供的頁碼。")
                    after = int(cursor)
                page = letters.list_letters(self.caller, after)
                lines = ["已領取信件"]
                for row in page["letters"]:
                    status = "未讀" if row["read_tick"] is None else "已讀"
                    lines.append(f"{row['source_id']}　寄件人 #{row['sender_id']}　{status}")
                if not page["letters"]:
                    lines.append("目前沒有已領取的信件。")
                if page["next"] is not None:
                    lines.append(f"下一頁：信件 更多 {page['next']}")
                self.caller.msg("\n".join(lines))
            elif args.strip() == "領取":
                acquired = letters.collect(self.caller)
                self.caller.msg(f"已領取 {len(acquired)} 封信件，開啟後才會標記已讀。")
            elif args.startswith("寄 ") and "=" in args:
                recipient, body = args[2:].split("=", 1)
                record = letters.send(self.caller, recipient.strip(), body)
                self.caller.msg(f"信件已寄出，編號 {record.source_id}。")
            elif args.startswith("讀 "):
                record = letters.read(self.caller, args[2:].strip())
                # Escape Evennia markup: arbitrary text stays literal in both channels.
                self.caller.msg(record.body.replace("|", "||"))
            else:
                self.caller.msg("用法：信件 [寄 <收件人>=<內容>|領取|讀 <信件編號>|更多 <頁碼>]")
        except letters.CorrespondenceError as error:  # observability: ignore R2: expected player refusal; cmd_done reports the boundary without private prose
            self.caller.msg(str(error))

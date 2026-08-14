"""Player-facing ``設定背景`` command for a character's persona background.

``設定背景`` shows the character's current background with no argument, sets it
with an argument (routed through the deterministic ``world.rules.persona_edit``
writer), and clears it with an empty argument. A character without a persona
record is handled by the writer (the import-card record is created on set; a
clear without a record is a no-op). Over-bound input is rejected with the
shared persona-field bound.
"""

from evennia import Command

from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH
from world.rules.persona_edit import update_background

_CURRENT_NONE = "你還沒有設定背景。"
_USAGE = "用法：設定背景 <文字>（不帶參數查看目前背景，傳入空白清除）"


class CmdBackground(Command):
    """查看或設定自己的背景（風味文字）。用法：設定背景 <文字>"""

    key = "設定背景"
    aliases = ("背景",)
    help_category = "General"

    def func(self) -> None:
        if not self.args:
            current = self.caller.persona.get("background")
            if current:
                self.caller.msg(f"目前背景：{current}")
            else:
                self.caller.msg(_CURRENT_NONE)
            self.caller.msg(_USAGE)
            return
        raw = self.args.strip()
        if not raw:
            # An explicit empty argument clears the background; a truly bare
            # command (``設定背景`` with nothing after the key) shows the
            # current value instead (design D4).
            update_background(self.caller, None)
            self.caller.msg("已清除背景。")
            return
        if len(raw) > MAX_PERSONA_FIELD_LENGTH:
            self.caller.msg(f"背景設定超過 {MAX_PERSONA_FIELD_LENGTH} 字上限。")
            return
        try:
            persisted = update_background(self.caller, raw)
        except ValueError as error:
            self.caller.msg(f"無法設定背景：{error}")
            return
        if persisted:
            self.caller.msg(f"已設定背景：{persisted}")
        else:
            self.caller.msg("已清除背景。")


__all__ = ["CmdBackground"]

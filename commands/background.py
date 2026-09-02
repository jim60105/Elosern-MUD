"""Player-facing persona prose commands built on one shared three-part base.

``CmdPersonaFieldBase`` implements the three-part behaviour shared by the whole
persona command family: no argument shows the current value and usage, an
argument sets the field, and a whitespace-only argument clears it. Every write
routes through the deterministic ``world.rules.persona_edit`` writer
(``update_persona_field``); the field key and the Traditional Chinese label
are class attributes on each subclass. A character without a persona record is
handled by the writer (the import-card record is created on set; a clear
without a record is a no-op). Over-bound input is rejected with the shared
persona-field bound before the writer is called.

``CmdBackground`` is the ``background`` subclass of this base and keeps its
key, aliases, and every player-visible message exactly as before.
"""

from commands.command import Command

from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH
from world.rules.persona_edit import update_persona_field


class CmdPersonaFieldBase(Command):
    """查看或設定自己的某一項人格敘事文字（風味文字）。"""

    # Subclass contract: the whitelisted persona field key and its zh-TW
    # label used in every player-visible line.
    field: str = ""
    zh_label: str = ""
    help_category = "General"

    def func(self) -> None:
        label = self.zh_label
        if not self.args:
            current = self.caller.persona.get(self.field)
            if current:
                self.caller.msg(f"目前{label}：{current}")
            else:
                self.caller.msg(f"你還沒有設定{label}。")
            self.caller.msg(
                f"用法：{self.key} <文字>（不帶參數查看目前{label}，"
                "傳入空白清除）"
            )
            return
        raw = self.args.strip()
        if not raw:
            # An explicit empty argument clears the field; a truly bare
            # command (nothing after the key) shows the current value
            # instead (design D4).
            update_persona_field(self.caller, self.field, None)
            self.caller.msg(f"已清除{label}。")
            return
        if len(raw) > MAX_PERSONA_FIELD_LENGTH:
            self.caller.msg(
                f"{label}設定超過 {MAX_PERSONA_FIELD_LENGTH} 字上限。"
            )
            return
        try:
            persisted = update_persona_field(self.caller, self.field, raw)
        except ValueError as error:
            self.caller.msg(f"無法設定{label}：{error}")
            return
        if persisted:
            self.caller.msg(f"已設定{label}：{persisted}")
        else:
            self.caller.msg(f"已清除{label}。")


class CmdBackground(CmdPersonaFieldBase):
    """查看或設定自己的背景（風味文字）。用法：設定背景 <文字>"""

    key = "設定背景"
    aliases = ("背景",)
    field = "background"
    zh_label = "背景"


__all__ = ["CmdBackground", "CmdPersonaFieldBase"]

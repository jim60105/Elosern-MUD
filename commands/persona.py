"""The persona prose command family for the other three editable fields.

``設定個性`` / ``設定生平`` / ``設定習慣`` are the ``personality``,
``life_story``, and ``habit`` subclasses of the shared
``commands.background.CmdPersonaFieldBase`` three-part behaviour (bare shows
the current value and usage, an argument sets the field, a whitespace-only
argument clears it). Every write routes through the deterministic
``world.rules.persona_edit`` writer, exactly like ``設定背景``.
"""

from commands.background import CmdPersonaFieldBase


class CmdPersonaPersonality(CmdPersonaFieldBase):
    """查看或設定自己的個性（風味文字）。用法：設定個性 <文字>"""

    key = "設定個性"
    aliases = ("個性",)
    field = "personality"
    zh_label = "個性"


class CmdPersonaLifeStory(CmdPersonaFieldBase):
    """查看或設定自己的生平（背景故事）。用法：設定生平 <文字>"""

    key = "設定生平"
    aliases = ("生平", "背景故事")
    field = "life_story"
    zh_label = "生平"


class CmdPersonaHabit(CmdPersonaFieldBase):
    """查看或設定自己的習慣（風味文字）。用法：設定習慣 <文字>"""

    key = "設定習慣"
    aliases = ("習慣",)
    field = "habit"
    zh_label = "習慣"


__all__ = [
    "CmdPersonaHabit",
    "CmdPersonaLifeStory",
    "CmdPersonaPersonality",
]

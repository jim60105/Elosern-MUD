"""Player-facing ``title`` command: browse the title册 and swap equipped slots.

``title list`` shows the current composed full title, every guild fixed-title
row (banked rows marked, locked rows carrying their authored ``hint_zh``), and
every banked epithet. ``title equip fixed`` and ``title equip epithet`` swap
one occupied slot for another (D8): both slots always hold a value once the
册 is non-empty, there is no unequip surface, and an unknown, unbanked, or
wrong-kind display fails with one stable rejection that never enumerates
candidates or hints at what the player is missing. Malformed stored title
state presents the same fixed unavailable line and changes nothing.
"""

from evennia import Command

from world.lore.titles import FIXED_TITLE_REGISTRY
from world.rules.titles import (
    TitleDataError,
    TitleEquipError,
    banked_fixed_keys,
    banked_epithets,
    compose_full_title,
    equip_epithet,
    equip_fixed,
)

_USAGE = "語法：title list | title equip fixed <稱號> | title equip epithet <異名>"
_UNAVAILABLE = "你的稱號冊暫時無法閱讀。"
_REJECTED = "無法掛上該稱號。"
_BANKED_MARK = "●"
_LOCKED_MARK = "○"


class CmdTitle(Command):
    """Browse the title册 and swap the equipped title or epithet."""

    key = "title"
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split()
        if not parts:
            self.caller.msg(_USAGE)
            return
        verb = parts[0].lower()
        if verb == "list" and len(parts) == 1:
            self._list()
            return
        if verb == "equip" and len(parts) > 2:
            kind = parts[1].lower()
            name = " ".join(parts[2:]).strip()
            if kind == "fixed":
                self._equip_fixed(name)
                return
            if kind == "epithet":
                self._equip_epithet(name)
                return
        self.caller.msg(_USAGE)

    def _list(self) -> None:
        try:
            full_title = compose_full_title(self.caller)
            fixed_keys = banked_fixed_keys(self.caller)
            epithets = banked_epithets(self.caller)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
            return
        lines = ["── 稱號冊 ──", f"當前全銜：{full_title}", "◆ 稱號"]
        for entry in FIXED_TITLE_REGISTRY.values():
            mark = _BANKED_MARK if entry.key in fixed_keys else _LOCKED_MARK
            suffix = "" if entry.key in fixed_keys else f"（{entry.hint_zh}）"
            lines.append(f"　{mark} {entry.display_name_zh}{suffix}")
        lines.append("◆ 異名")
        if epithets:
            lines.extend(f"　{_BANKED_MARK} {entry['display']}" for entry in epithets)
        else:
            lines.append("　（尚未取得）")
        self.caller.msg("\n".join(lines))

    def _equip_fixed(self, name: str) -> None:
        if not name:
            self.caller.msg(_USAGE)
            return
        try:
            fixed_display = equip_fixed(self.caller, name)
        except TitleEquipError:
            self.caller.msg(_REJECTED)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
        else:
            self.caller.msg(f"你掛上稱號：{fixed_display}")

    def _equip_epithet(self, name: str) -> None:
        if not name:
            self.caller.msg(_USAGE)
            return
        try:
            epithet = equip_epithet(self.caller, name)
        except TitleEquipError:
            self.caller.msg(_REJECTED)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
        else:
            self.caller.msg(f"你掛上異名：{epithet}")

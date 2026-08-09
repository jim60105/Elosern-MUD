"""Player-facing ``lore`` command for the knowledge codex (lore-knowledge-codex).

``lore`` lists the entries the player has discovered (grouped by category in
deterministic order), and ``lore <category> <key>`` renders one discovered
entry's card through the codex renderer. Unknown categories, unknown keys, and
known-but-undiscovered entries all return the same fixed not-found line so the
existence of a registry entry is never leaked; the command never displays an
entry the player has not revealed.
"""

from evennia import Command

from world.rules.lore_knowledge import (
    LoreCategoryError,
    LoreKeyError,
    LoreRecordError,
    list_discovered,
    lore_card,
)

# Player-facing category labels used by the listing groups (display-only).
CATEGORY_LABELS = {
    "race": "種族",
    "nation": "國家",
    "region": "地域",
    "monster": "魔物",
    "element": "元素",
    "magic": "魔法",
    "anchor": "地點",
    "guild": "公會",
}

_NOT_FOUND = "圖鑑中查無此知識。"
_UNAVAILABLE = "你的知識圖鑑暫時無法閱讀。"
_EMPTY = "你的知識圖鑑還是空的。"


class CmdLore(Command):
    """Browse the knowledge codex of discovered lore entries."""

    key = "lore"
    aliases = ("圖鑑",)
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        if not self.args.strip():
            self._list_all()
            return
        if len(parts) == 1:
            self.caller.msg(_NOT_FOUND)
            return
        category, key = parts[0], parts[1].strip()
        if not key:
            self.caller.msg(_NOT_FOUND)
            return
        self._show(category, key)

    def _list_all(self) -> None:
        try:
            discovered = list_discovered(self.caller)
        except LoreRecordError:
            self.caller.msg(_UNAVAILABLE)
            return
        if not discovered:
            self.caller.msg(_EMPTY)
            return
        lines = ["── 知識圖鑑 ──"]
        current = None
        for category, key in discovered:
            if category != current:
                lines.append(f"◆ {CATEGORY_LABELS.get(category, category)}")
                current = category
            lines.append(f"　{key}")
        self.caller.msg("\n".join(lines))

    def _show(self, category: str, key: str) -> None:
        try:
            discovered = list_discovered(self.caller)
        except LoreRecordError:
            self.caller.msg(_UNAVAILABLE)
            return
        if (category, key) not in discovered:
            self.caller.msg(_NOT_FOUND)
            return
        try:
            card = lore_card(category, key)
        except (LoreCategoryError, LoreKeyError):
            self.caller.msg(_NOT_FOUND)
            return
        title = card.get("display_name_zh") or card.get("key", key)
        body = [
            value
            for name, value in card.items()
            if name not in ("display_name_zh", "key")
        ]
        if body:
            self.caller.msg(f"◆ {title} ◆\n" + "\n".join(body))
        else:
            self.caller.msg(f"◆ {title} ◆")

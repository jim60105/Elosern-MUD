"""Player-facing ``交付`` command: deterministic quest-item delivery.

Parses the recipient and the item from the argument string, resolves the
recipient by the ordinary local search (any co-located entity type, mirroring
the web action's present-entity lookup), and calls the same shared
deterministic rule the ``explore.deliver`` action uses, so both surfaces
refuse and succeed identically. The combat-session refusal also comes from the
shared rule, keeping the two surfaces byte-identical.

The command carries no alias: ``給`` is owned by the localized general give
(``commands/localized/general.py::CmdGive``). The shared rule is the seam for
a future quest-delivery branch inside that general give.
"""

from commands.command import Command

from world.lore.items import ITEM_REGISTRY
from world.rules.quest_delivery import deliver_quest_item

_USAGE = "用法：交付 <對象> <物品>"
_AMBIGUOUS_TARGET = "這裡有好幾個對象，請說得更明確一些。"
_NO_TARGET = "這裡沒有這個對象。"
_AMBIGUOUS_ITEM = "這個名稱對應好幾種物品，請說得更明確一些。"
_UNKNOWN_ITEM = "你沒有帶著這種物品。"


def _resolve_item_key(raw_item: str) -> str | None:
    """Resolve an item token to a registry key by exact key or display name.

    Returns ``None`` when nothing in the item registry matches; a held check
    is the shared rule's job, not the parser's.
    """
    if raw_item in ITEM_REGISTRY:
        return raw_item
    matches = [
        key
        for key, definition in ITEM_REGISTRY.items()
        if definition.display_name_zh == raw_item
    ]
    if len(matches) == 1:
        return matches[0]
    return None


class CmdDeliver(Command):
    """Hand a quest item to the recipient its quest bound it to."""

    key = "交付"
    aliases = ()
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            self.caller.msg(_USAGE)
            return
        raw_target = parts[0]
        raw_item = parts[1].strip()

        candidates = self.caller.search(raw_target, quiet=True)
        if not candidates:
            self.caller.msg(_NO_TARGET)
            return
        if len(candidates) > 1:
            self.caller.msg(_AMBIGUOUS_TARGET)
            return
        recipient = candidates[0]

        item_key = _resolve_item_key(raw_item)
        if item_key is None:
            self.caller.msg(_UNKNOWN_ITEM)
            return

        outcome = deliver_quest_item(self.caller, recipient, item_key)
        self.caller.msg(outcome.message)

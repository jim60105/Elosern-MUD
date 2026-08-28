"""Player-facing item use and equipment toggle commands.

Both commands parse only the item key and delegate to the same deterministic
APIs the UI action adapters call: ``world.rules.items.use_item`` outside
combat, ``world.rules.combat_session.submit_player_item_use`` inside an
active session (one initiative-ordered round), and
``world.rules.equipment.toggle_equipment`` for equipment (a free action that
never consumes a round). Stable rejections render the same Traditional
Chinese reason semantics as UI actions through ``service_messages``.
"""

from evennia import Command

from world.lore.items import ITEM_REGISTRY
from world.rules.combat_result import settle_to_messages
from world.rules.combat_session import (
    CombatSessionError,
    is_in_active_session,
    submit_player_item_use,
)
from world.rules.equipment import toggle_equipment
from world.rules.event_log import render_plain_text
from world.rules.items import use_item
from world.rules.player_messages import session_reason_message
from world.rules.service_messages import rejection_message


def _item_display_name(item_key: str) -> str:
    definition = ITEM_REGISTRY.get(item_key)
    return definition.display_name_zh if definition is not None else item_key


def _toggle_message(result, item_key: str) -> str:
    """Render the accepted equipment toggle in the shared command prose."""
    display = _item_display_name(item_key)
    if result.action == "unequip-singleton":
        return f"你卸下了 {display}。"
    if result.action == "unequip-accessory":
        return f"你除下了 {display}。"
    if result.action == "equip-accessory":
        return f"你佩戴了 {display}。"
    if result.replaced_key is not None:
        return f"你裝備了 {display}，原本的 {_item_display_name(result.replaced_key)} 已收回背包。"
    return f"你裝備了 {display}。"


class CmdUseItem(Command):
    """Use one held item, in exploration or in an active combat round."""

    key = "使用"
    aliases = ("use",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        item_key = self.args.strip().partition(" ")[0]
        if not item_key:
            self.caller.msg("用法：使用 <item_key>")
            return
        if is_in_active_session(self.caller):
            self._use_in_session(item_key)
            return
        settlement = use_item(self.caller, item_key)
        result = settlement.result
        if result.outcome != "success":
            self.caller.msg(rejection_message(result.reason))
            return
        self.caller.msg(render_plain_text(result.event_log))

    def _use_in_session(self, item_key: str) -> None:
        try:
            result = submit_player_item_use(self.caller, item_key)
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        if result["outcome"] == "rejected":
            self.caller.msg(rejection_message(result.get("reason")))
            return
        lines, message = settle_to_messages(result)
        for line in lines:
            self.caller.msg(line)
        self.caller.msg(message)


class CmdToggleEquip(Command):
    """Equip or unequip one held equipment item (a free action)."""

    key = "裝備"
    aliases = ("equip",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        item_key = self.args.strip().partition(" ")[0]
        if not item_key:
            self.caller.msg("用法：裝備 <item_key>")
            return
        result = toggle_equipment(self.caller, item_key)
        if result.outcome != "success":
            self.caller.msg(rejection_message(result.reason))
            return
        self.caller.msg(_toggle_message(result, item_key))

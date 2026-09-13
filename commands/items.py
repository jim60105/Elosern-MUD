"""Player-facing item use and equipment toggle commands.

Both commands parse only the item key and delegate to the same deterministic
APIs the UI action adapters call: ``world.rules.items.use_item`` outside
combat, ``world.rules.combat_session.submit_player_item_use`` inside an
active session (one initiative-ordered round), and
``world.rules.equipment.toggle_equipment`` for equipment (a free action that
never consumes a round). Stable rejections render the same Traditional
Chinese reason semantics as UI actions through ``service_messages``.
"""

from typing import Any

from commands.command import Command

from world.lore.items import ITEM_REGISTRY
from world.rules.combat_result import settle_to_messages
from world.rules.combat_session import (
    CombatSessionError,
    is_in_active_session,
    submit_player_item_use,
)
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import equipment_adjustment_text
from world.rules.event_log import render_plain_text
from world.rules.items import use_item
from world.rules.player_messages import session_reason_message
from world.rules.service_messages import rejection_message


def _item_display_name(item_key: str) -> str:
    definition = ITEM_REGISTRY.get(item_key)
    return definition.display_name_zh if definition is not None else item_key


def _toggle_message(result, item_key: str) -> str:
    """Render the accepted equipment toggle in the shared command prose.

    Equip actions append the server-formatted adjustment summary (P3 D4);
    unequip actions keep the plain line since nothing new is gained.
    """
    display = _item_display_name(item_key)
    prose = equipment_adjustment_text(item_key)
    if result.action == "unequip-singleton":
        return f"你卸下了 {display}。"
    if result.action == "unequip-accessory":
        return f"你除下了 {display}。"
    if result.action == "equip-accessory":
        return f"你佩戴了 {display}" + (f"（{prose}）" if prose else "") + "。"
    if result.replaced_key is not None:
        base = f"你裝備了 {display}，原本的 {_item_display_name(result.replaced_key)} 已收回背包。"
        if prose:
            return f"你裝備了 {display}（{prose}），原本的 {_item_display_name(result.replaced_key)} 已收回背包。"
        return base
    return f"你裝備了 {display}" + (f"（{prose}）" if prose else "") + "。"


class CmdUseItem(Command):
    """Use one held item, in exploration or in an active combat round."""

    key = "使用"
    aliases = ("use",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        item_key, _, target_token = self.args.strip().partition(" ")
        target_token = target_token.strip()
        if not item_key:
            self.caller.msg("用法：使用 <item_key> [target]")
            return
        # The target token names *whom* an effect reaches, never what the
        # item does (add-item-effect-targeting D1): it resolves to a present
        # entity here, and an unresolvable token — including a group
        # shorthand the player typed by hand — travels to the deterministic
        # preflight as the raw string, where the fail-closed target guard
        # rejects it with the stable invalid-target reason instead of the
        # use silently ignoring a reach the rulebook never granted.
        target: Any = None
        if target_token:
            matches = self.caller.search(target_token, quiet=True)
            if len(matches) == 1:
                target = matches[0]
            else:
                # No match or ambiguous token: the raw token reaches preflight
                # as a non-entity and fails closed with the stable
                # TARGET_INVALID rejection; the command never guesses among
                # multiple candidates.
                target = target_token
        if is_in_active_session(self.caller):
            self._use_in_session(item_key, target)
            return
        settlement = use_item(self.caller, item_key, target=target)
        result = settlement.result
        if result.outcome != "success":
            self.caller.msg(rejection_message(result.reason))
            return
        self.caller.msg(render_plain_text(result.event_log))

    def _use_in_session(self, item_key: str, target=None) -> None:
        try:
            result = submit_player_item_use(self.caller, item_key, target=target)
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

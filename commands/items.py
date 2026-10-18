"""Player-facing item use, equipment toggle and member retrieve commands.

Each command parses only its arguments and delegates to the same deterministic
APIs the UI action adapters call: ``world.rules.items.use_item`` outside
combat, ``world.rules.combat_session.submit_player_item_use`` inside an
active session (one initiative-ordered round), and
``world.rules.equipment.toggle_equipment`` for equipment (a free action that
never consumes a round). Stable rejections render the same Traditional
Chinese reason semantics as UI actions through ``service_messages``.

``取回`` moves an item from a present party member back into the commander's
bag through ``world.rules.party_inventory.transfer_item``, the same rule the
``party.transfer`` action and the member branch of ``給`` call.
"""

from typing import Any

from commands.command import Command
from commands.localized.general import NumberedTargetCommand

from world.rules.combat_result import settle_to_messages
from world.rules.combat_session import (
    CombatSessionError,
    is_in_active_session,
    submit_player_item_use,
)
from world.rules.equipment_effects import toggle_equipment_message
from world.rules.event_log import render_plain_text
from world.rules.items import use_item
from world.rules.npc_identity import npc_display_name
from world.rules.party_inventory import (
    PartyTransferError,
    resolve_item_token,
    toggle_member_equipment,
    transfer_item,
)
from world.rules.party_scope import (
    PartyScopeError,
    resolve_commander,
    resolve_member_token,
)
from world.rules.player_messages import session_reason_message
from world.rules.quest_delivery import item_display_name
from world.rules.service_messages import rejection_message


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
    """裝備或卸下一件裝備（免費動作）

    用法：
      裝備 <物品> [= <成員>]

    裝備或卸下自己或一名同行隊伍成員身上的裝備；物品可用登錄鍵或背包中顯示
    的名稱指定，指定成員時以「=」分隔。成員可以是倒地的同伴，因為整理裝備
    不是行動。這是免費動作：探索與戰鬥中都不消耗時間或回合。成員不在場或
    不屬於你的隊伍時以固定語句拒絕，且不會改變任何人的裝備。
    """

    key = "裝備"
    aliases = ("equip",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        item_part, separator, member_token = self.args.partition("=")
        if not item_part.strip():
            self.caller.msg("用法：裝備 <物品> [= <成員>]")
            return
        member = self.caller
        if separator:
            try:
                member = resolve_member_token(self.caller, member_token)
            except PartyScopeError as error:
                self.caller.msg(error.message)
                return
        # The item token is the registry key or the held display name,
        # resolved against the selected member's own bag exactly like 給 and
        # 取回, so a display name (spaces included) names the same item the
        # action's `item_key` names. An unresolved token travels on unchanged
        # and the toggle rule rejects it with its own stable code.
        item_key = resolve_item_token(member, item_part)
        try:
            outcome = toggle_member_equipment(self.caller, member.pk, item_key)
        except PartyScopeError as error:
            self.caller.msg(error.message)
            return
        result = outcome.result
        if result.outcome != "success":
            self.caller.msg(rejection_message(result.reason))
            return
        subject = "你" if outcome.member is self.caller else npc_display_name(
            outcome.member
        )
        self.caller.msg(toggle_equipment_message(result, item_key, subject))


class CmdRetrieve(NumberedTargetCommand):
    """取回隊伍成員身上的物品

    用法：
      取回 [數量] <物品> = <成員>

    從同行的隊伍成員身上取回物品，放進指揮者的背包。免費動作：不推進時間、
    不改變好感度；戰鬥中會以固定語句拒絕，成員不在場或物品無法交換時也不會
    改變任何東西。
    """

    key = "取回"
    aliases = ("retrieve",)
    locks = "cmd:all()"
    help_category = "General"
    rhs_split = ("=", " to ")

    def func(self) -> None:
        """執行取回。"""
        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("用法：取回 [數量] <物品> = <成員>")
            return
        try:
            member = resolve_member_token(caller, self.rhs)
        except PartyScopeError as error:
            caller.msg(error.message)
            return
        try:
            outcome = transfer_item(
                caller,
                member.pk,
                resolve_commander(caller).pk,
                resolve_item_token(member, self.lhs),
                self.number if self.count_given else 1,
            )
        except (PartyTransferError, PartyScopeError) as error:
            caller.msg(error.message)
            return
        caller.msg(
            f"你從{npc_display_name(outcome.giver)}那裡取回了 "
            f"{outcome.quantity} 個{item_display_name(outcome.item_key)}。"
        )

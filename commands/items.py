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

``使用`` accepts a ``= <成員>`` suffix: outside combat the named member's own
bag is used through ``world.rules.party_inventory.use_member_item`` (the same
rule ``inventory.use`` calls), and inside a session that member's item
selection is saved through the actor-command facade ``combat command`` uses.
"""

from typing import Any

from commands.command import Command
from commands.localized.general import NumberedTargetCommand

from world.rules.combat_result import settle_to_messages
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    is_in_active_session,
    read_session,
    session_owner,
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
    use_member_item,
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
    """使用一件持有物品（探索或戰鬥中的一次行動）

    用法：
      使用 <item_key> [target] [= <成員>]

    使用自己或一名同行隊伍成員背包中的物品；物品以登錄鍵指定，指定成員時
    以「=」分隔。`[target]` 只決定效果「施加給誰」，不改變物品「做什麼」。
    指定成員時物品從該成員自己的背包消耗、自身效果綁定該成員，時間成本與
    指揮者相同（探索中約 6 秒，並結算在場隊伍）；成員必須在場且能行動，
    倒地的同伴會以固定語句拒絕。戰鬥中只會存入該成員的那筆指令（未指定
    成員時是你自己的），完整回合確認後才在結算時消耗道具與一個回合。
    """

    key = "使用"
    aliases = ("use",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        # The `= <成員>` suffix is reserved syntax and is split first, exactly
        # like 裝備: everything after the final `=` names the member, and the
        # ordinary `item [target]` parse runs on the left side. An empty
        # suffix never falls back to the caller.
        named = "=" in self.args
        if named:
            item_part, _, member_token = self.args.rpartition("=")
        else:
            item_part, member_token = self.args, ""
        item_key, _, target_token = item_part.strip().partition(" ")
        target_token = target_token.strip()
        if not item_key:
            self.caller.msg("用法：使用 <item_key> [target] [= <成員>]")
            return
        member: Any = None
        if named:
            try:
                member = resolve_member_token(self.caller, member_token)
            except PartyScopeError as error:
                self.caller.msg(error.message)
                return
        if is_in_active_session(self.caller):
            self._use_in_session(item_key, target_token, member)
            return
        target = self._field_target(target_token)
        if member is None:
            self._render(use_item(self.caller, item_key, target=target).result)
            return
        try:
            outcome = use_member_item(
                self.caller, int(member.pk), item_key, target=target
            )
        except PartyScopeError as error:
            self.caller.msg(error.message)
            return
        self._render(outcome.settlement.result)

    def _field_target(self, target_token: str) -> Any:
        """Resolve one optional target token for the field path.

        The target token names *whom* an effect reaches, never what the item
        does (add-item-effect-targeting D1): it resolves to a present entity
        here, and an unresolvable token — including a group shorthand the
        player typed by hand — travels to the deterministic preflight as the
        raw string, where the fail-closed target guard rejects it with the
        stable invalid-target reason instead of the use silently ignoring a
        reach the rulebook never granted. No match or an ambiguous token never
        makes the command guess among candidates.
        """
        if not target_token:
            return None
        matches = self.caller.search(target_token, quiet=True)
        return matches[0] if len(matches) == 1 else target_token

    def _render(self, result: Any) -> None:
        """Render one settled item use or its stable rejection."""
        if result.outcome != "success":
            self.caller.msg(rejection_message(result.reason))
            return
        self.caller.msg(render_plain_text(result.event_log))

    def _use_in_session(
        self, item_key: str, target_token: str, member: Any = None
    ) -> None:
        """Save one item selection into the party draft, consuming nothing yet.

        ``member`` is the explicitly named member; ``None`` keeps the caller's
        own entry through the commander facade. The member route builds the
        same actor item command ``combat command <token> item ...`` builds and
        admits it through the same actor-command facade, so a companion's text
        use and its graphical selection are one draft entry: no round, time,
        or item is consumed until the complete draft's final confirmation.
        """
        if member is not None:
            from commands.combat import build_item_command, submit_actor_command

            try:
                commander = session_owner(self.caller)
                record = read_session(commander)
            except CombatSessionError as error:
                self.caller.msg(session_reason_message(str(error.args[0])))
                return
            if record is None:
                self.caller.msg(
                    session_reason_message(str(SessionReason.NO_ACTIVE_SESSION))
                )
                return
            command = build_item_command(
                self.caller, item_key, target_token, commander=commander
            )
            if command is None:
                return
            submit_actor_command(
                self.caller, record, member, command, commander=commander
            )
            return
        target = self._field_target(target_token)
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

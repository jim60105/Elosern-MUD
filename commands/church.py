"""Player-facing Light Church commands (``join``, ``pray``, ``offer``,
``redeem``, ``merit``).

The command surface is deliberately thin: the deterministic enrollment rite,
the office branch, and the vestment handover all live in
``world/rules/church.py::enroll`` (design §5.1). This module owns host
resolution (the ``resolve_local_service_host`` pattern), the schedule gate
(``interaction_reason(host, "service_church")``), the stable rejection prose,
and the authored presentation around the deterministic grant — no dialogue
model, no LLM intent participates. ``church pray`` and ``church offer`` are
equally thin: ``world/rules/church.py::pray_step`` and
``offering_menu``/``offer_step`` own every mechanic; this module renders the
menu and maps the stable rejection reasons to fixed player-facing lines.
``church redeem`` and ``church merit`` are just as thin: the ordination
ladder (``redeem_step``) and the read-only ledger print own every mechanic,
and the rejection map below stays the only presentation surface.
"""

from commands.command import Command

from typeclasses.components import ChurchHost
from world.lore.items import ITEM_REGISTRY
from world.rules.church import (
    EnrollmentError,
    EnrollmentReason,
    OfferingError,
    OfferingReason,
    PrayerError,
    PrayerReason,
    RedemptionError,
    RedemptionReason,
    enroll,
    enrolled_tick,
    daily,
    merit,
    offer_step,
    offering_menu,
    pray_step,
    redeem_step,
    redemption_catalogue,
    redeemed_keys,
    read_ledger,
)
from world.rules.guild import GuildServiceError, resolve_local_service_host
from world.rules.npc_schedules import interaction_reason
from world.rules.service_gate import MESSAGE_OFF_ANCHOR
from world.skills.registry import SKILL_REGISTRY
from commands.talk import _resolve_npc

_NO_LOCAL_HOST_LINE = "這裡沒有教會的神職人員。"

_REJECTION_LINES = {
    EnrollmentReason.NOT_A_PLAYER: "只有冒險者能加入教會。",
    EnrollmentReason.ALREADY_ENROLLED: "你已屬光明教會。",
    EnrollmentReason.NO_HOST: _NO_LOCAL_HOST_LINE,
    EnrollmentReason.REMOTE_HOST: _NO_LOCAL_HOST_LINE,
    EnrollmentReason.SERVICE_UNAVAILABLE: MESSAGE_OFF_ANCHOR,
    EnrollmentReason.MALFORMED_LEDGER: "教會記錄異常，暫時無法入教。",
}

_PRAYER_REJECTION_LINES = {
    PrayerReason.NOT_A_PLAYER: "只有冒險者能祈禱。",
    PrayerReason.NOT_ENROLLED: "你尚未入教。請先與主祭交談。",
    PrayerReason.OUTSIDE_VENUE: "這裡並非教會聖所，無法祈禱。",
    PrayerReason.DAILY_CAP: "你今天已經祈禱夠了，改日再來吧。",
    PrayerReason.MALFORMED_LEDGER: "教會記錄異常，暫時無法祈禱。",
}

_OFFERING_REJECTION_LINES = {
    OfferingReason.NOT_A_PLAYER: "只有冒險者能獻上服務。",
    OfferingReason.NOT_ENROLLED: "你尚未入教。請先與主祭交談。",
    OfferingReason.ROW_NOT_UNLOCKED: "你尚未掌握這項服務。",
    OfferingReason.MALFORMED_LEDGER: "教會記錄異常，暫時無法獻上服務。",
    OfferingReason.ACT_REJECTED: "這項服務無法進行。",
}

_NPC_DECLINED_LINE = "她婉拒了你的服務。"
_OFFER_USAGE = "用法：church offer <npc> [row_key]"

_REDEMPTION_REJECTION_LINES = {
    RedemptionReason.NOT_A_PLAYER: "只有冒險者能兌換敘階。",
    RedemptionReason.NOT_ENROLLED: "你尚未入教。請先與主祭交談。",
    RedemptionReason.UNKNOWN_KEY: "沒有這個敘階項目。",
    RedemptionReason.ALREADY_REDEEMED: "你已經獲得這項敘階。",
    RedemptionReason.INSUFFICIENT_MERIT: "你的恩寵不足，無法兌換這項敘階。",
    RedemptionReason.UNMET_PREREQ: "你尚未滿足這項敘階的前置條件。",
    RedemptionReason.MALFORMED_LEDGER: "教會記錄異常，暫時無法兌換敘階。",
}
_REDEEM_USAGE = "用法：church redeem [list|<key>]"
_MERIT_USAGE = "用法：church merit"


class CmdChurchJoin(Command):
    """向主祭正式入教，成為光明教會的一員。"""

    key = "church join"
    aliases = ("入教", "洗禮")
    locks = "cmd:all()"
    help_category = "church"

    def func(self) -> None:
        try:
            host = resolve_local_service_host(self.caller, ChurchHost)
        except GuildServiceError:
            self.caller.msg(_NO_LOCAL_HOST_LINE)
            return
        reason = interaction_reason(host, "service_church")
        if reason is not None:
            self.caller.msg(reason)
            return
        try:
            record = enroll(self.caller, host)
        except EnrollmentError as error:
            reason = error.args[0] if error.args else None
            self.caller.msg(_REJECTION_LINES.get(reason, "入教失敗。"))
            return
        robe = ITEM_REGISTRY[record["item"]].display_name_zh
        if record["vessel_branch"]:
            self.caller.msg(
                f"你已加入光明教會。主祭以聖女之禮接納你，將{robe}放入你手中。"
            )
        else:
            self.caller.msg(f"你已加入光明教會。主祭將{robe}放入你手中。")


class CmdChurchPray(Command):
    """在教會聖所祈禱，花費時間並累積恩寵。"""

    key = "church pray"
    aliases = ("祈禱",)
    locks = "cmd:all()"
    help_category = "church"

    def func(self) -> None:
        try:
            result = pray_step(self.caller)
        except PrayerError as error:
            reason = error.args[0] if error.args else None
            self.caller.msg(_PRAYER_REJECTION_LINES.get(reason, "祈禱失敗。"))
            return
        self.caller.msg(
            f"你虔誠祈禱，沐浴在聖光之中，獲得 {result['merit']} 點恩寵。"
        )


class CmdChurchOffer(Command):
    """向眼前的 NPC 獻上性愛服務（依對方意願，恩寵與銅錢同筆入帳）。"""

    key = "church offer"
    aliases = ()
    locks = "cmd:all()"
    help_category = "church"

    def _resolve_recipient(self, raw_target: str):
        resolved = _resolve_npc(
            self.caller,
            raw_target,
            missing="你想服務誰？請指定一個目標。",
            ambiguous="這裡有好幾個目標，請說得更明確一些。",
            not_npc="那不是你可以服務的對象。",
        )
        if isinstance(resolved, str):
            self.caller.msg(resolved)
            return None
        return resolved

    def _show_menu(self, npc) -> None:
        try:
            rows = offering_menu(self.caller)
        except OfferingError as error:
            reason = error.args[0] if error.args else None
            self.caller.msg(_OFFERING_REJECTION_LINES.get(reason, "服務無法進行。"))
            return
        lines = [f"你目前能為{npc.key}提供的服務："]
        for row in rows:
            skill = SKILL_REGISTRY.get(row.act_key)
            label = skill.label if skill is not None else row.act_key
            lines.append(f"{row.key} — {label}（恩寵 {row.merit}）")
        lines.append(_OFFER_USAGE)
        self.caller.msg("\n".join(lines))

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        if not parts or not parts[0]:
            self.caller.msg(_OFFER_USAGE)
            return
        npc = self._resolve_recipient(parts[0])
        if npc is None:
            return
        row_key = parts[1].strip() if len(parts) > 1 else ""
        if not row_key:
            self._show_menu(npc)
            return
        try:
            result = offer_step(self.caller, npc, row_key)
        except OfferingError as error:
            reason = error.args[0] if error.args else None
            self.caller.msg(_OFFERING_REJECTION_LINES.get(reason, "服務無法進行。"))
            return
        if result["outcome"] == "declined":
            self.caller.msg(_NPC_DECLINED_LINE)
            return
        self.caller.msg(
            f"你為{npc.key}獻上服務，獲得 {result['merit']} 點恩寵與 "
            f"{result['copper']} 銅。"
        )


class CmdChurchRedeem(Command):
    """以恩寵兌換教會敘階（聖職敘階授予）。"""

    key = "church redeem"
    aliases = ("敘階",)
    locks = "cmd:all()"
    help_category = "church"

    def _show_list(self) -> None:
        try:
            rows = redemption_catalogue(self.caller)
        except RedemptionError as error:
            reason = error.args[0] if error.args else None
            self.caller.msg(
                _REDEMPTION_REJECTION_LINES.get(reason, "兌換無法進行。")
            )
            return
        lines = [f"你目前擁有 {merit(self.caller)} 點恩寵。"]
        for row, redeemed in rows:
            skill = SKILL_REGISTRY.get(row.skill_key)
            label = skill.label if skill is not None else row.skill_key
            mark = "（已兌換）" if redeemed else ""
            lines.append(f"{row.skill_key} — {label}（恩寵 {row.merit_price}）{mark}")
        lines.append(_REDEEM_USAGE)
        self.caller.msg("\n".join(lines))

    def func(self) -> None:
        args = self.args.strip()
        if not args or args == "list":
            self._show_list()
            return
        key = args.split(maxsplit=1)[0]
        try:
            result = redeem_step(self.caller, key)
        except RedemptionError as error:
            reason = error.args[0] if error.args else None
            self.caller.msg(
                _REDEMPTION_REJECTION_LINES.get(reason, "兌換失敗。")
            )
            return
        skill = SKILL_REGISTRY.get(result["row"])
        label = skill.label if skill is not None else result["row"]
        self.caller.msg(
            f"聖光降臨，你以 {result['price']} 點恩寵兌換了「{label}」。"
        )


class CmdChurchMerit(Command):
    """查閱自己的教會恩寵記錄（唯讀）。"""

    key = "church merit"
    aliases = ()
    locks = "cmd:all()"
    help_category = "church"

    def func(self) -> None:
        if self.args.strip():
            self.caller.msg(_MERIT_USAGE)
            return
        if read_ledger(self.caller) is None:
            self.caller.msg("你尚未入教。請先與主祭交談。")
            return
        redeemed = redeemed_keys(self.caller)
        daily_block = daily(self.caller)
        pray_usage = daily_block["pray"] if daily_block else 0
        lines = [
            f"恩寵：{merit(self.caller)} 點",
            f"入教時的世界時鐘刻度：{enrolled_tick(self.caller)}",
            f"今日祈禱次數：{pray_usage}",
        ]
        if redeemed:
            lines.append("已兌換敘階：" + "、".join(redeemed))
        else:
            lines.append("已兌換敘階：（無）")
        self.caller.msg("\n".join(lines))
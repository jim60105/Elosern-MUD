"""Player-facing Light Church commands (currently ``church join`` only).

The command surface is deliberately thin: the deterministic enrollment rite,
the office branch, and the vestment handover all live in
``world/rules/church.py::enroll`` (design §5.1). This module owns host
resolution (the ``resolve_local_service_host`` pattern), the schedule gate
(``interaction_reason(host, "service_church")``), the stable rejection prose,
and the authored presentation around the deterministic grant — no dialogue
model, no LLM intent participates.
"""

from commands.command import Command

from typeclasses.components import ChurchHost
from world.lore.items import ITEM_REGISTRY
from world.rules.church import EnrollmentError, EnrollmentReason, enroll
from world.rules.guild import GuildServiceError, resolve_local_service_host
from world.rules.npc_schedules import interaction_reason
from world.rules.service_gate import MESSAGE_OFF_ANCHOR

_NO_LOCAL_HOST_LINE = "這裡沒有教會的神職人員。"

_REJECTION_LINES = {
    EnrollmentReason.NOT_A_PLAYER: "只有冒險者能加入教會。",
    EnrollmentReason.ALREADY_ENROLLED: "你已屬光明教會。",
    EnrollmentReason.NO_HOST: _NO_LOCAL_HOST_LINE,
    EnrollmentReason.REMOTE_HOST: _NO_LOCAL_HOST_LINE,
    EnrollmentReason.SERVICE_UNAVAILABLE: MESSAGE_OFF_ANCHOR,
    EnrollmentReason.MALFORMED_LEDGER: "教會記錄異常，暫時無法入教。",
}


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
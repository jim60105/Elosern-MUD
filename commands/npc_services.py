"""Player-facing service discovery for one selected NPC.

``services <npc>`` prints the same derived descriptors the browser receives
from ``world.rules.npc_services.project_npc_services``: stable key, canonical
label, honest availability with its exact reason, and the existing text route
that opens the flow. Discovery is read-only — it selects nothing, starts
nothing, and grants no eligibility; every flow revalidates its exact provider
when the player submits it.
"""

from commands.command import Command
from commands.talk import _AMBIGUOUS_TARGET, resolve_visible_npc

from typeclasses.npcs import NPC
from world.rules.npc_services import project_npc_services, service_report_lines
from world.rules.service_messages import rejection_message
from world.rules.service_targets import (
    ServiceTargetError,
    ServiceTargetReason,
    require_service_target,
    split_terminal_target,
)

_TARGET_NOT_FOUND = rejection_message(ServiceTargetReason.UNKNOWN_TARGET)
_USAGE = "用法：services <npc>"


def split_selected_target(caller, args: str) -> tuple[str, int | None] | None:
    """Split one command line's terminal target, messaging a malformed one.

    Returns ``(remainder, npc_id)``; ``npc_id`` is ``None`` only when no
    suffix was supplied, so the caller keeps its established implicit room
    discovery. A malformed ``@#`` payload messages the shared unknown-target
    refusal and returns ``None``, so it can never fall through to that
    discovery either.
    """
    remainder, npc_id, explicit = split_terminal_target(args)
    if explicit and npc_id is None:
        caller.msg(_TARGET_NOT_FOUND)
        return None
    return remainder, npc_id


def resolve_selected_provider(caller, npc_id: int, component_class: type):
    """Return the exact visible provider for ``npc_id``, or ``None``.

    The admission rechecks visibility, co-presence, capability, binding and
    schedule with no substitution; every refusal renders the shared stable
    reason. Read-only: the caller's domain API still owns its own validation
    and writes.
    """
    try:
        npc, _component = require_service_target(caller, npc_id, component_class)
    except ServiceTargetError as error:
        caller.msg(rejection_message(error))
        return None
    return npc


class CmdServices(Command):
    """查看指定對象目前提供的服務

    用法：
      services <npc>
      服務 <npc>

    列出在場對象目前提供的服務：穩定的服務代號、名稱、是否可用（不可用時
    說明原因），以及前往該服務的既有文字指令。`<npc>` 可寫對方在場的名字或
    別名，也可用 `#<編號>` 指定。察看不會改變任何狀態，也不會代替你選擇服務。
    """

    key = "services"
    aliases = ("服務",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        """Render the selected NPC's projection without any mutation."""
        resolved = resolve_visible_npc(
            self.caller,
            self.args,
            missing=_USAGE,
            ambiguous=_AMBIGUOUS_TARGET,
            not_npc=_TARGET_NOT_FOUND,
        )
        if isinstance(resolved, str):
            self.caller.msg(resolved)
            return
        if not isinstance(resolved, NPC):
            self.caller.msg(_TARGET_NOT_FOUND)
            return
        services = project_npc_services(self.caller, self.caller, resolved)
        self.caller.msg("\n".join(service_report_lines(resolved, services)))

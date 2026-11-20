"""Whole-party inn lodging: quote, confirm and cancel.

``lodging`` prints the current innkeeper's quote for the present party;
``lodging confirm`` commits the exact stored quote; ``lodging cancel`` discards
it. All rule work lives in :mod:`world.rules.lodging`, which the web client's
service route pre-fills as this same command, so both transports agree.
"""

from commands.command import Command
from commands.talk import _AMBIGUOUS_TARGET, resolve_visible_npc

from typeclasses.components import Lodging
from typeclasses.npcs import NPC
from world.rules import lodging

_USAGE = "用法：lodging [<對象>]、lodging confirm [<對象>]、lodging cancel"
_NO_PROVIDER = "這裡沒有提供住宿的對象。"
_QUOTE_PENDING = "住宿登記尚未確認。"
_CANCELLED = "已取消住宿登記。"


def _lodging_host(caller):
    """The one visible present host carrying the lodging capability."""
    location = getattr(caller, "location", None)
    if location is None:
        return None
    visible = location.filter_visible(list(location.contents), caller)
    hosts = [
        obj
        for obj in visible
        if isinstance(obj, NPC)
        and obj.components.has(Lodging.get_component_slot())
    ]
    if not hosts:
        return None
    if len(hosts) > 1:
        return _AMBIGUOUS_TARGET
    return hosts[0]


def _resolve_target(caller, raw: str):
    if not raw:
        return _lodging_host(caller)
    return resolve_visible_npc(
        caller,
        raw,
        missing=_NO_PROVIDER,
        ambiguous=_AMBIGUOUS_TARGET,
        not_npc=_NO_PROVIDER,
    )


class CmdLodging(Command):
    """向旅店老闆詢問並確認整隊住宿

    用法：
      lodging [<對象>]
      lodging confirm [<對象>]
      lodging cancel

    詢問時列出在場的整隊旅客與每人房價；確認只接受剛剛那一份報價，會一次
    扣款、登記並把在場旅客帶進同一間客房，不會順便入睡或推進時間。
    """

    key = "lodging"
    aliases = ("住宿",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self) -> None:
        tokens = self.args.strip().split()
        action = "quote"
        raw_target = ""
        if tokens and tokens[0] in ("confirm", "確認"):
            action = "confirm"
            tokens = tokens[1:]
        elif tokens and tokens[0] in ("cancel", "取消"):
            action = "cancel"
            tokens = tokens[1:]
        if len(tokens) > 1:
            self.caller.msg(_USAGE)
            return
        raw_target = tokens[0] if tokens else ""
        if action == "cancel":
            if raw_target:
                self.caller.msg(_USAGE)
                return
            lodging.clear_pending_quote(self.caller)
            self.caller.msg(_CANCELLED)
            return
        target = _resolve_target(self.caller, raw_target)
        if isinstance(target, str):
            self.caller.msg(target)
            return
        if target is None:
            self.caller.msg(_NO_PROVIDER)
            return
        try:
            if action == "confirm":
                result = lodging.confirm_check_in(self.caller, target)
                self.caller.msg(
                    lodging.check_in_message(result, str(target.key))
                )
            else:
                quote = lodging.quote_for(self.caller, target)
                self.caller.msg(lodging.quote_message(quote, str(target.key)))
        except lodging.LodgingError as error:
            self.caller.msg(error.message)

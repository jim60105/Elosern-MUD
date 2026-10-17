"""Player-facing combat engagement, party commands, exits, and examinations.

The text client reaches exactly the same deterministic party-command facade
the browser adapters call: ``combat command`` admits one actor-scoped
skill/item/tactic draft entry through ``confirm_actor_command`` (the shared
admission that replaces an earlier entry and auto-resolves the one ordinary
round on the completing confirmation), ``combat actions`` renders one actor's
choices plus the whole draft's progress from the canonical combat view, and
``combat retreat``/``combat forfeit`` request or explicitly confirm one
party-scoped exit. No command here inspects or writes persisted state itself.
"""

from typing import Any

from commands.command import Command

from world.rules.action import RejectReason
from world.rules.combat_result import settle_to_messages
from world.rules.combat_session import (
    PARTY_EXIT_RETREAT,
    PARTY_EXIT_SURRENDER,
    CombatSessionError,
    SessionReason,
    confirm_actor_command,
    confirm_party_exit,
    engage,
    is_in_active_session,
    parse_session_targets,
    party_exit_operation_of_token,
    read_session,
    request_party_exit,
    resolve_target_token,
)
from world.rules.combat_view import (
    CombatViewError,
    build_combat_view,
)
from world.rules.guild_exam_request import (
    OUTCOME_SCHEDULE,
    next_exam_rank,
    request_guild_exam,
)
from world.rules.guild_exams import GuildExamError
from world.rules.items import ItemUseReason
from world.rules.event_log import render_plain_text
from world.rules.player_messages import (
    SESSION_REASON_MESSAGES,
    party_exit_prompt_lines,
    rejection_message as action_rejection_message,
    session_reason_message,
)
from world.rules.progression import scale_for_label
from world.rules.service_messages import (
    SERVICE_REASON_MESSAGES,
    exam_schedule_message,
    exam_started_message,
    rejection_message as service_rejection_message,
)
from world.skills.registry import SKILL_REGISTRY, TargetSpec

#: The closed tactic vocabulary of ``combat command`` (the same contract the
#: browser panel publishes).
_TACTIC_KEYS = ("defend", "dodge", "taunt")

_COMBAT_COMMAND_USAGE = (
    "用法：combat command <actor-token> skill <skill_key>[@<scale>][=<targets>]、"
    "combat command <actor-token> item <item_key>[=<target-token>]、"
    "combat command <actor-token> defend|dodge|taunt[=<enemy-token>]"
)

# The draft admission's own closed reason codes, which have no rules-layer
# message table of their own. The wording reuses the shared rejection strings;
# enum reasons (skill ``RejectReason`` / item ``ItemUseReason``) and session
# reasons never come through here.
_DRAFT_REASON_MESSAGES: dict[str, str] = {
    "target_invalid": "這項指令的目標形式不符合。",
    "target_missing": "目標不在這裡。",
    "invalid_tactical_key": "無法確認這項戰術指令。",
    "unknown_kind": "無法確認這項戰鬥指令。",
    "stale_draft_version": "戰鬥階段已經改變，請重新確認。",
    "already_committed": "這項操作已經結算。",
}

_ITEM_TARGET_SPEC_TEXTS = {
    TargetSpec.NONE.value: "無需目標",
    TargetSpec.SELF.value: "指定自己",
}

_NO_TARGET_TEXT = "目前無有效目標"


def _session_or_none(caller: Any) -> Any:
    """Return the caller's parsed session record, or ``None`` after messaging."""
    try:
        record = read_session(caller)
    except CombatSessionError as error:
        caller.msg(session_reason_message(str(error.args[0])))
        return None
    if record is None:
        caller.msg(session_reason_message(str(SessionReason.NO_ACTIVE_SESSION)))
        return None
    return record


def _ally_actor(caller: Any, record: Any, token: str) -> Any:
    """Resolve one actor token to a persisted party member, or ``None``.

    Actor tokens are the same stable ``aN`` aliases target tokens use, but an
    actor always names a party member: a foe token, an absent participant or a
    member the commander may not command reports the shared ``forbidden_actor``
    reason and selects nothing.
    """
    try:
        entity = resolve_target_token(caller, token)
    except CombatSessionError as error:
        caller.msg(session_reason_message(str(error.args[0])))
        return None
    if int(entity.pk) not in {int(dbref) for dbref in record.player_ids}:
        caller.msg(session_reason_message(str(SessionReason.FORBIDDEN_ACTOR)))
        return None
    return entity


def _tokens_by_identity(record: Any) -> dict[int, str]:
    """Map every persisted participant dbref to its session-local token."""
    tokens = {
        int(dbref): f"a{index}"
        for index, dbref in enumerate(record.player_ids, start=1)
    }
    tokens.update(
        {
            int(dbref): f"e{index}"
            for index, dbref in enumerate(record.enemy_ids, start=1)
        }
    )
    return tokens


def _reason_code(raw: Any) -> Any:
    """Return the stable reason of one progress/reselection entry."""
    if isinstance(raw, dict):
        return raw.get("reason", "unknown")
    return raw


def _stable_reason_message(code: str) -> str:
    """Resolve one stable code through every shared player-facing table.

    The admission returns its own string codes, while the skill preflight's
    ``RejectReason`` values and the item preflight's ``ItemUseReason`` values
    arrive as plain code strings. Each domain keeps the exact prose its own
    transport publishes instead of degrading to one generic fallback.
    """
    if code in SESSION_REASON_MESSAGES:
        return SESSION_REASON_MESSAGES[code]
    if code in _DRAFT_REASON_MESSAGES:
        return _DRAFT_REASON_MESSAGES[code]
    if code in SERVICE_REASON_MESSAGES:
        return SERVICE_REASON_MESSAGES[code]
    try:
        return action_rejection_message(RejectReason(code))
    except ValueError:
        return session_reason_message(code)


def _draft_reason_text(reason: Any, *, item_domain: bool = False) -> str:
    """Render one draft-admission rejection through the shared reason surface.

    ``item_domain`` lets an item command keep the exact item/equipment prose
    the browser's inventory surface publishes for the same stable code, where
    the shared tables overlap with the admission's own shape codes.
    """
    if isinstance(reason, RejectReason):
        return action_rejection_message(reason)
    if isinstance(reason, ItemUseReason):
        return service_rejection_message(reason)
    code = str(reason)
    if item_domain and code in SERVICE_REASON_MESSAGES:
        return SERVICE_REASON_MESSAGES[code]
    return _stable_reason_message(code)


def _token_of(tokens: dict[int, str], identity: Any) -> str:
    return tokens.get(int(identity), str(identity))


def _target_text(
    tokens: dict[int, str], descriptor: Any, *, empty_text: str
) -> str:
    """Render one descriptor's selectable targets, or why there are none."""
    if descriptor.targets:
        return "可指定：" + "、".join(
            _token_of(tokens, identity) for identity in descriptor.targets
        )
    target_spec = getattr(descriptor, "target_spec", None)
    return _ITEM_TARGET_SPEC_TEXTS.get(str(target_spec), empty_text)


def _skill_cost_text(skill: Any) -> str:
    if not skill.cost:
        return "無消耗"
    return "、".join(f"{key.upper()} {value}" for key, value in skill.cost.items())


def _scale_text(skill: Any) -> str:
    if not skill.freeform_scales:
        return ""
    entries = "、".join(
        f"{label}（MP {cost}）" for _scale, label, cost in skill.freeform_scales
    )
    return f"｜可調威力：{entries}"


def _entry_targets_text(payload: dict[str, Any], tokens: dict[int, str]) -> str:
    """Render one stored/wire skill payload's targets.

    The persisted draft keeps its internal ``targets_or_shorthand`` spelling
    while the combat view publishes the wire ``target_ids``/``target_shorthand``
    pair; both are rendered the same way here.
    """
    targets = payload.get("target_shorthand")
    if targets is None and isinstance(payload.get("targets_or_shorthand"), str):
        targets = payload["targets_or_shorthand"]
    if targets is not None:
        return str(targets)
    ids = payload.get("target_ids")
    if ids is None:
        ids = payload.get("targets_or_shorthand") or ()
    return (
        "、".join(_token_of(tokens, identity) for identity in ids)
        if ids
        else "無目標"
    )


def _draft_command_text(command: Any, tokens: dict[int, str]) -> str:
    """Render one admitted draft entry in its internal or wire spelling."""
    kind = command.get("kind")
    payload = command.get("payload") or {}
    if kind == "skill":
        scale = payload.get("scale")
        scale_text = (
            f"@{float(scale):g}"
            if isinstance(scale, (int, float)) and float(scale) != 1.0
            else ""
        )
        return (
            f"技能 {payload.get('skill_key')}{scale_text}"
            f"={_entry_targets_text(payload, tokens)}"
        )
    target_id = payload.get("target_id")
    target = "" if target_id is None else f"={_token_of(tokens, target_id)}"
    if kind == "item":
        return f"道具 {payload.get('item_key')}{target}"
    return f"戰術 {payload.get('tactical_key') or payload.get('key')}{target}"


class CmdEngage(Command):
    """Engage a present hostile monster in combat."""

    key = "engage"
    aliases = ("攻擊", "戰鬥")
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self) -> None:
        if is_in_active_session(self.caller):
            self.caller.msg("你已經在戰鬥中了。")
            return
        target_name = self.args.strip().partition(" ")[0]
        if not target_name:
            self.caller.msg("用法：engage <target>")
            return
        target = self.caller.search(target_name)
        if target is None:
            return
        try:
            result = engage(self.caller, target)
        except CombatSessionError as error:
            reason = error.args[0]
            message = {
                SessionReason.NOT_HOSTILE: "這個目標不是敵對魔物。",
                SessionReason.NOT_PRESENT: "目標不在這裡。",
                SessionReason.TARGET_DEAD: "目標已經無法行動。",
                SessionReason.ALREADY_IN_COMBAT: "你已經在戰鬥中了。",
            }.get(reason, "無法開始戰鬥。")
            self.caller.msg(message)
            return
        self.caller.msg("戰鬥開始！請選擇你的行動（cast <技能>[=<目標>]）。")


class _PartyExitCommand(Command):
    """Shared prompt/confirm surface for one party-scoped exit.

    A bare invocation only returns the party-scoped consequence prompt: it
    states the party scope, the consequences, the session/round the
    confirmation binds to, and the exact confirmation syntax with a
    server-issued token. Nothing mutates until the token is confirmed, and
    any other input simply cancels by doing nothing. ``confirm`` executes
    exactly the operation its token binds, so either exit command confirms a
    prompt the other one returned.
    """

    key = ""
    locks = "cmd:all()"
    help_category = "Combat"
    #: The party operation a bare invocation asks the boundary for.
    operation: str = ""

    def func(self) -> None:
        args = self.args.strip()
        if args.partition(" ")[0].lower() == "confirm":
            self._confirm(args.partition(" ")[2].strip())
            return
        if args:
            self.caller.msg(
                f"用法：{self.key}（取得整隊確認提示）、"
                f"{self.key} confirm <token>（確認）"
            )
            return
        self._request()

    def _request(self) -> None:
        """Return the party-scope confirmation prompt without mutating anything."""
        record = _session_or_none(self.caller)
        if record is None:
            return
        try:
            prompt = request_party_exit(
                self.caller,
                record.session_id,
                record.round_revision,
                self.operation,
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        for line in party_exit_prompt_lines(
            prompt["operation"],
            scope_count=len(prompt["party_scope"]),
            session_id=prompt["session_id"],
            round_number=record.rounds_elapsed + 1,
            confirmation_token=prompt["confirmation_token"],
            confirm_command=self.key,
        ):
            self.caller.msg(line)

    def _confirm(self, confirmation_token: str) -> None:
        """Execute the exit one token binds, or report why it cannot."""
        if not confirmation_token:
            self.caller.msg(
                f"用法：{self.key} confirm <token>"
                f"（請先輸入「{self.key}」取得確認提示）"
            )
            return
        operation = party_exit_operation_of_token(confirmation_token)
        record = _session_or_none(self.caller)
        if record is None:
            return
        if operation is None:
            self.caller.msg(
                session_reason_message(str(SessionReason.INVALID_CONFIRMATION_TOKEN))
            )
            return
        try:
            result = confirm_party_exit(
                self.caller,
                record.session_id,
                record.round_revision,
                operation,
                confirmation_token,
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        lines, message = settle_to_messages(result)
        for line in lines:
            self.caller.msg(line)
        self.caller.msg(message)


class CmdCombatForfeit(_PartyExitCommand):
    """Ask for, or explicitly confirm, the party's surrender."""

    key = "combat forfeit"
    aliases = ("combat 投降", "投降")
    operation = PARTY_EXIT_SURRENDER


class CmdCombatRetreat(_PartyExitCommand):
    """Ask for, or explicitly confirm, the party's retreat.

    The retreat is the party's contested escape attempt: it settles through
    its own deterministic contest once confirmed, and an unconfirmed request
    changes nothing.
    """

    key = "combat retreat"
    aliases = ("combat 撤退", "撤退")
    operation = PARTY_EXIT_RETREAT


class CmdCombatCommand(Command):
    """Confirm one party member's command through the shared draft facade.

    ``combat command <actor-token> skill|item|defend|dodge|taunt ...`` selects
    for the named allied member exactly what the browser panel selects for it:
    the same ``confirm_actor_command`` admission reauthorizes the actor,
    validates the skill/item/tactic against that actor's own capabilities and
    costs, replaces any earlier entry and resolves one ordinary round as soon
    as the final required member confirms. The command needs no possession of
    the member it commands.
    """

    key = "combat command"
    aliases = ("combat 指令", "戰鬥指令")
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self) -> None:
        actor_token, _, remainder = self.args.strip().partition(" ")
        remainder = remainder.strip()
        if not actor_token or not remainder:
            self.caller.msg(_COMBAT_COMMAND_USAGE)
            return
        record = _session_or_none(self.caller)
        if record is None:
            return
        actor = _ally_actor(self.caller, record, actor_token)
        if actor is None:
            return
        head, _, target_value = remainder.partition("=")
        verb, _, kind_argument = head.partition(" ")
        command = self._command_for(
            verb.strip().lower(), kind_argument.strip(), target_value.strip()
        )
        if command is None:
            return
        self._submit(record, actor, command)

    def _command_for(
        self, verb: str, kind_argument: str, target_value: str
    ) -> dict[str, Any] | None:
        """Build one internal draft command from the typed text, or ``None``."""
        if verb == "skill":
            return self._skill_command(kind_argument, target_value)
        if verb == "item":
            return self._item_command(kind_argument, target_value)
        if verb in _TACTIC_KEYS:
            return self._tactic_command(verb, kind_argument, target_value)
        self.caller.msg(_COMBAT_COMMAND_USAGE)
        return None

    def _skill_command(
        self, skill_argument: str, target_value: str
    ) -> dict[str, Any] | None:
        skill_key, at, scale_token = skill_argument.partition("@")
        skill_key = skill_key.strip()
        if not skill_key:
            self.caller.msg(_COMBAT_COMMAND_USAGE)
            return None
        scale = 1.0
        if at:
            label = scale_token.strip()
            parsed_scale = scale_for_label(label)
            if parsed_scale is None:
                # A non-label magnitude is the same stable rejection the
                # ``cast`` scale token reports; nothing is selected.
                self.caller.msg(
                    action_rejection_message(RejectReason.SCALED_CAST_FORBIDDEN)
                )
                return None
            scale = parsed_scale
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is not None and skill.target_spec in (
            TargetSpec.NONE,
            TargetSpec.SELF,
        ):
            # NONE carries no target and SELF binds the selected actor inside
            # the rules layer, so supplied target tokens are ignored exactly
            # like the shared facade's empty-target input: a SELF skill named
            # for a2 always acts on a2.
            targets: Any = []
        else:
            parsed_targets = self._targets(target_value)
            if parsed_targets is None:
                return None
            targets = parsed_targets
        return {
            "kind": "skill",
            "payload": {
                "skill_key": skill_key,
                "targets_or_shorthand": targets,
                "scale": scale,
            },
        }

    def _targets(self, target_value: str) -> list[int] | str | None:
        """Parse one target value into the facade's explicit token list."""
        try:
            parsed = parse_session_targets(
                self.caller, target_value, search=self._search
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return None
        if isinstance(parsed, str):
            return parsed
        return [int(target.pk) for target in parsed]

    def _one_target(self, target_value: str) -> int | None | str:
        """Resolve at most one explicit target identity for an item/tactic.

        Returns the target dbref, ``None`` when no target was given, or the
        string ``"invalid"`` when the value names more than one participant
        (an item use and a Taunt each take exactly one target).
        """
        if not target_value:
            return None
        parsed = self._targets(target_value)
        if parsed is None:
            return "invalid"
        if isinstance(parsed, str) or len(parsed) != 1:
            return "invalid"
        return parsed[0]

    def _item_command(
        self, item_argument: str, target_value: str
    ) -> dict[str, Any] | None:
        if not item_argument:
            self.caller.msg(_COMBAT_COMMAND_USAGE)
            return None
        target_id = self._one_target(target_value)
        if target_id == "invalid":
            return self._invalid_target()
        return {
            "kind": "item",
            "payload": {"item_key": item_argument, "target_id": target_id},
        }

    def _tactic_command(
        self, verb: str, kind_argument: str, target_value: str
    ) -> dict[str, Any] | None:
        if kind_argument:
            self.caller.msg(_COMBAT_COMMAND_USAGE)
            return None
        if verb != "taunt":
            if target_value:
                return self._invalid_target()
            return {
                "kind": "tactical",
                "payload": {"tactical_key": verb, "target_id": None},
            }
        target_id = self._one_target(target_value)
        if target_id == "invalid":
            return self._invalid_target()
        if target_id is None:
            # A Taunt names exactly one living enemy; the local shape check
            # reports the same stable reason the rules boundary would.
            return self._invalid_target()
        return {
            "kind": "tactical",
            "payload": {"tactical_key": verb, "target_id": target_id},
        }

    def _invalid_target(self) -> None:
        self.caller.msg(_draft_reason_text("target_invalid"))
        return None

    def _search(self, name: str):
        matches = self.caller.search(name, quiet=True)
        return matches[0] if len(matches) == 1 else None

    def _submit(self, record: Any, actor: Any, command: dict[str, Any]) -> None:
        """Admit one command through the shared facade and render its result."""
        try:
            result = confirm_actor_command(
                self.caller,
                record.session_id,
                record.round_revision,
                record.draft_version,
                int(actor.pk),
                command,
            )
        except CombatSessionError as error:
            self.caller.msg(session_reason_message(str(error.args[0])))
            return
        outcome = result.get("outcome")
        if outcome == "rejected":
            self.caller.msg(
                _draft_reason_text(
                    result.get("reason"),
                    item_domain=command.get("kind") == "item",
                )
            )
            return
        if outcome == "draft":
            # The shared settlement renderer owns the admitted-draft prose.
            _draft_lines, message = settle_to_messages(result)
            self.caller.msg(message)
            for line in _draft_progress_lines(self.caller, result):
                self.caller.msg(line)
            return
        lines, message = settle_to_messages(result)
        for line in lines:
            self.caller.msg(line)
        self.caller.msg(message)


def _draft_progress_lines(caller: Any, result: dict[str, Any]) -> tuple[str, ...]:
    """Render one admitted edit's remaining party progress."""
    record = read_session(caller)
    tokens = _tokens_by_identity(record) if record is not None else {}
    lines = []
    admitted = result.get("draft_entries") or {}
    if admitted:
        for identity, entry in sorted(admitted.items()):
            lines.append(
                f"{_token_of(tokens, identity)} 已選："
                f"{_draft_command_text(entry, tokens)}"
            )
    missing = tuple(result.get("missing_actors") or ())
    if missing:
        lines.append(
            "尚需選擇："
            + "、".join(_token_of(tokens, identity) for identity in missing)
        )
    for identity, reason in (result.get("reselection_reasons") or {}).items():
        lines.append(
            f"{_token_of(tokens, identity)} 需要重新選擇："
            f"{_draft_reason_text(_reason_code(reason))}"
        )
    return tuple(lines)


class CmdCombatActions(Command):
    """List one actor's choices and the party draft's progress in combat."""

    key = "combat actions"
    aliases = ("combat 動作", "戰鬥動作")
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self) -> None:
        if not is_in_active_session(self.caller):
            self.caller.msg("目前沒有進行中的戰鬥。")
            return
        record = _session_or_none(self.caller)
        if record is None:
            return
        try:
            view = build_combat_view(self.caller)
        except CombatViewError:
            self.caller.msg("目前無法顯示戰鬥動作。")
            return
        if view.recovery:
            self.caller.msg(
                "戰鬥紀錄異常，無法列出動作。可使用「投降」或「撤退」結束戰鬥。"
            )
            return
        requested = self.args.strip().partition(" ")[0]
        if requested:
            entity = _ally_actor(self.caller, record, requested)
            if entity is None:
                return
            try:
                view = build_combat_view(self.caller, for_actor=entity)
            except CombatViewError:
                self.caller.msg(self._member_reason(view, int(entity.pk)))
                return
        else:
            # The default actor is the commander; a commander who cannot act
            # right now still gets the canonical view rather than no listing.
            try:
                view = build_combat_view(self.caller, for_actor=self.caller)
            except CombatViewError:
                pass
        self.caller.msg("\n".join(self._lines(view, record)))

    def _member_reason(self, view: Any, identity: int) -> str:
        """Return the member-specific reason that actor cannot be commanded."""
        for actor in view.actors:
            if actor.identity == identity and actor.reason is not None:
                return actor.reason[1]
        return session_reason_message(str(SessionReason.FORBIDDEN_ACTOR))

    def _lines(self, view: Any, record: Any) -> list[str]:
        tokens = _tokens_by_identity(record)
        participants = {p.identity: p for p in view.participants}
        choices = view.choices
        actor_name = (
            participants[choices.actor_id].display_name
            if choices is not None and choices.actor_id in participants
            else ""
        )
        lines = [
            f"目前列出 {_token_of(tokens, choices.actor_id)}＝{actor_name} 的可用指令："
            if choices is not None
            else "目前沒有可列出的指令。",
            "可用技能與目標代號：",
        ]
        for category in choices.skills if choices is not None else ():
            lines.append(f"◆ {category.label}")
            for sub_group in category.groups:
                if sub_group.label is not None:
                    lines.append(f"  {sub_group.label}")
                for skill in sub_group.skills:
                    target_tokens = [
                        p.token
                        for p in view.participants
                        if p.identity in skill.valid_target_ids
                    ]
                    if target_tokens:
                        targets = "可指定：" + "、".join(target_tokens)
                    elif skill.target_spec == TargetSpec.NONE.value:
                        targets = "無需目標"
                    elif skill.target_spec == TargetSpec.SELF.value:
                        targets = "指定自己"
                    else:
                        targets = _NO_TARGET_TEXT
                    status = (
                        "可用"
                        if skill.enabled
                        else skill.reason_message or "無法使用"
                    )
                    lines.append(
                        f"  {skill.key}（{skill.label}）：{status}"
                        f"｜{_skill_cost_text(skill)}{_scale_text(skill)}｜{targets}"
                    )
        lines.append("目標代號：")
        lines.append(
            "  "
            + "、".join(
                f"{p.token}＝{p.display_name}" for p in view.participants
            )
        )
        lines.append("可使用道具：")
        items = choices.items if choices is not None else ()
        if not items:
            lines.append("  （沒有可用於本回合的道具）")
        for item in items:
            status = (
                "可用"
                if item.enabled
                else (item.reason[1] if item.reason else "無法使用")
            )
            lines.append(
                f"  {item.item_key}（{item.label}）×{item.quantity}：{status}"
                f"｜{_target_text(tokens, item, empty_text=_NO_TARGET_TEXT)}"
            )
        lines.append("戰術：")
        for tactic in choices.tactics if choices is not None else ():
            status = (
                "可用"
                if tactic.enabled
                else (tactic.reason[1] if tactic.reason else "無法使用")
            )
            lines.append(
                f"  {tactic.key}（{tactic.label}）：{status}"
                f"｜{_target_text(tokens, tactic, empty_text='無需目標')}"
            )
        lines.extend(self._draft_lines(view, tokens))
        lines.append(_COMBAT_COMMAND_USAGE)
        lines.append(
            "最後一位成員確認後會自動執行本回合；"
            "cast <技能>[=<代號>] 與使用 <道具> [目標] 亦可確認你自己的指令。"
        )
        return lines

    def _draft_lines(self, view: Any, tokens: dict[int, str]) -> list[str]:
        draft = view.draft
        if draft is None:
            return []
        lines = [f"本回合指令進度（第 {draft.round_revision} 版）："]
        if draft.required_actor_ids:
            lines.append(
                "  必要成員："
                + "、".join(
                    _token_of(tokens, identity)
                    for identity in draft.required_actor_ids
                )
            )
        if draft.entries:
            for entry in draft.entries:
                lines.append(
                    f"  {_token_of(tokens, entry.actor_id)} 已選："
                    f"{_draft_command_text(entry.command, tokens)}"
                )
        else:
            lines.append("  尚無已確認的指令。")
        if draft.needs_selection_ids:
            lines.append(
                "  尚需選擇："
                + "、".join(
                    _token_of(tokens, identity)
                    for identity in draft.needs_selection_ids
                )
            )
        for reselection in draft.reselection_reasons:
            lines.append(
                f"  {_token_of(tokens, reselection.actor_id)} 需要重新選擇："
                f"{_stable_reason_message(reselection.reason[0])}"
            )
        return lines


class CmdGuildExam(Command):
    """Ask the guild counter to arrange your next promotion examination.

    With the qualified examiner present this starts the simulated-battle
    examination; with the examiner away the counter answers the examiner's
    next planned attendance at the guild. Nothing is reserved either way.
    """

    key = "guild exam"
    aliases = ("guild 考核", "公會考核")
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self) -> None:
        target_rank = self.args.strip().partition(" ")[0] or next_exam_rank(self.caller)
        if target_rank is None:
            self.caller.msg(service_rejection_message("top_rank"))
            return
        try:
            outcome = request_guild_exam(self.caller, target_rank, requested_by="command")
        except GuildExamError as error:
            self.caller.msg(service_rejection_message(error))
            return
        if outcome.kind == OUTCOME_SCHEDULE:
            self.caller.msg(exam_schedule_message(
                outcome.host_name, outcome.target_rank,
                outcome.interval.start_tick, outcome.interval.end_tick,
            ))
            return
        self.caller.msg(
            exam_started_message(outcome.target_rank)
            + "請選擇你的行動（cast <技能>[=<目標>]）。"
        )

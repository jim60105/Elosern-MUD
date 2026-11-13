"""Text parity for the finite, offline-safe collaborative dream surface."""

import json

from commands.command import Command
from world.narrative.dream_proposal import LIST_FIELDS

_USAGE = (
    "用法：dream [enter|decline|thread [編號|new]|say <文字>|finalize|"
    "draft [願望]|confirm [願望]|awaken]"
)

_NO_DREAM = "目前沒有夢境。請先睡眠；主人未附身時會詢問是否進入夢境。"
_NEW_STORY = "一段新的故事"
LIST_LABELS = {
    "themes": "主題",
    "atmosphere": "氛圍",
    "participants": "人物",
    "emphasis": "描寫",
    "exclusions": "避開",
}
REQUIREMENT_LABELS = {
    "place": "指定的地點",
    "new_character": "需要的新角色",
    "private_commission": "私人委託",
}
# A thread argument that names nothing offered: distinct from ``None``, which
# is the offered new-story choice.
_UNKNOWN_THREAD = object()


def _changed_field(label, added, removed) -> str:
    """One field's line segment: its label once, then what moved either way."""
    if not added and not removed:
        return ""
    text = label
    if added:
        text += "新添" + "".join(f"「{item}」" for item in added)
    if removed:
        text += "劃去" + "".join(f"「{item}」" for item in removed)
    return text


def render_changes(changes) -> str:
    """The last settled exchange's edits on one line, or the none line.

    ``None`` means no exchange has settled, so there is nothing to report and
    the state shows no line at all. A report that names nothing changed is a
    settled exchange that edited nothing, and says so.
    """
    if not changes:
        return ""
    parts = []
    if changes.get("summary") == "formed":
        parts.append("願望成形")
    elif changes.get("summary") == "changed":
        parts.append("願望更動")
    lists = changes.get("lists") or {}
    for field in LIST_FIELDS:
        change = lists.get(field) or {}
        parts.append(_changed_field(
            LIST_LABELS[field], change.get("added"), change.get("removed"),
        ))
    requirements = changes.get("requirements") or {}
    parts.append(_changed_field(
        "需求",
        [str(row.get("text", "")) for row in requirements.get("added") or []],
        [str(row.get("text", "")) for row in requirements.get("removed") or []],
    ))
    parts = [part for part in parts if part]
    if not parts:
        return "女神這次沒有更動願望。"
    return "女神為你改了：" + "；".join(parts) + "。"


def _thread_text(state) -> str:
    """The wish's thread in words: a new story, a named offer, or a lost one."""
    thread_id = state.get("thread_id")
    if not thread_id:
        return _NEW_STORY
    for choice in state.get("thread_choices") or []:
        if choice.get("id") == thread_id:
            return f"延續：{choice.get('label', '')}"
    return "先前選定的故事線"


def render_wish(state) -> str:
    """The whole working wish as one readable block, skipping empty parts."""
    proposal = state.get("proposal") or {}
    summary = str(proposal.get("summary") or "").strip()
    lines = [f"此刻的願望：{summary}" if summary else "此刻的願望：尚未成形。"]
    for field in LIST_FIELDS:
        items = proposal.get(field) or []
        if items:
            lines.append(LIST_LABELS[field] + "：" + "、".join(str(item) for item in items))
    rows = proposal.get("requirements") or []
    if rows:
        lines.append("這個願望需要：" + "、".join(
            REQUIREMENT_LABELS.get(str(row.get("kind", "")), str(row.get("kind", "")))
            + f"「{row.get('text', '')}」"
            for row in rows
        ))
    lines.append("歸屬：" + _thread_text(state))
    return "\n".join(lines)


def render_threads(state) -> str:
    """The offered threads as numbered choices, or the already-fixed thread."""
    if not state.get("can_choose_thread"):
        return "願望的歸屬已經定下：" + _thread_text(state)
    lines = ["0 或 new：" + _NEW_STORY]
    for number, choice in enumerate(state.get("thread_choices") or [], start=1):
        lines.append(f"{number}：{choice.get('label', '')}")
    return "\n".join(lines)


def _hints(state) -> list[str]:
    """The operations this stage allows, in the order the player needs them."""
    hints = []
    if state.get("can_choose_thread") and state.get("thread_choices"):
        hints.append("dream thread [編號|new]：決定願望的歸屬（說出第一句話後便不能再改）")
    if state.get("can_input"):
        hints.append("dream say <想說的話>")
    if state.get("can_finalize"):
        hints.append("dream finalize：停止訴說，親自修改願望")
    if state.get("can_edit"):
        hints.append("dream draft [願望]：把願望收著 ／ dream confirm [願望]：許下這個願望")
        hints.append("願望也可使用 JSON，指定各欄位。")
    elif state.get("can_draft"):
        hints.append("dream draft：把願望收著")
    return hints


def render_state(state, *, changes_last=False) -> str:
    """The stage's prose, the whole wish, its change line and the next steps."""
    if state is None:
        return _NO_DREAM
    parts = [state["opening"], state["scene"], state["dialogue"],
             f"剩餘訴說次數：{state['remaining']}。"]
    if state["pending"]:
        parts.append("女神正在回應，你仍可把願望收著或醒來。")
    if state["failure"]:
        parts.append("回應暫時無法生成，這次不算數；你仍可把願望收著或醒來。")
    parts.append(render_wish(state))
    changes = render_changes(state.get("changes"))
    # The report sits with the wish while the conversation can still move it.
    # A delivered message ends with it instead, including the sixth exchange
    # that closes free text in the same settlement that produced the report.
    if not changes_last and state.get("stage") == "conversing":
        parts.append(changes)
    parts.extend(_hints(state))
    parts.append(state["ending"] or "dream awaken")
    if changes_last:
        parts.append(changes)
    return "\n".join(part for part in parts if part)


def _resolve_thread(state, argument):
    """The thread an argument names, or ``None`` for the offered new story."""
    choices = state.get("thread_choices") or []
    if argument.lower() == "new" or argument == "0":
        # The listing offers both spellings, so both resolve to a new story.
        return None
    if argument.isdecimal():
        number = int(argument)
        if 1 <= number <= len(choices):
            return choices[number - 1].get("id")
    for choice in choices:
        if choice.get("id") == argument:
            return argument
    return _UNKNOWN_THREAD


class CmdDream(Command):
    """Review a dream wish, choose its thread, speak, finalize, edit or awaken.

    Usage: dream [enter|decline|thread [number|new]|say <text>|finalize|draft [wish]|confirm [wish]|awaken]
    """

    key = "dream"
    aliases = ("夢境",)

    def func(self):
        from server.dream_service import (
            act,
            answer_sleep_dream,
            dream_state,
            pending_sleep_question,
        )
        from world.rules.time_skip import owner_sleep_view_state

        state = dream_state(self.caller)
        if not self.args.strip():
            question = pending_sleep_question(self.caller)
            if question is not None:
                self.caller.msg(question)
                return
            self.caller.msg(render_state(state))
            return
        action, _, text = self.args.strip().partition(" ")
        if action in {"enter", "decline"}:
            if text:
                self.caller.msg(_USAGE)
                return
            view = owner_sleep_view_state(self.caller)
            if view is None:
                self.caller.msg("目前沒有等待回答的睡眠夢境問題。")
                return
            answer = answer_sleep_dream(
                self.caller,
                decision=action,
                sleep_id=view["sleep_id"],
                revision=view["revision"],
                generation=view["generation"],
                session=self.session,
            )
            self.caller.msg(answer["message"])
            current = dream_state(self.caller)
            if current is not None and current["open"]:
                self.caller.msg(render_state(current))
            return
        if state is None:
            self.caller.msg(render_state(None))
            return
        changes_last = action == "say"

        def completed(value):
            if value["outcome"] == "rejected":
                self.caller.msg(value["message"])
            current = dream_state(self.caller)
            if current["open"]:
                delivered = changes_last and value["outcome"] == "success"
                self.caller.msg(render_state(current, changes_last=delivered))
            return value

        if action == "thread":
            argument = text.strip()
            if not argument:
                self.caller.msg(render_threads(state))
                return
            thread_id = _resolve_thread(state, argument)
            if thread_id is _UNKNOWN_THREAD:
                self.caller.msg("找不到這條故事線。輸入 dream thread 查看可選的編號。")
                return
            result = act(
                self.caller, "choose_thread", session_id=state["session_id"],
                revision=state["revision"], thread_id=thread_id,
                session=self.session,
            )
            result.addCallback(completed)
            return result
        if action not in {"say", "finalize", "draft", "confirm", "awaken"} or (
                action in {"awaken", "finalize"} and text):
            self.caller.msg(_USAGE)
            return
        direction = text if action in {"draft", "confirm"} else ""
        if direction.lstrip().startswith("{"):
            try:
                direction = json.loads(direction)
            except json.JSONDecodeError:
                # observability: ignore R2: malformed player JSON is a local syntax refusal; no persistent state or generation is touched
                self.caller.msg("故事方向 JSON 格式無法讀取。")
                return
        result = act(
            self.caller, action, session_id=state["session_id"],
            revision=state["revision"], message=text if action == "say" else "",
            direction=direction,
            session=self.session,
        )
        result.addCallback(completed)
        return result

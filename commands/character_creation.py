"""Player-facing character creation command and pending command gate."""

import evennia
from evennia import CmdSet
from evennia.commands.cmdhandler import CMD_NOMATCH, CMD_NOINPUT
from world.observability import log_error, log_warn
from evennia.utils.evmenu import InputCmdSet
from evennia.utils.utils import inherits_from, strip_control_sequences

from commands.command import Command
from commands.localized import CmdHelp, CmdQuit
from server.ai_director_service import request_character_proposal
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    max_affinity_elements,
    resolve_starting_profile,
)
from world.rules.creation_wizard import (
    ALLOCATION_AXIS_EXPLANATIONS,
)

# The concept input bound mirrors the generative layer's prompt-side cap
# (``MAX_CONCEPT_LENGTH`` in the character-creation layer module); the command
# enforces the same bound up front so an over-long concept is rejected before
# any generative call. A parity test keeps the two in lock step.
MAX_CONCEPT_LENGTH = 500

_UNAVAILABLE_MESSAGE = "生成不可用，請手動創角"
_CONCEPT_USAGE = "用法：character concept <構想>"


def _integer(response: str, field: str) -> int:
    if response.strip().lower() == "cancel":
        raise CharacterCreationError("角色建立已取消")
    try:
        return int(response.strip())
    except ValueError as error:
        raise CharacterCreationError(f"{field} 必須是整數。") from error



def _collect_affinity_elements(
    race: str, max_elements: int
):
    """Yield the affinity-choice prompt and collect the race-bounded set.

    A generator driven by the wizard's ``yield`` machinery. Human (0-2) and
    beastfolk (0-1) players pick from the eight lore elements; an elf skips the
    prompt entirely (its set is seeded from the chosen subrace, never
    player-chosen).
    """
    element_lines = "\n".join(
        f"  {key}：{ELEMENT_REGISTRY[key].display_name_zh}"
        for key in ELEMENT_REGISTRY
    )
    prompt = (
        f"屬性親和（可選擇 0–{max_elements} 個，各屬性以空格分隔，"
        f"留空表示無，可輸入 cancel 取消）：\n{element_lines}\n"
    )
    response = (yield prompt).strip()
    if response.lower() == "cancel":
        raise CharacterCreationError("角色建立已取消")
    if not response:
        return ()
    keys = [key for key in response.split() if key]
    if len(keys) > max_elements:
        raise CharacterCreationError(
            f"屬性親和最多只能選擇 {max_elements} 個屬性"
        )
    return tuple(keys)


def creation_start_screen() -> str:
    """Render the no-argument ``character`` presentation (design.md D6).

    A world-view framing line followed by one preview line per preset drawn
    entirely from immutable registry data: the race one-liner, the allocation
    emphasis, and the background. Reused by ``CmdCharacter.func`` and by the
    ``Account.at_post_login`` login coordinator.
    """
    lines = ["你站在伊洛瑟恩大陸的門口，世界正等待你的名字。", "可選擇的預設角色："]
    for key, preset in PLAYER_PRESET_REGISTRY.items():
        race = RACE_REGISTRY[preset.race]
        lines.append(
            f"  {key}（{preset.display_name}）：{race.description} "
            f"｜配點：{preset.emphasis}｜背景：{preset.background}"
        )
    lines.append("請選擇角色建立方式。")
    lines.append(f"預設角色：character preset <key>（{'、'.join(PLAYER_PRESET_REGISTRY)}）")
    lines.append("自訂角色：character create")
    lines.append("構想角色：character concept <構想>")
    return "\n".join(lines)


def _activate_creation(
    account,
    caller,
    request: CharacterCreationRequest,
    *,
    persona=None,
) -> None:
    """Activate one pending shell through the ordinary all-or-nothing path.

    Shared by every creation entry (preset, custom wizard, concept proposal):
    the deterministic preflight (adult gate, registry checks, allocation
    bands) is the only authority, and a failure leaves the shell pending with
    no state change. ``persona`` carries the server-owned persona block from
    the concept draft when one exists; the activation persists it in the
    import-card shape inside the same all-or-nothing transaction.

    A concept proposal rides the request as a transient form-filler: its
    background and affinity elements arrive as ordinary custom-request fields
    (an absent proposal field is ``None``, which the custom validator
    normalises to no background / neutral affinity), and the preflight stays
    the sole authority over them.
    """
    try:
        result = activate_player_character(
            account, caller, request, persona=persona
        )
    except CharacterCreationError as error:  # observability: ignore R2: player-facing recovery; the reason is rendered to the caller and the draft stays retryable
        caller.msg(f"角色建立失敗：{error}")
        return
    from world.rules.onboarding import (
        maybe_play_arrival,
        relocate_to_starting_location,
    )

    # Portrait finalization (named ``portrait_policy`` + post-commit ensure)
    # runs INSIDE the activation transaction through the shared
    # ``finalize_player_portrait``, so a rolled-back creation never writes a
    # policy or emits a job (fix-creation-finalization-safety D3).
    relocate_to_starting_location(caller)
    # Release a concept prompt chain a competing surface may have opened on
    # this shell (the async rack's ndb slot survives its cmdset eviction;
    # the stale continuation itself self-cleans through its release check on
    # any further input, and the sync rack self-cleans via CmdGetInput).
    if hasattr(caller.ndb, "concept_prompt"):
        del caller.ndb.concept_prompt
    caller.msg(
        f"角色 {result.display_name} 已建立，初始魔力為 {result.magic_power}。"
    )
    maybe_play_arrival(caller)


class CmdCharacter(Command):
    """建立角色。用法：character、character preset <key>、character create"""

    key = "character"
    aliases = ("角色",)

    def _activate(self, request: CharacterCreationRequest) -> None:
        _activate_creation(self.account, self.caller, request)

    def func(self):
        args = self.args.strip().split()
        if not args:
            self.caller.msg(creation_start_screen())
            return
        if args[0].lower() == "preset":
            if len(args) != 2:
                self.caller.msg("用法：character preset <key>")
                return
            self._activate(CharacterCreationRequest(mode="preset", preset_key=args[1]))
            return
        if args != ["create"]:
            self.caller.msg("用法：character preset <key> 或 character create")
            return

        try:
            name = yield "角色姓名（輸入 cancel 取消）："
            if name.strip().lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            age = _integer((yield "實際年齡（至少 18，可輸入 cancel 取消）："), "實際年齡")
            apparent_age = _integer((yield "外表年齡（至少 18，可輸入 cancel 取消）："), "外表年齡")
            race_explanations = "\n".join(
                f"  {key}：{RACE_REGISTRY[key].description}" for key in RACE_REGISTRY
            )
            race = (yield (
                f"種族（{'、'.join(RACE_REGISTRY)}，可輸入 cancel 取消）：\n"
                f"{race_explanations}\n"
            )).strip()
            if race.lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            available = [key for key, value in SUBRACE_REGISTRY.items() if value.race_key == race]
            if not available:
                raise CharacterCreationError(f"種族 {race} 沒有可用的子種族")
            subrace_lines = "\n".join(
                f"  {key}：{SUBRACE_REGISTRY[key].display_name_zh}（{SUBRACE_REGISTRY[key].common_name_zh}）"
                f"——{SUBRACE_REGISTRY[key].specialty}"
                for key in available
            )
            prompt = (
                f"子種族（請選擇一個，可輸入 cancel 取消）：\n{subrace_lines}\n"
            )
            subrace = (yield prompt).strip()
            if subrace.lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            if subrace not in available:
                raise CharacterCreationError(
                    f"子種族必須是 {race} 的已註冊子種族（{'、'.join(available)}）"
                )
            affinity_max = max_affinity_elements(race)
            affinity_elements: tuple[str, ...] = ()
            if affinity_max > 0:
                # Human/beastfolk collect a race-bounded affinity pick; an elf
                # picks none (its set is seeded from the subrace, D4).
                affinity_elements = yield from _collect_affinity_elements(
                    race, affinity_max
                )
            profile = resolve_starting_profile(race, subrace)
            briefing_lines = [
                f"配點說明：共 {len(ALLOCATABLE_AXES)} 個項目，可用點數 {profile.budget}。",
            ]
            for axis, (lower, upper) in profile.bounds:
                span = upper - lower
                label = ALLOCATION_AXIS_EXPLANATIONS.get(axis, "")
                briefing_lines.append(f"  {axis} {label}：0–{span}")
            briefing_lines.append(f"七項配點總和必須恰好等於 {profile.budget}。")
            self.caller.msg("\n".join(briefing_lines))
            allocations: dict[str, int] = {}
            for axis, (lower, upper) in profile.bounds:
                span = upper - lower
                explanation = ALLOCATION_AXIS_EXPLANATIONS.get(axis, "")
                allocations[axis] = _integer(
                    (yield f"{axis} 配點（0–{span}）：{explanation}\n"), axis
                )
            background = (yield (
                f"背景設定（風味文字，可留空或輸入 cancel 取消，上限 {MAX_PERSONA_FIELD_LENGTH} 字）："
            )).strip()
            if background.lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            if len(background) > MAX_PERSONA_FIELD_LENGTH:
                raise CharacterCreationError(
                    f"背景設定超過 {MAX_PERSONA_FIELD_LENGTH} 字上限"
                )
            background = background or None
            affinity_label = (
                "、".join(
                    f"{key}（{ELEMENT_REGISTRY[key].display_name_zh}）"
                    for key in affinity_elements
                )
                or "無"
            )
            summary = (
                f"姓名 {name.strip()}，年齡 {age}/{apparent_age}，種族 {race}，"
                f"子種族 {subrace}，屬性親和 {affinity_label}，配點總和 "
                f"{sum(allocations.values())}/{profile.budget}。"
                f"輸入 yes 確認，或 cancel 取消："
            )
            confirmation = (yield summary).strip().lower()
            if confirmation != "yes":
                self.caller.msg("已取消角色建立。")
                return
            self._activate(CharacterCreationRequest(
                mode="custom", display_name=name, age=age,
                apparent_age=apparent_age, race=race, subrace=subrace,
                allocations=allocations, background=background,
                affinity_elements=affinity_elements,
            ))
        except CharacterCreationError as error:  # observability: ignore R2: player-facing recovery; cancel and invalid-input outcomes reach the caller
            if str(error) == "角色建立已取消":
                self.caller.msg("已取消角色建立。")
            else:
                self.caller.msg(f"輸入無效：{error} 請重新執行 character create。")


def _proposal_summary(proposal) -> str:
    """Render the proposal summary: race, subrace, allocations, and previews.

    The transient concept flow persists nothing: the summary IS the terminal
    form fill, the player's completion of the name/age prompts turns the
    proposal into their own input, and the persona prose activates with the
    request (retool-concept-transient-fill D6).

    The five transient-fill fields ride the summary so the player reads every
    value the flow is about to adopt before completing the prompts
    (prefill-telnet-concept-from-proposal D3). An absent field is worded
    distinctly from an explicitly neutral one: ``（未提案…）`` versus the
    normalized empty affinity set's ``（無）``.
    """
    race = RACE_REGISTRY[proposal.race_key]
    subrace = SUBRACE_REGISTRY[proposal.subrace_key]
    lines = [
        "角色提案（依你的構想生成）：",
        f"種族：{proposal.race_key}（{race.description}）",
        f"子種族：{proposal.subrace_key}（{subrace.display_name_zh}——{subrace.specialty}）",
        "配點：" + "、".join(
            f"{axis} {value}" for axis, value in proposal.allocations.items()
        ),
    ]
    if proposal.suggested_skills:
        lines.append("建議技能（僅供參考）：" + "、".join(proposal.suggested_skills))
    else:
        lines.append("建議技能（僅供參考）：無")
    if proposal.affinity_elements is None:
        affinity_text = "（未提案）"
    elif not proposal.affinity_elements:
        affinity_text = "（無）"
    else:
        affinity_text = "、".join(
            ELEMENT_REGISTRY[key].display_name_zh
            for key in proposal.affinity_elements
        )
    lines.extend(
        [
            "姓名："
            + (
                _terminal_safe(proposal.display_name)
                if proposal.display_name is not None
                else "（未提案，將由你輸入）"
            ),
            "實際年齡："
            + (
                str(proposal.age)
                if proposal.age is not None
                else "（未提案，將由你輸入）"
            ),
            "外表年齡："
            + (
                str(proposal.apparent_age)
                if proposal.apparent_age is not None
                else "（未提案，將由你輸入）"
            ),
            "背景："
            + (
                _terminal_safe(proposal.background)
                if proposal.background is not None
                else "（未提案，將留空）"
            ),
            "元素親和：" + affinity_text,
        ]
    )
    lines.extend(
        [
            "人設（將寫入角色檔案，啟動後可另行修改）：",
            f"  性格：{_terminal_safe(proposal.persona['personality'])}",
            f"  人生經歷：{_terminal_safe(proposal.persona['life_story'])}",
            f"  習慣：{_terminal_safe(proposal.persona['habit'])}",
            "接下來請確認或輸入角色姓名與年齡以完成建立：",
        ]
    )
    return "\n".join(lines)


def _terminal_safe(value: str) -> str:
    """Render proposal-derived text inertly on the telnet surfaces.

    LLM reply text is data, never presentation: the generative normaliser
    trims and truncates but does not sanitize, so the summary and prompts
    neutralise terminal control sequences, collapse any residual C0 control
    (CR/LF/tab) to spaces, and double Every Evennia ``|`` markup escape
    before interpolation. Activation keeps the untouched normalised value;
    only rendering is inert-ified.
    """
    text = strip_control_sequences(value)
    text = "".join(ch if ch >= " " else " " for ch in text)
    return text.replace("|", "||")


def _name_prompt(default: str | None) -> str:
    """Render the name prompt, prefilled when the proposal carries a value."""
    if default is None:
        return "角色姓名（輸入 cancel 取消）："
    return (
        f"角色姓名（預設：{_terminal_safe(default)}，Enter 採納，"
        "cancel 取消）："
    )


def _age_prompt(label: str, default: int | None) -> str:
    """Render one age prompt, prefilled when the proposal carries a value."""
    if default is None:
        return f"{label}（至少 18，可輸入 cancel 取消）："
    return (
        f"{label}（預設：{default}，Enter 採納，至少 18，"
        "可輸入 cancel 取消）："
    )


def _collect_age(reply: str, label: str, default: int | None) -> int:
    """Resolve one age reply: an empty reply accepts the prefilled default.

    With no default the existing ``_integer`` authority stays fully in charge
    (empty input remains its format-error outcome); a non-empty reply always
    goes through ``_integer``, so the ``cancel`` parse and the deterministic
    adult gate keep their exact current semantics
    (prefill-telnet-concept-from-proposal D1/D2).
    """
    if default is not None and not reply.strip():
        return default
    return _integer(reply, label)


class CmdCharacterConcept(Command):
    """以構想生成角色提案。用法：character concept <構想>"""

    key = "character concept"
    aliases = ("構想",)

    def _reject_invalid_concept(self) -> str | None:
        """Return the bounded concept or ``None`` after messaging a rejection.

        Empty and over-bound concepts are rejected with a named error before
        any generative call is made.
        """
        raw = self.args.strip()
        if not raw:
            self.caller.msg(_CONCEPT_USAGE)
            return None
        if len(raw) > MAX_CONCEPT_LENGTH:
            self.caller.msg(f"構想過長：請控制在 {MAX_CONCEPT_LENGTH} 字以內。")
            return None
        return raw

    def func(self):
        concept = self._reject_invalid_concept()
        if concept is None:
            return
        deferred = request_character_proposal(concept=concept)
        if deferred.called:
            proposal = self._resolve_fired(deferred)
            if proposal is None:
                return
            yield from self._complete_interactively(proposal)
            return
        self.caller.msg("正在生成角色提案，請稍候……")
        deferred.addCallback(self._on_proposal_ready)
        deferred.addErrback(self._on_proposal_failed)

    def _resolve_fired(self, deferred):
        """Resolve an already-fired proposal Deferred to a proposal or ``None``.

        A Failure result propagates (a genuine registration or pipeline bug
        must surface loudly in tests); ``None`` — the layer's degraded marker —
        maps to the stable unavailable message.
        """
        from twisted.python.failure import Failure

        if isinstance(deferred.result, Failure):
            deferred.result.raiseException()
        if deferred.result is None:
            self.caller.msg(_UNAVAILABLE_MESSAGE)
            return None
        return deferred.result

    def _on_proposal_ready(self, proposal):
        if proposal is None:
            self.caller.msg(_UNAVAILABLE_MESSAGE)
            return
        self._start_interactive(proposal)

    def _on_proposal_failed(self, failure):
        self.caller.msg(_UNAVAILABLE_MESSAGE)
        return None

    def _start_interactive(self, proposal):
        """Drive the interactive continuation on the live async path.

        The proposal resolved asynchronously, so the cmdhandler's progressive
        generator machinery is no longer available. The continuation runs
        through a dedicated high-priority prompt cmdset
        (``_ConceptPromptCmdSet``): the prompt command feeds each player reply
        into the continuation generator with ``generator.send`` and re-prompts
        or finishes exactly like the cmdhandler's ``_progressive_cmd_run``
        loop. The set's priority outranks the pending-character gate, whose
        ``Replace`` merge would otherwise drop Evennia's default input set and
        swallow every answer with the creation-required gate.
        """
        if not bool(getattr(self.caller, "creation_pending", False)):
            # The character was already activated (or the flow otherwise
            # completed) while the proposal was in flight; the proposal is
            # moot and must not start a stale prompt chain.
            self.caller.msg(_UNAVAILABLE_MESSAGE)
            return
        generator = self._complete_interactively(proposal)
        self.caller.ndb.concept_prompt = {
            "generator": generator,
            "feeder": self._feed_input,
        }
        self.caller.cmdset.add(_ConceptPromptCmdSet, persistent=False)
        try:
            first_prompt = next(generator)
        except StopIteration:  # observability: ignore R2: control flow; an instantly-exhausted generator is a completed prompt
            self._finish_prompt()
            return
        self.caller.msg(first_prompt)

    def _feed_input(self, caller, result, generator):
        """Feed one reply into the continuation and re-prompt or finish.

        ``_CmdConceptPrompt.func`` invokes this as its input callback: the
        reply is sent into the continuation generator; a yielded string
        becomes the next prompt, and ``StopIteration`` clears the prompt state
        and restores the pending-character gate.
        """
        try:
            value = generator.send(result)
        except StopIteration:  # observability: ignore R2: control flow; generator completion is the prompt's normal end
            self._finish_prompt()
            return
        caller.msg(value)

    def _finish_prompt(self):
        if hasattr(self.caller.ndb, "concept_prompt"):
            del self.caller.ndb.concept_prompt
        while self.caller.cmdset.has(_ConceptPromptCmdSet):
            self.caller.cmdset.remove(_ConceptPromptCmdSet)
        self.at_post_cmd()

    def _complete_interactively(self, proposal):
        """Present the proposal and collect the remaining player-entered fields.

        A generator driven by the cmdhandler (sync path) or by
        ``_start_interactive``/``_feed_input`` (async path). The concept is a
        transient form-filler (retool-concept-transient-fill D6): nothing is
        persisted before or during the prompts. The name and both ages are
        collected as proposal-prefilled defaults
        (prefill-telnet-concept-from-proposal D1/D2): each prompt names the proposal's
        normalised value for its field, an empty reply accepts that default,
        and any non-empty reply overrides it — with the deterministic adult
        gate staying the final authority over either source. A prompt whose
        proposal field is absent stays a mandatory input; for the name, an
        empty or whitespace-only reply re-prompts the same prompt instead of
        proceeding to an activation doomed to be rejected. The activation
        writes the proposal's values — race, subrace, allocations, persona
        block, background, affinity — plus the accepted-or-entered name and
        ages in the same all-or-nothing transaction, exactly like the
        browser's save of a proposal-filled form.
        """
        self.caller.msg(_proposal_summary(proposal))

        def _released() -> bool:
            # A competing surface (browser activation) may complete the
            # character while a prompt chain is open. The next reply then
            # releases the continuation quietly: the sync rack self-cleans
            # after feeding (CmdGetInput), and the async feeder's
            # StopIteration path removes the prompt cmdset — either way a
            # stale chain never keeps consuming the player's commands or
            # resumes toward an activation doomed by the pending gate.
            return not bool(getattr(self.caller, "creation_pending", False))

        try:
            name_prompt = _name_prompt(proposal.display_name)
            while True:
                reply = yield name_prompt
                # A programmatically driven generator (test harness, headless
                # send) can deliver None where the live racks always deliver a
                # string; a missing reply is an Enter.
                reply = reply if isinstance(reply, str) else ""
                if _released():
                    return
                if reply.strip().lower() == "cancel":
                    self.caller.msg("已取消角色建立。")
                    return
                if reply.strip():
                    # Pass the raw reply on: the rules-layer display-name
                    # validator owns stripping, exactly as before the
                    # prefill flow existed.
                    name = reply
                    break
                if proposal.display_name is not None:
                    name = proposal.display_name
                    break
                # Mandatory name with a blank reply: re-prompt in place —
                # an empty Enter must never doom the whole activation.
            age_reply = yield _age_prompt("實際年齡", proposal.age)
            if _released():
                return
            age = _collect_age(
                age_reply if isinstance(age_reply, str) else "",
                "實際年齡",
                proposal.age,
            )
            apparent_reply = yield _age_prompt("外表年齡", proposal.apparent_age)
            if _released():
                return
            apparent_age = _collect_age(
                apparent_reply if isinstance(apparent_reply, str) else "",
                "外表年齡",
                proposal.apparent_age,
            )
        except CharacterCreationError as error:  # observability: ignore R2: player-facing recovery; cancel and invalid-input outcomes reach the caller
            if str(error) == "角色建立已取消":
                self.caller.msg("已取消角色建立。")
            else:
                self.caller.msg(f"輸入無效：{error} 請重新執行 character concept。")
            return
        _activate_creation(
            self.account,
            self.caller,
            CharacterCreationRequest(
                mode="custom",
                display_name=name,
                age=age,
                apparent_age=apparent_age,
                race=proposal.race_key,
                subrace=proposal.subrace_key,
                allocations=dict(proposal.allocations),
                background=proposal.background,
                affinity_elements=proposal.affinity_elements,
            ),
            persona=dict(proposal.persona),
        )


class _CmdConceptPrompt(Command):
    """Prompt-state command that feeds player replies into the continuation.

    Mounted by ``_ConceptPromptCmdSet`` while a live async proposal's
    interactive continuation is open. Every input (including empty input,
    via the ``CMD_NOINPUT`` alias) is routed to the stored feeder, mirroring
    Evennia's own ``CmdGetInput`` prompt command but at a priority that
    survives the pending-character gate's ``Replace`` merge.
    """

    key = CMD_NOMATCH
    aliases = (CMD_NOINPUT,)

    def func(self) -> None:
        caller = self.caller
        pending = getattr(caller.ndb, "concept_prompt", None)
        if pending is None:
            while caller.cmdset.has(_ConceptPromptCmdSet):
                caller.cmdset.remove(_ConceptPromptCmdSet)
            return
        try:
            pending["feeder"](caller, self.raw_string.rstrip(), pending["generator"])
        except Exception as error:
            # Never leak the prompt state or leave the gate replaced; the
            # deterministic wizard stays usable and the player can retry.
            log_warn(
                "character_creation_concept_feed_failed",
                exc=error,
                context={"char": getattr(caller, "pk", 0) or 0},
            )
            if hasattr(caller.ndb, "concept_prompt"):
                del caller.ndb.concept_prompt
            while caller.cmdset.has(_ConceptPromptCmdSet):
                caller.cmdset.remove(_ConceptPromptCmdSet)
            caller.msg("|r提示流程發生錯誤，請重新執行 character concept。|n")


class _ConceptPromptCmdSet(CmdSet):
    """Prompt set for the live async concept continuation.

    Priority outranks ``CharacterCreationCmdSet`` (200) so the ``Replace``
    merge keeps this set's prompt command instead of the creation gate's
    ``CMD_NOMATCH`` command. During the prompt every input is consumed by
    ``_CmdConceptPrompt``; removing the set restores the gate.
    """

    key = "ConceptPrompt"
    priority = 250
    mergetype = "Replace"
    no_exits = True
    no_objs = True
    no_channels = True

    def at_cmdset_creation(self) -> None:
        self.add(_CmdConceptPrompt)


class CmdCreationRequired(Command):
    """Explain why an ordinary command is unavailable during creation.

    The pending-character gate wins the ``__nomatch_command`` system-command
    dedup against Evennia's ``InputCmdSet`` (priority 200 > 1), so every reply
    to an open wizard ``get_input`` prompt lands here instead of on Evennia's
    ``CmdGetInput``. When a prompt is actually open (``caller.ndb._getinput``
    is set), this command routes the reply into the stored callback exactly
    like ``CmdGetInput.func`` — resuming the wizard's ``yield`` chain —
    instead of rejecting it with the creation-required message.
    """

    key = CMD_NOMATCH
    aliases = (CMD_NOINPUT,)

    def func(self) -> None:
        caller = self.caller
        try:
            getinput = caller.ndb._getinput
            if not getinput and inherits_from(caller, evennia.DefaultObject):
                getinput = caller.account.ndb._getinput
                if getinput:
                    caller = caller.account
            if not getinput:
                # No wizard prompt is open: preserve the exact gate behavior
                # for every unmatched in-world command (and now also empty
                # lines).
                self.caller.msg("你必須先完成角色建立。請輸入 character 查看建立方式。")
                return
            callback = getinput._callback
            caller.ndb._getinput._session = self.session
            prompt = caller.ndb._getinput._prompt
            args = caller.ndb._getinput._args
            kwargs = caller.ndb._getinput._kwargs
            result = self.raw_string.rstrip()  # strip the ending line break

            ok = not callback(caller, prompt, result, *args, **kwargs)
            if ok:
                # only clear the state if the callback does not return
                # anything
                del caller.ndb._getinput
                caller.cmdset.remove(InputCmdSet)
        except Exception as error:
            # never leak the prompt state or leave the gate replaced; the
            # deterministic wizard stays usable and the player can retry.
            # ``caller`` may have been reassigned to the account in the
            # fallback branch; deleting on the (possibly absent) key is a
            # quiet no-op for Evennia's in-memory nattr backend.
            log_error(
                "character_creation_input_error",
                exc=error,
                context={"char": getattr(caller, "pk", 0) or 0},
            )
            del caller.ndb._getinput
            caller.msg("|rError in get_input. Choice not confirmed (report to admin)|n")
            caller.cmdset.remove(InputCmdSet)


class CharacterCreationCmdSet(CmdSet):
    """High-priority replacement set for an uninitialized player shell."""

    key = "CharacterCreation"
    priority = 200
    mergetype = "Replace"
    no_exits = True
    no_objs = True

    def at_cmdset_creation(self) -> None:
        self.add(CmdCharacter)
        self.add(CmdCharacterConcept)
        self.add(CmdCreationRequired)
        self.add(CmdHelp)
        self.add(CmdQuit)

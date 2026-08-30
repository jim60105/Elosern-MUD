"""Player-facing character creation command and pending command gate."""

import evennia
from evennia import CmdSet, Command
from evennia.commands.cmdhandler import CMD_NOMATCH, CMD_NOINPUT
from evennia.utils import logger
from evennia.utils.evmenu import InputCmdSet
from evennia.utils.utils import inherits_from

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
    ConceptDraftStaleError,
    apply_concept_proposal,
    draft_fingerprint,
    read_draft,
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
    """
    try:
        result = activate_player_character(
            account, caller, request, persona=persona
        )
    except CharacterCreationError as error:
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
        except CharacterCreationError as error:
            if str(error) == "角色建立已取消":
                self.caller.msg("已取消角色建立。")
            else:
                self.caller.msg(f"輸入無效：{error} 請重新執行 character create。")


def _draft_matches_concept(draft, proposal) -> bool:
    """True when the stored draft is still the applied concept draft.

    The name/age prompts run after the concept-apply; another session or entry
    could replace the draft while they are open. Activation must refuse to mix
    the stale proposal's finite controls with a newer draft's state
    (creation-persona-persistence D2).
    """
    if draft is None or draft.get("mode") != "concept":
        return False
    return (
        draft.get("race") == proposal.race_key
        and draft.get("subrace") == proposal.subrace_key
        and draft.get("allocations") == dict(proposal.allocations)
    )


def _proposal_summary(proposal) -> str:
    """Render the proposal summary: race, subrace, allocations, and previews.

    Suggested skills and the persona draft are informational in this change:
    nothing is persisted, and the player completes the flow through the
    ordinary activation path.
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
    lines.extend(
        [
            "人設草稿（僅供預覽）：",
            f"  性格：{proposal.persona['personality']}",
            f"  人生經歷：{proposal.persona['life_story']}",
            f"  習慣：{proposal.persona['habit']}",
            "接下來請輸入角色姓名與年齡以完成建立：",
        ]
    )
    return "\n".join(lines)


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
        # The draft fingerprint is captured before the generative call; the
        # concept-apply service compares against it so a late response can
        # never overwrite a draft changed by another session or entry
        # (creation-persona-persistence D2).
        self._concept_fingerprint = draft_fingerprint(self.caller)
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
        except StopIteration:
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
        except StopIteration:
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
        ``_start_interactive``/``_feed_input`` (async path). The concept draft
        is saved through the deterministic apply service FIRST (so a mid-flow
        disconnect resumes from the draft and both Telnet and the WebClient
        share one apply service), then the summary and prompts collect the
        display name and both ages through the existing prompts and the
        deterministic adult gate — the proposal never supplies them — and the
        activation persists the draft's persona block in the same
        all-or-nothing transaction.
        """
        try:
            apply_concept_proposal(
                self.account,
                self.caller,
                {
                    "race_key": proposal.race_key,
                    "subrace_key": proposal.subrace_key,
                    "allocations": dict(proposal.allocations),
                    "persona": dict(proposal.persona),
                },
                expected_fingerprint=self._concept_fingerprint,
            )
        except ConceptDraftStaleError:
            self.caller.msg("構想草稿已被修改，請重新執行 character concept。")
            return
        except CharacterCreationError as error:
            self.caller.msg(f"角色建立失敗：{error}")
            return
        self.caller.msg(_proposal_summary(proposal))
        try:
            name = yield "角色姓名（輸入 cancel 取消）："
            if name.strip().lower() == "cancel":
                self.caller.msg("已取消角色建立。")
                return
            age = _integer((yield "實際年齡（至少 18，可輸入 cancel 取消）："), "實際年齡")
            apparent_age = _integer((yield "外表年齡（至少 18，可輸入 cancel 取消）："), "外表年齡")
        except CharacterCreationError as error:
            if str(error) == "角色建立已取消":
                self.caller.msg("已取消角色建立。")
            else:
                self.caller.msg(f"輸入無效：{error} 請重新執行 character concept。")
            return
        draft = read_draft(self.caller)
        if not _draft_matches_concept(draft, proposal):
            # Another session or entry replaced the applied concept draft while
            # the name/age prompts were open; activating with the stale
            # proposal values would mix old finite controls with whatever the
            # newer draft carries. Reject instead (creation-persona-persistence
            # D2).
            self.caller.msg("構想草稿已被修改，請重新執行 character concept。")
            return
        persona = draft.get("persona") if draft is not None else None
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
            ),
            persona=persona,
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
        except Exception:
            # Never leak the prompt state or leave the gate replaced; the
            # deterministic wizard stays usable and the player can retry.
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
        except Exception:
            # never leak the prompt state or leave the gate replaced; the
            # deterministic wizard stays usable and the player can retry.
            # ``caller`` may have been reassigned to the account in the
            # fallback branch; deleting on the (possibly absent) key is a
            # quiet no-op for Evennia's in-memory nattr backend.
            del caller.ndb._getinput
            caller.msg("|rError in get_input. Choice not confirmed (report to admin)|n")
            logger.log_trace("Error in get_input")
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

## Why

The interactive custom-creation wizard is stuck in a dead end: after `character create`
prints `角色姓名（輸入 cancel 取消）：`, every reply — the name, the age, and even `cancel` —
is swallowed by the pending-character gate and answered with
`你必須先完成角色建立。請輸入 character 查看建立方式。` The player can neither enter a name
nor cancel, and the stuck prompt state persists. The same defect hits the
`character concept <構想>` flow whenever its proposal resolves synchronously.

Root cause (verified against the merged cmdset): Evennia's progressive-command machinery
(`yield` inside `func`) collects replies through `evmenu.get_input`, which mounts
`InputCmdSet` (priority 1, `Replace`) whose `CmdGetInput` uses the system key
`__nomatch_command`. The pending-character gate `CharacterCreationCmdSet` (priority 200,
`Replace`) also ships a `__nomatch_command` command, `CmdCreationRequired`. During cmdset
merging, system commands (`__*` keys) are deduplicated by key/alias matchset with the
higher-priority set winning, so `CmdGetInput` is dropped and `CmdCreationRequired` wins.
Every wizard reply is therefore dispatched to the creation-required message while
`ndb._getinput` and `InputCmdSet` stay mounted. The async concept continuation already
works around this with a higher-priority prompt set (`_ConceptPromptCmdSet`, 250 > 200);
only the synchronous `yield` paths were left broken.

## What Changes

- The gate's `__nomatch_command` handler becomes prompt-aware: when an Evennia
  `get_input` prompt is open on the caller (`ndb._getinput`), it feeds the reply into
  that prompt's callback exactly like Evennia's own `CmdGetInput` (including state
  cleanup), so the wizard's `yield` chain resumes normally.
- The handler also covers `__noinput_command`, so empty replies (e.g. a blank subrace)
  reach the wizard instead of being dropped, and `cancel` cancels at any step.
- Replies that match a command the gate exposes (`character`, `說明`, `登出`) keep
  running as commands — stock Evennia behavior for every `get_input` prompt; the
  wizard stays open and its prompt state is untouched.
- When no prompt is open, the handler keeps today's exact behavior: every unmatched
  in-world command (now including empty lines, previously silent) is rejected with the
  creation-required message.
- The same fix restores the `character concept` sync-fired interactive continuation,
  which uses the identical `yield` machinery.
- The async concept prompt set (`_ConceptPromptCmdSet`) is untouched and keeps winning
  over the gate during its own prompts.
- No command keys, aliases, syntaxes, or docs change: `docs/game/commands.md` and
  `docs/game/command-reference.md` already promise that the wizard accepts `cancel`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `player-character-creation`: the pending-character gate requirement gains the
  exception that open wizard prompt replies are routed to the wizard (not rejected),
  so the creation-only gate cannot strand a player mid-wizard, and that wizard
  completion/cancellation/failure tears prompt state down.
- `character-creation-ux`: custom creation's interactive prompts are usable end to end
  through the real command pipeline — every unmatched or empty reply is delivered to
  the wizard, `cancel` always exits cleanly, and replies matching gate-exposed
  commands run those commands instead.

## Impact

- `commands/character_creation.py`: `CmdCreationRequired` (extended to route open
  `get_input` prompts, key `__nomatch_command` plus `__noinput_command` alias);
  `CharacterCreationCmdSet` unchanged in priority/mergetype (the Replace-gate contract
  and its existing tests stay intact).
- Tests: new regression coverage in `commands/tests/test_character_creation.py`
  (merged-cmdset contract, direct handler behavior, and real-handler end-to-end runs
  using a queued-`deferLater` fixture that preserves Evennia's cleanup-before-resume
  ordering); existing wizard unit tests must stay green.
- No Evennia-core, dependency, schema, or docs changes.

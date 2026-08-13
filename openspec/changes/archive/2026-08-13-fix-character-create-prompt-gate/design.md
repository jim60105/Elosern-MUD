## Context

The interactive custom-creation wizard (`character create`, and the synchronously-fired
`character concept` continuation) is implemented with Evennia's progressive-command
machinery: `func()` is a generator whose `yield "prompt text"` pauses for player input.
The cmdhandler (`cmdhandler._progressive_cmd_run`) collects each reply through
`evmenu.get_input`, which:

1. stores the pending state on `caller.ndb._getinput` (callback, prompt, session, args),
2. mounts `InputCmdSet` (priority 1, `Replace`, key `input_cmdset`) whose
   `CmdGetInput` has key `__nomatch_command` and alias `__noinput_command`,
3. sends the prompt text.

On a reply, `CmdGetInput.func` feeds `self.raw_string.rstrip()` to the stored callback
and, when the callback returns falsy, clears `ndb._getinput` and removes `InputCmdSet`.

The pending-character gate `CharacterCreationCmdSet` (priority 200, `Replace`,
`no_exits`/`no_objs`) also provides a `__nomatch_command` system command,
`CmdCreationRequired`, which prints the creation-required message. During cmdset
merging, Evennia deduplicates system commands (`__*` keys) by key/alias matchset with
the higher-priority set winning (`CmdSet.__add__` / `cmdset.add` in
`evennia/commands/cmdset.py`). A merge probe confirmed the outcome: the merged set
contains `CmdCreationRequired` and **not** `CmdGetInput`.

Consequently every wizard reply — name, age, `cancel`, everything — is dispatched to
`CmdCreationRequired`, printing `你必須先完成角色建立。請輸入 character 查看建立方式。`
while `ndb._getinput` and `InputCmdSet` stay mounted. The async concept continuation
already dodges this with `_ConceptPromptCmdSet` (priority 250, `Replace`), which wins
the same dedup against the gate and feeds its own stored generator; only the sync
`yield` paths were left broken.

## Goals / Non-Goals

**Goals:**
- Every reply to an open wizard `get_input` prompt reaches the wizard, so the
  `yield` chain resumes: names, ages, races, allocations, `yes`/`cancel`, and empty
  replies (blank subrace) all behave as the wizard defines.
- `cancel` exits the wizard cleanly at any step, with prompt state fully torn down.
- All other gate behavior is preserved: unmatched in-world input still gets the
  creation-required message; the gate stays `Replace`, priority 200, `no_exits`,
  `no_objs`; `CmdQuit`/`CmdHelp` are untouched.
- Fix both broken flows (`character create` and the sync-fired `character concept`
  continuation) with one mechanism; the async concept prompt set is not disturbed.
- Regression tests reproduce the reported failure through the real cmdhandler.

**Non-Goals:**
- No rework of the async concept prompt machinery (`_ConceptPromptCmdSet` /
  `_CmdConceptPrompt`).
- No re-architecture of the wizard to a custom feeder (larger diff, more risk).
- No changes to Evennia core, command keys/aliases/syntax, player docs, or the
  deterministic activation path in `world.rules.character_creation`.
- Typing `character create` again while a prompt is already open re-enters the wizard
  and orphanes the old prompt — stock Evennia behavior outside the gate too; out of
  scope.

## Decisions

### D1: Make the gate's no-match handler prompt-aware (chosen)

Extend `CmdCreationRequired` so `func()` first looks up `caller.ndb._getinput` and,
when a prompt is open, behaves exactly like Evennia's `CmdGetInput.func`:

- `result = self.raw_string.rstrip()`
- invoke `callback(caller, prompt, result, *args, **kwargs)`; the stock `_process_input`
  callback re-schedules `_progressive_cmd_run` via `deferLater` and returns falsy, so
  the wizard generator resumes and the handler then cleans up: `del caller.ndb._getinput`
  and `caller.cmdset.remove(InputCmdSet)` (the handler-level `remove` drops every
  stacked `input_cmdset`, matching stock chained-prompt teardown). A truthy callback
  return keeps the prompt state, exactly like stock.
- Exceptions during the callback mirror stock behavior: clean up the prompt state and
  log the trace, so a broken flow can never strand the gate again.

When no prompt is open, the handler falls back to the exact current creation-required
message.

Scope boundary: this routing only covers input that reaches the handler — unmatched
commands and empty input. Replies that match a command the gate exposes (`character`,
`角色`, `說明`, `登出`) are dispatched to that command by the parser before the handler
is ever consulted, which is stock Evennia behavior for `get_input` prompts everywhere
and matches the game docs (`docs/game/command-reference.md`: 說明 and 登出 remain
available during creation). A reply whose text equals such a key therefore runs the
command rather than becoming a wizard reply; the wizard remains open (its prompt state
is untouched by unrelated commands).

Rationale: the gate set already wins the `__nomatch_command` dedup against
`InputCmdSet`, so the winning command is the single place that must learn to route
prompt replies. This reuses Evennia's own prompt state (`_getinput`), callback, and
`deferLater` resume path, so the wizard code (`CmdCharacter.func`,
`_complete_interactively`) needs zero changes.

Alternatives rejected:
- **Raise `InputCmdSet`'s priority above 200** — would require patching
  `evennia.utils.evmenu` or replacing `get_input` everywhere; touches Evennia core.
- **`Union` mergetype on the gate** — breaks the documented/tested Replace contract
  (`test_pending_gate_is_replace_and_blocks_world_commands`) and would leak world
  commands into the pending shell.
- **A dedicated high-priority prompt cmdset per prompt** (the concept-flow pattern)
  — would need lifecycle hooks at wizard start and every completion/cancel/error to
  mount and unmount it, and would consume gate-exposed commands like `character` and
  說明 during prompts (as the async concept set does today); the existing
  `InputCmdSet` lifecycle already tracks the narrower stock behavior.
- **Refuse to run the wizard through `yield` at all** — rewrite of the sync flows;
  out of proportion to the defect.

### D2: Add the `__noinput_command` alias to the handler

The handler gets `aliases = (CMD_NOINPUT,)`. `cmdset.get(CMD_NOINPUT)` resolves via
matchset equality, so an empty reply reaches the handler (and thus the wizard — e.g.
the blank-subrace prompt) instead of being dropped silently. When no prompt is open,
an empty line now prints the creation-required message where previously it was
silent — a deliberate, consistent-with-gate-policy consequence.

### D3: Leave the async concept prompt set as-is

`_ConceptPromptCmdSet` (priority 250) still beats the gate (200) in the
`__nomatch_command` dedup, and its `_CmdConceptPrompt` uses its own `ndb.concept_prompt`
state, never `_getinput`. Both prompt mechanisms coexist: the gate handler only ever
sees input outside async-prompt windows.

### D4: Three-layer regression tests

The end-to-end tests must not mock `cmdhandler.deferLater` to fire synchronously: the
real reactor order is reply-command cleanup **first** (the handler deletes the old
`_getinput` and removes `InputCmdSet`), then the deferred resume **later** (the
generator mounts the next prompt). A synchronous mock would resume the generator
inside the reply command and the handler's trailing cleanup would then wipe the newly
mounted next prompt. Instead the tests capture the deferred callbacks in a queue,
finish the `execute_cmd` that produced them, and then drain the queue in order,
reproducing the reactor's cleanup-before-resume sequence.

1. **Merged-cmdset contract** — merge `InputCmdSet` + `CharacterCreationCmdSet` exactly
   as the cmdhandler does; assert the surviving `__nomatch_command` command is an
   instance of `CmdCreationRequired` (not `CmdGetInput`, which must be absent) and that
   `cmdset.get(CMD_NOINPUT)` resolves to it. Pins the exact failure mode (before the
   fix, the survivor ignores `_getinput`).
2. **Direct handler behavior** — with a stub `ndb._getinput` + mock callback,
   `func()` forwards `raw_string`; a callback returning falsy triggers cleanup
   (`_getinput` deleted, `input_cmdset` removed from the stack) while a truthy
   callback keeps both; without `_getinput` it emits the creation-required message and
   mutates nothing; a throwing callback still cleans up. A separate case covers the
   stock account-level fallback (prompt state on `caller.account.ndb._getinput` is
   routed with the account as the callback's caller and torn down there).
3. **Real-handler end-to-end** — with the queued-`deferLater` mock:
   - `char1.execute_cmd("character create")` shows the name prompt and mounts
     `_getinput`;
   - `execute_cmd("cancel")` then draining the queue exits with `已取消角色建立`,
     leaves the shell pending, and tears `_getinput`/`InputCmdSet` down;
   - a full success run (name, ages, race, subrace, allocations, `yes`) activates the
     shell;
   - an invalid reply (non-integer age) reports the input error and tears the prompt
     state down;
   - the sync `character concept` continuation with an already-fired proposal reaches
     the name prompt and `cancel` exits cleanly.
   Before the fix, the first reply fails with the creation-required message — the
   user's exact report.

## Risks / Trade-offs

- [The handler must stay behaviorally identical to stock `CmdGetInput` or the wizard
  chain breaks subtly] → replicate stock logic verbatim (including the account-level
  `_getinput` fallback, the truthy-callback keep behavior, and the error path), with
  tests asserting both forwarding and cleanup.
- [An exception inside the callback could leave `_getinput` mounted and swallow later
  input forever] → cleanup runs on the exception path too; a test covers a throwing
  callback.
- [Empty input during the gate becomes vocal instead of silent] → intended and
  consistent with the gate's "reject everything" policy; recorded as a scenario in the
  `player-character-creation` delta spec.
- [A wizard reply equal to a gate-exposed command key (`character`, `角色`, `說明`,
  `登出`) runs that command instead of reaching the wizard — stock Evennia behavior
  for every `get_input` prompt] → documented in the specs as an explicit scenario;
  the wizard's prompt state is untouched by such input, and `cancel`/ordinary names
  are unaffected.
- [Evennia's system-command dedup is implicit; an upstream change could alter it] →
  Evennia 6.1.0 is pinned in this project, and the merged-cmdset contract test keeps
  the behavior visible.
- [The wizard still re-enters if the player types `character create` mid-prompt]
  → accepted stock behavior; the stale `_getinput` is overwritten by the new prompt,
  and activation/all-or-nothing semantics are unaffected.
- [The queued-`deferLater` mock must not be mistaken for a synchronous one in future
  test edits] → the queue helper is a small shared fixture documented in the test
  module docstring, and the multi-step wizard tests fail loudly if the drain step is
  omitted (the next prompt never mounts).

## Migration Plan

Unreleased project with no users in the wild: no data migration or backward
compatibility layer. The change is a behavioral fix inside one command file plus
tests; rollback is a revert of the command change.

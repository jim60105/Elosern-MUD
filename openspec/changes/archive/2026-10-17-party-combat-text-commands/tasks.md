# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Mount actor command/action-list syntax with deterministic token resolution; test actor versus target identity, skill scale and duplicate/unknown/mixed target rejection.
  - `commands/combat.py` adds `CmdCombatCommand` (`combat command`, aliases `combat 指令`/`戰鬥指令`), mounted on `CharacterCmdSet`: one actor token from the persisted participant order (`a1`, `a2`, …) is reauthorized against `record.player_ids`, then `skill <skill_key>[@<scale>][=<targets>]`, `item <item_key>[=<target-token>]` and `defend|dodge|taunt[=<enemy-token>]` build the exact internal command the guarded browser payloads translate into and admit it through the one `confirm_actor_command` facade. `CmdCombatActions` takes an optional actor token and renders cost/scale, items, tactics and draft progress, defaulting to the commander.
  - Evidence: `commands.tests.test_combat_actions` (41 cases with the exit module) — actor and target tokens independent on the same session (`a2` acting on `e1`, then `a1` acting on `e1` completing the round), foe/absent actor tokens rejecting with `forbidden_actor`/`unknown_session_id`, the scale label reaching the shared mastery gate plus the non-label rejection, duplicate/unknown/mixed/shorthand-mixed target values rejecting with no draft, round or resource change, SELF/NONE skills ignoring supplied target tokens and binding the selected actor, a valid `@1/2` scale admitted with the actor's own halved MP cost, and text payloads equal to the guarded adapter's translation for skill/item/tactic.

## 2. Bounded implementation and evidence (1.5h)

- [x] 2.1 Route companion skill/item/tactic confirmation and commander legacy cast/use through the shared facade; test replacing earlier choice, last-auto-round, no cost before complete and local item consumption.
  - Companion skill/item/tactic selections and the commander's own `cast`/`use` all enter `confirm_actor_command`: one admitted entry per actor, replacement bumps `draft_version` while keeping a single entry, and only the confirmation that completes every required actor resolves exactly one ordinary round. Item rejections keep the item surface's own prose (the admission returns item codes as strings), reselection reasons resolve through the shared tables, and the `combat actions` hint no longer advertises an `=` form `使用` does not parse.
  - Evidence: `commands.tests.test_combat_actions` — replacing a companion skill with a companion item keeps one entry and advances `draft_version` by one; no MP, item or round is consumed before the completing confirmation, and the completing confirmation consumes the companion's own item at its resolution; `cast`/`use` in a two-actor session save only the commander entry and cannot execute the incomplete round; `item_not_held`/`hp_full` render the exact item reason prose; a companion entry invalidated by its own resource change is reported per member with its specific reason.

## 3. Bounded implementation and evidence (1h)

- [x] 3.1 Implement retreat/forfeit token prompts and all allied flee aliases; test explicit cancellation, stale/replayed token and unchanged enemy flee.
  - `CmdCombatForfeit` and the new `CmdCombatRetreat` (`combat retreat`, aliases `combat 撤退`/`撤退`) share one `_PartyExitCommand` base: a bare invocation returns that operation's party-scoped prompt, and `<command> confirm <token>` executes exactly the operation the token binds, so either entry point confirms a prompt the other returned. In-combat `cast flee` (and its `施法`/`c` aliases) requests the same retreat prompt and now names the retreat command; any other continuation cancels without mutating anything.
  - Evidence: `commands.tests.test_combat_exit_commands` — the retreat prompt names `combat retreat confirm` and mutates nothing, an unrelated continuation cancels with the draft/revision/session untouched, a token replayed after its round advanced reports `stale_round_revision` and settles nothing while a fresh live token settles once, a retreat prompt issued by `cast flee` is confirmed at the `combat forfeit` entry point and executes the retreat, and every exit token binds a party operation while an allied personal flee still rejects with `personal_flee_forbidden` (the enemy's own disengagement policy is untouched).

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Update both command docs and curated command manifest for every key/alias/syntax/context change; test command-doc parity and document no possession requirement.
  - `docs/game/command-reference.md` gains canonical `combat retreat` and `combat command` entries and updates `combat actions`, `combat forfeit`, `使用` and the in-combat `flee` prose; `docs/game/commands.md` carries the same keys, syntax, confirmation and draft-routing facts. Both state that commanding or inspecting a member needs no possession. The curated `EXPECTED_COMMANDS` manifest carries the two new keys plus the new `combat actions [<actor-token>]` syntax.
  - Evidence: `uv run --locked python -m unittest tests.test_command_docs` → 30 tests OK, including the new assertion that both documents carry the skill/item/tactic syntax, `combat retreat confirm <token>`, `combat actions [<actor-token>]` and the no-possession rule, alongside the alias/syntax/context/overview contract checks.

## 5. Bounded implementation and evidence (1h)

- [x] 5.1 Exercise a real text command path for multiple actors, skill, item, revision and confirmed exit in isolated encounters; record outputs and reconnect restoration.
  - Evidence: `commands.tests.test_combat_actions` — `FullTextPartyRoundTests` runs one bounded encounter through the real commands: `combat actions` reports the required members, the companion's skill and the commander's skill resolve the first round, the companion's item and the commander's `defend` resolve the second (inventory consumed, draft emptied), and the requested retreat prompt's own token exits the party. `CombatCommandTests` additionally restores a partial text draft across a simulated restart (`_BATTLEFIELDS` cleared + `restore_active_session`) and then completes it, proving the reopened draft is still usable and was never executed on restore.

## 6. Integration gate (1h)

- [x] 6.1 Update canonical annotations and shard ownership; run focused command/session/doc tests and tools.contract_gate, plus observability lint if command logging changes.
  - `uv run --locked python -m tools.contract_gate` → passed: traceability (2254 requirements, 9537 associations, 0 uncovered), observability (0 violations), test-data (0 violations), manifests, contracts (18 tests OK).
  - `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb commands.tests.test_combat_actions commands.tests.test_combat_exit_commands` → 41 tests OK; `uv run --locked python -m unittest tests.test_command_docs` → 30 tests OK.
  - Requirement IDs: the new tests annotate only requirements that already exist in `openspec/specs/` (the MODIFIED `player-combat-session`/`inventory-item-actions` requirements plus the neighbouring draft, actor-scope, taunt and reconnect requirements). This delta's ADDED requirements cannot resolve before the archive sync, so they stay unannotated now (the party-combat-command-transport precedent).
  - Shard ownership: no test module was added, renamed or moved — both touched modules keep their existing `commands` shard label, so `.github/evennia-shards.json` and `.github/browser-shards.json` are unchanged and `tests.test_evennia_test_optimization_contract` stays green through the gate's manifest check.
  - No logging code path changed, so the observability lint inside the contract gate is the complete logging check. CI-owned and therefore not run locally: the managed browser suites.

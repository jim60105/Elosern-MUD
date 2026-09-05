# Tasks: companion-possession-rules

## 1. The predicate

- [x] 1.1 `world/rules/player_control.py`: `is_player_driven(entity)` per the delta (puppeted PC
  check reused from `world/rules/movement.py`'s current shape; NPC leg = `db.possessed_by` +
  `entity.sessions.count() > 0`); module docstring cites clock design D4.
- [x] 1.2 `world/rules/movement.py::charge_movement`: replace the isinstance check with the
  predicate (flight waiver logic untouched).
- [x] 1.3 Room-entry action-options trigger site (`typeclasses/characters.py::_schedule_action_options_committed`
  and `typeclasses/npcs.py::NPC.at_post_move`): gate on `is_player_driven` (with the live-session
  condition) instead of the raw `PlayerCharacter` check, so a possessed puppeted NPC triggers options on move.

## 2. The possession writer

- [x] 2.1 `world/rules/possession.py`: `PossessionError` / `PossessionGateError` /
  `PossessionWriteError`; reason constants + fixed zh-TW message table (`not_bound`,
  `not_co_located`, `in_combat`, `dialogue_open`, `already_possessing`, `handback_first`);
  `enter_possession` (gate order per spec; `_write_possession` snapshot/restore in
  `transaction.atomic()`; seam call sites `_transfer_puppet` / `_mount_cmdset` as documented
  no-ops with `# possession: seam R1-transition` comments; facade info event).
- [x] 2.2 `release_possession(player, npc, reason)` (idempotent, mirrored clear, event);
  `release_for_party_change(npc, player)` (FULL release: handback seam then attribute clear,
  idempotent — used by auto-leave BEFORE its atomic opens, and by purge);
  `release_on_disconnect(account)` (account-keyed scan of the account's characters'
  `db.possession`, full release per hit); `restored_possession_surfaces` export naming the
  party-core restore-helper family; `current_possession(player)` read helper.
- [x] 2.3 `world/rules/party.py`: `leave_party` gains the handback-first guard (raises
  `PartyJoinError(REASON_HANDBACK_FIRST)`-shaped refusal when `npc.db.possessed_by` names the
  acting player, exempting nothing — the auto-leave hook releases first); the affinity auto-leave
  hook calls `release_for_party_change` BEFORE opening its atomic block (release-then-commit);
  `purge_npc_memberships` runs it unconditionally before unwinding.
- [x] 2.4 `world/rules/service_gate.py::schedule_silenced`: OR in the possessed-NPC leg
  (`npc.db.possessed_by` non-null).
- [x] 2.5 `typeclasses/npcs.py::LLMNPC.at_talked_to` (and the freeform seam entry that precedes
  the LLM call): refuse when `self.db.possessed_by` is set — fixed 「他現在無法回應你。」, zero
  writes; reuse the existing gate-return shape.

## 3. Commands and docs

- [x] 3.1 `commands/possess.py`: `CmdPossess` (key `possess`, aliases `附身`, `possess` English
  retained) and `CmdUnpossess` (key `unpossess`, alias `歸位`), mounted on `CharacterCmdSet`
  in `commands/default_cmdsets.py`; localized errors for absent/ambiguous/unbound targets;
  `help_category` matching the party commands' category.
- [x] 3.2 `docs/game/command-reference.md` + `docs/game/commands.md` canonical rows for both;
  curated manifest in `tests/test_command_docs.py` extended; drift contract green.

## 4. Tests

- [x] 4.1 `world/rules/tests/test_possession.py` (EvenniaTest): gate matrix — one test per reason
  with zero-write assertions; atomic enter/rollback-restore (injected write failure); release
  idempotence; account-wide `already_possessing` (two characters, two sessions or sequential
  puppet); auto-leave release-before-open ordering (injected release failure → affinity
  untouched); commit-failure retry converges via 歸位; purge unwinds;
  `release_on_disconnect` account-keyed double-run.
- [x] 4.2 `world/rules/tests/test_player_control.py` (pure-ish): four predicate rows incl. the
  stale-attribute window.
- [x] 4.3 Command tests (`commands/tests/test_possess_commands.py`): resolution errors, gate
  lines, 歸位 release; register new modules in `.github/evennia-shards.json`.
- [x] 4.4 Silence integration: schedule skip for a possessed non-service companion (the
  place-bound rows already exist from change 5); `at_talked_to` refusal writes nothing;
  quest-credit pin — possessed companion's kill still advances the owner's quest.
- [x] 4.5 `covers_requirement` annotations for every requirement across the four delta files.

## 5. Verification

- [x] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world commands typeclasses` focused; `tools.spec_traceability check`;
  `tests.test_command_docs` green.
- [x] 5.2 `uv run --locked python -m tools.observability_lint check` (new modules are adopters —
  named facade imports, no freeze-list additions); `compileall -q world commands typeclasses`.
- [x] 5.3 Grep: no new inline `isinstance(...PlayerCharacter)` in movement/trigger paths; the
  seam comments exist exactly twice in `possession.py`.

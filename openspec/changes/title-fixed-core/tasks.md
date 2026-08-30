# Tasks: title-fixed-core

## 1. Lore registry

- [ ] 1.1 `world/lore/titles.py`: `TitleCategory` enum, declarative
  `TitlePredicate` family dataclasses, frozen `FixedTitleDef`, keyed
  `FIXED_TITLE_REGISTRY`, `STARTER_EPITHET` constant (display 「南門新客」 +
  authored basis). Content rows: the guild-rank pairings (F→S) at minimum.
- [ ] 1.2 Load validation: unique keys; non-empty `hint_zh`; predicate
  references resolve against existing registry faces (elements, monster tiers,
  quest keys, guild ranks, sexual experience types).
- [ ] 1.3 Idempotent startup sync into Scripts beside the other lore registries.

## 2. Rules writer + composition

- [ ] 2.1 `world/rules/titles.py`: `compose_title` (full-width space, empty
  string when both slots empty); collection bank API (`bank_fixed(entity, key,
  tick)`, `bank_epithet(entity, display, origin_quote, tick)`) with dedupe
  (fixed key once; display unique) and D8 auto-equip on empty slots inside the
  caller's transaction; `equip_fixed(entity, ident)` / `equip_epithet(entity,
  display)` accepting banked identifiers only (stable rejection, no candidate
  listing). No un-equip, no delete API anywhere.
- [ ] 2.2 Register `title_collection` / `title_equipped` on the snapshot/restore
  surface registry (unregistered surfaces raise at registration — existing
  invariant).

## 3. Grant paths

- [ ] 3.1 `world/rules/action.py`: register the title event-effect planner —
  scan the completed EventLog, evaluate pending predicates (shared
  `status_query` read helpers for non-EventLog faces), stage `PendingEffect`
  title writes idempotent by key; push the OOB grant toast on live commit.
- [ ] 3.2 Guild registration transaction: bank 「F級冒險者」 + 「南門新客」
  (auto-equip both) in the same commit; re-registration no-op via dedupe.
- [ ] 3.3 `settle_exam_outcome` PASS path: bank the new rank's title inside the
  promotion transaction.

## 4. Consumer layering

- [ ] 4.1 Wire narrative consumers (character panel header, appraisal prose,
  status surface, Director/NPC prompt `epithet` section + up-to-five banked
  entries with basis on identity request) to live `compose_title`; empty →
  name fallback / prompt section omitted.
- [ ] 4.2 Mechanical predicates (this change's own + future quest conditions)
  read `title_collection` only.

## 5. Command + docs + tests

- [ ] 5.1 `commands/`: `title` command (`list`, `equip fixed|epithet
  <display|key>`; unknown subcommand → usage; unknown/unbanked target → stable
  rejection without oracles); mount on `CharacterCmdSet`.
- [ ] 5.2 Docs trio: `docs/game/command-reference.md` canonical `title`
  entry, `docs/game/commands.md` row, `tests/test_command_docs.py` manifest.
- [ ] 5.3 New test modules (register all in `.github/evennia-shards.json`):
  `world/lore/tests/test_titles_registry.py` (load validation, sync idempotence),
  `world/rules/tests/test_titles.py` (compose matrix, dedupe, auto-equip,
  slot invariant, planner atomicity/rollback, guild pairing),
  `commands/tests/test_title_command.py` (list/equip/reject paths).

## Verification

- [ ] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore world.rules commands tests.test_command_docs`
- [ ] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors after sync; pre-sync: unchanged, no new main-spec IDs yet)
- [ ] V3 `uv run --locked python -m compileall -q world typeclasses commands server`
- [ ] V4 `openspec validate title-fixed-core --strict`
- [ ] V5 `git diff --check`

## Post-sync traceability (during archive/sync)

- [ ] P1 On sync, obtain the `title-system` / `guild-registration` /
  `guild-rank-exams` / `game-command-docs` new IDs from
  `uv run --locked python -m tools.spec_traceability list` and annotate the
  §5.3 tests that establish each requirement.

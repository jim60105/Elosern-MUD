# Proposal: title-fixed-core

## Why

`magic-power-static-rename` deleted the numeric magic rank-title bands
(`RANK_TITLE_REGISTRY`), leaving the game with no title system. Design
`docs/superpowers/specs/2026-08-30-title-system-design.md` §5/§6 (D1/D2/D3/D8)
defines the replacement: a two-kind title model (fixed titles / epithets) whose
full title composes live, whose fixed side is granted deterministically by an
EventLog planner plus the guild registration/promotion transactions, and whose
equip slots are never empty once onboarding completes.

## What Changes

- New lore registry `world/lore/titles.py`: frozen `FixedTitleDef` (key,
  zh-tw display, category, flavor, hint, declarative predicate family),
  load-validated (unique keys, non-empty hints, predicates reference existing
  registry faces); idempotent startup sync like every other lore registry.
  Includes the `STARTER_EPITHET` constant (「南門新客」).
- New persistent state on the character: `db.title_collection` (append-only
  fixed entries; epithets only ever removable by H's guarded path) and
  `db.title_equipped` (`{"fixed": key|None, "epithet": display|None}`), both
  registered on the snapshot/restore face.
- New rules writer `world/rules/titles.py`: collection writes, equip,
  `compose_title` (fixed　epithet over a full-width space, live-composed,
  never stored), and the D8 slot-non-empty invariant (grant/adopt auto-equips
  an empty slot in the same transaction; no unequip path exists).
- Grants ride existing atomic transactions: a title EventLog planner stages
  predicate-verified fixed-title grants inside the triggering action's commit
  (OOB notification 「獲得稱號：屠龍者」); guild rank changes pair titles
  (exam promotions via `settle_exam_outcome`; F-rank plus the starter epithet
  both inside `register_guild_member`'s transaction, so the onboarding-complete
  full title is 「F級冒險者　南門新客」). Re-registration is an idempotent no-op.
- Telnet `title list` and `title equip fixed|epithet <display|key>`
  (swap-only, never empty), with the command-docs trio updated in this change.
- Consumer layering: narrative/social consumers compose the full title (empty
  → character name); mechanical predicates read the whole collection, never the
  equip slots.

## Capabilities

### New Capabilities

- `title-system`: the two-kind storage model, `compose_title`, registry +
  predicates, deterministic grants, slot invariants, equip surface, and
  consumer layering. (Epithet nomination and codex/removal land in G/H as
  later requirements of the same capability.)

### Modified Capabilities

- `guild-registration`: the registration transaction additionally grants the F-rank
  title plus the starter epithet atomically.
- `guild-rank-exams`: PASS promotion transactions additionally grant the new rank's
  paired title atomically.
- `game-command-docs`: canonical entries for `title list` / `title equip`.

### Removed Capabilities

(None.)

## Impact

- Code: `world/lore/titles.py` (new), `world/rules/titles.py` (new),
  guild register/promotion transaction hooks, `world/rules/action.py` planner
  registration, `commands/` title command + `commands/default_cmdsets.py`,
  character snapshot-surface registration.
- Tests: new modules `world/lore/tests/test_titles_registry.py`,
  `world/rules/tests/test_titles.py`, `commands/tests/test_title_command.py`
  registered in `.github/evennia-shards.json` in this change.
- Docs: `docs/game/commands.md`, `docs/game/command-reference.md`,
  `tests/test_command_docs.py`.
- No backward-compatibility or migration work: the project is unreleased with
  zero users.

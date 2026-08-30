# Proposal: title-codex-removal

## Why

After `title-fixed-core` and `title-epithet-nomination`, titles are granted,
nominated, and equipped — but players can neither browse the whole ladder (locked
rows, hints, flavor) nor shed an epithet they no longer want. Design
`docs/superpowers/specs/2026-08-30-title-system-design.md` §8 (D5) and §10 (D7)
close the loop: a pure read model feeding a WebClient codex window (two blocks:
fixed titles with locked cards, epithets with basis quotes and an equipment
star) and the system's only destructive operation — epithet removal, guarded by
exactly two gates and a two-step confirm — so collection-non-empty stays
equivalent to slot-non-empty (D8) with no unequip path anywhere.

## What Changes

- `world/rules/title_view.py`: pure `TitleCodexView` read model — fixed rows
  (locked/unlocked, `hint_zh` only when locked, flavor for unlocked), epithet
  rows (newest first, basis quote, equipped flag, `can_remove` flag), composed
  full-title preview, progress counters.
- `title` OOB schema v1 (`{fixed_rows, epithet_rows, equipped, full_title,
  unlocked, total, pending_ballot}`) with max-row/max-char constants
  (`TITLE_MAX_ROWS` / `TITLE_MAX_DISPLAY_CHARS` / `TITLE_MAX_BASIS_CHARS`)
  enforced across all four mirrors; title-category enum mirrored.
- WebClient codex big window: 「稱號」block (category tabs, locked cards with 🔒 +
  hint, click unlocked card = equip fixed slot), 「異名」block (click = equip
  epithet, ★ on equipped, 「移除」button rendered purely from `can_remove`),
  「提名中」tab for a pending ballot (G's menu relocated), header full-title
  preview updating live. No 卸裝 control.
- `world/rules/titles.py::remove_epithet(entity, display)` — the ONLY delete
  path, gated twice before the confirm flow even starts (precedence: unknown/
  wrong-kind ⇒ stable rejection; `TITLE_LAST_EPITHET` first, because the D8
  invariant makes the sole epithet the equipped one; then
  `TITLE_EQUIPPED_UNREMOVABLE`), both stable codes, neither ever reaching
  review; success deletes the collection entry, records `{tick, display}` in
  the durable bounded `title_epithet_removals` log (Director-facing digest,
  same discipline as the decline log), leaves slots untouched, and returns the
  `title_epithet_removed` EventLog. Fixed titles have no delete path at all
  (structural test asserts absence).
- Telnet `title remove epithet <display>` → echo review info (display + basis),
  literal `confirm` suffix executes, anything else cancels; `title codex` prints
  the same two blocks in text. Docs trio updated in this change.

## Capabilities

### New Capabilities

(None — lands as added requirements of `title-system`.)

### Modified Capabilities

- `title-system`: codex read model, OOB payload contract, gated two-step removal.
- `game-command-docs`: `title codex` / `title remove` syntax coverage.

### Removed Capabilities

(None.)

## Impact

- Code: `world/rules/title_view.py` (new), `world/rules/titles.py`
  (`remove_epithet`), OOB schema/constants + mirrors, WebClient codex window,
  Telnet `title` subcommands.
- Tests: pure (view trimming/counters, removal matrix), integration (EventLog
  entry, cross-session persistence), one browser class (locked/unlocked render,
  two equip paths, preview update, ballot tab, `can_remove` button visibility,
  confirm card display/cancel). New modules registered in
  `.github/evennia-shards.json` in this change.
- No backward-compatibility or migration work: the project is unreleased with
  zero users.

# Proposal: skill-lineage-panel

## Why

`use-driven-skill-lineage` makes proficiency the only growth currency and the
prerequisite DAG the only use gate, but the player cannot see either: level,
XP-into-level, saturation, and the next locked node live only in registry
data and `db.skill_proficiency`. Design
`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md` §12 (D8)
specifies the lineage ledger: a pure read model exported to the WebClient as
one versioned panel and to Telnet as one `lineage` command, rendering
everything with zero hidden information.

## What Changes

- New pure read model `world/rules/lineage_query.py`: frozen
  `LineageNodeView` / `LineageChainView` / `LineageView` dataclasses derived
  only from `db.skill_proficiency` + registry prerequisite edges. No new
  persistent state, no writer.
- New versioned WebClient panel (big window opened from a new stage icon)
  with the frozen-contract flow: one OOB payload shape, four mirrored
  validators (protocol validator, panel view, JS validator, boundary tests),
  conventional `LINEAGE_MAX_*` bounds.
- New Telnet `lineage` command printing the same tree: 見頂 markers on
  saturated nodes, `prereq_text_zh` on locked nodes.
- Unlock notification: the moment `can_use_skill` flips true for a skill, one
  line (e.g. 「新法術可用：火焰風暴」) rides the existing post-commit
  notification channel (`ActionResult.notifications`, the title-grant-toast
  delivery), not a new transport.
- Command docs: `lineage` canonical entry in
  `docs/game/command-reference.md` + row in `docs/game/commands.md` + curated
  manifest in `tests/test_command_docs.py`.

## Capabilities

### New Capabilities

- `skill-lineage-panel`: the lineage read model, its bounded OOB contract and
  WebClient window, the Telnet command surface, and the unlock notification.

### Modified Capabilities

- `game-command-docs`: one new canonical entry requirement for `lineage`.

### Removed Capabilities

(None.)

## Impact

- Code: `world/rules/lineage_query.py` (new), `web/webclient/` panel presenter
  + protocol validator + JS panel/view + JS validator, `commands/` Telnet
  command + `commands/default_cmdsets.py` mount, `world/rules/progression.py`
  unlock-diff hook (reads the transient per-tick seam; no new persistence).
- Tests: new Python panel/command test modules registered in
  `.github/evennia-shards.json` in this change; Vitest component tests; one
  managed browser class (CI-owned budget).
- No backward-compatibility or migration work: the project is unreleased with
  zero users.

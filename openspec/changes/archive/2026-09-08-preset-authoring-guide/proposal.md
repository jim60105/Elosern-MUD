## Why

After the field-parity changes, `PlayerPreset` carries roughly twenty fields
across six concerns — identity, allocation, skills with lineage seeding, items
and worn equipment, a seven-key persona, a sexual baseline, a disguise layer,
and starting companions — each guarded by its own load-time validator. Adding a
card is now a real authoring task with non-obvious rules: an elf must declare an
empty affinity set, `starting_equipment` must be a subset of `starting_items`,
the lineage closure fills prerequisites for you, and the card blurb has a
tighter bound than the persona field it lives in.

None of that is written down. `docs/gm/characters.md` documents the JSON import
path, which is a different mechanism with different rules, and the two nearest
siblings — `docs/development/adding-items.md` and `adding-spells.md` — show
exactly the shape this guide should take.

## What Changes

- New docsify page `docs/development/adding-player-presets.md`, titled
  新增角色模板指南, in Traditional Chinese, structured after
  `docs/development/adding-items.md`: where a preset's data lives, the decisions
  to make first, a step-by-step walkthrough, the load-time validator messages
  and what triggers each, common mistakes, and when to reach for another guide.
- The guide explains why presets declare *allocations* while the import card
  declares *absolute stats*, so an author does not mistake the difference for an
  oversight.
- Registered in `docs/_sidebar.md` under 開發者指南, after 新增物品指南.
- A contract test keeps the guide honest: every `PlayerPreset` field name must
  appear in the page, so a future field cannot land undocumented. This mirrors
  the coupling `tests/test_command_docs.py` already enforces between the command
  surface and its documentation.
- Cross-links to 新增物品指南, 新增魔法指南, and `docs/gm/characters.md`.

The guide is placed under `development/` rather than `gm/` because adding a
preset is a code change; the GM page documents the path that is not.

## Capabilities

### New Capabilities

- `preset-authoring-docs`: the player-preset authoring guide exists, is
  reachable from the documentation sidebar, and stays in sync with the registry
  field set.

### Modified Capabilities

None.

## Impact

- `docs/development/adding-player-presets.md` — new page.
- `docs/_sidebar.md` — one entry.
- `tests/test_command_docs.py` or a sibling repo-wide contract module — the
  field-coverage test. If a new test module is created it MUST be registered in
  exactly one shard of `.github/evennia-shards.json` in this same change.
- No production code changes.

## 1. Guide

- [x] 1.1 Create `docs/development/adding-player-presets.md` titled 新增角色模板指南, in Traditional Chinese, following `docs/development/adding-items.md`'s section structure
- [x] 1.2 Section 1 — where a preset's data lives: the field-group table (identity, allocation, skills, items and equipment, persona, sexual baseline, disguise, companions) and how the preset, custom-creation, and JSON-import paths differ, including why presets declare allocations while the import card declares absolute stats
- [x] 1.3 Section 2 — decisions to make first: race and subrace, the allocation budget from `resolve_starting_profile()`, whether the skill kit touches a lineage prerequisite, whether the card needs a hidden identity layer
- [x] 1.4 Section 3 — step by step: read the bounds, write the entry, author the seven persona keys, declare the skill kit and what the closure adds for you, declare starting items and the worn subset, declare the sexual baseline and disguise layer, declare starting companions, add tests
- [x] 1.5 Section 4 — every load-time validator, its error message, and what triggers it
- [x] 1.6 Section 5 — common mistakes: an elf card must declare an empty `affinity_elements`; the divine-arts race gate; exceeding the allocation budget; a `starting_equipment` key absent from `starting_items`; a persona field over `MAX_PERSONA_FIELD_LENGTH`; a card blurb over `MAX_BACKGROUND_CODE_POINTS`; a duplicate `starting_items` key
- [x] 1.7 Section 6 — when this guide is not enough: cross-link 新增物品指南, 新增魔法指南, and `docs/gm/characters.md`
- [x] 1.8 Verify every code path, constant, and file reference named in the guide against the current source before publishing

## 2. Sidebar

- [x] 2.1 Add the entry to `docs/_sidebar.md` under 開發者指南, immediately after 新增物品指南
- [x] 2.2 Confirm the docsify link resolves (path without the `.md` suffix, matching the existing entries' form)

## 3. Contract test

- [x] 3.1 Add a repo-wide contract test asserting every `dataclasses.fields(PlayerPreset)` name appears in the guide **as an inline-code span** (`` `field_name` ``), not a bare substring, so short names like `key`/`age`/`sex`/`race` cannot pass incidentally; derive the field set from the dataclass rather than a duplicated literal
- [x] 3.1a Add a negative test: a field mentioned only in plain prose fails the check
- [x] 3.2 Assert the sidebar contains the guide's link
- [x] 3.3 If the test lands in a new module, register it in exactly one shard of `.github/evennia-shards.json` in this same change and verify with `tests.test_evennia_test_optimization_contract` (conditional evaluated: the test lands in repo-root `tests/`, which the top-level `unittest discover -s tests` job owns and which the evennia shard manifest must NOT list — a `tests.…` label would break the shard-ownership contract, since that test discovers only the `commands`/`server`/`typeclasses`/`world`/`web/webclient` roots; `tests.test_evennia_test_optimization_contract` verified green with the manifest unchanged)
- [x] 3.4 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list` (the delta spec was synced to `openspec/specs/preset-authoring-docs/spec.md` in this change so the IDs are listable and the CI traceability gate sees them)

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_command_docs`
- [x] 4.2 Render the docsify site locally and confirm the page and its sidebar entry appear (served `docs/` over a local HTTP server: `/`, `/_sidebar.md` with the 新增角色模板指南 entry, and `/development/adding-player-presets.md` all return 200; the entry uses the exact link form of its working siblings, so docsify's hash router resolves `/development/adding-player-presets` to the page — no headless-browser daemon is available in this environment for a pixel check)
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check` (1383 requirements, 4986 associations, 1383 covered, 0 uncovered, 0 errors)
- [x] 4.4 `openspec validate preset-authoring-guide --strict` (Change 'preset-authoring-guide' is valid)

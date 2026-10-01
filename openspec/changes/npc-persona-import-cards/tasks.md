Apply on branch `feat/npc-persona-import-cards` in worktree `.worktrees/npc-persona-import-cards`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Validation

- [x] 1.1 Add `_check_npc_persona_card` to `world/imports/validate.py` per design D1/D2 (NPC target only, named `persona.<leaf>` issue, normalized card stored on the report record); verify in `world/imports/tests/`: partial persona rejected by leaf, `background` rejected as unknown field, `PlayerCharacter` target with arbitrary nesting accepted, normalization reflected in `report.record`, and a batch with one bad NPC persona loads nothing.
- [x] 1.2 Update `CHARACTER_SCHEMA_V1`'s persona description per the new import-schema requirement; verify the description test in `world/imports/tests/` asserts all three clauses.

## 2. Loader

- [x] 2.1 Write NPC-target personas through `initialize_npc_persona` with `import` provenance per design D3, keeping verbatim storage for non-NPC targets; verify: NPC card equals the validated card with metadata version 1, a second record's failure in the batch rolls back the first record's card, metadata, and attribute cache, and a `PlayerCharacter` import stores arbitrary nesting verbatim with no metadata.
- [x] 2.2 Give every synthetic NPC import fixture outside `world/imports` a complete card through one shared helper (`rg '"persona"' world web commands tests --glob "*tests*"`), never relaxing the check; verify each touched label passes in its own command.

## 3. Reference example and docs

- [x] 3.1 Rewrite `world/imports/examples/example_character.json`'s persona per design D4; verify `uv run --locked -m world.imports.validate world/imports/examples/example_character.json` reports zero rejections and zero warnings, and the reference-example tests assert the new requirements (replace the background and "never inspected" assertions).
- [x] 3.2 Update `docs/gm/characters.md` (persona row and example) and the JSON-card, validation, and validator-table sections of `docs/development/adding-npcs.md` for NPC cards (Traditional Chinese, matching the docs' language); run any docs contract test that covers these files (`rg "characters.md|adding-npcs" tests`).

## 4. Gates

- [x] 4.1 Confirm the `world.imports` package shard label owns every new test module (no manifest edit) with `tests.test_evennia_test_optimization_contract`; sync the deltas (ADDED, MODIFIED, REMOVED) into `openspec/specs/`, edit `openspec/specs/import-reference-example/spec.md`'s Purpose so it no longer mentions a background block, re-anchor annotations from removed requirement IDs to the new ones with literal IDs from `uv run --locked python -m tools.spec_traceability list`, and verify `tools.spec_traceability check`.
- [x] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-import-cards --strict`; record results.

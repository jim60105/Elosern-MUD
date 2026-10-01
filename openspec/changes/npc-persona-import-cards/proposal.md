## Why

Administrator imports are a production NPC creation path, and today the import pipeline treats `persona` as an opaque object that is "never inspected" and stores it verbatim. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §6.1 "NPC imports", §13) explicitly amends that rule for NPC targets only: an NPC import must provide a complete valid compact card, validated through the target-typeclass-aware path, persisted as validated (not model-rewritten) through the shared persona writer, while player and other non-NPC imports keep their opaque persona contract. The shipped reference example must be rewritten to a complete card.

## What Changes

- `validate_character(record, typeclass)` applies the compact card contract to `persona` when the resolved target class (the class actually passed to validation and instantiation, `issubclass(typeclass, NPC)`, `None` meaning the NPC default) is an NPC; each failure is reported as an `Issue` on `persona.<leaf>` (or `persona`) with the contract's stable reason; the validated record carries the normalized card. Non-NPC targets keep the opaque object rule. No typeclass string inside the record is consulted.
- The loader writes an NPC target's persona through `initialize_npc_persona` with `import` provenance (record key) inside the existing all-or-nothing batch transaction; a non-NPC target's persona is stored verbatim as before.
- **BREAKING (pre-release):** `world/imports/examples/example_character.json` is rewritten with a complete compact card in Traditional Chinese (`identity{public,hidden}`, `speech_style`, no `background`), and the reference-example requirements that demanded a `background` key and an uninspected persona are replaced.
- `CHARACTER_SCHEMA_V1`'s `persona` description states the schema layer checks only for an object and that NPC-target semantic validation applies the card contract.
- `docs/gm/characters.md` and the import steps of `docs/development/adding-npcs.md` document the card for NPC imports.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `import-validation`: ADDED requirement for typeclass-aware compact card validation of NPC imports.
- `import-schema`: the opaque-persona requirement is replaced by one that keeps the schema-layer object check and points NPC targets to semantic card validation.
- `import-loader`: NPC-target personas are written through the shared persona initializer with metadata; non-NPC targets stay verbatim.
- `import-reference-example`: the background requirement and the opaque-persona branch requirement are replaced by a complete-card requirement.

## Impact

- Code: `world/imports/validate.py`, `world/imports/loader.py`, `world/imports/schema.py` (description text), `world/imports/examples/example_character.json`.
- Tests: `world/imports/tests/` (package-owned shard label `world.imports`), any test that loads synthetic NPC records with partial personas (`rg '"persona"' world/imports/tests world/rules/tests web commands`).
- Docs: `docs/gm/characters.md`, `docs/development/adding-npcs.md` (import steps and validator table only).

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: sole editor of `world/imports/*` in this batch. `docs/development/adding-npcs.md` is also edited by `npc-persona-roster-cutover` (authoring-flow sections); this change edits only the JSON-card, validation, and validator-table sections, so rebase conflicts are adjacent-section at most. Synthetic NPC import fixtures used by other packages' tests may need complete cards — coordinate through the test-data kit, not per-change copies. Prerequisite of `npc-persona-roster-cutover`.

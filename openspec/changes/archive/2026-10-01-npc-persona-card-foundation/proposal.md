## Why

Every NPC needs a compact, individual character card that free-form dialogue consumes and that scripted dialogue is written against (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md`, sections 4 and 5.1). Today `entity.db.persona` is an opaque record with no NPC shape, no speech-style field, no budget that guarantees the prompt reader never truncates it, and no version for concurrent editing. Every producer, the dialogue gate, the editor, and the cutover need one shared contract and one persistence/versioning writer, so they land first. (The profile vocabulary is split into `npc-persona-profile-registry` so this root change stays one workday.)

## What Changes

- Add a pure compact-card contract (`world/lore/npc_card.py`) shared by every NPC producer and the editor: exactly seven top-level fields (`identity{public,hidden}`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`, `social_connection`), plain-text normalization, per-leaf 600-code-point bounds, a rendered identity-section bound, and a 2,000-code-point bound on the complete labeled block counted with labels and separators; stable per-field and total-budget rejection reasons; one field order and label policy shared with the prompt reader; the closed provenance vocabulary.
- Add `說話風格` as the `speech_style` label in `PersonaStore` rendering; its generic shape handling and truncation for other consumers stay unchanged.
- Add the deterministic NPC persona service (`world/rules/npc_persona.py`): a separate `db.npc_persona_meta` record (card format, content-generation marker, monotonic `persona_version`, provenance), a read that never initializes or repairs, an initializer that never overwrites a marked instance, and a compare-and-set update whose lock, cache-bypassing version read, and write share one database transaction serialized across processes, with a stable storage-unavailable outcome, attribute-cache restoration on rollback, and commit-bound observability events that never carry persona text.
- Add the boundary-case fixture shared by the Python contract tests and the later browser mirror.

No profile, creation path, prompt, dialogue, editor, or cutover behavior changes here.

## Capabilities

### New Capabilities

- `npc-persona-card`: the compact NPC card contract, its render budget, and deterministic persistence/versioning of NPC persona instances.

### Modified Capabilities

- `persona-store`: adds the `speech_style` label to flattening (ADDED requirement; existing generic behavior unchanged).

## Impact

- New: `world/lore/npc_card.py`, `world/rules/npc_persona.py`, `world/lore/tests/fixtures/npc_card_boundary_cases.json`.
- Modified: `world/rules/persona.py` (label only), observability catalog (`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4).
- Tests: `world/lore/tests/test_npc_card.py` (package-owned shard) and `world/rules/tests/test_npc_persona.py` (explicit rules-shard registration).
- No migration, compatibility layer, dependency, or UI change.

## Batch:

This change has no prerequisites; it is the root of the NPC persona batch.

Code-conflict notes: creates `world/lore/npc_card.py` and `world/rules/npc_persona.py`. Later changes add distinct functions to `npc_persona.py` (`npc-persona-dialogue-consumption`: read-only version/provenance helpers; `npc-persona-editor-actions`: a silent availability predicate; `npc-persona-roster-cutover`: writer suspension) — mechanical rebases only. Shared append-only files that later changes also touch: `.github/evennia-shards.json`, `tools/test_data_freeze.json`, and the observability catalog table.

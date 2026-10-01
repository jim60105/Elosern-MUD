## Why

Every NPC needs a compact, individual character card that free-form dialogue consumes and that scripted dialogue is written against (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md`, sections 4 and 5.1). Today `entity.db.persona` is an opaque record with no NPC shape, no speech-style field, no budget that guarantees the prompt reader never truncates it, no version for concurrent editing, and no authored profile source: service hosts and examiners have no persona at all. Every later change in this set (content rewrite, producers, dialogue gate, editor, cutover) needs one shared contract, one persistence/versioning writer, and one profile vocabulary to build on, so they land first.

## What Changes

- Add a pure compact-card contract shared by every NPC producer and the editor: exactly seven top-level fields (`identity{public,hidden}`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`, `social_connection`), plain-text normalization, per-leaf 600-code-point bounds, a rendered identity-section bound, and a 2,000-code-point bound on the complete labeled block counted with labels and separators; stable per-field and total-budget rejection reasons; one field order and label policy shared with the prompt reader.
- Add `說話風格` as the `speech_style` label in `PersonaStore` rendering; its generic shape handling and truncation for other consumers stay unchanged.
- Add the deterministic NPC persona service (`world/rules/npc_persona.py`): a separate `db.npc_persona_meta` record (card format, content-generation marker, monotonic `persona_version`, provenance), a read that never initializes or repairs, an initializer that never overwrites a marked instance, and a compare-and-set update whose version check and write share one database transaction serialized across processes, with attribute-cache restoration on rollback and commit-bound observability events that never carry persona text.
- Add the immutable profile vocabulary under `world/lore/npc_profiles/`: `NpcProfile` (stable key, compact card, bounded voice lines), validated through the card contract at import; one assembly module owning the fixed slice order; pre-created empty slice modules, one per content change, so content slices never edit the assembly; a source inventory enumerating every shipped NPC source and the slice that owns it.
- Add an optional `host_profile_key` to `PlaceDefinition`, validated when set (it must resolve and may only appear on a host-authoring place). Making it mandatory belongs to `npc-persona-host-examiner-producers`.
- Split `world/lore/dialogue/altoria.py` into terrace slices (`altoria_lower.py`, `altoria_middle.py`, `altoria_upper.py`) with no prose change and an unchanged assembled key order, so the parallel content slices never edit one file.
- Add the boundary-case fixture shared by the Python contract tests and the later browser mirror.

No NPC persona content is authored here, no creation path is switched to the new writer, and no prompt, dialogue, editor, or cutover behavior changes. No placeholder profile is created: every profile slice starts as an empty tuple that its owning content change fills.

## Capabilities

### New Capabilities

- `npc-persona-card`: the compact NPC card contract, its render budget, and deterministic persistence/versioning of NPC persona instances.
- `npc-profile-registry`: immutable authored NPC profiles, their assembly and validation, and the shipped NPC source inventory.

### Modified Capabilities

- `persona-store`: adds the `speech_style` label to flattening (ADDED requirement; existing generic behavior unchanged).
- `settlement-place-registry`: adds validation of an optional authored host-profile reference on place records (ADDED requirement).

## Impact

- New: `world/lore/npc_card.py`, `world/lore/npc_profiles/` (`__init__.py`, `shape.py`, `inventory.py`, slice modules `altoria_lower.py`, `altoria_trade.py`, `altoria_guild.py`, `altoria_upper.py`, `ciaran_homes_a.py`, `ciaran_homes_b.py`, `companions.py`), `world/rules/npc_persona.py`, `world/lore/dialogue/altoria_{lower,middle,upper}.py` (moved rows), `world/lore/tests/fixtures/npc_card_boundary_cases.json`.
- Modified: `world/rules/persona.py` (label only), `world/lore/settlements/places.py` (optional field + validation), `world/lore/dialogue/__init__.py` (assembly order), observability catalog (`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4).
- Tests: new modules under `world/lore/tests/` (package-owned shard) and `world/rules/tests/` (explicit shard registration).
- No migration, compatibility layer, dependency, or UI change.

## Batch:

This change has no prerequisites; it is the root of the NPC persona batch.

Code-conflict notes: this change is the single integration owner of `world/lore/npc_profiles/__init__.py` (profile assembly) and `world/lore/dialogue/__init__.py` (dialogue assembly); no later change edits either. It creates `world/lore/npc_card.py` and `world/rules/npc_persona.py`, which `npc-persona-roster-cutover` later extends (writer suspension and the cutover writer) and every producer/editor change calls without editing. `world/lore/settlements/places.py` is edited here and again by `npc-persona-host-examiner-producers` (sequential dependency). Shared append-only files that later changes also touch: `.github/evennia-shards.json`, `tools/test_data_freeze.json`, and the observability catalog table; expect mechanical rebase conflicts there only.

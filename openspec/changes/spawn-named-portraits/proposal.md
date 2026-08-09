# spawn-named-portraits Proposal

## Why

The blueprint side can now declare named occupants with story-driven identity and age, but the
SceneBuilder still spawns every occupant without applying them — so the art-assets portrait seam
(`_schedule_occupant_portraits`, the adult gate, and the internal sd-webui client) has no
production producer. Generated quests must be able to materialize a named NPC whose unique
portrait is actually generated.

## What Changes

- `_spawn_npc` applies the characterization carried by `StageSpawnRequirement` per field:
  `db.display_name`, canonical adult `db.age` / `db.apparent_age`, and
  `db.portrait_policy = {"mode": "named", "stable_key": ...}` when a portrait is declared.
- A portrait-bearing occupant without declared ages receives the deterministic adult baseline 25
  — always within the adult-to-lifespan-maximum validation range for every race — so the portrait
  adult gate provably passes.
- Name-only, ages-only, and role-based occupants keep today's behavior (no policy, no baseline,
  no portrait job).
- The existing post-commit portrait-eligibility seam is exercised end to end: spawn → on_commit
  ensure → adult gate → fake worker with an adult, story-driven description. Shared `stable_key`
  across quests resolves to one asset, first-writer-wins.
- No art-layer code changes: subject derivation, description, adult gate, queue, and the internal
  sd-webui client consume the applied policy as designed.

## Capabilities

### New Capabilities
- `spawn-named-portraits`: the deterministic SceneBuilder applies blueprint characterization —
  display name, canonical adult ages, and the named portrait policy — to spawned occupants and
  schedules their unique portraits through the existing seam.

### Modified Capabilities
- `scene-builder`: the existing portrait-eligibility requirement is rewritten to cover the applied
  characterization and the baseline, preserving the post-commit and rollback guarantees.

## Impact

- `world/quests/scene_builder.py` — `_spawn_npc` application of characterization and baseline ages.
- `world/art/service.py`, `subjects.py`, `adult.py`, `sd_worker.py` — read-only consumers,
  unchanged.
- Tests: `world/quests/tests/test_scene_builder.py`, `world/art/tests/` integration, template
  quests carrying the fields.

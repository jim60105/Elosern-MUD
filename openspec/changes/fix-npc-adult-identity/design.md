## Context

`_sync_service_host` (`world/rules/guild_economy.py:38-56`) and `_spawn_opponent` (`world/rules/guild_exams.py:189-219`) create NPCs with race/traits/skills but never set `db.age`/`db.apparent_age`. The portrait adult gate `_read_age` (`world/art/adult.py:26-42`) rejects missing ages, and the project invariant requires every character to be an adult. Existing patterns: `_repair_guard_identity` (`world/rules/onboarding.py:360-366`) persists 18/18, and `PORTRAIT_ADULT_BASELINE` (`world/quests/scene_builder.py:231-238`) fills 25 for unnamed occupants.

## Goals / Non-Goals

**Goals:**
- Every production NPC spawn/sync path yields canonical adult `age`/`apparent_age`.
- One enforcement point shared by future spawn paths.

**Non-Goals:**
- Backfilling pre-existing NPCs in live databases (project has no users).
- Validating story-derived ages in quest characterization (already handled).
- Changing the import/creation adult gates.

## Decisions

**D1 — One helper, set-if-absent per field.** `ensure_npc_adult_identity(npc)` sets `db.age = 18` when `age` is missing and `db.apparent_age = 18` when `apparent_age` is missing, independently — never overwriting an existing value and never forcing both fields because one is absent. Placed next to the NPC typeclass (`typeclasses/npcs.py`) so all spawn paths can reach it.

**D2 — Call at creation sites, not in the typeclass.** Explicit calls in `_sync_service_host` and `_spawn_opponent` keep the deterministic spawn flows self-contained and testable; a typeclass-level default is avoided to prevent masking characterization bugs.

**D3 — No behavior change to existing adult paths.** The helper is a no-op where characterization/import already set ages.

## Risks / Trade-offs

- **Duplicate enforcement**: the helper duplicates the guard's 18/18 logic; acceptable for a 3-line invariant, and it keeps each call site explicit.
- **None-adult NPCs intentionally created later**: any future path wanting a non-adult NPC must override after the call; consistent with project rules that such NPCs cannot exist.

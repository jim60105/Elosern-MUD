# skill-lineage delta

## MODIFIED Requirements

### Requirement: Import and scene-build auto-seed prerequisite proficiency exactly
The character loader SHALL, inside the existing all-or-nothing transaction, seed the practice
proficiency of any prerequisite edge that is unsatisfied for an owned skill to EXACTLY the required
value, never above, and SHALL extend the record's ownership with the transitive prerequisite
closure so a deep import is gate-usable, not merely seeded. Auto-seed normalization SHALL run on
the record before the semantic validation phase reads it (schema range checks included), so
malformed imports still reject wholesale, and an explicit `skill_proficiency` entry in the import
record SHALL always win over auto-seed, even when it leaves an edge unmet. Every explicit
`skill_proficiency` key SHALL resolve in `SKILL_REGISTRY` — the check runs against the RAW record
before normalization, so an unregistered key names itself and rejects the whole record instead of
being silently dropped or silently persisted by the seed.
`world/quests/scene_builder.py`'s NPC spawn path SHALL share the same helper, and so SHALL
`world/rules/character_creation.py`'s preset activation path, which composes
`lineage_ownership_closure` and `seed_lineage_proficiency` directly over the preset's declared keys
rather than through the import-record wrapper. The closure and seed helpers SHALL therefore have
exactly three production callers, and no caller SHALL reimplement either algorithm.

#### Scenario: A deep imported skill arrives usable
- **WHEN** an import record owns `firestorm` (prereq `scorching_wave >= 3`) and carries no proficiency for `scorching_wave`
- **THEN** the loaded entity owns the closed chain, its `scorching_wave` level is exactly 3 and `can_use_skill` passes

#### Scenario: Explicit proficiency beats auto-seed
- **WHEN** the same record explicitly carries `skill_proficiency: {"scorching_wave": 120}` (level 2)
- **THEN** the loaded level is 2 (below the edge) and auto-seed does not overwrite it

#### Scenario: Auto-seed never overshoots
- **WHEN** auto-seed satisfies a `>= 5` edge
- **THEN** the stored XP is exactly `5 * 50`, the minimal value meeting the threshold

#### Scenario: Malformed imports still reject all-or-nothing
- **WHEN** a record with an invalid field also triggers auto-seed
- **THEN** validation rejects the record and nothing persists, seed included

#### Scenario: An unregistered proficiency key rejects the record
- **WHEN** a record carries `skill_proficiency: {"not_a_skill": 50}`
- **THEN** validation rejects the record naming the key, and nothing persists

#### Scenario: Preset activation shares the same helpers
- **WHEN** a preset activation seeds a prerequisite edge
- **THEN** the seeded value equals what the import path would write for the same skill set, produced by the same two helpers rather than a parallel implementation

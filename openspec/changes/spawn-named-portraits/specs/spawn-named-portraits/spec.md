## ADDED Requirements

### Requirement: The SceneBuilder applies blueprint characterization to named occupants
When `_spawn_npc` materializes an occupant whose compiled `StageSpawnRequirement` carries
characterization, it SHALL apply each present field independently: `display_name` sets
`npc.db.display_name`; paired `age`/`apparent_age` set `npc.db.age` and `npc.db.apparent_age`; a
named-portrait `stable_key` sets `npc.db.portrait_policy = {"mode": "named", "stable_key": ...}`
and, when the ages are absent, sets `npc.db.age = npc.db.apparent_age = 25` (the deterministic
adult baseline — a value always within the adult-to-lifespan-maximum validation range for every
race, so the portrait gate provably passes). An occupant without a portrait policy SHALL never
receive the baseline or a policy; name-only and ages-only occupants keep today's portrait-less
behavior. The baseline and the policy SHALL be set inside the same materialization transaction,
before the existing `_schedule_occupant_portraits` loop runs, so the post-commit ensure fires with
complete data.

#### Scenario: A named occupant with story-driven ages is materialized fully
- **WHEN** a compiled requirement declares `display_name`, `age: 68`, `apparent_age: 68`, and a
  `stable_key`
- **THEN** the spawned NPC carries the display name, ages 68, and
  `{"mode": "named", "stable_key": ...}`, and exactly one post-commit portrait ensure is scheduled

#### Scenario: A portrait-bearing occupant without ages receives the adult baseline
- **WHEN** a compiled requirement declares a portrait but no age fields
- **THEN** `db.age` and `db.apparent_age` are both 25 and the adult gate passes at enqueue

#### Scenario: The baseline is valid for every race, including elves
- **WHEN** a portrait-bearing elven occupant (`elven_civilian`) is spawned without ages
- **THEN** `db.age` and `db.apparent_age` are 25, which lies in the adult-to-lifespan-maximum
  validation range (18..1200) for the elf race, and the adult gate passes

#### Scenario: A name-only occupant is named but portrait-less
- **WHEN** a compiled requirement declares only `display_name`
- **THEN** the spawned NPC carries the display name, no ages, no portrait policy, and no portrait
  job is scheduled

#### Scenario: A role-based occupant without characterization is untouched
- **WHEN** a compiled requirement declares no optional fields
- **THEN** the spawned NPC has no display name, no ages, no portrait policy, and no portrait job is
  scheduled — identical to today's behavior

### Requirement: A spawned named occupant completes the full portrait pipeline
A spawned named occupant SHALL reach the fake worker with the deterministic adult-safe description
built by `character_description()` (display name, race label, story-driven age or the baseline 25,
style template) and the correct `portrait:character:<stable_key>` subject — proving subject
derivation, the adult gate, queue enqueue, and prompt rendering work end to end with no art-layer
code changes. A rolled-back materialization SHALL emit no portrait job, preserving the existing
atomicity guarantee. A `stable_key` shared across quests SHALL resolve to one asset whose
description is set by the first materialization (first-writer-wins; the queue never overwrites a
done record).

#### Scenario: The fake worker receives the story-driven adult description
- **WHEN** a quest scene with a named occupant is materialized (commit callbacks executed
  explicitly) and drained with the fake worker
- **THEN** the worker receives a `portrait:character:<stable_key>` job whose description contains
  the display name and the declared age (or the baseline 25), and the asset completes

#### Scenario: Two quests sharing a stable key produce one asset
- **WHEN** two different quest scenes declare the same `stable_key` and both are materialized
- **THEN** both schedules resolve to the same subject, the store settles to one completed asset,
  and the first materialized description wins

#### Scenario: A rolled-back materialization schedules no portrait
- **WHEN** the spawn transaction rolls back after occupants were created
- **THEN** no post-commit portrait job is emitted and the existing full rollback behavior is
  unchanged

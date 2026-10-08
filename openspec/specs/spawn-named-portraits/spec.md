# spawn-named-portraits Specification

## Purpose

Define the deterministic SceneBuilder side of named occupant portraits: the spawn path applies
blueprint characterization (display name, canonical ages, and the named portrait policy) to
spawned occupants and schedules their unique portraits through the existing post-commit seam, so
generated quests materialize named NPCs whose portraits the art pipeline actually produces.

## Requirements

### Requirement: The SceneBuilder applies blueprint characterization to named occupants
When `_spawn_npc` materializes an occupant whose compiled `StageSpawnRequirement` carries
characterization, it SHALL apply each present field independently: `display_name` sets
`npc.db.display_name`; paired `age`/`apparent_age` set `npc.db.age` and `npc.db.apparent_age`; a
named-portrait `stable_key` sets `npc.db.portrait_policy = {"mode": "named", "stable_key": ...}`
and, when the ages are absent, sets the deterministic age baseline
`npc.db.age = npc.db.apparent_age = 25`.

#### Scenario: A named occupant with story-driven ages is materialized fully
- **WHEN** a compiled requirement declares `display_name`, `age: 68`, `apparent_age: 68`, and a
  `stable_key`
- **THEN** the spawned NPC carries the display name, ages 68, and
  `{"mode": "named", "stable_key": ...}`, and exactly one post-commit portrait ensure is scheduled

#### Scenario: A portrait-bearing occupant without ages receives the age baseline
- **WHEN** a compiled requirement declares a portrait but no age fields
- **THEN** `db.age` and `db.apparent_age` are both 25 and the canonical-age check passes at enqueue

#### Scenario: The baseline is valid for every race, including elves
- **WHEN** a portrait-bearing elven occupant (`elven_civilian`) is spawned without ages
- **THEN** `db.age` and `db.apparent_age` are 25, which lies in the zero-to-lifespan-maximum
  validation range (0..1200) for the elf race, and the canonical-age check passes

#### Scenario: A name-only occupant is named but portrait-less
- **WHEN** a compiled requirement declares only `display_name`
- **THEN** the spawned NPC carries the display name, no ages, no portrait policy, and no portrait
  job is scheduled

#### Scenario: A role-based occupant without characterization is untouched
- **WHEN** a compiled requirement declares no optional fields
- **THEN** the spawned NPC has no display name, no ages, no portrait policy, and no portrait job is
  scheduled — identical to today's behavior

#### Scenario: A forged requirement with invalid ages is rejected before any spawn
- **WHEN** a forged `StageSpawnRequirement` (bypassing the compile boundary) carries negative,
  non-integer, or unpaired ages
- **THEN** the spawn path re-validates the characterization through the shared helper and raises a
  named `SceneBuilderSpawnError` before any room or occupant is created, so no permanently
  ineligible occupant can ever be written

#### Scenario: An occupant without a portrait policy receives neither baseline nor policy
- **WHEN** a compiled requirement declares no named-portrait `stable_key`, with only
  `display_name` or only paired ages
- **THEN** the spawned NPC never receives the age baseline or a portrait policy, keeping today's
  portrait-less behavior

#### Scenario: Baseline and policy are set before portrait scheduling
- **WHEN** a named occupant is materialized
- **THEN** the age baseline and portrait policy are set inside the same materialization
  transaction, before the existing `_schedule_occupant_portraits` loop runs, so the post-commit
  ensure fires with complete data

### Requirement: A spawned named occupant completes the full portrait pipeline
A spawned named occupant SHALL reach the fake worker with the deterministic description
built by `character_description()` and the correct `portrait:character:<stable_key>` subject —
proving subject derivation, the canonical-age check, queue enqueue, and prompt rendering work end
to end with no art-layer code changes. A rolled-back materialization SHALL emit no portrait job,
preserving the existing atomicity guarantee.

#### Scenario: The fake worker receives the story-driven description
- **WHEN** a quest scene with a named occupant is materialized (commit callbacks executed
  explicitly) and drained with the fake worker
- **THEN** the worker receives a `portrait:character:<stable_key>` job whose description contains
  the display name and the declared age (or the baseline 25), and the asset completes

#### Scenario: Two quests sharing a stable key produce one card
- **WHEN** two different quest scenes declare the same `stable_key`, the first is materialized and
  drained, and the second is then materialized
- **THEN** both schedules resolve to the same subject, the gallery holds exactly one auto-generated
  card whose description came from the first materialization, and the second materialization
  requests no generation

#### Scenario: A rolled-back materialization schedules no portrait
- **WHEN** the spawn transaction rolls back after occupants were created
- **THEN** no post-commit portrait job is emitted and the existing full rollback behavior is
  unchanged

#### Scenario: The completed job publishes one unbound card
- **WHEN** a quest scene with a named occupant is materialized and drained with the fake worker
- **THEN** the occupant's gallery holds exactly one card, that card is unbound, and it carries the shared default face rectangle

#### Scenario: The worker description composes the full character portrait text
- **WHEN** the fake worker receives a named occupant's job
- **THEN** the description contains the display name, race label, story-driven age or the baseline
  25, and the style template

#### Scenario: The published card is not a fixed-identity asset
- **WHEN** a named occupant's portrait job completes
- **THEN** the publication is exactly one UNBOUND gallery card carrying the shared default face
  rectangle for that subject, not a single fixed-identity asset

#### Scenario: Shared-subject suppression runs the automatic-generation guard
- **WHEN** a materialization declares a `stable_key` whose subject gallery is already occupied by
  an auto-generated card from an earlier materialization
- **THEN** the later materialization is suppressed by the automatic-generation guard without
  requesting a second generation

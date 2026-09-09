## MODIFIED Requirements

### Requirement: A spawned named occupant completes the full portrait pipeline
A spawned named occupant SHALL reach the fake worker with the deterministic description
built by `character_description()` (display name, race label, story-driven age or the baseline 25,
style template) and the correct `portrait:character:<stable_key>` subject — proving subject
derivation, the canonical-age check, queue enqueue, and prompt rendering work end to end with no art-layer
code changes. A rolled-back materialization SHALL emit no portrait job, preserving the existing
atomicity guarantee. The completed job SHALL publish exactly ONE UNBOUND gallery card carrying the
shared default face rectangle for that subject, rather than a single fixed-identity asset. A
`stable_key` shared across quests SHALL resolve to one gallery holding exactly one auto-generated
card whose description is set by the first materialization: the later materialization sees the
subject's occupied gallery and is suppressed by the automatic-generation guard without requesting a
second generation.

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

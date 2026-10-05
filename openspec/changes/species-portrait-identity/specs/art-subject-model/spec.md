## MODIFIED Requirements

### Requirement: Scene and generic-monster subjects resolve from immutable registries
A scene subject SHALL re-validate its archetype against `SCENE_ARCHETYPE_REGISTRY`; a monster subject
SHALL re-validate its archetype against `MONSTER_TIER_REGISTRY`. An unresolvable registry key SHALL
raise a named `ArtSubjectError` and produce no record. This tier-validated monster subject SHALL remain
the built-in silhouette/gallery generic layer's only monster subject vocabulary: a species key is never
a valid `portrait:monster` subject key, and a species-backed individual's species image identity lives
exclusively in the official content reference layer (the `species-portrait-identity` capability), so no
queue, store, worker, command, or presenter path can smuggle a species key into the tier-validated
subject vocabulary or confuse the two identity layers.

#### Scenario: A registered archetype yields a valid scene subject
- **WHEN** a room carries `scene_archetype = "tavern_interior"` and that key exists in the registry
- **THEN** the subject resolves to `scene:tavern_interior`

#### Scenario: An unknown archetype is rejected
- **WHEN** a room's `scene_archetype` or a forged monster subject names a key absent from the
  registries
- **THEN** resolution raises a named `ArtSubjectError` and no asset record is created

#### Scenario: A species key is not a subject key
- **WHEN** a registered species key is forged into a `portrait:monster` subject
- **THEN** it is rejected exactly like any other key absent from `MONSTER_TIER_REGISTRY`, and the species' official reference resolves through its own provenance-derived path instead

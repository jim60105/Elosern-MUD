## MODIFIED Requirements

### Requirement: Scene and generic-monster subjects resolve from immutable registries
Scene and monster typed subjects SHALL revalidate against their immutable archetype and visual-species registries before queue or official-reference access. A capability-declared registry reference SHALL derive from that validated subject without an entity. Character references SHALL remain entity-provenance-only. Unknown keys SHALL produce a named rejection and no state.

#### Scenario: A registered archetype yields a valid scene subject
- **WHEN** a room carries `scene_archetype = "tavern_interior"` and that key exists in the registry
- **THEN** the subject resolves to `scene:tavern_interior`

#### Scenario: An unknown archetype is rejected
- **WHEN** a room's `scene_archetype` or a forged monster subject names a key absent from the
  registries
- **THEN** resolution raises a named `ArtSubjectError` and no asset record is created

#### Scenario: A species key is not a subject key
- **WHEN** a registered visual species key is supplied as a monster art subject
- **THEN** it resolves that species subject; a threat-tier or unknown key is rejected before any record or prompt

#### Scenario: The tier-validated vocabulary is the generic layer's only monster subject vocabulary
- **WHEN** any queue, store, worker, command or presenter resolves a monster subject
- **THEN** only registered visual-species keys are admitted; the subject and its official reference name the same declared visual species, and no threat tier is an image identity

#### Scenario: Registry lookup does not need a live entity
- **WHEN** a registered scene or monster subject has no spawned entity
- **THEN** official lookup uses its own registry key; an invalid key creates no reference, prompt, record or job

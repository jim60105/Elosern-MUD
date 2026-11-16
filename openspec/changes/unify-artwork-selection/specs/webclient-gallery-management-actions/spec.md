## MODIFIED Requirements

### Requirement: Gallery mutations resolve scene subjects through the scene producer
Gallery mutation adapters SHALL resolve admitted scene keys through the typed scene producer and shared capability-driven generation/default/preference seams. Scene official select/clear SHALL use archetype-scoped state. Scene geometry operations SHALL remain refused and official files SHALL remain immutable.

#### Scenario: Generating a scene image queues one job
- **WHEN** `gallery.generate` names an entered synthetic archetype's scene subject with empty fields and empty text
- **THEN** the result succeeds and exactly one scene gallery job is queued

#### Scenario: Deleting a scene card returns to the bundled image
- **WHEN** `gallery.card.delete` names the only card of an entered archetype
- **THEN** the result succeeds, the gallery is empty, and the archetype's background resolves its explicit official choice or official default when available, else its bundled image

#### Scenario: A face rectangle on a scene card is refused
- **WHEN** `gallery.face_rect.update` names a scene card
- **THEN** the result is `rejected` with `face_rect_unsupported`

#### Scenario: Admitted scene official selection uses shared state
- **WHEN** an actor admitted to a synthetic scene selects a valid official image then requests generation
- **THEN** selection succeeds without writing official files; the generated card cannot clear it; an unadmitted scene request is rejected without writes

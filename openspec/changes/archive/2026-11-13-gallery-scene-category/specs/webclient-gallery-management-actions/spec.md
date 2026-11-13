## ADDED Requirements

### Requirement: Gallery mutations resolve scene subjects through the scene producer
The gallery mutation adapters SHALL resolve a `scene:<archetype>` subject key through the scene kind's typed producer, so an admitted scene subject can be generated or have its card deleted through the existing actions under the scene kind's declared capabilities.

#### Scenario: Generating a scene image queues one job
- **WHEN** `gallery.generate` names an entered synthetic archetype's scene subject with empty fields and empty text
- **THEN** the result succeeds and exactly one scene gallery job is queued

#### Scenario: Deleting a scene card returns to the bundled image
- **WHEN** `gallery.card.delete` names the only card of an entered archetype
- **THEN** the result succeeds, the gallery is empty, and the archetype's background resolves its bundled image

#### Scenario: A face rectangle on a scene card is refused
- **WHEN** `gallery.face_rect.update` names a scene card
- **THEN** the result is `rejected` with `face_rect_unsupported`

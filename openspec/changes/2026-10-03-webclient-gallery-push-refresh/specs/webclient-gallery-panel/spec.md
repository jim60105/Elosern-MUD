## MODIFIED Requirements

### Requirement: Subject selection is session presentation state retired with the options layer

Canonical requirement ID: `webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer`.

The selected subject SHALL be stored per live WebSocket-and-puppet presentation
sequence, defaulting to the puppet. A selection naming no current rail entry
SHALL re-select the puppet at render time without an error. The store SHALL be
retired at disconnect, unpuppet, and account character switch, exactly like the
session options state. The store SHALL expose a write API taking a
rail-grammar subject key and reporting `unknown_subject` for a key naming no
rail entry; the gallery subject-selection `ui_action` adapter is its only
caller, writes nothing else, and publishes one affected-panel update containing
freshly rendered `gallery`, `art`, and `roster` panels on success or domain
rejection under the gallery-management action contract. Nothing in this
capability mutates a gallery record, card, or job.

#### Scenario: Selecting a companion re-renders the companion's gallery

- **WHEN** a client dispatches `gallery.subject.select` naming a listed companion subject
- **THEN** the result succeeds, one update contains freshly rendered gallery, art, and roster with gallery's `selected` naming that subject, and no `GalleryRecord` was touched

#### Scenario: A retired selection falls back to the puppet

- **WHEN** the selected subject's character is destroyed and the panel is re-rendered
- **THEN** `selected` names the puppet again and the panel is available

#### Scenario: Unpuppet clears the selection

- **WHEN** the session unpuppets and later puppets again
- **THEN** the new sequence's selection is the new puppet and no prior selection survives

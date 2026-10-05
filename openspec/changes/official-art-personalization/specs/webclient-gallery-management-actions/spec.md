## ADDED Requirements

### Requirement: Personal official-selection and override adapters reject official-file mutation authoritatively
The production `ui_action` layer SHALL add adapters for the personal official-art preference surface —
selecting an official image identity, clearing the personal official selection, setting an official
image's personal geometry triple (face rectangle and stage), and clearing one geometry override —
each bound to one exact payload validator, re-resolving every client-supplied identity through the
public `world/art/gallery.py` preference API and the startup official catalog (never a direct record
write, never a caller-supplied path), and mapping typed backend errors to stable codes with bounded
localized messages exactly like the existing seven adapters. The existing mutation adapters
(`gallery.card.delete`, generation, default-setting, face-rect, stage, binding) SHALL reject any
request naming an official identity with the stable code `official_read_only` and zero side effects;
the frontend SHALL hide or disable the corresponding affordances, and the backend rejection SHALL
hold for direct requests regardless of client state.

#### Scenario: Selection adapter writes only the preference
- **WHEN** a client dispatches the official-select action with a valid identity inside the selected subject's content reference
- **THEN** the request succeeds through the gallery preference API, one affected-panel update carries freshly rendered gallery/art/roster, and the official directory plus every runtime file are unchanged

#### Scenario: An out-of-reference identity is refused
- **WHEN** a selection or geometry request names an official identity outside the selected subject's content reference, an unindexed identity, or a malformed triple
- **THEN** the adapter refuses with its stable code, no partial write occurs, and the panels re-render truthfully

#### Scenario: Existing mutation adapters refuse official targets
- **WHEN** `gallery.card.delete`, the generate drawer, or the stage-transform action is dispatched with an official identity where a card `image_id` belongs
- **THEN** the stable `official_read_only` rejection returns, no file, card, or preference changes, and one bounded adapter warning event is emitted

#### Scenario: Client-side hiding never weakens the backend
- **WHEN** a client bypasses the hidden affordances and dispatches an official-mutation payload directly
- **THEN** the backend rejects it exactly as if the UI had shown it

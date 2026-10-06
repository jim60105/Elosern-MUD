## MODIFIED Requirements

### Requirement: Seven gallery management actions are registered with exact payload validators

The production action registry SHALL register exactly the seven actions
`gallery.subject.select`, `gallery.generate`, `gallery.default.set`,
`gallery.card.delete`, `gallery.face_rect.update`, `gallery.stage.update`, and `gallery.binding.save`,
each bound to one exact payload validator rejecting any missing, extra, or
wrongly typed field before the adapter runs, and each declaring exactly
`affected_panels: ("gallery", "art", "roster")` on success and domain rejection.
The declaration SHALL be uniform for all seven actions, including subject
selection and generation, even when an action leaves art or roster resolution
unchanged. Each such completed action SHALL publish one newer affected-panel
`ui_update` containing freshly rendered `gallery`, `art`, and `roster` panels
before its action result, whose presentation revision SHALL identify that
update. The existing coordinator's mode-coherence companion panels SHALL remain
permitted; no full snapshot SHALL substitute for this declared-panel update.
Admission failures before the adapter runs and cached duplicate requests SHALL
retain their existing dispatcher publication behavior.

Every persistent-mutation adapter SHALL re-resolve the payload's
`subject_key` — character kind through
`world/art/service.py::resolve_gallery_subject_by_key` (returning the typed
subject and its live entity), registry kinds through the kind's typed producer
— and (where an `image_id` is named) against the subject's tolerant card read,
and SHALL call only `world/art/service.py` / `world/art/gallery.py` public
APIs (including `update_card_face_rect` / `update_card_binding` / `set_stage`) — never a
direct record write. Payloads SHALL use the shared subject-key grammar, and
their `image_id` field SHALL be one of the closed card-reference union: a
canonical lowercase UUID text naming a card of that subject, or a validated
root-relative official image identity naming a catalog-admitted image inside
that subject's content reference (see the `official-art-personalization`
capability).

Selection SHALL instead use `select_gallery_subject(session, actor, subject_key)`
to validate current rail membership and return its result through the dispatcher.
A card image ID SHALL be canonical lowercase UUID text (8-4-4-4-12
hexadecimal). An official image identity arriving in that field SHALL be
refused by the adapter — never by the payload schema — with the stable code
`official_read_only` and zero side effects, before any card read: the official
read-only guarantee holds for a direct request exactly as it does inside the
finder/needle family.

#### Scenario: A tampered subject key resolves or refuses

- **WHEN** `gallery.default.set` names a subject key neither resolver resolves (unknown prefix, dead entity, unknown tier)
- **THEN** the result is `rejected` with a stable code and no gallery record is touched

#### Scenario: A companion subject reaches the entity-gated seams

- **WHEN** `gallery.generate` names a live companion's rail subject key
- **THEN** the adapter resolves the companion entity through the public resolver, passes it to `request_gallery_image`, and the request validates through the declared age precondition

#### Scenario: Extra payload fields reject before any adapter runs

- **WHEN** `gallery.generate` carries a field beyond `subject_key`, `fields`, and `custom_prompt`
- **THEN** the dispatcher returns `malformed_payload` and the adapter never executes

#### Scenario: Every successful gallery action refreshes the same three panels

- **WHEN** any of the seven gallery actions completes successfully under a fresh valid request in exploration mode
- **THEN** its adapter declares exactly `("gallery", "art", "roster")` and one newer `ui_update` contains exactly those three freshly rendered panels, with no `ui_snapshot`, followed by the successful result naming that revision

#### Scenario: Every gallery domain rejection refreshes the same three panels

- **WHEN** any of the seven gallery adapters returns a domain rejection after admission under a fresh request
- **THEN** it declares exactly `("gallery", "art", "roster")`, no rejected mutation is applied, and one newer update refreshes all three panels before the rejected action result naming that revision

#### Scenario: Setting a default refreshes stage portrait sources

- **WHEN** `gallery.default.set` changes the card selected by canonical portrait resolution for an owned roster character or a currently catalogued dialogue host or combat participant
- **THEN** the same action-completion update carries the new gallery default and freshly resolved roster and art portraits, so existing stage consumers receive their new value without a full snapshot

### Requirement: Stage save accepts one exact triple and preserves gallery publication discipline
`gallery.stage.update` SHALL accept exactly `subject_key`, a card reference `image_id` (the closed uuid-or-official-image-identity union above), and `stage`, reject malformed references and stage shape/types/bounds before mutation, re-resolve the subject and card through public gallery APIs, and store accepted values unchanged through the sole writer. An official image identity in `image_id` SHALL be refused with the stable `official_read_only` code and zero side effects, exactly like every other card-reference mutation adapter. Success and admitted domain rejection SHALL declare exactly gallery, art and roster affected panels and reuse the existing result/revision, idempotency and localized rejection ladder. Stage rejection SHALL have a bounded zh-TW message. The adapter SHALL emit one `gallery_action` info event for success or warn for domain rejection. No coordinate-only payload or source image mutation SHALL be accepted.

#### Scenario: Exact stage action saves and publishes once
- **WHEN** a fresh valid stage action submits `{scale: 0.6, x: 0.1, y: -0.2}` for a resolvable existing card
- **THEN** the complete triple is saved unchanged, one newer affected-panel update precedes its successful result and one adapter info event is emitted

#### Scenario: Syntax failures never reach the writer
- **WHEN** a stage action carries an extra/missing payload field, a malformed subject key or card reference, or an invalid stage including a coordinate-only mapping
- **THEN** admission returns malformed_payload and no adapter mutation runs

#### Scenario: Domain rejection preserves storage and draft-correlatable revision
- **WHEN** an admitted request names an unknown card or unresolvable subject, or the writer raises a record error
- **THEN** no partial write occurs, the standard stable code and localized message are returned, gallery/art/roster are refreshed and one adapter warning event is emitted

#### Scenario: Duplicate completed request does not save again
- **WHEN** the same completed stage request id is replayed
- **THEN** the dispatcher returns its cached result without a second write or completion event

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

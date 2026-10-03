## RENAMED Requirements

- FROM: `### Requirement: Six gallery management actions are registered with exact payload validators`
- TO: `### Requirement: Seven gallery management actions are registered with exact payload validators`

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
direct record write. Payloads SHALL use the shared subject-key grammar and
uuid-form `image_id` bound.

Selection SHALL instead use `select_gallery_subject(session, actor, subject_key)`
to validate current rail membership and return its result through the dispatcher.
Image IDs SHALL be canonical lowercase UUID text (8-4-4-4-12 hexadecimal).

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

### Requirement: Every management mutation emits one facade event

Each of the seven adapters SHALL emit exactly one `gallery_action` event through
the `world.observability` facade on completion (info for success, warn for
domain rejection) carrying `subject`, `action_id`, and — when the action names
one — `image_id` and `kind` in `context`. No adapter SHALL import Evennia
logging directly, and the existing `gallery_generate` /
`gallery_card_removed` / `gallery_default_set` service-boundary events SHALL
stay unchanged.

#### Scenario: A set-default emits one info event with business ids

- **WHEN** `gallery.default.set` succeeds
- **THEN** one `gallery_action` info event carries the subject, action id, image id, and kind, and the service-level `gallery_default_set` event still fires

## ADDED Requirements

### Requirement: Stage save accepts one exact triple and preserves gallery publication discipline
`gallery.stage.update` SHALL accept exactly `subject_key`, canonical lowercase UUID `image_id`, and `stage`, reject malformed identities and stage shape/types/bounds before mutation, re-resolve the subject and card through public gallery APIs, and store accepted values unchanged through the sole writer. Success and admitted domain rejection SHALL declare exactly gallery, art and roster affected panels and reuse the existing result/revision, idempotency and localized rejection ladder. Stage rejection SHALL have a bounded zh-TW message. The adapter SHALL emit one `gallery_action` info event for success or warn for domain rejection. No coordinate-only payload or source image mutation SHALL be accepted.

#### Scenario: Exact stage action saves and publishes once
- **WHEN** a fresh valid stage action submits `{scale: 0.6, x: 0.1, y: -0.2}` for a resolvable existing card
- **THEN** the complete triple is saved unchanged, one newer affected-panel update precedes its successful result and one adapter info event is emitted

#### Scenario: Syntax failures never reach the writer
- **WHEN** a stage action carries an extra/missing payload field, malformed subject/UUID, or invalid stage including a coordinate-only mapping
- **THEN** admission returns malformed_payload and no adapter mutation runs

#### Scenario: Domain rejection preserves storage and draft-correlatable revision
- **WHEN** an admitted request names an unknown card or unresolvable subject, or the writer raises a record error
- **THEN** no partial write occurs, the standard stable code and localized message are returned, gallery/art/roster are refreshed and one adapter warning event is emitted

#### Scenario: Duplicate completed request does not save again
- **WHEN** the same completed stage request id is replayed
- **THEN** the dispatcher returns its cached result without a second write or completion event

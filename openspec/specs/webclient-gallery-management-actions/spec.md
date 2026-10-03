# webclient-gallery-management-actions Specification

## Purpose

Defines the seven production `ui_action` adapters that let the webclient reach the gallery backend's management seam: subject selection, image generation, default setting, card deletion, face-rect re-marking, stage transformation, and binding saving. Each action binds one exact payload validator, re-resolves every client-supplied identity through the public `world/art/service.py` / `world/art/gallery.py` APIs (never a direct record write), maps typed backend errors to stable codes with bounded zh-TW messages, uniformly declares `("gallery", "art", "roster")` so each completed success or domain rejection publishes one newer three-panel update plus one facade observability event, and obeys the dispatcher's idempotency discipline.

## Requirements

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

### Requirement: Subject selection writes only session presentation state

Canonical requirement ID: `webclient-gallery-management-actions::subject-selection-writes-only-session-presentation-state`.

`gallery.subject.select` SHALL accept exactly `subject_key`, SHALL write only
the per-presentation-sequence selection store shipped by the gallery panel, and
SHALL return stable code `unknown_subject` (zh-TW message) when the key names no
current rail entry. It SHALL NOT create, mutate, or delete any gallery record,
card, or job, and its success or domain rejection SHALL declare exactly
`affected_panels: ("gallery", "art", "roster")` and publish one newer
`ui_update` containing those freshly rendered panels through the dispatcher.

#### Scenario: Selecting a rail subject re-renders the panel

- **WHEN** a client selects a listed companion subject key
- **THEN** the result succeeds, one update contains `gallery`, `art`, and `roster`, gallery names the subject as `selected`, and the selection store is retired with the sequence at unpuppet

#### Scenario: An unknown selection preserves state while refreshing presentation

- **WHEN** a schema-valid selected key names no current rail entry
- **THEN** selection is rejected with `unknown_subject`, the prior selection and all gallery records remain unchanged, and one update re-renders gallery, art, and roster from the current state

### Requirement: Generation routes one request through the service seam

`gallery.generate` SHALL accept exactly `subject_key`, `fields` (a possibly
empty list of distinct ids from the closed catalog `appearance`,
`weapon_main`, `weapon_off`, `armor`, `accessories`), and `custom_prompt` (text
of at most 512 code points, control-character-free; whitespace-only is legal
and normalizes to empty). Printable text SHALL follow the shared backend
validator: every Unicode C or Z category except ASCII space is rejected.
Unknown or duplicated field ids and oversized/non-printable prompts SHALL
fail the kind-neutral payload schema with `malformed_payload`, without invoking
the adapter. The `unknown_field`, `prompt_too_long`, and `invalid_prompt` domain
codes SHALL remain the defensive mapping of typed service errors when an
adapter is invoked directly or the service adds a stricter refusal.
A successful adapter call SHALL invoke
`request_gallery_image` exactly once and SHALL return outcome `success` with the
minted `image_id` in the result's bounded `data` slot. Typed rejections SHALL
map to stable codes with bounded zh-TW messages — at minimum `unknown_field`,
`prompt_too_long`, and the kind-capability refusals naming the undeclared
capability. The adapter SHALL NOT probe service connectivity: an unreachable
image server keeps the request successful (§12.3.1) and the failure surfaces
later as the panel's failed row.

#### Scenario: A character request mints one pending image

- **WHEN** `gallery.generate` carries `fields: ["appearance", "armor"]` and bounded free text for the puppet
- **THEN** one gallery job is queued, the result data carries the minted `image_id`, and the panel re-render lists exactly one pending row

#### Scenario: Monster generation is field-free and replace-shaped

- **WHEN** `gallery.generate` names a monster-tier subject with empty fields and empty free text
- **THEN** the request succeeds, and when its job settles the subject holds exactly one card (the cap's replace semantics), with no binding affordances offered by the panel's capability flags

#### Scenario: A monster request carrying fields is refused naming the capability

- **WHEN** `gallery.generate` names a monster-tier subject with a non-empty `fields` list
- **THEN** the result is `rejected` with a stable capability-naming code and nothing is queued

### Requirement: Default set and card delete follow the shipped delete-never-dangles contract

`gallery.default.set` SHALL accept exactly `subject_key` and `image_id` and call
`world/art/gallery.py::set_default`; `gallery.card.delete` SHALL accept the same
exact pair and call `remove_card`. An unknown card SHALL refuse with stable code
`unknown_card`. Deleting the current default SHALL leave `default_image_id`
null (never dangling) and the panel SHALL re-render truthfully afterwards; the
adapter SHALL NOT synthesize a replacement default. Both actions SHALL be
idempotency-deduplicated by the dispatcher's completed-request cache.

#### Scenario: Deleting the default falls through to the chain

- **WHEN** the only card of a subject is deleted
- **THEN** the record's default is null, the panel lists no card, and resolution falls to the classic/fallback chain

#### Scenario: A second delete of the same card refuses

- **WHEN** `gallery.card.delete` names an already-removed card under a fresh request id
- **THEN** the result is `rejected` with `unknown_card`

### Requirement: Face-rect save stores the validated rect verbatim

`gallery.face_rect.update` SHALL accept exactly `subject_key`, `image_id`, and
`face_rect` (`x`, `y`, `w`, `h` reals in [0,1], `x+w ≤ 1`, `y+h ≤ 1`, positive
`w`/`h`), SHALL reject a rect that is not pixel-square against the target card's
recorded `image_size` (`w × width` and `h × height` within one pixel; no rect
value is exempt — a replayed shared default constant on a non-square card is
rejected like any other non-square rect), SHALL
persist an accepted rect verbatim through
`world/art/gallery.py::update_card_face_rect`, and SHALL NOT crop,
resize, or store any second image. The payload schema SHALL NOT admit an image
size: the squareness reference is always the card's server-recorded size, never
client-asserted. The 1:1 crop preview is a client-local
rendering of the same image; the server stores only the rectangle.

#### Scenario: A stored rect equals the submitted rect exactly

- **WHEN** a pixel-square rect is saved for a card
- **THEN** the stored card rect matches field-for-field and exactly one image file remains referenced by that card

#### Scenario: An out-of-bounds rect rejects with no write

- **WHEN** `face_rect` carries `x + w > 1`
- **THEN** the result is `rejected` and the stored card is unchanged

#### Scenario: A non-square rect rejects with no write

- **WHEN** `face_rect` marks a box whose pixel width and height disagree beyond one pixel on the card's recorded image size
- **THEN** the result is `rejected` and the stored card is unchanged

#### Scenario: The legacy default constant rejects on a non-square card

- **WHEN** `face_rect` is field-for-field equal to the shared default constant for a card whose recorded `image_size` makes it non-square
- **THEN** the result is `rejected` and the stored card is unchanged

#### Scenario: A square-on-screen rect on a portrait card is accepted

- **WHEN** a card whose recorded `image_size` is 768×1024 receives `face_rect` `w = 0.4`, `h = 0.3` inside the unit square
- **THEN** the result is the declared success presentation and the stored rect equals the submitted rect verbatim

### Requirement: Binding save captures the current snapshot and never accepts item keys

`gallery.binding.save` SHALL accept exactly `subject_key`, `image_id`, and
`slots` (a non-empty list of distinct ids from `weapon_main`, `weapon_off`,
`armor`, `accessories`) — no item key SHALL ever appear in the payload. The
adapter SHALL build the binding as `{mask: slots in declared order, snapshot:
the CURRENT normalized equipment snapshot over exactly the masked slots}` from
the stored-state no-create reader, and persist through
`world/art/gallery.py::update_card_binding`. An
enabled slot whose equipment is empty binds `None` (empty list for
accessories); an all-empty snapshot stays legal. For a kind whose declaration
supports no bindings the action SHALL refuse with stable code
`binding_unsupported`.

The declared mask order SHALL be the backend `SLOT_ORDER`, independent of
the client's slot-list permutation. A resolved kind without binding support
SHALL return `binding_unsupported` before card lookup, including when no card
exists.

#### Scenario: Saving binds what is worn right now

- **WHEN** the puppet wears a main weapon and armor and the editor enables both slots
- **THEN** the stored mask is `["weapon_main", "armor"]` in declared order and the snapshot carries exactly the currently worn keys

#### Scenario: An enabled empty slot binds emptiness

- **WHEN** the editor enables `weapon_off` while the puppet is unarmed in that hand
- **THEN** the stored snapshot carries `null` for that slot

#### Scenario: Item keys cannot be smuggled

- **WHEN** a `gallery.binding.save` payload carries any item-key field
- **THEN** validation rejects the payload before the adapter runs

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

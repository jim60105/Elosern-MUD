# webclient-gallery-management-actions Specification

## Purpose

Defines the seven production `ui_action` adapters that let the webclient reach the gallery backend's management seam: subject selection, image generation, default setting, card deletion, face-rect re-marking, stage transformation, and binding saving. Each action binds one exact payload validator, re-resolves every client-supplied identity through the public `world/art/service.py` / `world/art/gallery.py` APIs (never a direct record write), maps typed backend errors to stable codes with bounded zh-TW messages, uniformly declares `("gallery", "art", "roster")` so each completed success or domain rejection publishes one newer three-panel update plus one facade observability event, and obeys the dispatcher's idempotency discipline.

## Requirements

### Requirement: Seven gallery management actions are registered with exact payload validators

The production action registry SHALL register exactly the seven actions
`gallery.subject.select`, `gallery.generate`, `gallery.default.set`,
`gallery.card.delete`, `gallery.face_rect.update`, `gallery.stage.update`, and `gallery.binding.save`,
each bound to one exact payload validator that admits no missing, extra, or
wrongly typed field before the adapter runs.

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

#### Scenario: Every action declares the same affected panels

- **WHEN** any of the seven actions completes successfully or with a domain rejection
- **THEN** it declares exactly `affected_panels: ("gallery", "art", "roster")`, uniformly for all
  seven actions, including subject selection and generation, even when an action leaves art or
  roster resolution unchanged

#### Scenario: A completed action publishes its declared-panel update first

- **WHEN** any such action completes
- **THEN** it publishes one newer affected-panel `ui_update` containing freshly rendered `gallery`,
  `art`, and `roster` panels before its action result, whose presentation revision identifies that
  update

#### Scenario: Companion panels stay permitted and snapshots never substitute

- **WHEN** a gallery action completes while the coordinator has mode-coherence work pending
- **THEN** the existing coordinator's mode-coherence companion panels remain permitted and no full
  snapshot substitutes for the declared-panel update

#### Scenario: Pre-adapter and cached-request publication is unchanged

- **WHEN** a request fails admission before the adapter runs, or is a cached duplicate request
- **THEN** it retains its existing dispatcher publication behavior

#### Scenario: Mutation adapters re-resolve every client identity

- **WHEN** a persistent-mutation adapter runs
- **THEN** it re-resolves the payload's `subject_key` — character kind through
  `world/art/service.py::resolve_gallery_subject_by_key` (returning the typed subject and its live
  entity), registry kinds through the kind's typed producer — and (where an `image_id` is named)
  against the subject's tolerant card read, and calls only `world/art/service.py` /
  `world/art/gallery.py` public APIs (including `update_card_face_rect` / `update_card_binding` /
  `set_stage`) — never a direct record write

#### Scenario: Payloads use the shared grammar and closed card references

- **WHEN** any of the seven payloads is validated
- **THEN** it uses the shared subject-key grammar, and its `image_id` field is one of the closed
  card-reference union: a canonical lowercase UUID text naming a card of that subject, or a
  validated root-relative official image identity naming a catalog-admitted image inside that
  subject's content reference (see the `official-art-personalization` capability)

#### Scenario: Selection validates rail membership through the service API

- **WHEN** `gallery.subject.select` runs
- **THEN** it uses `select_gallery_subject(session, actor, subject_key)` to validate current rail
  membership and returns its result through the dispatcher

#### Scenario: An official identity in a card field is refused by the adapter

- **WHEN** an official image identity arrives in an `image_id` field (a card image ID is canonical
  lowercase UUID text, 8-4-4-4-12 hexadecimal)
- **THEN** the adapter — never the payload schema — refuses it with the stable code
  `official_read_only` and zero side effects, before any card read: the official read-only
  guarantee holds for a direct request exactly as it does inside the finder/needle family

### Requirement: Subject selection writes only session presentation state

Canonical requirement ID: `webclient-gallery-management-actions::subject-selection-writes-only-session-presentation-state`.

`gallery.subject.select` SHALL accept exactly `subject_key`, SHALL write only
the per-presentation-sequence selection store shipped by the gallery panel, and
SHALL return stable code `unknown_subject` (zh-TW message) when the key names no
current rail entry. It SHALL NOT create, mutate, or delete any gallery record,
card, or job.

#### Scenario: Selecting a rail subject re-renders the panel

- **WHEN** a client selects a listed companion subject key
- **THEN** the result succeeds, one update contains `gallery`, `art`, and `roster`, gallery names the subject as `selected`, and the selection store is retired with the sequence at unpuppet

#### Scenario: An unknown selection preserves state while refreshing presentation

- **WHEN** a schema-valid selected key names no current rail entry
- **THEN** selection is rejected with `unknown_subject`, the prior selection and all gallery records remain unchanged, and one update re-renders gallery, art, and roster from the current state

#### Scenario: Selection publishes its declared-panel update through the dispatcher

- **WHEN** `gallery.subject.select` completes with success or with a domain rejection
- **THEN** it declares exactly `affected_panels: ("gallery", "art", "roster")` and publishes one
  newer `ui_update` containing those freshly rendered panels through the dispatcher

### Requirement: Generation routes one request through the service seam

`gallery.generate` SHALL accept exactly `subject_key`, `fields` (a possibly
empty list of distinct ids from the closed catalog `appearance`,
`weapon_main`, `weapon_off`, `armor`, `accessories`), and `custom_prompt` (bounds pinned by the
prompt-validator scenario below).
A successful adapter call SHALL invoke
`request_gallery_image` exactly once and SHALL return outcome `success` with the
minted `image_id` in the result's bounded `data` slot.

#### Scenario: A character request mints one pending image

- **WHEN** `gallery.generate` carries `fields: ["appearance", "armor"]` and bounded free text for the puppet
- **THEN** one gallery job is queued, the result data carries the minted `image_id`, and the panel re-render lists exactly one pending row

#### Scenario: Monster generation is field-free and replace-shaped

- **WHEN** `gallery.generate` names a monster-tier subject with empty fields and empty free text
- **THEN** the request succeeds, and when its job settles the subject holds exactly one card (the cap's replace semantics), with no binding affordances offered by the panel's capability flags

#### Scenario: A monster request carrying fields is refused naming the capability

- **WHEN** `gallery.generate` names a monster-tier subject with a non-empty `fields` list
- **THEN** the result is `rejected` with a stable capability-naming code and nothing is queued

#### Scenario: Prompt text bounds follow the shared printable-text validator

- **WHEN** a `custom_prompt` is validated
- **THEN** it is text of at most 512 code points, control-character-free; whitespace-only is legal
  and normalizes to empty; and printable text follows the shared backend validator — every Unicode
  C or Z category except ASCII space is rejected

#### Scenario: Bad fields or prompts fail the schema without the adapter

- **WHEN** field ids are unknown or duplicated, or the prompt is oversized or non-printable
- **THEN** the kind-neutral payload schema fails with `malformed_payload`, without invoking the
  adapter

#### Scenario: Domain codes remain the defensive typed-error mapping

- **WHEN** an adapter is invoked directly or the service adds a stricter refusal
- **THEN** the `unknown_field`, `prompt_too_long`, and `invalid_prompt` domain codes remain the
  defensive mapping of typed service errors

#### Scenario: Typed rejections map to stable localized codes

- **WHEN** the service rejects a generation request with a typed error
- **THEN** it maps to stable codes with bounded zh-TW messages — at minimum `unknown_field`,
  `prompt_too_long`, and the kind-capability refusals naming the undeclared capability

#### Scenario: An unreachable image server keeps the request successful

- **WHEN** the image server is unreachable when a generation request is admitted
- **THEN** the adapter does not probe service connectivity, the request stays successful (§12.3.1),
  and the failure surfaces later as the panel's failed row

### Requirement: Default set and card delete follow the shipped delete-never-dangles contract

`gallery.default.set` SHALL accept exactly `subject_key` and `image_id` and call
`world/art/gallery.py::set_default`; `gallery.card.delete` SHALL accept the same
exact pair and call `remove_card`. An unknown card SHALL refuse with stable code
`unknown_card`. Deleting the current default SHALL leave `default_image_id`
null (never dangling) and the panel SHALL re-render truthfully afterwards; the
adapter SHALL NOT synthesize a replacement default.

#### Scenario: Deleting the default falls through to the chain

- **WHEN** the only card of a subject is deleted
- **THEN** the record's default is null, the panel lists no card, and resolution falls to the classic/fallback chain

#### Scenario: A second delete of the same card refuses

- **WHEN** `gallery.card.delete` names an already-removed card under a fresh request id
- **THEN** the result is `rejected` with `unknown_card`

#### Scenario: Replay of a completed default-set or delete is deduplicated

- **WHEN** the dispatcher sees a repeated request id for a completed `gallery.default.set` or
  `gallery.card.delete`
- **THEN** both actions are idempotency-deduplicated by the dispatcher's completed-request cache

### Requirement: Face-rect save stores the validated rect verbatim

`gallery.face_rect.update` SHALL accept exactly `subject_key`, `image_id`, and
`face_rect` (`x`, `y`, `w`, `h` reals in [0,1], `x+w ≤ 1`, `y+h ≤ 1`, positive
`w`/`h`), SHALL reject a rect that is not pixel-square against the target card's
recorded `image_size`, SHALL persist an accepted rect verbatim through
`world/art/gallery.py::update_card_face_rect`, and SHALL NOT crop,
resize, or store any second image.

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

#### Scenario: The squareness tolerance is one pixel and no value is exempt

- **WHEN** a rect's squareness is judged against the card's recorded `image_size`
- **THEN** `w × width` and `h × height` must be within one pixel, and no rect value is exempt — a
  replayed shared default constant on a non-square card is rejected like any other non-square rect

#### Scenario: The squareness reference is never client-asserted

- **WHEN** a `gallery.face_rect.update` payload is validated
- **THEN** the payload schema admits no image size: the squareness reference is always the card's
  server-recorded size, never client-asserted

#### Scenario: The crop preview stays client-local

- **WHEN** the client renders the 1:1 crop preview
- **THEN** it is a client-local rendering of the same image and the server stores only the rectangle

### Requirement: Binding save captures the current snapshot and never accepts item keys

`gallery.binding.save` SHALL accept exactly `subject_key`, `image_id`, and
`slots` (a non-empty list of distinct ids from `weapon_main`, `weapon_off`,
`armor`, `accessories`) — no item key SHALL ever appear in the payload. The
adapter SHALL build the binding as `{mask: slots in declared order, snapshot:
the CURRENT normalized equipment snapshot over exactly the masked slots}`.

#### Scenario: Saving binds what is worn right now

- **WHEN** the puppet wears a main weapon and armor and the editor enables both slots
- **THEN** the stored mask is `["weapon_main", "armor"]` in declared order and the snapshot carries exactly the currently worn keys

#### Scenario: An enabled empty slot binds emptiness

- **WHEN** the editor enables `weapon_off` while the puppet is unarmed in that hand
- **THEN** the stored snapshot carries `null` for that slot

#### Scenario: Item keys cannot be smuggled

- **WHEN** a `gallery.binding.save` payload carries any item-key field
- **THEN** validation rejects the payload before the adapter runs

#### Scenario: An empty-slot binding uses the no-create reader

- **WHEN** the adapter reads stored equipment state to build a binding
- **THEN** it reads through the stored-state no-create reader and persists through
  `world/art/gallery.py::update_card_binding`, with no record creation or direct write

#### Scenario: Empty accessories and all-empty snapshots stay legal

- **WHEN** the editor enables `accessories` with nothing worn, or every enabled slot is empty
- **THEN** the stored snapshot carries the empty list for `accessories` where a single slot binds
  `None`, and an all-empty snapshot stays legal

#### Scenario: Declared mask order ignores the client's permutation

- **WHEN** a binding is built from a client slot list in any permutation
- **THEN** the declared mask order is the backend `SLOT_ORDER`, independent of the client's
  slot-list permutation

#### Scenario: Unsupported kinds refuse before card lookup

- **WHEN** the resolved kind supports no bindings
- **THEN** the action returns `binding_unsupported` before card lookup, including when no card
  exists

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
`gallery.stage.update` SHALL accept exactly `subject_key`, a card reference `image_id` (the closed uuid-or-official-image-identity union above), and `stage`, reject malformed references and stage shape/types/bounds before mutation, re-resolve the subject and card through public gallery APIs, and store accepted values unchanged through the sole writer.

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

#### Scenario: An official identity in a stage payload is refused
- **WHEN** an official image identity arrives in `image_id`
- **THEN** it is refused with the stable `official_read_only` code and zero side effects, exactly
  like every other card-reference mutation adapter

#### Scenario: Stage results reuse the gallery publication and rejection discipline
- **WHEN** a stage action succeeds or an admitted request is domain-rejected
- **THEN** it declares exactly gallery, art and roster affected panels and reuses the existing
  result/revision, idempotency and localized rejection ladder, and a stage rejection carries a
  bounded zh-TW message

#### Scenario: One stage adapter event per completion
- **WHEN** a stage action completes
- **THEN** the adapter emits one `gallery_action` info event for success or warn for domain
  rejection

#### Scenario: Coordinate-only payloads and source mutation are inadmissible
- **WHEN** a stage payload is coordinate-only or asks for source image mutation
- **THEN** no such payload or mutation is accepted

### Requirement: Personal official-selection and override adapters reject official-file mutation authoritatively
The production `ui_action` layer SHALL add adapters for the personal official-art preference surface —
selecting an official image identity, clearing the personal official selection, setting an official
image's personal geometry triple (face rectangle and stage), and clearing one geometry override —
each bound to one exact payload validator.

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

#### Scenario: Preference adapters re-resolve identities and map typed errors
- **WHEN** a preference adapter handles a request
- **THEN** it re-resolves every client-supplied identity through the public `world/art/gallery.py`
  preference API and the startup official catalog (never a direct record write, never a
  caller-supplied path), and maps typed backend errors to stable codes with bounded localized
  messages exactly like the existing seven adapters

#### Scenario: Every existing mutation adapter rejects official targets
- **WHEN** any of `gallery.card.delete`, generation, default-setting, face-rect, stage, or binding
  is requested naming an official identity
- **THEN** it is rejected with the stable code `official_read_only` and zero side effects

#### Scenario: The frontend hides official-mutation affordances
- **WHEN** the client renders official-art surfaces
- **THEN** it hides or disables the corresponding affordances, while the backend rejection holds for
  direct requests regardless of client state

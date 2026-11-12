## MODIFIED Requirements

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
- **THEN** it uses the version-4 selection store to validate membership of the selected
  category and returns its result through the dispatcher

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
SHALL return stable code `unknown_subject` (zh-TW message) when the key is not
listed in the selected category. It SHALL NOT create, mutate, or delete any gallery record,
card, or job.

#### Scenario: Selecting a rail subject re-renders the panel

- **WHEN** a client selects a companion subject key listed in the selected `party` category
- **THEN** the result succeeds, one update contains `gallery`, `art`, and `roster`, gallery names the subject as `selected`, and the selection store is retired with the sequence at unpuppet

#### Scenario: An unknown selection preserves state while refreshing presentation

- **WHEN** a schema-valid selected key is not listed in the selected category
- **THEN** selection is rejected with `unknown_subject`, the prior selection and all gallery records remain unchanged, and one update re-renders gallery, art, and roster from the current state

#### Scenario: Selection publishes its declared-panel update through the dispatcher

- **WHEN** `gallery.subject.select` completes with success or with a domain rejection
- **THEN** it declares exactly `affected_panels: ("gallery", "art", "roster")` and publishes one
  newer `ui_update` containing those freshly rendered panels through the dispatcher


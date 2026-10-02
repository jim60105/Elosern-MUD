## MODIFIED Requirements

### Requirement: Six gallery management actions are registered with exact payload validators

Canonical requirement ID: `webclient-gallery-management-actions::six-gallery-management-actions-are-registered-with-exact-payload-validators`.

The production action registry SHALL register exactly the six actions
`gallery.subject.select`, `gallery.generate`, `gallery.default.set`,
`gallery.card.delete`, `gallery.face_rect.update`, and `gallery.binding.save`,
each bound to one exact payload validator rejecting any missing, extra, or
wrongly typed field before the adapter runs, and each declaring exactly
`affected_panels: ("gallery", "art", "roster")` on success and domain rejection.
The declaration SHALL be uniform for all six actions, including subject
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
APIs (including `update_card_face_rect` / `update_card_binding`) — never a
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

- **WHEN** any of the six gallery actions completes successfully under a fresh valid request in exploration mode
- **THEN** its adapter declares exactly `("gallery", "art", "roster")` and one newer `ui_update` contains exactly those three freshly rendered panels, with no `ui_snapshot`, followed by the successful result naming that revision

#### Scenario: Every gallery domain rejection refreshes the same three panels

- **WHEN** any of the six gallery adapters returns a domain rejection after admission under a fresh request
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

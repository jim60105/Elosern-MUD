## MODIFIED Requirements

### Requirement: Default set and card delete follow the shipped delete-never-dangles contract

`gallery.default.set` SHALL accept exactly `subject_key` and `image_id` and call
`world/art/gallery.py::set_default`; `gallery.card.delete` SHALL accept the same
exact pair and call `remove_card`. An unknown card SHALL refuse with stable code
`unknown_card`. Deleting the current default SHALL leave `default_image_id`
null (never dangling) and the panel SHALL re-render truthfully afterwards; the
adapter SHALL NOT synthesize a replacement default.

#### Scenario: Deleting the default falls through to the chain

- **WHEN** the only card of a subject is deleted
- **THEN** the record's default is null, the panel lists no card, and resolution falls to the official-default and declared-terminal chain

#### Scenario: A second delete of the same card refuses

- **WHEN** `gallery.card.delete` names an already-removed card under a fresh request id
- **THEN** the result is `rejected` with `unknown_card`

#### Scenario: Replay of a completed default-set or delete is deduplicated

- **WHEN** the dispatcher sees a repeated request id for a completed `gallery.default.set` or
  `gallery.card.delete`
- **THEN** both actions are idempotency-deduplicated by the dispatcher's completed-request cache

## MODIFIED Requirements

### Requirement: The gallery prompt field catalog is a closed, ordered vocabulary
`world/art/gallery_prompt.py` SHALL define exactly one closed field catalog for gallery generation
requests: `appearance`, `weapon_main`, `weapon_off`, `armor`, `accessories`, in that declared order.
The catalog SHALL apply ONLY to subject kinds whose capability declaration supports a field selection;
a kind that does not — the generic monster kind, whose description is registry-owned — SHALL have no
selectable field, and a non-empty selection for such a kind SHALL raise a typed error at the service
boundary naming the undeclared capability rather than being silently dropped.

A request's selected fields SHALL be validated against the catalog before any prompt render and
before any queue write: an unknown id, a non-string id, or a duplicated id SHALL raise a typed error
at the service boundary. The selection SHALL be normalized to the declared order and stored verbatim
on the resulting card's `requested_fields`, so a card always reports which data blocks produced it.
Selecting no field SHALL be legal for every gallery-bearing kind.

#### Scenario: A selection is normalized and recorded on the card
- **WHEN** a gallery image is requested selecting `armor` and `appearance` in that order
- **THEN** the prompt contributions are composed in the declared catalog order and the settled card's `requested_fields` is `["appearance", "armor"]`

#### Scenario: An unknown or duplicated field id is rejected before any render
- **WHEN** a gallery image is requested with a field id absent from the catalog, a non-string id, or the same id twice
- **THEN** a typed error is raised, no prompt is rendered, and no record is created

#### Scenario: Selecting nothing is legal
- **WHEN** a gallery image is requested with an empty field selection
- **THEN** the request is accepted and the card records an empty `requested_fields`

#### Scenario: A kind without field support rejects any selection
- **WHEN** a gallery image is requested for a monster subject naming any catalog field
- **THEN** a typed error is raised, no prompt is rendered, no record is created, and the card provenance never claims a field the kind cannot use

#### Scenario: A monster card records an empty provenance
- **WHEN** a monster gallery generation settles successfully
- **THEN** the settled card's `requested_fields` is empty and its description came from the monster registry

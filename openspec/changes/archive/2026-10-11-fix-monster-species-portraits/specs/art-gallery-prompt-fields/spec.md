# Spec Delta

## MODIFIED Requirements

### Requirement: The gallery prompt field catalog is a closed, ordered vocabulary
`world/art/gallery_prompt.py` SHALL define exactly one closed field catalog for gallery generation
requests: `appearance`, `weapon_main`, `weapon_off`, `armor`, `accessories`, in that declared order.
The catalog SHALL apply ONLY to subject kinds whose capability declaration supports a field
selection.

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
- **WHEN** a registered visual species monster gallery generation settles successfully
- **THEN** requested_fields is empty and its description contains only the selected visual species public physical appearance, with no threat-tier rank or mixed-species examples

#### Scenario: A write claiming field provenance for a kind without selection is refused
- **WHEN** a card carrying a non-empty `requested_fields` is appended for a subject whose kind declaration supports no field selection
- **THEN** a typed error is raised and the record is unchanged

#### Scenario: A kind without selection support declares no selectable field
- **WHEN** a subject kind's capability declaration does not support field selection — the generic
  monster kind, whose visual species physical description is registry-owned
- **THEN** it has no selectable field, and a non-empty selection for such a kind raises a typed
  error at the service boundary naming the undeclared capability rather than being silently dropped

#### Scenario: Field validation precedes render and queue write
- **WHEN** a request's selected fields are checked against the catalog
- **THEN** validation runs before any prompt render and before any queue write, and an unknown id,
  a non-string id, or a duplicated id raises a typed error at the service boundary

#### Scenario: Provenance is stored verbatim in declared order
- **WHEN** a selection is accepted
- **THEN** it is normalized to the declared order and stored verbatim on the resulting card's
  `requested_fields`, so a card always reports which data blocks produced it

#### Scenario: Empty selection is legal for every gallery-bearing kind
- **WHEN** any gallery-bearing kind requests an image with no field selected
- **THEN** the request is accepted

#### Scenario: The card-write boundary enforces the same declaration
- **WHEN** a card settles for a kind that does not support field selection
- **THEN** it stores an empty `requested_fields`, because `requested_fields` is a provenance claim
  about which data blocks produced the image and a stored claim the kind could never have requested
  would make the card lie


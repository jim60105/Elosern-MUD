# art-gallery-prompt-fields Specification

## Purpose

Define the closed gallery prompt-field vocabulary — the persona `appearance`
block plus the four equipment slots — its typed validation and declared-order
normalization at the service seam, the registry-owned visual text and bounded
free-text contributions to the composed character description, and the
`requested_fields` provenance every settled card carries.

## Requirements

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

A card's `requested_fields` is a provenance claim about which data blocks produced the image, so the
gallery card-write boundary SHALL enforce the same declaration: a card whose kind does not support a
field selection SHALL store an empty `requested_fields`, and a write claiming a non-empty provenance
for such a kind SHALL raise a typed error and leave the record unchanged — a stored claim the kind
could never have requested would make the card lie.

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

#### Scenario: A write claiming field provenance for a kind without selection is refused
- **WHEN** a card carrying a non-empty `requested_fields` is appended for a subject whose kind declaration supports no field selection
- **THEN** a typed error is raised and the record is unchanged

### Requirement: Equipment fields contribute registry-owned visual text and nothing else
An equipment field's contribution SHALL be derived exclusively from the item keys stored in that slot
and the matching `world/lore/items.py::ItemPresentation` visual text of the immutable item registry,
read read-only. `accessories` SHALL contribute its items in lexicographically sorted key order so the
contribution is deterministic. An empty slot, an item key absent from the registry, and malformed
equipment storage SHALL contribute nothing and SHALL NOT raise. No item mechanic, stat, price, rarity
weighting, or non-presentation registry field SHALL reach the prompt, and no equipment state SHALL be
written or materialized while composing.

#### Scenario: Equipped registered items contribute their presentation text
- **WHEN** a request selects `weapon_main` and `armor` for a character wearing registered items in both slots
- **THEN** the composed description contains both items' registry presentation text in the declared slot order

#### Scenario: Accessories are contributed in sorted key order
- **WHEN** a request selects `accessories` for a character wearing several accessories stored in arbitrary order
- **THEN** their contributions appear in lexicographically sorted item-key order

#### Scenario: Unknown keys and malformed storage contribute nothing
- **WHEN** a request selects an equipment field for a slot holding an unregistered item key, or for an entity whose equipment storage is malformed
- **THEN** that field contributes no text, no exception propagates, and no equipment state is written

### Requirement: Free-form prompt text is bounded, sanitized, and appended verbatim
`custom_prompt` SHALL be validated before any render: it SHALL be text, SHALL be rejected when it
exceeds the declared code-point bound, and SHALL be rejected when it contains any control character
(including line and paragraph separators). Accepted text SHALL be whitespace-normalized to a single
line and appended verbatim after every selected field's contribution, through a prompt-library slot —
never by string concatenation onto rendered template output. An empty or whitespace-only value SHALL
contribute nothing and SHALL be legal.

#### Scenario: Accepted free text is appended verbatim
- **WHEN** a request supplies bounded free text alongside a field selection
- **THEN** the composed description ends with that text verbatim, after the field contributions

#### Scenario: Over-long or control-bearing text is rejected before any render
- **WHEN** a request supplies free text exceeding the bound or containing a control character
- **THEN** a typed error is raised, no prompt is rendered, and no record is created

#### Scenario: Empty free text is a legal no-op
- **WHEN** a request supplies an empty or whitespace-only `custom_prompt`
- **THEN** the request is accepted and the composed description carries no free-text section

### Requirement: The prompt library remains the sole source of the composed template
The `{equipment}` and `{custom}` sections SHALL be slots of the `art.character_description` template
in `prompts/art.yaml`, declared in the `art.character_description` `PromptSpec`'s
`allowed_placeholders`; `world/art/` SHALL NOT embed their surrounding text as Python constants. When
the prompt library cannot resolve the template, the existing registry-driven fallback SHALL be used
unchanged: it reads no persona, no equipment, and no free text.

#### Scenario: The template owns every section's surrounding text
- **WHEN** the composed character description is generated
- **THEN** its appearance, equipment, and free-text sections are rendered from the `art.character_description` template, and no surrounding text is defined in Python

#### Scenario: A broken library key degrades without reading equipment
- **WHEN** the prompt library cannot resolve `art.character_description`
- **THEN** the fallback description is built from the display name, race label, and age only, with no persona, equipment, or free-text read

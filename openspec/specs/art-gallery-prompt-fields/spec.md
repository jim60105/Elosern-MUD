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
- **WHEN** a monster gallery generation settles successfully
- **THEN** the settled card's `requested_fields` is empty and its description came from the monster registry

#### Scenario: A write claiming field provenance for a kind without selection is refused
- **WHEN** a card carrying a non-empty `requested_fields` is appended for a subject whose kind declaration supports no field selection
- **THEN** a typed error is raised and the record is unchanged

#### Scenario: A kind without selection support declares no selectable field
- **WHEN** a subject kind's capability declaration does not support field selection — the generic
  monster kind, whose description is registry-owned
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

### Requirement: Equipment fields contribute registry-owned visual text and nothing else
An equipment field's contribution SHALL be derived exclusively from the item keys stored in that slot
and the matching `world/lore/items.py::ItemPresentation` visual text of the immutable item registry,
read read-only. `accessories` SHALL contribute its items in lexicographically sorted key order so the
contribution is deterministic.

#### Scenario: Equipped registered items contribute their presentation text
- **WHEN** a request selects `weapon_main` and `armor` for a character wearing registered items in both slots
- **THEN** the composed description contains both items' registry presentation text in the declared slot order

#### Scenario: Accessories are contributed in sorted key order
- **WHEN** a request selects `accessories` for a character wearing several accessories stored in arbitrary order
- **THEN** their contributions appear in lexicographically sorted item-key order

#### Scenario: Unknown keys and malformed storage contribute nothing
- **WHEN** a request selects an equipment field for a slot holding an unregistered item key, or for an entity whose equipment storage is malformed
- **THEN** that field contributes no text, no exception propagates, and no equipment state is written

#### Scenario: An empty slot contributes nothing
- **WHEN** a request selects an equipment field whose slot is empty
- **THEN** the field contributes nothing and nothing raises

#### Scenario: Only presentation text reaches the prompt
- **WHEN** an equipment contribution is composed
- **THEN** no item mechanic, stat, price, rarity weighting, or non-presentation registry field
  reaches the prompt, and no equipment state is written or materialized while composing

### Requirement: Free-form prompt text is bounded, sanitized, and appended verbatim
`custom_prompt` SHALL be validated before any render: it SHALL be text, SHALL be rejected when it
exceeds the declared code-point bound, and SHALL be rejected when it contains any control character
(including line and paragraph separators). Accepted text SHALL be appended verbatim after every
selected field's contribution, through a prompt-library slot.

#### Scenario: Accepted free text is appended verbatim
- **WHEN** a request supplies bounded free text alongside a field selection
- **THEN** the composed description ends with that text verbatim, after the field contributions

#### Scenario: Over-long or control-bearing text is rejected before any render
- **WHEN** a request supplies free text exceeding the bound or containing a control character
- **THEN** a typed error is raised, no prompt is rendered, and no record is created

#### Scenario: Empty free text is a legal no-op
- **WHEN** a request supplies an empty or whitespace-only `custom_prompt`
- **THEN** the request is accepted and the composed description carries no free-text section

#### Scenario: Accepted text is single-lined and never concatenated
- **WHEN** free text is accepted
- **THEN** it is whitespace-normalized to a single line and appended through the prompt-library
  slot, never by string concatenation onto rendered template output

### Requirement: The prompt library remains the sole source of the composed template
The `{equipment}` and `{custom}` sections SHALL be slots of the `art.character_description` template
in `prompts/art.yaml`, declared in the `art.character_description` `PromptSpec`'s
`allowed_placeholders`; `world/art/` SHALL NOT embed their surrounding text as Python constants. The
declared placeholder set SHALL be exactly `race`, `age`, `appearance`, `equipment`, and `custom`.

#### Scenario: The template owns every section's surrounding text
- **WHEN** the composed character description is generated
- **THEN** its appearance, equipment, and free-text sections are rendered from the `art.character_description` template, and no surrounding text is defined in Python

#### Scenario: The declared placeholder set is closed on both sides
- **WHEN** the shipped `art.character_description` template and its declared `allowed_placeholders` are compared
- **THEN** both name exactly `race`, `age`, `appearance`, `equipment`, and `custom`, and neither declares `name` or `style`

#### Scenario: A broken library key degrades without reading equipment
- **WHEN** the prompt library cannot resolve `art.character_description`
- **THEN** the fallback description is built from the race label and the apparent age only, with no persona, equipment, or free-text read, and with no display name

#### Scenario: One-sided edits cannot reintroduce a removed slot
- **WHEN** a template names a placeholder outside the declared set, or a render passes a value the
  set does not declare
- **THEN** both fail at the library boundary, so a removed slot cannot be reintroduced by an edit on
  one side alone

#### Scenario: The fallback stays the existing registry-driven one
- **WHEN** the prompt library cannot resolve the template
- **THEN** the existing registry-driven fallback is used, unchanged in kind from the one that
  existed before this change

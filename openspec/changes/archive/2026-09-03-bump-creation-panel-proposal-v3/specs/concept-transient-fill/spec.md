## MODIFIED Requirements

### Requirement: The creation panel renders the transient proposal
The `creation` panel available payload SHALL additionally accept the optional top-level key
`proposal`, present only when the authenticated session holds a transient proposal. The proposal
object SHALL contain exactly `revision` (a positive integer transient sequence number, strictly
increasing within the session across successive applies), `race` (a registry key), `subrace` (a
registry key or null), `allocations` (one integer per `ALLOCATABLE_AXES` axis — the full seven-axis
set including `magic_power`), and `persona` (an object with exactly `personality`, `life_story`,
and `habit`, each 1..600 non-empty code points), plus five optional transient-fill keys that are
present only when the validated generative proposal carried a value: `display_name` (1..64 code
points), `age` and `apparent_age` (integers in 18..10000), `background` (1..600 code points), and
`affinity_elements` (a list of at most 8 distinct registered element keys). An absent optional key
SHALL NOT be encoded as null, and every value SHALL be deep-copied from the session snapshot with
no live object reference. A worst-case proposal (three 600-code-point persona fields, a maximum
background, a maximum display name, both ages, and an eight-element affinity set) SHALL still fit
the canonical envelope bound.

#### Scenario: A panel renders the pending proposal
- **WHEN** a creation panel is built for a session whose slot holds a proposal
- **THEN** the payload contains the `proposal` key with the exact base shape and the snapshot's
  values

#### Scenario: A proposal carries the transient-fill fields it received
- **WHEN** a validated proposal carried a display name, both ages, a background, and an affinity set
- **THEN** the panel's `proposal` object names all five additional keys with those exact values

#### Scenario: A proposal omits absent transient-fill keys
- **WHEN** a validated proposal carried none of the five optional transient-fill fields
- **THEN** the panel's `proposal` object contains none of the five keys (never null-valued copies)

#### Scenario: A slotless panel omits the key
- **WHEN** a creation panel is built for a session with an empty slot
- **THEN** the payload contains no `proposal` key at all (not a null value)

#### Scenario: A worst-case proposal fits the envelope bound
- **WHEN** a proposal with three maximum-length persona fields, a maximum background, a maximum
  display name, and an eight-element affinity set renders through the panel
- **THEN** the canonical JSON stays within `MAX_CANONICAL_JSON_BYTES` and passes exact-schema
  validation

#### Scenario: Successive identical applies carry increasing revisions
- **WHEN** the same concept is applied twice and both responses are byte-identical in content
- **THEN** the second panel proposal carries a strictly greater `revision` than the first

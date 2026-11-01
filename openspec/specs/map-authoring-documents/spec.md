# map-authoring-documents Specification

## Purpose
Define the complete typed authoring schema, restricted round-trip YAML codec, source discovery and runtime acceptance gates. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Map documents are discovered and schema checked as a complete candidate
Authoring load SHALL discover the documented source set deterministically and reject unsupported document identity, version, fields or typed values with source diagnostics.

#### Scenario: Discovery and identity
- **WHEN** files are added in arbitrary directory order or a filename disagrees with its document identity
- **THEN** supported sources load in sorted order and identity/kind/version errors reject the candidate

#### Scenario: Complete schema
- **WHEN** a nested prototype includes an unknown field or an integer field receives true, a fraction or a numeric string
- **THEN** loading rejects that field without coercion or partial document publication

#### Scenario: Empty passes are a legal document
- **WHEN** a continent retains its ridge pass field with an empty list
- **THEN** parsing succeeds without a structure error or fabricated pass

#### Scenario: Physical stem is authored
- **WHEN** a continent is parsed
- **THEN** its ridge requires a physical stem route with at least two integer nonnegative cell points; missing or malformed routes reject without substituting a periodic physical curve

#### Scenario: Retired periodic fields are rejected
- **WHEN** a ridge document supplies old base, period, step or manually duplicated extent fields
- **THEN** strict schema validation rejects them as unknown rather than preserving a second shape authority

#### Scenario: Paired branch shape
- **WHEN** optional ridge branches are present
- **THEN** exactly west and east routes are required, each with at least two integer nonnegative cell points; missing arms, unknown keys and wrong field types reject as structure errors

### Requirement: Restricted YAML preserves supported authored information
Map YAML SHALL accept only restricted data-only values and preserve retained stable-object comments and supported semantic values through round trips.

#### Scenario: Unsafe constructs
- **WHEN** duplicate keys, custom tags, anchors, aliases, merge keys, timestamps, non-finite numbers or unsupported scalars are parsed
- **THEN** the candidate is rejected before a writable authoring model exists

#### Scenario: Round trip
- **WHEN** multiline text, footprint masks, road bends and comments on a retained ID are edited and serialized
- **THEN** unmodified semantic values and those comments remain, and the emitted document passes the same parser

#### Scenario: Empty pass and branch preservation
- **WHEN** a synthetic continent with no passes, an arbitrary physical stem and paired ridge branches is parsed, edited in an unrelated field, serialized and reparsed
- **THEN** the empty list, stem and both arm routes and supported retained comments survive; no pass or physical curve is dropped or invented

### Requirement: Authoring diagnostics and runtime acceptance have distinct gates
Authoring load SHALL use shared map diagnostics to reject invalid structure and permit semantically unfinished maps, while runtime acceptance rejects blocking map errors and requires authoritative external-reference and artifact-freshness validation without treating advisory midpoint disagreement as an error.

#### Scenario: Saveable unfinished world
- **WHEN** a valid empty graph or inaccessible landmark is loaded
- **THEN** authoring succeeds with a semantic diagnostic and runtime construction is rejected

#### Scenario: Invalid structure
- **WHEN** a road has a missing endpoint or duplicate outgoing direction
- **THEN** structured editing/writing is blocked rather than treating it as game-readiness WIP

#### Scenario: DIAG-ANCHOR missing or ambiguous anchor
- **WHEN** a settlement has no anchor node, multiple anchor_room nodes, an anchor_key unequal to location_ref, or a location_ref already owned by another settlement
- **THEN** the core reports the named source defect and game adoption rejects it; a missing anchor is saveable semantic WIP, while multiple anchors, mismatched keys and duplicate location ownership are structure errors

#### Scenario: DIAG-MASK invalid physical mask
- **WHEN** a mask is disconnected, its midpoint misses its hash cells, a hash cell lies outside the frame or on impassable ground, or its occupied cells intersect another footprint or point entry
- **THEN** the core reports a semantic map diagnostic naming the involved entries and game adoption rejects the same world, including point-cell terrain failures despite point entries owning no wilderness obstacle

#### Scenario: DIAG-GATE invalid approach and point entry
- **WHEN** a gate ray cannot yield an in-frame exterior cell, an approach is blocked or inside another footprint, a point entry has multiple gates, or its authored direction leads to a provider-invalid neighbor
- **THEN** the core reports a semantic map diagnostic and game adoption rejects the same world; unrelated point-entry directions remain ordinary wilderness movement and a zero-gate entry remains a schema structure error

#### Scenario: DIAG-COLLISION unprovisionable gates
- **WHEN** gates share an approach-cell/direction pair or destination room, or another gate approach equals a point entry
- **THEN** the core diagnoses the collision before runtime publication; duplicate destinations are structure errors and spatial approach collisions are semantic map errors

#### Scenario: DIAG-INTERIOR duplicated identity or doorway
- **WHEN** interior room IDs repeat across documents or two interiors declare the same doorway_key on one settlement node
- **THEN** the core reports a structure diagnostic naming both owners and game adoption rejects without changing the previously published world or persistent rooms

#### Scenario: DIAG-AGREEMENT independently invalid candidate matrix
- **WHEN** each remaining former game-only rule is violated separately in an otherwise valid synthetic world and loaded through the core and game candidate path
- **THEN** each core code/category/source identifies that rule, the game rejects through the shared diagnostic, and the static checker reports the same decision without a second rule implementation; removed binding fields fail schema validation

#### Scenario: DIAG-MIDPOINT advisory location disagreement
- **WHEN** mask growth moves its valid hash-cell midpoint away from the location cell while all blocking geometry, external and freshness checks pass
- **THEN** authoring saves and emits a semantic warning, runtime adoption remains permitted, and a blocking terrain/collision diagnostic still rejects independently of that warning

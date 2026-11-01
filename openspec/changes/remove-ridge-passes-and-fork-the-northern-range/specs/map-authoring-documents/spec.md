# Spec Delta

## MODIFIED Requirements

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

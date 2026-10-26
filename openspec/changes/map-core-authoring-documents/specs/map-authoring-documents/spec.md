# Spec Delta

## Purpose

Define the complete typed authoring schema, restricted round-trip YAML codec, source discovery and runtime acceptance gates. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Map documents are discovered and schema checked as a complete candidate
Authoring load SHALL discover the documented source set deterministically and reject unsupported document identity, version, fields or typed values with source diagnostics.

#### Scenario: Discovery and identity
- **WHEN** files are added in arbitrary directory order or a filename disagrees with its document identity
- **THEN** supported sources load in sorted order and identity/kind/version errors reject the candidate

#### Scenario: Complete schema
- **WHEN** a nested prototype includes an unknown field or an integer field receives true, a fraction or a numeric string
- **THEN** loading rejects that field without coercion or partial document publication

### Requirement: Restricted YAML preserves supported authored information
Map YAML SHALL accept only restricted data-only values and preserve retained stable-object comments and supported semantic values through round trips.

#### Scenario: Unsafe constructs
- **WHEN** duplicate keys, custom tags, anchors, aliases, merge keys, timestamps, non-finite numbers or unsupported scalars are parsed
- **THEN** the candidate is rejected before a writable authoring model exists

#### Scenario: Round trip
- **WHEN** multiline text, footprint masks, road bends and comments on a retained ID are edited and serialized
- **THEN** unmodified semantic values and those comments remain, and the emitted document passes the same parser

### Requirement: Authoring diagnostics and runtime acceptance have distinct gates
Authoring load SHALL permit structurally valid unfinished maps while runtime acceptance requires complete map, authoritative external-reference and artifact-freshness validation.

#### Scenario: Saveable unfinished world
- **WHEN** a valid empty graph or inaccessible landmark is loaded
- **THEN** authoring succeeds with a semantic diagnostic and runtime construction is rejected

#### Scenario: Invalid structure
- **WHEN** a road has a missing endpoint or duplicate outgoing direction
- **THEN** structured editing/writing is blocked rather than treating it as game-readiness WIP


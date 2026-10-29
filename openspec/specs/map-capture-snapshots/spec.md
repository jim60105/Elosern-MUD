# map-capture-snapshots Specification

## Purpose
Supply a current, confined authoring snapshot for offline visualization while separating source failures, semantic diagnostics and conditional derived-boundary freshness.

## Requirements

### Requirement: Capture snapshots are confined and read only
The capture loader SHALL read current disk sources once through confined shared loading and projection, returning world data, layouts and diagnostics without service lifecycle, source writes or generation.

#### Scenario: Complete fresh snapshot
- **WHEN** a synthetic workspace with geography, bent settlement roads and partially positioned interior rooms is loaded
- **THEN** one read supplies the complete projection and terrain preview, authored layout positions survive, absent room positions remain available for deterministic renderer fallback, and later source changes do not trigger reloads

#### Scenario: Source ownership remains unchanged
- **WHEN** capture snapshot loading succeeds or fails with game/editor services absent
- **THEN** source YAML, layout files, partition and reference index remain byte-identical, no fallback layout is persisted, and no watcher, command writer, arrange operation or game startup occurs

#### Scenario: Unsafe or unreadable source
- **WHEN** discovery finds an escaping symlink, refused path or unreadable document
- **THEN** loading fails through the existing confinement boundary without exposing outside data or writing workspace files

### Requirement: Capture distinguishes malformed input from semantic work in progress
The capture loader SHALL reject source or layout structure failures while permitting loadable semantic work in progress with diagnostics and without requiring current external-reference context.

#### Scenario: Malformed authored layout
- **WHEN** authored YAML or any discovered layout is malformed, including duplicate keys or invalid coordinate values
- **THEN** capture fails with source diagnostics and never silently substitutes fallback positions for the malformed layout

#### Scenario: Loadable semantic diagnostics
- **WHEN** a structurally loadable world contains unresolved semantic references and its external-reference index is missing or stale
- **THEN** visualization data and diagnostics are returned without claiming game readiness or authorizing edits/deletion

### Requirement: Visible continental partition requires current decoded output
The capture loader SHALL require a decodable fresh partition artifact only for a continent view with partition visible, comparing freshness against the invocation's loaded world.

#### Scenario: Missing malformed or stale partition
- **WHEN** a visible-partition continent request encounters missing, malformed or stale output
- **THEN** it fails with explicit regeneration or --hide partition guidance, preserves the old artifact, and never presents outdated boundaries as current

#### Scenario: Hidden partition or another view
- **WHEN** partition output is missing, malformed or stale and the request hides partition or selects settlement/interior
- **THEN** capture loading succeeds independently of that artifact, terrain preview still derives from the loaded current source, and no partition or reference-index generation runs

#### Scenario: Snapshot scoped freshness
- **WHEN** a partition signature matches the already-loaded synthetic world but source bytes subsequently change
- **THEN** the invocation uses its single snapshot for freshness and outline decoding, without rereading source files or claiming the later source state was captured

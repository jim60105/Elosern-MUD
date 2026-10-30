# Design

## Context

Observed owners and nearby test targets: packages/map-core/elosern_map_core/terrain.py, partition.py, sources.py; new elevation.py and tests/test_elevation.py.

## Goals / Non-Goals

Generate deterministic physical elevation and prominence offline. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Expose generate_elevation(terrain,shapes,config) returning uint8 band/tier arrays indexed [y,x]. Reuse the terrain definition, coastline, ridge and waterways; numpy belongs only to the offline generation extra. All seeds, octaves, wavelengths, amplitudes, ring radii, thresholds and cluster minimum live in one immutable versioned configuration. Runtime imports no generator.

Stages in order: land/coast-distance base plus ridge-proximity mountain rise and river carving; domain-warped multi-octave smoothstep-interpolated value noise; ordered feathered shapes; fixed-config quantization to bands0..15; ring-mean prominence thresholds0..3, suppressing four-connected clusters below configured minimum. Use an avalanche integer hash, e.g. xor shifts16/15/16 with multipliers0x7feb352d/0x846ca68b and explicit uint32 overflow. Do not use coordinate-linear congruential noise. Region amplitudes satisfy hills>open>coast. Feather weight decreases linearly outside the shape interior. no_prominence is a final override mask. Reapply sea=0 and river<=immediate land-bank constraints after shapes/quantization. Canopy and no_prominence always force tier0.

Physical/noise parameters are authored configuration, not duplicated balance assertions. Synthetic small-frame tests inject known configs, fixed seeds and independently known physical relationships. Directional residual-noise autocorrelation test covers x/y and both diagonals, integer lags2..32, evaluating lags at least two base wavelengths and requiring absolute correlation<=0.30. Exclude coastline/ridge trends from that residual test. Human review of visual relief uses the approved detailed design §4, not raster snapshots. No production artifact, codec/startup loader or new geography is part of this slice.

## Dependency contracts

- [wilderness-elevation-shapes](../wilderness-elevation-shapes/design.md) must land first.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

Requirement traceability mapping for this change (task 2.2), using IDs from `uv run --locked python -m tools.spec_traceability list`, never hand-composed:

- ADDED requirement: `wilderness-elevation-generation::elevation-generation-is-deterministic-and-physically-constrained` (the delta spec in this change).
- Pre-sync canonical mount: `wilderness-elevation-authoring::elevation-shapes-reject-invalid-candidates` (nearest current canonical requirement; the ordered shape declarations and their rejection boundary are the shared authored surface). Annotations live in `tests/test_elevation_contract.py`, whose subprocess probes execute the real generator with every game namespace blocked and prove the runtime surface imports without NumPy/SciPy or the generator.
- Mechanism evidence: `packages/map-core/tests/test_elevation.py` covers repeat-byte determinism, sea/ridge/river/shape-order/canopy/no-prominence physics, ring thresholds, minimum-area component suppression and directional residual autocorrelation on synthetic frames.
- Post-sync planned target: `wilderness-elevation-generation::elevation-generation-is-deterministic-and-physically-constrained`; sync remounts the annotation with no uncovered requirement and no waiver.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.

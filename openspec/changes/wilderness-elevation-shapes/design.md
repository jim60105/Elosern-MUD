# Design

## Context

Observed owners and nearby test targets: packages/map-core/elosern_map_core/schema.py (_DOCUMENT_KINDS), documents.py (ContinentDocument), authoring.py; packages/map-core/tests/test_authoring.py and test_yaml_codec.py.

## Goals / Non-Goals

Validate ordered elevation shapes before authored-map publication. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Add optional root continent `elevation_shapes`, absent means empty and remains absent when serialized. Frozen declarations preserve list order. Exact shape union: circle has centre:{cell_x,cell_y} and positive integer radius; polygon has vertices:[{cell_x,cell_y},...] with at least three distinct unclosed vertices, implicit closure. Exact op union: raise/lower has amount integer1..15 and feather positive integer; flatten has target_band integer0..15 and feather positive integer; no_prominence has no amount, target or feather. Optional note is a string. Reject unknown fields, booleans as integers, degenerate/self-intersecting polygons and footprints including feathers outside the frame. Coordinates are north-positive cell indices; coverage samples cell centres.

Extend existing authoring diagnostics before candidate publication. Preserve fields through generic editor parse/save/round-trip; no drawing tools, authored shapes or geography edits. Update docs/development/map-authoring-documents.md and the map-data-authoring skill continent reference during implementation. Tests use synthetic documents and establish parser/geometry/order/preservation behavior, never shipped shape counts.

## Dependency contracts

Independent root slice.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.

# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 2 partition sub-change, split from establish-map-districts to keep deterministic routing, outline generation and recomputation testing within 8h. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Use a deterministic multi-source Dijkstra on 540×540 cells; order equal distances by stable district key, then coordinates. Reserve region-district cells before Voronoi propagation. Sample the existing 1 km terrain for each edge, not only 5 km endpoints, to prevent thin-river/ridge jumps; reject diagonal corner cutting and national-border crossings even at passes/fords. Preserve actual walking reachability through same-nation passes/fords. Resolve grid landmarks to their settlement anchor cell consistently with the approved world-coordinate mapping.

For exact coverage at the coast and 1 km lookup, store a deterministic coarse ownership raster plus boundary refinements/lookup rules tied to mainland land cells; sea must never acquire an owner. Every disconnected legal Voronoi component needs a seed; fail generation with actionable component coordinates rather than crossing barriers or leaving cells unowned. Regions take priority even if they span nations. Trace/smooth outlines deterministically without altering ownership, smoothing across national borders, or creating misleading gaps/overlaps. Store inputs/version fingerprint with frozen RLE data; runtime imports decode/read only.

Expose a focused `uv run --locked python -m tools.map_district_partition` generator (proposed path), and a recomputation test comparing the complete generated artifact, not only counts or a self-derived expected hash. No new service, elevation model, runtime generation or new movement graph.

## Risks / Trade-offs

Raster edge validation costs more offline but preserves one-cell barriers. The initial small registry is valid input; the next authoring slice adds the final content and regenerates using this exact tool.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `tools.spec_traceability list` to obtain canonical IDs, never guess them. Because active deltas are not indexed, obtain new/retired IDs by running `uv run --locked python -m tools.spec_traceability list` against a disposable equivalent spec tree with these deltas merged, using `--repo-root <equivalent-root>` before the `list` or `check` subcommand. Apply literal `covers_requirement` annotations to real discoverable Python assertions (including managed browser assertions for client behavior); do not leave unknown active-delta IDs in the unsynced repository. Run `check` against the equivalent merged tree with those tests before sync, and the normal root `check` after sync. A pre-sync root pass alone does not establish coverage of this change. Existing IDs remain checked at root; CI alone runs full evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run `uv run --locked python -m tools.contract_gate` and `openspec validate <change> --strict`. Update existing development/game documentation for changed behavior; do not add unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.

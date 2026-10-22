# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 5 is split: this 6h measurement/transport slice precedes the 8h world presenter/narrative slice; the combined work exceeds 8h. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Observed `check_envelope` rejects canonical bytes above 65536, and generic nested collection limits also affect trails/225-cell areas. A panel-level exemption alone cannot work. Measure compact UTF-8 serialization from final generated geometry/roster, representative exploration and all-lit plus capped trail/accepted-quest cases before selecting a finite bound. Record sizes, transport frame settings and bound in existing protocol development documentation. No invented universal MB budget.

Preferred route is one registered world_map replacement inside the existing exact ui_update transport shape with map-only envelope/collection allowances and independently unchanged limits for all other sibling panels. Walk/validate the rest of the envelope normally; bypassing generic recursive checks on an entire envelope is forbidden. Maintain existing protocol version and schema parity; this pre-release change has no old-reader shims. Keep world-map payloads out of eager snapshots under the upstream on-demand policy.

Exercise the actual Evennia portal/server socket and production browser decoder/store using measured representative production geometry and synthetic player knowledge; a JSON-only unit test is insufficient. Only if frame-size limits prevent this supported payload, implement bounded indexed parts in the registered map delivery path with complete epoch/revision assembly, finite part count/bytes, duplicate/missing/old-epoch rejection and atomic replacement. No unrelated streaming framework. The implementing worker resolves this evidence-driven branch within this change, records which route was selected and completes it, rather than leaving a TODO or requesting a follow-up.

This slice owns transport only, not a fake world presenter. Its fixtures assemble real static output for transport testing. The next world presenter consumes the measured limits; if final payload assembly exceeds them, complete/adjust the bounded transport in that owning change and retain the actual round-trip proof. Coordinate area-specific collection/bounds support established upstream without broadening unrelated panels.

## Risks / Trade-offs

The final registry is a prerequisite for credible size evidence. Optional multipart complexity is bounded to the map panel and must not alter ordering or expose partial maps. A single scoped exception must not make arbitrary oversized mixed-panel envelopes valid.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `tools.spec_traceability list` to obtain canonical IDs, never guess them. Because active deltas are not indexed, obtain new/retired IDs by running `uv run --locked python -m tools.spec_traceability list` against a disposable equivalent spec tree with these deltas merged, using `--repo-root <equivalent-root>` before the `list` or `check` subcommand. Apply literal `covers_requirement` annotations to real discoverable Python assertions (including managed browser assertions for client behavior); do not leave unknown active-delta IDs in the unsynced repository. Run `check` against the equivalent merged tree with those tests before sync, and the normal root `check` after sync. A pre-sync root pass alone does not establish coverage of this change. Existing IDs remain checked at root; CI alone runs full evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run `uv run --locked python -m tools.contract_gate` and `openspec validate <change> --strict`. Update existing development/game documentation for changed behavior; do not add unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.

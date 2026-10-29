# Tasks

## 1. Pure confined snapshot consumer

- [X] 1.1 Extract the minimal shared source/layout/core projection seam from `snapshot.py` and add `capture_snapshot.py` without EditorService/writer/watcher construction; add adjacent synthetic tests plus discoverable `tests/test_map_capture_snapshot.py` real independent-environment assertions for complete current projection, one source read per discovered document, later-change snapshot isolation and no game imports, and document loader ownership in `docs/development/map-editor.md`.
- [X] 1.2 Enforce capture-only source/layout structure rejection, preserve absent/partial layout positions for existing deterministic fallback, and return semantic diagnostics without reference-index readiness gating; add malformed-YAML/layout, unsafe/unreadable-path, semantic-WIP and missing/stale-index cases asserting real payload/error outcomes, unchanged workspace digests and unchanged interactive-editor snapshot policy, and document the failure distinction.

## 2. Conditional partition admission

- [X] 2.1 Decode/freshness-check partition only for visible-partition continent against the already-loaded core signature and land predicate; add synthetic missing/malformed/stale/fresh cases across visible/hidden continent and both other views, including valid metadata with corrupt body, and assert current terrain preview remains available independently.
- [X] 2.2 Return the agreed `{world,partition,diagnostics}` contract, resolve requested map identity against that snapshot, and provide explicit regenerate-or-hide refusal guidance without generation; verify absent/wrong-domain IDs, exact source/layout/artifact/reference byte preservation after success/failure and no persisted fallback, and update existing developer loading/partition documentation.

## 3. Final integration and evidence

- [X] 3.1 Attach each new requirement to substantive discoverable top-level adapter tests using canonical IDs obtained from an equivalent merged spec tree; record any meaningful provisional nearest-current associations/reasons while active and verify zero uncovered post-sync requirements without inventing IDs or tests that only assert forwarding.
- [X] 3.2 Run `uv run --locked --project tools/map-editor python -m pytest tools/map-editor/tests/test_capture_snapshot.py tools/map-editor/tests/test_snapshot.py tools/map-editor/tests/test_confinement.py` from root, the focused `uv run --locked python -m unittest tests.test_map_capture_snapshot`, `openspec validate map-capture-snapshot --strict` and `uv run --locked python -m tools.contract_gate`; record observed loader/partition/read-only outcomes. Do not run full CI suites or implement browser/command functionality in this slice.

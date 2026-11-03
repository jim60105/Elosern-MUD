# Proposal

## Why

The approved settlement-synthesis batch requires this follow-up once `world.maps.tests.test_bootstrap` more than doubles. Its unchanged 50 tests grew from 147.381 s with two authored settlements to 775 s after Grandia, 1,306 s after Altoria and 1,868 s after Valhalla, with 60 settlements published.

## What Changes

- Add an explicit settlement selector to the existing grid synchronizer and its wilderness gate companion. Omitted selection retains full production convergence. Selection changes the inputs to the existing read-only planning and transactional writing implementation, with no second writer.
- Add test helpers requiring a declaration of map IDs. Keep complete immutable map-world publication and authoritative reference validation intact. Add a narrowly scoped startup-test adapter that invokes the real synchronizers with those declarations and restores its patches on every exit.
- Cut over non-browser settlement consumers to declared selections, including class fixtures and the startup calls in `test_bootstrap`. World-adoption contract cases explicitly declare their full candidate because candidate-wide synchronization is their subject. Browser seeds and production entry points keep their full-world behavior.
- Add synthetic behavior tests for selected work, rollback, omitted selection and isolation. Compare planner/writer call membership as unrelated graphs are added; do not add a timing gate or pin authored data.
- Update the existing development testing guide with the declaration contract and measured diagnosis. No migrations, compatibility shims, dependency changes or authored-map edits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `grid-room-sync`: add an explicit selection mechanism for test synchronization while retaining the existing default full-world contract.

## Impact

Implementation touches `world/maps/bootstrap.py`, `world/tests/geography_fixture.py`, the non-browser callers enumerated in `design.md`, existing test modules for behavioral evidence and `docs/development/evennia-testing-guide.md`. `world/maps/runtime.py::synchronize` and production startup remain selector-free and continue to call the complete synchronizer. New or renamed non-browser test modules, if needed, must be registered in `.github/evennia-shards.json`; reusing existing registered modules is preferred.

The target is about one engineer-day, including the mechanical caller cutover. Scope is bounded to settlement synchronization inputs and fixture declarations; it excludes a new publication cache, test-runner redesign, interior subset selection and timing-based CI enforcement. Existing gates remain mandatory: `tools.contract_gate`, `tools.observability_lint check`, `tools.test_data_lint check` and `tools.spec_traceability check`.

## Evidence and Expected Effect

The historical times above are completed-batch measurements, not reruns. `design.md` records a focused current-checkout diagnostic that separates publication from per-method convergence and records the exact observed cost removable by selecting the settlements the sample tests use. This proposal claims elimination of unrelated graph planning/writing and unrelated gate/art ORM work, not a promised suite duration. Complete publication and reference validation still read the roster; their cost is not hidden or described as constant-time.

## Batch:

This is exactly one follow-up change. The named prerequisites are archived on `master`.

```text
depends-on: unpin-settlement-map-data
depends-on: settlement-rework-and-prose
depends-on: grandia-settlement-maps
depends-on: altoria-settlement-maps
depends-on: valhalla-settlement-maps
```

Code-conflict notes: `unpin-settlement-map-data` overlaps bootstrap and movement test files; the other synthesis changes have no implementation-file conflict because this change does not write `content/maps/`, synthesis tools or `world/maps/data/district_partition.json`. The rest of the active change set was empty when this proposal was created. The dependency/conflict matrix in `design.md` records the remaining archived synthesis changes and the affected current capabilities.

## Requirement Shape

One added mechanism requirement covers explicit selection, rejection and the default full-roster behavior. Its evidence uses synthetic graphs and observed persistent effects or selected planner/writer calls. Runtime targets, human-reviewed prose quality and a wall-clock speed threshold are not new requirements. Existing production requirement names and canonical IDs remain unchanged; new annotations must use tool-derived IDs as described in `tasks.md`.

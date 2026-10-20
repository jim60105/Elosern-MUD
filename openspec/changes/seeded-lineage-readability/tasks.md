# Tasks

## 1. Diagnose and fix the owning graph mechanism

- [x] 1.1 Compare live prerequisites, reverse consumers and component indegrees immediately after synthetic install and browser graft in seed/server startup; separately locate member query versus bounded-presentation refusal and the commander GM failure, then fix the earliest owning inconsistency; verify a focused regression reproduces the corrected graph/index/sort boundary and document the diagnosed cause plus catalog/index lifecycle in the existing fixture guide.
- [x] 1.2 Add independent branching/two-parent merge and install/graft/reinstall regressions with complete cleanup of catalog/index globals; verify roots, nodes once in deterministic topological order, edge thresholds, consistent consumers and unchanged refusal for malformed/cyclic input, without query-time repair or a new cache.

## 2. Prove real lineage consumers

- [x] 2.1 Add a real managed synthetic-member regression through authenticated text and viewed-member lineage panel, plus a separate commander GM lineage assertion; verify matching bounded roots/nodes/edges, available sections and unchanged persistent state after repeated reads, register exact methods/modules in browser/Evennia manifests and annotate the existing lineage requirement.
- [x] 2.2 Run the focused mechanism/command/presentation tests and affected live method, `openspec validate seeded-lineage-readability --strict` and exact ownership/frozen contracts; record the two observed failures' disposition separately and merged-spec traceability evidence without claiming general production impact.

## Workflow follow-up

- Synchronize the full parent requirement without changing intended lineage semantics; run ordinary post-sync contract/traceability gates.
- The dedicated named fixture uses the corrected installation path; original acceptance remains open until its text and assembled UI lineage checks succeed.

## Evidence

- **Observed failure 1 — `系譜 艾拉` returned unavailable.** Diagnosed: the process-scope
  synthetic install cleared and refilled the live skill registry without rebuilding
  `validate_prerequisite_graph`'s reverse-edge cache. `_topological_order` mixed the new
  declared prerequisites with consumers from the shipped cache, so the installed
  `t_ember_burst → t_ember_comet` edge never drained and the read model raised its cycle
  error; the command mapped that to the unavailable line. Fixed at the catalog mutation
  boundaries (install, graft, scoped patch entry/restore). The suppression regression in
  `world.rules.tests.test_lineage_catalog_lifecycle` reproduces the false cycle, and the
  managed `test_browser_synth_lineage` journey now reads the installed graphs through the
  authenticated text command and the viewed-member 系譜 tab.
- **Observed failure 2 — commander `/gm/api/state/characters/1` logged a lineage cycle.**
  Diagnosed as the same owning inconsistency measured through a separate consumer: the GM
  character reader builds the same read model against the same stale index. It is asserted
  independently by `web.gm.tests.test_reader_characters` (lineage section available,
  matching bounded nodes, repeated reads unchanged). The two failures share a mechanism;
  neither observation establishes general production impact, and shipped startup never
  installs the synthetic catalog.
- **Traceability evidence.** `uv run --locked python -m tools.contract_gate` passed:
  2349 requirements, 10145 associations, 2349 covered, 0 uncovered, 0 errors; observability,
  test-data, manifest and contract gates all passed. `openspec validate
  seeded-lineage-readability --strict` reported the change valid. No merged-spec sync is
  claimed in this apply.
- **Post-implementation review disposition.** The blocking finding (the managed journey did
  not prove persistent-state non-mutation) was fixed: the journey now snapshots the private
  runtime database's object and attribute rows for the companion and commander before and
  after repeated text reads, and re-requests the viewed-member panel by selecting another
  rail row and returning. The non-blocking findings were also adopted: failed scoped entry
  and nested scopes now assert registry/index restoration after each unwind.

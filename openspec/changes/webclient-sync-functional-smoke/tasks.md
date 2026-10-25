# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Production-path browser scenarios

- [ ] 1.1 Implement IncrementalSyncBrowserTests.test_graphical_and_text_checkpoint_sequence and test_oversized_snapshot_and_delta_adopt_once with the exact test-only fixture in design. Use real registry/coordinator/socket/browser and canonical action/command paths, count target-revision commits/frames and assert byte bounds, content and result order. Add synthetic seed registration and focused functional documentation together; no production code.
- [ ] 1.2 Implement test_missing_publication_recovers_complete_baseline and test_failed_recovery_and_alignment_preserve_local_state using one bounded transport fault per case. Assert complete canonical repair including deliberately omitted candidate, one automatic sync/no mutation retry, failed-repair lock/text fallback, explicit recovery/new epoch and valid local UI state. Restore interception/listeners and release all buffers between cases. Register four method labels once in browser-shards and traceability.

## 2. Final integrated acceptance

- [ ] 2.1 Run F-BROWSER-1 through F-BROWSER-4 as separate focused commands below, then affected existing map smoke and contract_gate. Capture actual pass/failure evidence; fix owning runtime defects without weakening scenarios before accepting. Document exercised paths/blockers and explicitly state that no performance/latency/no-stutter evidence is claimed. Full browser/evidence suite remains CI-owned.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### F-BROWSER-1

```text
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_incremental_sync.IncrementalSyncBrowserTests.test_graphical_and_text_checkpoint_sequence
```

### F-BROWSER-2

```text
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_incremental_sync.IncrementalSyncBrowserTests.test_oversized_snapshot_and_delta_adopt_once
```

### F-BROWSER-3

```text
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_incremental_sync.IncrementalSyncBrowserTests.test_missing_publication_recovers_complete_baseline
```

### F-BROWSER-4

```text
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_incremental_sync.IncrementalSyncBrowserTests.test_failed_recovery_and_alignment_preserve_local_state
```

### Existing specialized-map regression

```text
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_transport.WorldMapTransportTests.test_representative_world_map_round_trips_intact
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

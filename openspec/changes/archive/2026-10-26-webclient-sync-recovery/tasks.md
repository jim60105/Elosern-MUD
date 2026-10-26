# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Single bounded recovery state

- [x] 1.1 Write new protocol_recovery.test.js and extend app_client_resync.test.js, then implement reducer recovery states/locks with markRecoveryRequested/failRecovery and a single bridge request gate. Cover simultaneous base/schema/assembly failure, one automatic sync, failed repair staying locked across repeated traffic, exact 30-second response deadline, complete-snapshot-only clear and manual explicit attempt. Update recovery state documentation. (Done: the reducer owns `{status, cause, generation, targetRevision}`, `noteRecovery`/`markRecoveryRequested`/`failRecovery`/`resetRecoveryEpisode`; every failure path notifies; `requestPresentationSync(mode)` in the store is the one gate behind `bridge.js`; the 30,000 ms response deadline lives in `web/webclient-app/transport.js`; `docs/development/webclient-synchronization.md` carries the state machine, gate table, deadline and clear rules.)
- [x] 1.2 Update app stores/elosern/transport.js result/release and use-resync.js/transport.js timer lifecycle so newer matching claimed revision starts recovery and pending publication never unlocks. Test older/foreign/busy/duplicate results, disconnect uncertainty, no mutation replay and generation reset; preserve active dialogue completion queue callbacks. (Done: a matching result claiming a newer uncommitted revision is recorded once, cannot release the in-flight action and starts one repair; `publishView` re-reads the reducer state after the transition so a nested publish can never be overwritten; `useResync` derives the episode from the reducer only; `tests/store/action_result_feedback.test.js`, `app_client_resync.test.js` and `transport.test.js` cover the matrix.)

## 2. Server failure and full repair

- [x] 2.1 Adjust ingress/dispatcher safe failure envelopes to avoid claiming synchronized future revisions after preflight/send failure, reusing B invalid-baseline ownership. Extend coordinator/dispatcher tests for failed complete recovery returning safe unavailable without repeated retry or truncation. Project locked/unavailable state through view.js with text fallback still usable; update protocol degradation documentation/traceability. (Done: `PresentationCoordinator.held_revision` is what a result-only safe answer claims; a failed completion publication also emits one `presentation_unavailable` protocol error; an unpublishable complete `ui_sync` snapshot answers `presentation_unavailable` with `reload_required=false` and stops; the view projects `recovery` beside the existing `mutationsLocked` failure surface; `test_incremental_publication.py` covers all three.)

## 3. Focused integrated verification

- [x] 3.1 Run R-NODE, R-VUE and R-PY below after edits plus contract_gate. Deterministic tests must prove no automatic retry after an identical failed recovery and valid complete repair replacing every eager field. (Done: node gate 689/689, the three R-VUE files plus the store/bridge suites green, R-PY green, `tools.contract_gate` green, `openspec validate webclient-sync-recovery --strict` valid, and the live-transport smoke run in `app_client_resync.test.js` covers base mismatch preservation, coalescing, the expired deadline and the full repair. The full vitest suite's only three failures are pre-existing on the primary branch and verified there.)

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### R-NODE

```text
node --test web/static/webclient/js/tests/protocol_recovery.test.js web/static/webclient/js/tests/protocol_transport.test.js
```

### R-VUE

```text
pnpm exec vitest run web/webclient-app/tests/app_client_resync.test.js web/webclient-app/tests/app_client_completion.test.js web/webclient-app/tests/transport.test.js
```

### R-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_incremental_publication web.webclient.actions.tests.test_dispatcher
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

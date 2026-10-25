# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Single bounded recovery state

- [ ] 1.1 Write new protocol_recovery.test.js and extend app_client_resync.test.js, then implement reducer recovery states/locks with markRecoveryRequested/failRecovery and a single bridge request gate. Cover simultaneous base/schema/assembly failure, one automatic sync, failed repair staying locked across repeated traffic, exact 30-second response deadline, complete-snapshot-only clear and manual explicit attempt. Update recovery state documentation.
- [ ] 1.2 Update app stores/elosern/transport.js result/release and use-resync.js/transport.js timer lifecycle so newer matching claimed revision starts recovery and pending publication never unlocks. Test older/foreign/busy/duplicate results, disconnect uncertainty, no mutation replay and generation reset; preserve active dialogue completion queue callbacks.

## 2. Server failure and full repair

- [ ] 2.1 Adjust ingress/dispatcher safe failure envelopes to avoid claiming synchronized future revisions after preflight/send failure, reusing B invalid-baseline ownership. Extend coordinator/dispatcher tests for failed complete recovery returning safe unavailable without repeated retry or truncation. Project locked/unavailable state through view.js with text fallback still usable; update protocol degradation documentation/traceability.

## 3. Focused integrated verification

- [ ] 3.1 Run R-NODE, R-VUE and R-PY below after edits plus contract_gate. Deterministic tests must prove no automatic retry after an identical failed recovery and valid complete repair replacing every eager field.

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

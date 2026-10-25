# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Exact logical schemas

- [ ] 1.1 Write Python test_protocol and Node protocol_core cases for required base_revision/removed_panels, empty metadata-only update, invalid overlap/unknown/map removal and bool integer rejection; then update protocol.py and protocol/envelope.js validators/exports to the shared design. Observable acceptance is identical server/client admission, no fallback defaults.
- [ ] 1.2 Write exact-base staged reducer tests in new protocol_delta.test.js, then update protocol/store.js receive/commit so invalid replacements/removals/metadata or B mismatch preserve all old fields, delta cannot establish epoch and a valid skipped-number target admits from its exact B. Verify staged dialogue coupling and one notification.

## 2. Complete emitter and fixture cutover

- [ ] 2.1 Update coordinator _build_presentation/panel_update/_publish_with_maps to emit exact B/N for every update, including repeated same-B specialized map parts. Migrate actual update fixture producers enumerated in design, including JS helper/direct literals, Vue stories/tests, Python dispatcher/map fixtures and world_map_transport_fixture.py. Tests must supply the actual committed predecessor for nonconsecutive targets; no legacy schema aliases.
- [ ] 2.2 Replace unconditional dialogue wire-presence checks with fresh candidate/staged consistency behavior while preserving all registered schema versions and map retention. Update docs/development/webclient-synchronization.md (new protocol contract) and old OOB foundation supersession notes; register new Python labels only when adding a Python module, and keep requirement decorators on meaningful changed-behavior tests.

## 3. Focused integrated verification

- [ ] 3.1 After all owned edits land, run D-PY, D-NODE and D-VUE below once as focused batches, plus contract_gate. Check existing fixture-driven suites affected by this breaking shape in CI, without running full managed browser locally. Acceptance includes zero remaining production/fixture emitters relying on missing B/N; a source search over ui_update producers is an inventory check, not a compatibility path.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### D-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_protocol web.webclient.presentation.tests.test_coordinator web.webclient.presentation.tests.test_map_panel_protocol
```

### D-NODE

```text
node --test web/static/webclient/js/tests/protocol_core.test.js web/static/webclient/js/tests/protocol_delta.test.js web/static/webclient/js/tests/protocol_transport.test.js web/static/webclient/js/tests/protocol_map_panels.test.js
```

### D-VUE

```text
pnpm exec vitest run web/webclient-app/tests/transport.test.js web/webclient-app/tests/app_client_completion.test.js
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

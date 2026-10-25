# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Invisible bounded assembly

- [ ] 1.1 Write new protocol_publication_parts.test.js with injected clock/timers, then implement publication_parts.js exact ordered append, derived lengths/count, canonical base64 and fixed first-part deadline. Test 683-part limit, byte overflow before allocation, corrupt headers/body, duplicate/skipped index, CJK strict decode and timeout without traffic. Document bounds and teardown.
- [ ] 1.2 Connect general assembler to protocol/store.js receive, final logical validation/staged commit and prune lifecycle; initial multipart snapshot establishes epoch only after complete validation. Test pending returns accepted:false/pending:true, zero notification/revision changes before final part, base recheck and old generation/epoch discard.

## 2. Transport routing and lifecycle

- [ ] 2.1 Add ui_publication_part exports/OOB routing through protocol.js, app lib facade and app transport.js; add Python-encoder-to-Node-reducer fixture in test_publication_parts.py and app transport tests. Prove map parts coexist under separate bounds, newer snapshot supersedes old general transfer, later delta cannot skip incomplete predecessor, and disconnect/detach/reset frees both buffers/timers.
- [ ] 2.2 Register any new Python labels once, attach assembly requirement assertions and update synchronization receiver documentation. Preserve existing scoped world-map/area-map tests and same-epoch complete-map references; partial frames must never clear rejection state or release action completion.

## 3. Focused integrated verification

- [ ] 3.1 Run A-NODE, A-PY and A-VUE below after edits plus contract_gate. No polling-based deadline tests or browser timing benchmark; use deterministic fake scheduler assertions and actual codec fixture bytes.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### A-NODE

```text
node --test web/static/webclient/js/tests/protocol_publication_parts.test.js web/static/webclient/js/tests/protocol_map_panels.test.js web/static/webclient/js/tests/protocol_world_map_transport.test.js
```

### A-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_publication_parts
```

### A-VUE

```text
pnpm exec vitest run web/webclient-app/tests/transport.test.js
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

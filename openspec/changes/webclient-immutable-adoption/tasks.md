# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Ownership and explicit read APIs

- [ ] 1.1 Write protocol_immutable.test.js hostile-input/subscriber and detached snapshot tests, then implement copy-and-freeze-on-adoption, immutable getCommittedState/subscribe and isolated mutable getState. Retain unchanged delta references, immutable old records and same-epoch map references; reuse equal snapshot payloads without serialize/hash equality. Document the two read APIs and immutable-consumer contract.
- [ ] 1.2 Migrate elosern.js/view.js subscription payload flow and every live resolver/consumer read in the design's exact inventory, including hud.js, to getCommittedState. Keep one reducer and remove unconditional all-state clone/serialization on ordinary notify/view/resolver paths. Replace any actual payload mutation at those consumers with a local owned copy; leave local form/model/reading queues mutable. Extend immutable_presentation.test.js and frame resolver tests with frozen inputs.

## 2. Preserve UI semantic lifecycle

- [ ] 2.1 Add component assertions for same-mode checkpoint keeping valid menu/focus/unsaved text/playback progress, and actual mode/identity/availability change retaining existing teardown. Regress maps, creation drafts, beat/delivery identity and snapshot isolation; update frozen-contract audit/API documentation and traceability without weakening frozen behavior claims.

## 3. Focused integrated verification

- [ ] 3.1 Run I-NODE and I-VUE below after edits plus contract_gate. Acceptance uses reference equality/mutation resistance and functional component behavior only, with no profiling or measurement gate.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### I-NODE

```text
node --test web/static/webclient/js/tests/protocol_immutable.test.js web/static/webclient/js/tests/protocol_transport.test.js
```

### I-VUE

```text
pnpm exec vitest run web/webclient-app/tests/immutable_presentation.test.js web/webclient-app/tests/frame-resolvers.test.js web/webclient-app/tests/mode_transitions.test.js web/webclient-app/tests/dialogue_view_model.test.js
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

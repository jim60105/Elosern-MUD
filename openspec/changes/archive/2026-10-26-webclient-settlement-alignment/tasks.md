# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Authoritative completion hooks

- [x] 1.1 Write test_settlement_alignment graphical/text terminal cases, then emit combat_terminal from settle_session after final committed terminal writes and safe actual session-retirement cleanup. Exercise terminal opening, field-cast opening, successful exit, defeat/victory/exam and deduplicated replay. Keep start/nonterminal round incremental and terminal action-local round data intact. Update checkpoint docs.
- [x] 1.2 Write explicit rest/wait/sleep receipt cases, then emit skip_completed from successful advance_wait and completed nonreplayed sleep owners after final receipt/decision writes. Cover all exact caller routes listed in design including retained owner continuation/dream departure, zero-time entry/no receipt, partial retained, completed terminal, rollback and operation replay. Do not hook general WorldClock.advance or _record and do not classify action IDs.

## 2. Integration and ownership

- [x] 2.1 Enroll combat_result/action normalization and sleep/dream refreshes in P causal groups plus M facts without empty-scope forced snapshots; set private publication_group_id and attach terminal round context before drain. Assert nested movement/combat/skip reasons produce one final fresh snapshot for each watcher in both callback orders, its result names the actual receipt target and text/async no-ingress paths agree. Register test_settlement_alignment.py once, retain existing test_art_panel terminal no-partial assertions, and update traceability/checkpoint documentation.

## 3. Focused integrated verification

- [x] 3.1 Run S-PY below after edits plus contract_gate. Preserve existing guild exam, skip safety, compensation, sleep and dialogue availability ownership; no persistent synchronization attributes or new player command syntax.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### S-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_settlement_alignment web.webclient.presentation.tests.test_art_panel
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

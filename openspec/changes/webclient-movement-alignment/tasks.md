# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Authoritative identities and committed facts

- [x] 1.1 Write test_movement_alignment identity cases before extracting read-only room_component and adding world/maps/area_identity.py. Verify grid map-key change, identical labels, same-map pooled wilderness, interior connected component, instance root/scene identity replacement and unknown identity conservative alignment. Preserve area_map existing graph output and never invoke map presenters for identity.
- [x] 1.2 Reuse P's complete frozen alignment fact/emit API and add movement_settlement grouped commit-only emission with source captured before traversal and destination after compensation; register ingress watcher callback idempotently. Test rollback/refusal no fact, lawful current watcher fan-out, independent session baselines and late epoch callback drop. Document deterministic-owner to read-only observer boundary.

## 2. Serialized settlement integration

- [x] 2.1 Enroll deterministic movement/direct-player hooks in P causal groups and attach _move_adapter's private publication_group_id before queue drain; preserve P independent text completion and always-Deferred receipt APIs. Test real UI/text boundary moves yielding one fresh final eager snapshot/result for every watcher in either push/fact callback order, no intermediate dialogue cleanup delta, unchanged same-area moves incremental, deliberate omitted candidate repaired and no unopened map load. Register test_movement_alignment.py once and update movement checkpoint docs. Do not reimplement P queue/callback infrastructure.

## 3. Focused integrated verification

- [x] 3.1 Run M-PY and existing map protocol regression below after all edits plus contract_gate. Preserve original text Deferred value/Failure and Telnet exclusion. Tests must demonstrate source identity captured before pooled room mutation, not a post-move heuristic.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### M-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_movement_alignment web.webclient.presentation.tests.test_map_panel_protocol
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

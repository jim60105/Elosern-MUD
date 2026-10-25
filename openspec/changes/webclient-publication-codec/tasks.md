# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Exact codec and bounds

- [ ] 1.1 Write new test_publication_parts byte/header cases, then add production publication_parts.py encoder/part validator and mirrored constants to the exact wire table. Cover maximum/final remainder, canonical padding, extra fields, bool indices, CJK split and logical/header parity. Add protocol message registration/exports. Document exact wire/constant table.
- [ ] 1.2 Split logical validation from single-frame byte checks without relaxing root structural or panel-local limits. Test invalid oversized panel vs valid logical aggregate, existing scoped dialogue intact allowance, single near-cap panel whose envelope cannot fit, 16MiB maximum and overflow before sends. Pure byte-split helper may test synthetic larger schema; production acceptance fixture must stay within registered schema.

## 2. Actual sender integration

- [ ] 2.1 Wire encoder into coordinator eager snapshot/delta plans and eager companions of specialized map plans; prevalidate all frames and result before any send, preserve B receipt/baseline failure semantics and no ACK. Test real session.msg command order, intact small vs ui_publication_part large publication and specialized map path remaining distinct. Register test_publication_parts.py in one shard, add traceability and update synchronization delivery docs.

## 3. Focused integrated verification

- [ ] 3.1 Run C-PY and C-NODE constants/parity regressions below once after edits plus contract_gate. A supplies the real browser assembly next; do not install a legacy receiver, fake decoder or deployment compatibility flag in this sender slice.

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### C-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_publication_parts web.webclient.presentation.tests.test_map_panel_protocol
```

### C-NODE

```text
node --test web/static/webclient/js/tests/protocol_core.test.js web/static/webclient/js/tests/protocol_dialogue.test.js
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.

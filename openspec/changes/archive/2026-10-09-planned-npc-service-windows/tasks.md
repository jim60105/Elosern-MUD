## 1. Predecessor and Contract Context

- [x] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [x] 2.1 Implement bounded projection using the predecessor parsed data/occurrence seam and shared service-state vocabulary. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.2 Define frozen interval and named reason outcomes for missing/malformed/held/silenced/unresolved data. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.3 Test snapshot equality and reader/settlement agreement at boundaries, skipped arrivals and busy windows. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.

## 3. Traceability, Documentation and Handoff

- [x] 3.1 Update affected owning game/development authoring documentation and synchronize this delta via the repository OpenSpec workflow during authorized archive; obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable behavior tests. Verify every delta requirement/scenario has matching assertions and no obsolete caller/contract remains.
- [x] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [x] 3.3 Update the approved parent design references where this slice supersedes earlier mechanics, preserving numeric/evidence qualifications; verify implemented documentation matches authored/runtime shapes.
- [x] 3.4 Run one final focused verification batch: Focused new synthetic Evennia reader module, fixed absolute ticks, real room/Exit settlement comparisons and complete before/after attribute/location/clock snapshots; no private-route output. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate planned-npc-service-windows --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.

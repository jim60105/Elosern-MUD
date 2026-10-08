## 1. Predecessor and Contract Context

- [ ] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [ ] 2.1 Amend validated template/custom/parsed shapes and optional cycle contract while preserving daily inputs. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [ ] 2.2 Factor cycle-based due occurrence arithmetic and use it in the existing settlement source. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [ ] 2.3 Add differential bulk-versus-consecutive boundary tests across week/day/season/year and assignment/reload boundaries. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.

## 3. Traceability, Documentation and Handoff

- [ ] 3.1 Update affected owning game/development authoring documentation and synchronize this delta via the repository OpenSpec workflow during authorized archive; obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable behavior tests. Verify every delta requirement/scenario has matching assertions and no obsolete caller/contract remains.
- [ ] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [ ] 3.3 Update the approved parent design references where this slice supersedes earlier mechanics, preserving numeric/evidence qualifications; verify implemented documentation matches authored/runtime shapes.
- [ ] 3.4 Run one final focused verification batch: Focused existing schedule model/runtime modules with synthetic cycles 1 and 7, offsets 0/end-1/end, same-tick ordering, multi-cycle jumps, failed Exit and companion-silencing cases. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate weekly-npc-schedule-cycles --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.

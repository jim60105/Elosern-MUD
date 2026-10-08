## 1. Predecessor and Contract Context

- [ ] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [ ] 2.1 Register budget-valid limiting accessories, non-tradeability enforcement and validated profile/allowlist data. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [ ] 2.2 Implement persisted restriction policy and reducing-only neutral baseline/accessors with shared activation/removal ownership. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [ ] 2.3 Wire all direct action, availability, passive, gauge, initiative, gear/hit/modifier and view consumers to the policy. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [ ] 2.4 Prove sealed pre-cost rejection, negative debuff ordering, higher-host lowering, weak-host rejection and S-domain retention with resolver-backed real accessory tests. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.

## 3. Traceability, Documentation and Handoff

- [ ] 3.1 Update affected owning game/development authoring documentation and synchronize this delta via the repository OpenSpec workflow during authorized archive; obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable behavior tests. Verify every delta requirement/scenario has matching assertions and no obsolete caller/contract remains.
- [ ] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [ ] 3.3 Update the approved parent design references where this slice supersedes earlier mechanics, preserving numeric/evidence qualifications; verify implemented documentation matches authored/runtime shapes.
- [ ] 3.4 Run one final focused verification batch: Focused synthetic restriction module plus affected action/traits/initiative/equipment consumers. Wear real accessory and pair, never project equipment adjustments; compare complete base/ownership/proficiency snapshots before/after. Test slot overflow and forbidden sale/transfer/loot paths. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate guild-exam-restriction-policy --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.

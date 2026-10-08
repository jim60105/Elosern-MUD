## 1. Predecessor and Contract Context

- [x] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [x] 2.1 Author all twelve item identities/presentation and budget-valid modifiers; validate keys, slots and rarity without changing budgets. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.2 Add magic_armor band and exact buy prices, resale rules, finite stock and shared assortment membership. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.3 Exercise actual equipment on synthetic player/NPC and transactional buy/sell/restock including insufficient stock and rollback. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.

## 3. Traceability, Documentation and Handoff

- [x] 3.1 Update affected owning game/development authoring documentation; obtain existing canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable tests of current requirements. Verify every delta requirement/scenario has matching assertions and no obsolete caller/contract remains. Delta synchronization and new canonical-ID annotation belong to the later authorized archive owner, outside this implementation assignment.
- [x] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [x] 3.3 Update the approved parent design references where this slice supersedes earlier mechanics, preserving numeric/evidence qualifications; verify implemented documentation matches authored/runtime shapes.
- [x] 3.4 Run one final focused verification batch: Focused equipment-effect, shop-economy and assortment tests; one real-item equip/purchase/restock smoke with identical player/NPC effects. Separate tagged authored-data price/bonus checks from synthetic mechanics. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate shared-military-equipment --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.

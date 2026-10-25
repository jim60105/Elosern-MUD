# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Owner progression hook group

Shared contract v2 includes package-role/phase-aware discovery and current-phase-only publication. Test phase/binding/cancellation retirement with saved reading retained; generated-packages exercises the actual production path.

- [x] 1.1 Wire guild registration/rank, all quest transition/claim and affinity hooks per matrix using existing helper, with world/rules/tests/test_dialogue_refresh_lifecycle.py. Verify each source independently and rollback/no-session controls; document canonical callback owners.

## 2. Membership and presence hook group

- [x] 2.1 Wire _write_binding, NPC move/delete and captured prior-owner discovery. Test unrelated-host conversation on companion leave/return, membership reason expiry and deletion, including rollback. Keep existing stale-host clear seams intact.

## 3. Clock phase and control hook group

- [x] 3.1 Wire WorldClock.advance and existing phase/control retirement callbacks, test global valid-session owner discovery, changed body and obsolete receipts. Verify model services remain offline and current ordinary variant does not switch.

## 4. Cross-source integration acceptance

- [x] 4.1 Exercise a single committed operation changing quest/item/affinity and show one final-state opening batch once notice support is attached; before notices verify final availability only. Update callback source docs and shard ownership, then run focused tests and contract_gate. No new event bus.


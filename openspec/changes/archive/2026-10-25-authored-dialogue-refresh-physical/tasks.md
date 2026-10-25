# Tasks

All units follow Shared contract v2 source-neutral context discovery, including package-role hosts. Add synthetic generated scene cases proving the same hooks refresh eligibility without editing immutable packages/current wording or requiring static membership.

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Narrow callback and owner discovery

- [x] 1.1 Implement queue_dialogue_refresh/affected_dialogue_owners using explicit owner capture and on_commit, with synthetic owner/companion/prior-owner tests and module documentation. Verify no unrelated account character is included and no context is created.

## 2. Inventory and exposure hooks

- [x] 2.1 Wire apply_inventory_plan, toggle_equipment and apply_event per matrix, adding world/rules/tests/test_dialogue_refresh_physical.py cases for Telnet/other-connection/no-session success and late outer rollback; keep active delivery unchanged.

## 3. Identity and skill hooks

- [x] 3.1 Wire set_social_identities, award_practice_xp, apply_lineage_auto_seed and the live cross-lineage ownership write, testing ownership versus proficiency flips and persona-prose negative control. Document canonical source matrix and register new tests; run focused tests and contract_gate.


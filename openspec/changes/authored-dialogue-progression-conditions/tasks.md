# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Guild and affinity leaves

Shared contract v2 covers authorized package quest definitions through the same owner record/claim readers. Test foreign reference rejection without requiring static quest registry membership.

- [ ] 1.1 Implement canonical registration/rank and host-to-owner stage readers/hints; add world/rules/tests/test_dialogue_progression_conditions.py with owner/actor inverse controls and private-number omission. Document existing registry ownership and no independent ordering.

## 2. Quest lifecycle predicates

- [ ] 2.1 Implement definition-key matching over read_records and parse_reward_claims with explicit six-state semantics; add deterministic absence/in-progress/completed/claim/failed/invalidated/repeatable/corruption cases and no-write assertions.

## 3. Complete condition selection acceptance

- [ ] 3.1 Test mixed physical/progression All/Any scenes through real selection offline, with a stale state change refusing without effects. Update condition author documentation, manifests and traceability; run focused condition tests and contract_gate.


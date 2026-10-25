# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. One disclosure projection

- [ ] 1.1 Implement hidden/locked/open project_topics for panel, affordance, text and action consumers, with stable hints and no formal-body leakage. Add world/rules/tests/test_dialogue_availability.py and presentation tests for hidden, locked refusal and recursive sentinel absence.

## 2. Selection recheck and source refresh

- [ ] 2.1 Wire deterministic refresh into existing general action/text settlement and shared clock/NPC/party/control commit seams; add a source-family integration table testing every required cause and rollback nonpublication. Document exact hook ownership in dialogue_availability.py; do not create a general event bus.

## 3. Stale invalidation and native paths

- [ ] 3.1 Keep native generated phase authority and freeform unaffected; test selection losing equipment/quest eligibility, fixed live variant and phase/move/combat/host cleanup. Update dialogue command documentation for server-qualified topic/refusal semantics, manifests and traceability; run focused availability/action tests and contract_gate.


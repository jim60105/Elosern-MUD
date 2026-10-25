# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. One disclosure projection

- [ ] 1.1 Implement hidden/locked/open project_topics for panel, affordance, text and action consumers, with stable hints and no formal-body leakage. Add world/rules/tests/test_dialogue_availability.py and presentation tests for hidden, locked refusal and recursive sentinel absence.

## 2. Selection recheck and explicit refresh API

- [ ] 2.1 Implement the complete explicit refresh_dialogue_availability API and test current-state projection/fan-out, fixed delivered wording and rollback-safe invocation. Test stale selection after changing equipment/quest context directly through synthetic canonical fixtures. Production source hooks are wholly owned by the two named refresh changes, not deferred generic investigation here. Document that command presentation observers are insufficient.

## 3. Stale invalidation and native paths

- [ ] 3.1 Keep native generated phase authority and freeform unaffected; test selection losing equipment/quest eligibility, fixed live variant and phase/move/combat/host cleanup. Update dialogue command documentation for server-qualified topic/refusal semantics, manifests and traceability; run focused availability/action tests and contract_gate.


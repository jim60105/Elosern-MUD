# Spec Delta

## REMOVED Requirements

### Requirement: The implementation-bound public contract is frozen before the shell is swapped
**Reason**: The Phase-0 audit is a historical snapshot of the Vue migration. Committed Docsify pages describe current state only, so a durable audit deliverable is no longer part of the contract; the current façade surface, keyboard path, browser identifiers and layout-persistence keys are asserted directly by the managed browser suite.

**Migration**: Use `git log` and the archived change `2026-08-20-webclient-vue-00-audit-and-design-docs` for the frozen list. Delete `docs/development/webclient-vue-frozen-contract-audit.md`, `tests/test_webclient_frozen_contract.py` and the audit wording in `web/webclient-app/bridge.js` and `tools/contract_gate.py`.

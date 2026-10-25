# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Canonical tag model and read/write API

Shared contract v2 uses this reader for both sources. Test empty/typed identity without profile membership and prove generated persona prose grants no tags; no model-owned writer.

- [x] 1.1 Implement registry and pure reader/sole writer with <=8 registered keys and fail-closed corrupt-state behavior; add world/rules/tests/test_social_identity.py and module docs, verifying persona/title/race never grant identity.

## 2. Import and profile producers

- [x] 2.1 Add optional typed field to schema/semantic validation/loader and NpcProfile/profile application; seed only explicit producer mappings specified in design, with synthetic import/reload/invalid-batch tests. Update existing import author documentation and retain ages/card constraints.

## 3. Player and guild construction integration

- [x] 3.1 Thread explicit preset tags and empty custom baseline through character creation snapshots, and adventurer union through existing successful guild registration atomic. Add rollback tests, register tests and update traceability/manifests. Verify focused import/creation/social tests and contract_gate.


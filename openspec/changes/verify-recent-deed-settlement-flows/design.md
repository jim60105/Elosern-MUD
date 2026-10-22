# Design

## Context

The current `TitleNominationSmokeTests` creates narrative rows directly, then reads the same character's ballot. Its rollback phase inserts only an event. The late-result test releases only one candidate, so schema invalidation can prevent it from exercising the arrival-time writer guard.

## Goals / Non-Goals

**Goals:** Demonstrate the existing contract through real owners and persistence rather than mocks of the boundaries under review.

**Non-Goals:** No production feature, live LLM/network service, full browser suite, broad suite restructuring, source-text assertions, wiring-only tests, test transport as semantic proof, or new game balance.

## Decisions

1. Replace the seed-only end-to-end smoke claim with a small synthetic integration fixture using normal Evennia entity construction and isolated synthetic registries. Drive an actual non-title-bearing ACQUIRE purchase/delivery completion and an actual adult resolver settlement. Drive repeated same-skill combat actions in a real session and settle its terminal outcome. A uses its narrow outcome regressions; H proves the full composition, not a duplicate matrix of every mechanic.
2. Let the real trigger/selection/prompt/guardrail/rules writer run. The fake client replaces only external transport and returns exactly five bounded candidates with citations obtained from the captured rendered source set. Never insert the expected deed or patch settlement, selection, prompt construction or ballot persistence. The fixture's known action/recipient/result assertions establish meaning; citation membership alone does not validate model prose.
3. Establish real commit and reload boundaries using the existing `TransactionTestCase` precedent in `EquipmentGrowthCommittedReloadTests` and `DurableRoundAdmissionTests`. This narrow committed-state probe is the documented exception to ordinary `EvenniaTest` integration fixtures. Force-evict both `ObjectDB` and `Attribute` idmapper caches, then fetch a fresh typeclass instance after the outer commit; ordinary transaction-wrapped tests plus callback capture alone do not prove committed reload. Retain existing fixture isolation/cleanup and test database ownership. No persistent development data is modified.
4. Inject failure after real effect, title award and immutable evidence writes but before the owning outer commit, including the purchase/quest nested-writer case. Assert gameplay gauges/inventory/wallet, title collection/equipped state, awards, events and projection work restore durably and in the warmed cache. Source replay tests replay settlement evidence/notifications, never call the gameplay resolver again to demand a new idempotency contract.
5. Test concurrency with an actually pending fake transport and a valid five-candidate result. A pre-existing ballot or decline cooldown must be what refuses the late result, not invalid count/citation shape. Cover cancellation and persistence/query failures releasing admission, privacy controls, disabled/empty material, acceptance/decline and transcript provenance without broadening the test matrix.

## Risks / Trade-offs

- Integration smoke can become slow -> split self-contained methods with deterministic fixed inputs, share safe construction only, and use the smallest affected labels; no local batch over ten minutes.
- Registry and clock leakage can make CI flaky -> use existing synthetic-data isolation and explicit cleanup; no live authored keys or transport.
- Component tests may be mislabeled end-to-end -> retain them only under their actual behavior claim or replace tautological/wiring assertions; keep traceability annotations substantive.

## Migration Plan

Integrate all prior corrective changes. Replace misleading smoke claims in existing test modules where possible; register added/moved modules in exactly one Evennia shard. No production data migration or compatibility layer. Update testing/feature documentation and spec traceability during implementation.

## Verification and size

Budget: real quest/adult composition 2 h; combat/reload boundary 2 h; rollback/valid late-result controls 2 h; documentation/traceability/focused smoke and gates 2 h. CI retains full browser and complete evidence verification ownership. Focused implementation tests and offline smoke use the normal uv-managed test guard and isolated test settings.

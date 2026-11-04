# Tasks

Future implementation only; begin after global-monster-activity. Use design.md exact interval/cursor contracts. No proactive contact or forecast work belongs here.

## 1. Paid-prefix accounting and threshold semantics

- [x] 1.1 Add strict settled_rounds to combat_session/records.py storage, all builders/fixtures and round/terminal accounting. Factor unpaid actual posture intervals so clock/gauges/mental settlement pay the same suffix once; invoke preceding settle_monster_combat_through for mapped participants. Add explicit allow_hostile_round_wake to canonical interval context, retaining existing threshold/receipt observers. Register world.rules.tests.test_hostile_incapacitated_rounds exactly once in evennia-shards and document cursor semantics. Check: six-second prefix reaches71928→72000 for an undefeated forced sleeper, later terminal billing excludes that prefix, and failure after reserve/cursor writes restores DB/live state.

## 2. Real continuation at authoritative writer hooks

- [x] 2.1 Implement continue_incapacitated_hostile_rounds in rounds.py using existing run_round/empty allied provider/finalization and the design’s writer-local recursion guard. Replace hostile forced-opening zero-defeat and connect the normally confirmed ordinary-round completion hook after _continue_or_settle; keep exam-only FAIL helper and requested-retreat no-acting-ally policy. Extend actual engagement/round/exam consumer tests and developer docs. Check: a real normal confirmed round disables its last actionable ally and automatically executes ordinary enemy actions/upkeep until choice/terminal/cap; awake companion stops continuation immediately, and preview/reconnect reads run no rounds.

## 3. Atomic publication and complete contract amendments

- [x] 3.1 Extend existing round/admission snapshots, outer publication and operation receipts to include paid-prefix state, monster cursors and all clock-source surfaces. Add committed combat_incapacitated_continued catalog event via named observability imports; update both command documents. Migrate substantive tests for all five delta capabilities and remove the retired sleep-caused hostile defeat annotation using generated IDs. Check: actual enemy effects/time/resources survive committed reload once, injected late failure restores the whole operation, and ordinary interactive/exam/voluntary sleep gates retain their specified behavior.

## 4. Change handoff checks

- [x] 4.1 Run design.md’s focused named methods/classes after the change lands, observability lint with logging tests, command-doc contract, strict validation and contract_gate. Use tools.spec_traceability list on the equivalent merged tree for annotation IDs and record scenario assertions and actual evidence in the developer document. Check: commands exit zero, the new module has one shard owner and no unexecuted browser/CI evidence is claimed.

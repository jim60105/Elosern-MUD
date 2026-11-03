# Tasks

All work is future implementation. Complete regional-population-owner, combat-individual-identity and manual-monster-compositions first. Use the exact transition, timeline, projection, protection and coordinator contracts in design.md. No field movement, aggression or content expansion.

## 1. Persist transition and session occurrence evidence

- [ ] 1.1 Implement PopulationPresence/PopulationTransition serialization, the population_timeline Attribute, the at_tick count projection and required started_tick/population_cell session fields; migrate all candidate, strict-storage and pure fixtures in regional_population and combat_session records/builders. Add synthetic tests in world/maps/tests/test_regional_population_recovery.py and session persistence tests. Document exact shapes and rejection/retirement rules. Check: a deleted home-owned member outside its zone still counts before its loss tick, same-label IDs stay separate, and malformed/missing state refuses rather than inferring an old save.
- [ ] 1.2 Integrate actual combat/upkeep transition capture in round finalization and copy closed coordinate protection before terminal or lawful GM session clearing. Include timeline surfaces in existing round/clock compensation. Test start100/round3 death118/delay10, nonterminal restart, deletion before catch-up and a late failure. Check: no due before128, no birth during the closed protected interval, and reload/live caches retain or restore the exact evidence without a second revision execution.

## 2. Coordinate chronological site and regional recovery

- [ ] 2.1 Implement population_lifecycle.py with the exact merged-boundary APIs and refactor monster_sites to next_site_boundary/settle_monster_sites_at. Keep all site writes under the site owner, preserve one-shot/pure binding semantics and combine snapshot contracts. Document ordering. Test a regional due110 and colocated site recovery140 under one interval and [100,125],[125,160]. Check: identical legal birth plans and due/sequence state; the later site never consumes earlier headroom and same-tick site births precede ordinary births. Do not enable the production coordinator before final cutover.
- [ ] 2.2 Implement chronological deficit transitions and delayed episodes, complete fitting waves, cancellation, positive blocked retries and pure boundary projection. Add the L3/local2/due110/future-loss118 case and its earlier manual-restoration counterpart, both requiring a new due128 after the old episode ends. Test multiple waves, manual excess, home ceiling, active/historical session protection, later-stage failure after real registrations and same-plan retry. Check: no loss/visit/view/quest-triggered immediate birth, no pending-delay reset, cancellation changes no sequence and both partitions agree.

## 3. Integrate existing mapped mutation owners

- [ ] 3.1 Add transactional transition notifications to the exact caller table in design.md: maps GM spawn/delete, rules GM HP setters, existing settle_relocation, quest materializer/scene placement, mapped action/upkeep commits and site lifecycle. Capture complete before facts before deletion, retain foreign/home ownership and reuse actual map registration. Extend world/maps/tests/test_gm.py, world/rules/tests/test_movement_settlement.py, world/quests/tests/test_permanent_occupants.py and recovery tests; document normal versus explicit raw-repair boundaries. Check: GM/quest spawn is visible and counted after recycle/reload, deletion/local departure schedules delay without freeing away-home ownership, HP restoration cancels recovery, and post-write faults restore DB plus caches.

## 4. Focused evidence and handoff

- [ ] 4.1 Register any new test modules once in evennia-shards; run focused methods/classes independently using design.md's guarded command form, observability lint for changed logging, strict OpenSpec validation and contract_gate. Check: commands exit zero, actual evidence and scenario/requirement assertion roles are recorded, no retired annotation or extra source stage remains, and no broad/full browser suite is run locally.

# Tasks

Future implementation only. Begin after proposal.md Batch prerequisites land. Use design.md signatures and data shapes verbatim. Each step lands its own tests/docs; named checks run under design.md focused-command policy at the completed change boundary. Do not change the excluded content/ecology/AI scope.

## 1. Durable group and journey owner

- [x] 1.1 Implement strict monster_activity.py group/journey/receipt codecs, owner initialization and constructor integrations exactly as design.md, using stable population seed and actual member IDs. Modify bootstrap fresh initialization, regional_population.commit_population_wave, monster_sites._populate, guild_exams.start_guild_exam stationary-opponent registration/owned cleanup and GM/quest explicit placement input boundaries. Do not enable ordinary roaming. Add new test_monster_journeys and its shard entry; document refusal of unsupported existing saves. Extend PopulationPlacement/planner/fresh-plan equality with retained composition_key and activity_key as design.md requires; test identical member rows with different activity bindings. Check: the saved selected binding survives commit/replay, fresh complete compositions acquire one stable group, living site absentees stay owned, missing/malformed existing owner state refuses without reset, and no foreign identity/resource is replaced.

## 2. Pure world escape context and planning

- [x] 2.1 Implement WorldEscapeContext/AbstractEscapeContext and plan_individual_escape in world/rules/world_escape.py with the shared combat-posture projector factored from combat_session/settlement.py. Migrate combat_session/battlefield.py::_context_for and all real/standalone/manual-campaign flee-capable context builders to explicit authority. Reuse movement_edges quotes and existing agility eligibility; no new combat pipeline step or rulebook constants. Add test_world_escape and its shard entry plus disengage integration controls. Check: post-action reserve prices the real neighbor, no-route fails even without pursuer, out-of-range refuge is allowed, and missing mapped context/partial physiology gives named rejection.

## 3. Commit actual resolver departure

- [x] 3.1 Extend disengage._handle_disengage PendingEffect surfaces and actual action/round journals to atomically apply fled identity, map-owner detachment, coordinate removal, journey and PopulationTransition at action round offset. Update battlefield reconstruction to allow only fled departed roster entities, keeping nonfled presence strict. Extend session persistence/disengage tests with real A+A+B and faults after each actual map/effect/session write; document journal interfaces. Implement member_time cursors and rules project/settle_monster_combat_through handoff at admission, completed rounds, escape and terminal settlement; exclude combat-owned time from ordinary activity. Check: two deferred rounds pay12 seconds before departure, then travel/idle only once across catch-up/arrival/reload; only chosen A departs, remaining enemies continue, same-label B resources stay independent, and fault/replay restores or applies all surfaces once.

## 4. Settle global passage and actual presence

- [x] 4.1 Integrate next/settle/snapshot activity boundaries into existing population_lifecycle source, including newly due arrivals, wilderness PopulationProtection and the specified persistent-room protection/positive retry; pay only elapsed passage through canonical physiology without calling clock.advance from NPC action. Update actual-view, GM journey inspection, exact quest entity destination and stale text/browser consumers; update both command docs and observability catalog. Extend journey/view/quest tests. Check: neither endpoint targets transit, inactive arrival creates no room, protected arrival waits without repricing, partition/restart preserve resources/IDs, actual arrival can be followed and voluntarily engaged, and late clock failure restores DB/live caches.

## 5. Change handoff checks

- [x] 5.1 Run the focused named methods/classes from this change, observability lint with changed-logging tests, applicable command-doc contract, strict OpenSpec validation and contract_gate using design.md commands. Generate requirement IDs with the traceability list tool against the equivalent merged tree and record substantive scenario/assertion mappings in the developer document, removing retired claims. Check: required commands exit zero, every new module has exactly one shard owner, all stated behavior has exercised evidence and no unrun full-browser/CI evidence is reported.

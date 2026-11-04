# Tasks

Future implementation only. Begin after proposal.md Batch prerequisites land. Use design.md signatures and data shapes verbatim. Each step lands its own tests/docs; named checks run under design.md focused-command policy at the completed change boundary. Do not change the excluded content/ecology/AI scope.

## 1. Legal edge discovery and pricing

- [ ] 1.1 Implement LocationRef/PhysicalEdge strict codecs and legal_edges/quote_edge/location_ref in new world/rules/movement_edges.py using design.md exact signatures. Refactor typeclasses/exits.py preflight to consume shared discovery and existing travel_cost.resolve_traversal_cost; preserve movement.py charges and wilderness_destination topology. Do not alter lore, combat, routing weights or waiver policy. Add test_movement_edges with synthetic corner/gate/depletion/no-physiology cases and its exact evennia-shards entry; document contracts in the developer document. Check: execution and quotes agree on legal/refused edges, exact-zero arrival is affordable, partial physiology refuses, and queries change no DB/cache/room count.

## 2. Persist actual completed history

- [ ] 2.1 Integrate record_completed_edge/read_previous_edge/invalidate_previous_edge in movement_settlement.settle_movement and settle_relocation. Capture source before stock relocation; bind active-body possession/follow scope and snapshot history. Inventory existing nontraversal controlled-body move callers and route their history invalidation through the same owner. Add existing movement_settlement and party_follow_possession tests and developer examples. Check: gate/pooled-room/reload preserves the same completed locators; failed/rolled-back movement retains old history; teleport invalidates it; remote party is unchanged.

## 3. Protect actual passage visibility

- [ ] 3.1 Bind immutable traversal scope before early room relocation and expose field_presence through rules movement owner, with full-window rollback/publication compensation. Add movement alignment tests and observability catalog/history boundary events using named facade imports. Check: synthetic interval [100,150) has no idle endpoint exposure, actual arrival is150, and a fault after history/clock write restores source, history, contents, Attributes and tick with no success event.

## 4. Change handoff checks

- [ ] 4.1 Run the focused named methods/classes from this change, observability lint with changed-logging tests, applicable command-doc contract, strict OpenSpec validation and contract_gate using design.md commands. Generate requirement IDs with the traceability list tool against the equivalent merged tree and record substantive scenario/assertion mappings in the developer document, removing retired claims. Check: required commands exit zero, every new module has exactly one shard owner, all stated behavior has exercised evidence and no unrun full-browser/CI evidence is reported.

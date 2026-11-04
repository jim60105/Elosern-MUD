# Tasks

Future implementation only. Begin after proposal.md Batch prerequisites land. Use design.md signatures and data shapes verbatim. Each step lands its own tests/docs; named checks run under design.md focused-command policy at the completed change boundary. Do not change the excluded content/ecology/AI scope.

## 1. Pure declarations and bindings

- [x] 1.1 Add world/lore/monster_activity.py with the exact frozen ActivityArea/AggressionCondition/MonsterActivity shapes, closed policy/condition vocabulary and registries in design.md. Add required composition/site activity_key bindings in monster_placement.py and migrate every constructor/reference in that authoring subsystem, retaining existing compositions. Do not add runtime group writes or infer species behavior. Register new world.lore.tests.test_monster_activity once; extend test_monster_placement. Document complete schema and human review in the developer document. Check: a count1..2 solitary declaration rejects before sampling, site overrides validate every composition outcome, and bool/nonpositive timing or unknown references reject while valid frozen declarations resolve.

## 2. Atomic candidate publication

- [x] 2.1 Implement resolve_activity_area from the same candidate map bundle; wire lore __init__/sync/registry_index reference metadata and maps/runtime.py candidate validation. Author explicit bounded bindings for all existing compositions and stationary/passive site/exam declarations, without new species or copied tuning tables. Extend geography_source and registry-reference tests; document that birth exclusions are not activity barriers. Check: malformed bounds/dayparts/room-home radius reject the whole candidate and retain prior published snapshot; valid region/home predicates are deterministic and neither read DB nor create rooms.

## 3. Change handoff checks

- [x] 3.1 Run the focused named methods/classes from this change, observability lint with changed-logging tests, applicable command-doc contract, strict OpenSpec validation and contract_gate using design.md commands. Generate requirement IDs with the traceability list tool against the equivalent merged tree and record substantive scenario/assertion mappings in the developer document, removing retired claims. Check: required commands exit zero, every new module has exactly one shard owner, all stated behavior has exercised evidence and no unrun full-browser/CI evidence is reported.

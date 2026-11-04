# Tasks

Future implementation only. Begin after proposal.md Batch prerequisites land. Use design.md signatures and data shapes verbatim. Each step lands its own tests/docs; named checks run under design.md focused-command policy at the completed change boundary. Do not change the excluded content/ecology/AI scope.

## 1. Shared seeded activity decision

- [ ] 1.1 Implement ActivityDecision/plan_group_decision/commit_group_decision in monster_activity.py with exact design signatures, stable hash sampling, positive next interval and stay choice. Use authored resolved bounds and movement_edges for all member legality/pricing. Do not change combat AI or content. Register test_monster_activity in evennia-shards and document selection inputs. Check: synthetic seeded stay/departure survives reads/reload, a mixed group travels at slowest speed, one blocked or unaffordable member prevents every departure, and bounds/corners/locked gates hold while birth-buffer travel remains legal.

## 2. Activate global chronological decisions

- [ ] 2.1 Extend population_lifecycle _settle_population_at/_next_population_boundary and its full snapshot registry to run real decisions globally, merging arrivals, existing site-before-regional births and departures in the specified order. Settle each group physiology cursor once and exclude duplicate generic clock settlement for the same bodies. Keep startup/fresh-state semantics from the predecessor. Extend population/recovery/site/journey tests and developer accounting notes. Check: unobserved groups change real coordinates without rooms, equal time partitions agree including resources, newly born groups can become due within one advance, transit owners retain home cap, visitors block local headroom and a late source fault restores all births/departures/cache state.

## 3. Return behavior and real observations

- [ ] 3.1 Add detached outside-bound return preference with positive waiting retry; preserve stationary exam/site and living quest bindings. Update real map/travel/GM group inspection, both command docs, event catalog and changed-logging tests. Amend wilderness-monster-population Purpose during authorized implementation to include activity rather than recovery-only evolution. Check: escaped member returns only via a lawful adjacent edge or waits, no teleport/replacement/site clearing occurs, stationary groups remain stationary, and active/historical battlefield protection prevents wandering/reinforcement.

## 4. Change handoff checks

- [ ] 4.1 Run the focused named methods/classes from this change, observability lint with changed-logging tests, applicable command-doc contract, strict OpenSpec validation and contract_gate using design.md commands. Generate requirement IDs with the traceability list tool against the equivalent merged tree and record substantive scenario/assertion mappings in the developer document, removing retired claims. Check: required commands exit zero, every new module has exactly one shard owner, all stated behavior has exercised evidence and no unrun full-browser/CI evidence is reported.

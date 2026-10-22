# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Register world_map and extend map.view scope union; implement common/district geometry caches plus per-request knowledge filtering and both validator/store schemas with version parity.
- [ ] 1.2 Encode the visited trail and its >20000 5 km downsampling; include current position/visited hidden places and filter/round accepted commission markers before serialization.
- [ ] 1.3 Integrate first-arrival discovery into the shared committed movement narrative using pre-arrival visited membership, unchanged knowledge writer and post-settlement emission; update existing map/narrative docs.

## 2. Focused behavioral verification

- [ ] 2.1 Add focused proposed `web.webclient.presentation.tests.test_world_map` tests with secret sentinels for unlit/hidden/cross-player cache privacy, exact-versus-rounded markers and whole serialized output; run smallest relevant classes plus one matching Node validator file.
- [ ] 2.2 Test trail at 20000/20001 and large downsampled coverage, then rerun only `WorldMapTransportTests` using the actual assembled real-data payload and record measured size against its bound.
- [ ] 2.3 Add focused landmark-arrival methods to `typeclasses.tests.test_exits` or a new exactly-owned module for first/repeat/gateway/grid arrivals, veto and rollback; patch caller facade logs and verify one committed narrative only.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.

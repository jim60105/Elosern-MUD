# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Register world_map and extend map.view scope union; implement common/district geometry caches plus per-request knowledge filtering and the fixed shared validator/store schemas with version parity.
- [ ] 1.2 Encode the visited trail and its >20000 5 km downsampling; include current position/visited hidden places and filter/round accepted commission markers before serialization.
- [ ] 1.3 Integrate first-arrival discovery into the shared committed movement narrative using pre-arrival visited membership, unchanged knowledge writer and post-settlement emission; update existing map/narrative docs.

## 2. Focused behavioral verification

- [ ] 2.1 Add focused proposed `web.webclient.presentation.tests.test_world_map` tests with secret sentinels for unlit/hidden/cross-player cache privacy, exact-versus-rounded markers and whole serialized output; run smallest relevant classes plus one matching Node validator file.
- [ ] 2.2 Test trail at 20000/20001 and large downsampled coverage, then rerun only `WorldMapTransportTests` using the actual assembled real-data payload and record measured size against its bound.
- [ ] 2.3 Add focused landmark-arrival methods to `typeclasses.tests.test_exits` or a new exactly-owned module for first/repeat/gateway/grid arrivals, veto, rollback, corrupt knowledge and swallowed record_arrival write failure with no false discovery; patch caller facade logs and verify one committed narrative only.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

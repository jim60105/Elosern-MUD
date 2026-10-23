# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Register world_map and extend map.view scope union; implement common/district geometry caches plus per-request knowledge filtering and the fixed shared validator/store schemas with version parity.
- [x] 1.2 Encode the visited trail and its >20000 5 km downsampling; include current position/visited hidden places and filter/round accepted commission markers before serialization.
- [x] 1.3 Integrate first-arrival discovery into the shared committed movement narrative using pre-arrival visited membership, unchanged knowledge writer and post-settlement emission; update existing map/narrative docs.

## 2. Focused behavioral verification

- [x] 2.1 Add focused proposed `web.webclient.presentation.tests.test_world_map` tests with secret sentinels for unlit/hidden/cross-player cache privacy, exact-versus-rounded markers and whole serialized output; run smallest relevant classes plus one matching Node validator file.
- [x] 2.2 Test trail at 20000/20001 and large downsampled coverage, then rerun only `WorldMapTransportTests` using the actual assembled real-data payload and record measured size against its bound.
- [x] 2.3 Add focused landmark-arrival methods to `typeclasses.tests.test_exits` or a new exactly-owned module for first/repeat/gateway/grid arrivals, veto, rollback, corrupt knowledge and swallowed record_arrival write failure with no false discovery; patch caller facade logs and verify one committed narrative only.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

All commands ran in the feature worktree unless explicitly identified as the
disposable equivalent copy. The Evennia environment file contained
`MUD_TEST_SETTINGS=1`.

- Focused Evennia command prefix:
  `uv run --locked --env-file=tmp/world-map-test.env evennia test --settings test_settings.py --keepdb`.
  The batch covering `web.webclient.presentation.tests.test_world_map`,
  `typeclasses.tests.test_map_discovery`,
  `web.webclient.presentation.tests.test_area_map.MapViewDispatchTests`,
  `web.webclient.presentation.tests.test_map_panel_protocol.MapSchemaParityTests`,
  `web.webclient.presentation.tests.test_map_panel_protocol.OnDemandRegistryTests`,
  and `web.webclient.presentation.tests.test_world_map_transport` passed 35 tests.
  After the last classification, terrain, and discovery-isolation changes, the
  three focused feature modules (`test_world_map`, `test_map_discovery`,
  `test_world_map_measurement`) passed 19 tests.
- `node --test web/static/webclient/js/tests/protocol_world_map_transport.test.js`
  passed 10 tests, including maximal 5 km coverage and retained 1 km limits.
- `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_transport.WorldMapTransportTests`
  passed both real-socket tests in 49.558 seconds. The initial attempt could not
  open the SPA because this worktree had no built assets; `pnpm install
  --frozen-lockfile` and `pnpm run build` supplied the required local assets.
  No new browser methods were added, so existing browser ownership is unchanged.
- `uv run --locked python -m tools.world_map_payload --json` measured
  195,220 bytes all-unlit, 213,117 representative, 575,844 at the 1 km threshold,
  and 1,535,088 for maximal separated 5 km coverage with all content and markers.
  The new scoped bound is 2,097,152 bytes; schema versions and other panel
  bounds are unchanged.
- The complete implementation, tests, tooling and manifests were copied into
  an ordinary disposable directory with prerequisite specs already present and
  this change's two deltas merged. Canonical IDs came from
  `uv run --locked python -m tools.spec_traceability --repo-root
  tmp/publish-world-map-equivalent list --json-output tmp/world-map-requirements.json`.
  Its explicit `check` passed. The copied `tools.contract_gate` passed with
  1,416 test-data sources scanned after creating a standalone index for its
  `git ls-files` consumer. This was not a linked git worktree and had no commits.
  The disposable copy was removed before running normal root gates, avoiding
  duplicate traceability associations.
- After feature-branch main-spec synchronization,
  `uv run --locked python -m tools.spec_traceability check` passed with
  2,485 requirements, 11,118 associations, zero uncovered and zero errors.
  `uv run --locked python -m tools.contract_gate` passed traceability,
  observability, test-data, manifests and all 18 bundled contract tests.
  Observability reported zero violations; test-data scanned 1,416 sources with
  zero violations.
- `openspec validate publish-world-map-panel --strict` passed.
  `openspec validate --specs` passed all 366 capability specs.

Existing behavior documentation was updated in
`docs/development/map-panel-protocol.md`, including the committed discovery
narrative and production transport measurements. The new arrival module is
owned by the existing `typeclasses` shard prefix; the new presenter test module
has its explicit web-presentation shard entry. The real-geography measurement
module has matching production-contract classification and rationale.

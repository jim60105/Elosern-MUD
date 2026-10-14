# Tasks

Estimated total: **6.25 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [x] 1.1 **1.25 h.** Declare explicit scene/archetype and optional room-art metadata for authored grid/permanent place/interior inputs, referencing the registered room-art keys from scene-catalog. Do not derive keys from room name/id/tier or nearby location. Extend map_data/bootstrap service-interior construction with existing attribute persistence; plain Room interiors must read their valid scene metadata while keeping doorway identity/typeclass behavior. Add/register world.maps.tests.test_room_art_metadata with repeated startup/new interior/reload assertions and independently expected authored metadata; document authored room-art input examples.

- [x] 1.2 **1.5 h.** Repair wilderness_provider.at_prepare_room by reading an explicit region→registered-scene mapping instead of assigning unregistered region keys as archetypes. Use forest_path for forest regions, mountain_path for central mountains, coastal_path for coast and wilderness_path for plains/hills. Derive logical identity from wilderness name/current coordinates; reset every scene fact and clear previous room_art_key when no declaration applies. Extend synthetic test_wilderness_provider and room-art tests with a single pooled object prepared for A(with key) then B(without key), including equal archetypes/different coordinates and restart restoration; terrain/exits/population behavior must be unchanged.

- [x] 1.3 **1.5 h.** Extend the existing supported instance construction inputs in world/maps/instance.py to carry only explicitly authored registered room_art_key plus stable nonpooled instance scene identity. Dynamic undeclared instances have no room-art key; do not add coordinates, prompts/jobs/generated per-room records or migrations. Expose read-only logical identity to presentation from map-owned metadata with bounded strings. Test invalid declared key rejection before supported construction, absent key defaults, instance reload and no art-resolver mutation; preserve existing reclamation/pin/exit behavior.

- [x] 1.4 **0.75 h.** Add representative runtime smoke RoomMetadataSmokeTests.test_bootstrap_and_pool_reuse in world.maps.tests.test_room_art_metadata using real map/bootstrap construction and actual wilderness preparation/reuse, not mocked descriptor inputs. Assert current art panel archetype is registered, permanent interiors no longer lack supported metadata, and pooled coordinates differ in logical identity with stale key cleared. Run its exact Evennia label below; this slice does not claim the later scene browser renderer is already cut over. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.5 **0.5 h.** Update affected existing map/art authoring development documentation with room-art declaration and region mapping ownership, plain-interior support and logical-place identity. Record data-contract assertions in the existing freeze ledger only where actual authored inventories are read; ordinary A/B pooling tests stay synthetic. Attach effective room metadata requirement claims and register the new module exactly once in the non-browser shard manifest. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.6 **0.75 h.** Run the focused map/typeclass labels plus exact runtime smoke and final strict/contract commands below. Completion means startup is idempotent, all supported authored rooms use valid metadata, undeclared dynamic rooms use archetype only, and neither old key nor old logical identity can survive pooled object reuse. Preserve room mixin permissive assignment and all unrelated map/quest/gameplay behavior. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_room_art_metadata world.maps.tests.test_service_interiors world.maps.tests.test_wilderness_provider
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_room_art_metadata.RoomMetadataSmokeTests.test_bootstrap_and_pool_reuse
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-room-art-metadata --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.

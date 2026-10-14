# Tasks

Estimated total: **6.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1.75 h.** Implement describe_portrait/describe_entity attempt enumeration in world/art/presenter.py using the canonical art-domain types already introduced by gallery. Preserve bound-card specificity/newest tie, explicit official, default, classic, official order plus deterministic alpha terminal; use stable source identities/ranks, source-scoped facts and independent generation truth. Add/register world.art.tests.test_portrait_attempts with synthetic expected attempts/faults, missing completed output, failed recorded job with generation disabled and unchanged stored preferences/records/files.

- [ ] 1.2 **1.25 h.** Integrate the enumerator immediately inside current resolve_entity/resolve_character portrait resolution so existing production serialization still selects the same first valid real source and existing fallback. Preserve the current single flat registered wire until the atomic portrait change. Do not change generic resolve_subject/resolve_scene delegation or introduce aliases/dual accepted shapes. A focused art-panel test must show current v2 portraits/scenes both remain schema-valid; current resolve_entity is normal production selection, not a compatibility re-export.

- [ ] 1.3 **0.75 h.** Retain bounded named-import facade diagnostics distinguishing failed selected sources from fallback success, with subject/entity/source identifiers in context. Explicit default/selection faults precede safe substitutes; unselected sibling refusal is operational only. Eligibility remains canonical ages/species/declared policy; no source reader creates records, queue jobs, geometry repairs or files. Tests patch caller facade bindings and assert boundary semantics.

- [ ] 1.4 **1 h.** Exercise existing direct presenter callers in test_presenter, test_species_portrait_identity, test_service/test_autogen_retrofit, test_service/test_monster_gallery, test_worker/test_store_isolation and test_character_creation/test_portrait_finalization using their still-current expected flat consumer contract. Extend independent-source/no-write controls as needed; do not migrate wire assertions early. The later portrait wire task names all these files again for its clean canonical migration.

- [ ] 1.5 **0.75 h.** Add production-boundary runtime smoke in world.art.tests.test_portrait_attempts.PortraitAttemptSmokeTests.test_real_gallery_official_and_alpha_resolution. Construct real eligible synthetic entity/card/catalog fixture via existing writers/startup admission, call production resolver then canonical enumerator, and assert expected first candidate plus ordered faults and unchanged persistent state. This is not a browser shape cutover or a mocked source selection; record the focused result. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.6 **1 h.** Update official-artwork-deployment/frontend art developer notes for art-owned canonical source facts and still-current one-shape serializers. Register new non-browser module and substantive effective requirement claims, then run focused caller/runtime tests and strict/contract gates below. Completion means one production-used selector owns source/alpha policy, and portrait wire/figures can migrate without unestimated chain implementation or scene regression. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_portrait_attempts world.art.tests.test_presenter world.art.tests.test_species_portrait_identity
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_service.test_autogen_retrofit world.art.tests.test_service.test_monster_gallery world.art.tests.test_worker.test_store_isolation
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation.test_portrait_finalization web.webclient.presentation.tests.test_art_panel
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_portrait_attempts.PortraitAttemptSmokeTests.test_real_gallery_official_and_alpha_resolution
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-portrait-source-resolution --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.

## 1. Registry model and contracts (3 hours)

- [ ] 1.1 Add leaf ref/ref_many metadata helpers and frozen RegistrySpec/lazy REGISTRY_INDEX covering every S4 category; verify synthetic helper tests, lazy-import boundary and complete inventory contracts without modifying `_ALL_REGISTRIES`.
- [ ] 1.2 Add recursive field-path traversal, process-cached forward/inverse maps and DanglingReference diagnostics; verify single/many/nullable/nested synthetic fixtures, inverse declaration collisions, missing targets and cache reuse.
- [ ] 1.3 Declare first-batch direct-key references for monster species/variants/sites/ambient placements, quests, items, places/settlements/shops and NPC profiles, correcting any exposed shipped dangling keys; verify unchanged dataclass defaults/types/values and empty shipped dangling list, valid targets and unique inverses. Tag/register shipped-data contracts in the existing data-freeze manifest.

## 2. Read-only API, sources and reload (2 hours)

- [ ] 2.1 Add `web/gm/readers/world.py` inventory/list/search/detail reads with authored serialization and nested string search; verify shapes, loaded-versus-disk distinction, stable query-preserving cursor pages/default 50/max 200 and missing-registry/key errors in focused tests and existing reader AST contract.
- [ ] 2.2 Add request-time qualified YAML allowlist/source reads and all GET routes through gm_path before API fallbacks; verify rulebook/commerce/prompts text/provenance, fresh allowlist, same-basename files, traversal/encoded traversal/absolute path/escaping symlink rejection and source_not_found envelope.
- [ ] 2.3 Add CSRF-protected prompt reload handler outside readers, reset then authoritative load and diagnostics, gm_prompts_reloaded/gm_action context; verify successful/failed loader behavior, no GET/no invalid-CSRF loader call, request/denial events and no source/persistent changes. Run focused event tests with observability lint.
- [ ] 2.4 Test every S4 page/API with anonymous/ordinary/Developer/superuser access, inherited envelope/method/cursor/limit errors, resolver protection, offline operation and unchanged rows/Attributes/source bytes; verify with focused GM tests and read-only contracts.

## 3. Browser composition and S3 links (2 hours)

- [ ] 3.1 Enable grouped world-data navigation and reserved source/list/detail routes; compose existing GM table/filter/pager components for summaries and search. Verify grouped inventory, summary fallback, search/paging, source paths and source/restart instructions in focused Vitest.
- [ ] 3.2 Render all converted fields through GmJsonTree with field-path reference links plus outgoing and inverse-grouped sections; extend existing GmEntityLink routing and S3 registry-key presentation including race/species/variant/definition_key. Verify nested rendering and every link target in Vitest without regressing object/call/media links or runtime read semantics.
- [ ] 3.3 Add line-numbered monospace source view and prompt-only reload action/diagnostics/failure display; verify disk-vs-loaded notice, explicit reload exception, Traditional Chinese copy, verbatim identifiers and same-origin API-client CSRF handling in focused frontend tests. Add stories for each new component and verify showcase coverage.

## 4. Integrated evidence and documentation (1 hour)

- [ ] 4.1 Register each new Python module in exactly one Evennia shard; update relevant implementation developer docs/changelog and substantive requirement annotations using canonical traceability IDs. Verify data-contract ownership, shard ownership and local traceability via `uv run --locked python -m tools.contract_gate`.
- [ ] 4.2 Run `openspec validate gm-portal-s4-world-data --strict`, the smallest affected lore/GM Evennia labels with the required test env-file spelling, focused Vitest, `pnpm run test:gm-boundary`, `pnpm run build:gm`, and new stories/showcase coverage from the existing frontend workspace. Record pass/fail evidence for all requirements; preserve isolated GM output, game frozen contracts, .elosern-root and OOB. Leave full browser/evidence verification to CI.

## Context

See proposal.md for motivation, consumed dependencies and eight-hour sizing. The approved S4 design is authoritative; parent §3 and S1 transport conventions apply. Landed S1 provides gm_path, access/response helpers, CSRF and the same-origin API client. S3 provides read-only readers, GmEntityLink, GmJsonTree, filters and paging. Existing registry/dataclass values and prompt loader semantics remain authoritative.

## Goals / Non-Goals

**Goals:** One explicit inventory, one declarative reference walk, one reader/API surface, and existing-component page composition. Complete first-batch declarations and all inventory categories from S4 §3.2.

**Non-Goals:** No heuristic discovery, composite/prefixed parsing, startup reference enforcement, `_ALL_REGISTRIES` refactor, bespoke config adapters, prompt diagnostics/integrity report pages, authored-to-runtime reverse links, source editing, schema migrations or compatibility shims. S5/S6 stay untouched.

## Decisions

### 1. Leaf metadata and lazy inventory

`world/lore/registry_refs.py` has no game imports. `ref(registry, *, inverse, nullable=False)` and `ref_many(registry, *, inverse)` return metadata mappings consumed by dataclasses.field without changing defaults/types/values. `registry_index.py` defines frozen RegistrySpec(name, label, group, loader, source_path, summary_fields=()) and REGISTRY_INDEX as a tuple. Use existing registry/load APIs lazily rather than constructing parallel values or importing subsystem modules when the index is imported. Groups use the eight approved display labels. Inventory includes all S4 §3.2 categories, while parameter-only YAML remains source text. Preserve `_ALL_REGISTRIES` unchanged.

### 2. One recursive reference model

Walk dataclass fields and their nested dataclass/collection children, retaining full field paths (including collection positions). Interpret only metadata-declared single/many direct keys; nullable None produces no edge. Cache `build_reference_index()` forward/inverse maps once per process. Identify declaration uniqueness by declaring dataclass and field, not by each entry occurrence; distinct declarations targeting the same registry cannot reuse an inverse. `check_references()` returns DanglingReference(registry, key, field_path, target_registry, missing_key). Existing validators retain composite/parsed integrity responsibilities. Synthetic fixtures exercise traversal and caching; shipped contracts assert target existence, inverse uniqueness, inventory coverage and frozen dataclass mappings. Fix discovered shipped dangling keys in this implementation before acceptance.

### 3. Loaded entry reader and inherited transport

Place immutable registry reads in `web/gm/readers/world.py`, covered by the existing reader AST contract. Use existing `_db_safe` conversion semantics (including recursive dataclasses) without changing sync behavior. Inventory/list/search/detail obtain current loaded mappings through their authoritative loaders, not reload/import source. Search keys and string leaves recursively. Entry pagination uses stable key order, existing cursor/limit handling (50 default, 200 cap), query-preserving opaque cursors and items/next_cursor shape. Search results carry registry/key identities; details carry fields and forward/inverse descriptors with full paths. Use gm_path and shared response helpers for all six S4 routes; register the reserved prompt-reload route before the source-name route and API fallbacks. Unknown registry/key/source use the three S4 404 codes; access, CSRF, unsupported-method and pagination errors retain existing codes/envelopes.

### 4. Disk source viewer is explicitly distinct

Build the YAML allowlist at request time under `world/rules/rulebook/` (including commerce) and `prompts/`. Use repository-relative qualified names, not colliding basenames, as opaque source names; route captures qualified names and frontend encodes them consistently. Resolve candidates and require canonical containment in the approved roots, including symlink checks; do not concatenate an untrusted path and read it. Unlisted, absolute, traversal and escaped-symlink names return source_not_found. Show disk text with line numbers and source path, clearly distinct from loaded entry values. A source edit does not refresh registries: restart applies authored changes except the explicit prompt reload.

### 5. Reload stays outside read-only readers

An API action handler calls `reset_prompt_library()` then `load_prompt_library()` through the existing prompt owner APIs. Keep this handler outside readers so their AST contract is not weakened. Reuse loader diagnostics/results, including failure semantics; do not add transactional rollback, startup changes, LLM requests or source writes. Valid Developer access plus existing CSRF is required before either call. Return diagnostics for the prompts source view on success or loader-reported failure; use inherited transport envelopes. Emit `gm_prompts_reloaded` and `gm_action` through named facade imports, with account, target (`prompts`), action and outcome in context; retain gm_request/gm_denied and do not log full prompt text or credentials.

### 6. Compose landed presentation and links

Enable world-data navigation and routes `/gm/world/<registry>`, `/gm/world/<registry>/<key>` and `/gm/world/sources/<name>` with source routes registered ahead of generic registry routes. Compose GmPageHeader/GmPanel/GmTable/GmJsonTree/GmFilterBar/GmPager. Add narrow registry link descriptors/routing through existing GmEntityLink and field-aware JSON rendering rather than duplicating tree or link renderers. Preserve raw values while attaching declared field-path links; references and inverse groups also use the same link component. Extend S3's authoritative key-field presentation to authored targets (race, species, variant, quest definition and other existing registry-key fields), leaving runtime read semantics and object/call/media targets intact. Each page states source-path provenance and source/restart workflow; prompt view states its reload exception. UI translations are Traditional Chinese; technical documentation remains English.

## Risks / Trade-offs

- Explicit inventory can drift: enforce startup inventory subset plus the named extra categories in contracts; do not introduce discovery.
- Inverse collisions arise across reused dataclasses: validate declarations once, then collect entry instances independently.
- Disk YAML may differ from loaded values: label disk source explicitly and never promise reload for rulebooks/registries.
- Prompt failure may change effective library: expose actual loader diagnostics/behavior, not an invented all-or-nothing guarantee.
- Routing/source names may overlap: reserve source/reload routes before generic routes and test qualified names/traversal through the resolver.
- Broad content references can expose bad shipped data: resolve direct-key defects within this change and do not expand into composite integrity work.

## Delivery and verification

Implement the four bounded slices in proposal.md within one workday, with tests alongside each slice and one integrated final verification. Add new Python module shard ownership and shipped-data freeze registration; no player-command docs change is needed. Update relevant developer docs/changelog in the implementation (this proposal changes artifacts only). Obtain canonical IDs from the traceability tool and attach substantive tests before archive; active delta specs do not alter current-contract indexing. Run strict OpenSpec validation, focused lore/GM tests, observability lint with focused event tests, focused Vitest and new stories/showcase coverage, test:gm-boundary, build:gm and contract_gate. CI owns complete browser/evidence suites. No audit model, external runtime dependency or game-bundle modification is introduced.

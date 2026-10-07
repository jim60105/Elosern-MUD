## Why

Operators can inspect runtime state but cannot yet browse the authored registries or follow their references. S1 and S3 are landed, so S4 can add a read-only authoring browser without rebuilding portal infrastructure.

## What Changes

- Add explicit lazy registry inventory and dataclass `ref`/`ref_many` metadata, cached forward/inverse indexes, and shipped-data integrity contracts.
- Browse every indexed registry, search loaded entries, show fields/references/referrers, and link S3 registry-key fields to authored entries.
- Add allowlisted rulebook/prompt YAML source viewing and CSRF-protected in-memory prompt reload with diagnostics and facade events.
- Preserve Developer access, read-only readers, single-writer boundaries, offline operation, and isolated GM assets.
- No startup integrity enforcement, registry discovery, sync refactor, web authoring, runtime reverse lookups, diagnostics/report pages, compatibility layers, or migrations.

## Capabilities

### New Capabilities
- `authored-registry-references`: Lazy inventory, declarative references, and CI integrity contracts.
- `gm-world-data`: Protected world-data APIs, browser, source viewing, prompt reload, and S3 navigation integration.

### Modified Capabilities
None. S1/S3 contracts are consumed unchanged; the additional authored targets and navigation behavior belong to `gm-world-data`.

## Impact

Implementation touches `world/lore/registry_refs.py`, `registry_index.py`, first-batch dataclass declarations, `web/gm/` readers/API/routes, `web/admin-app/` pages/router/link integration, focused tests/stories, shard/data-contract manifests, and implementation documentation. No database schema or player command changes. Authoritative scope: `docs/superpowers/specs/2026-10-06-gm-portal-s4-world-data-design.md`, with parent §3 constraints from `2026-10-06-gm-portal-design.md`.

## Dependencies and conflicts

| Surface | Relationship | Conflict notes |
| --- | --- | --- |
| S1 `gm-portal-s1-foundation` | Consumed; landed and archived | Reuse access, envelopes, CSRF, component layer and separate build; extend GM URLs/router only |
| S3 `gm-portal-s3-runtime-state` | Consumed; landed and archived | Reuse reader AST contract, GmEntityLink/GmJsonTree/filter/pager; extend registry-key links without changing runtime reads |
| S5 saves | Unaffected/deferred; no dependency | Future edits may share GM URLs/router/navigation; no save APIs or content changed |
| S6 console | Unaffected/deferred; no dependency | Future edits may share GM URLs/router/navigation; no console APIs or content changed |
| Active proposals | None at assignment start | No in-flight code conflict |

## Implementation split and sizing

One change, one engineer-day (approximately eight hours): registry model/declarations/contracts (3h), readers/API/source/reload (2h), existing-component page composition and S3 links (2h), focused verification/documentation/traceability (1h). These are sequential integration slices, not separate proposals or reduced deliverables. Reusing landed S1/S3 and existing loaders keeps the work bounded; no bespoke rulebook adapters, new infrastructure, diagnostics pages, or generalized reference parsing. Any dangling first-batch data must be fixed in this implementation before acceptance, not deferred to S5/S6.

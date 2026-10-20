# Design: Seeded lineage consumer consistency

## Context

See proposal.md and handoff issue 3. The text request for 艾拉 returned unavailable. A separate commander detail request logged `LineageQueryError` at `world/rules/lineage_query.py:307`. These observations establish two failures; they do not establish one cause. `_topological_order()` builds indegrees from the live registry and drains them via `prerequisite_consumers()`. The registry is a mutable live dict in `world/skills/registry/assembly.py`; synthetic installation replaces its contents, and browser grafts add innate rows after installation.

## Goals / Non-Goals

Restore readable valid synthetic lineage and preserve the existing lineage contract. No new OOB schema, fabricated graph, query-time repair, cycle suppression, relaxed load validation or changes to skill eligibility are authorized.

## Decisions

Trace one bounded mechanism question during implementation: do registry prerequisites, reverse-edge consumer entries and the query's component/indegree construction describe the same post-install/post-graft graph? Compare them immediately after synthetic install and after browser graft completion in both seed and server process startup. Include cached import bindings and identity filtering in that comparison. Separately locate whether 艾拉 fails query construction or bounded serialization. Retain the commander diagnostic as a second regression if the causes differ.

Correct the earliest owning source of inconsistency. If installation or grafting leaves a stale consumer index, rebuild/validate that index at catalog mutation boundaries, never on each read. If the graph is malformed, correct the authored synthetic graph and preserve fail-closed validation. If sorting/filtering is inconsistent for a valid graph, correct that logic against a fixed branching/merging DAG. This is a bounded diagnosis-and-fix task with an end-to-end acceptance criterion, not a deferred investigation deliverable. Do not select a cause from the handoff alone.

Add focused tests using an independently authored DAG with a branch and a two-parent merge. Assert roots, every node once, edge direction/threshold and deterministic topological order. Cover install followed by innate graft and repeated installation without stale edges; use the owning teardown to restore global catalogs/indexes between tests. A malformed registry, real cycle or malformed proficiency must still fail through existing safe consumer refusals, with no invented rows.

A managed-runtime regression uses the existing synthetic companion surface, independent of the forthcoming dedicated party fixture. Read the named member through authenticated text and `party.view_member` plus `lineage` v2. Normalize transport-specific framing and compare roots, node identities/order and edges/thresholds within common bounds. Record stored entity/world values before/after repeated reads and assert no mutation. Exercise a commander GM lineage read separately; do not infer it from member success.

## Risks / Trade-offs

Global synthetic installation can make import order observable. Keep index construction under its current owner and avoid a second cache. Stay within the existing pure-read contract; this proposal strengthens its regression scenarios without changing intended lineage semantics. If diagnosis reveals an unrelated production feature, record it outside this slice rather than broadening the fix.

## Verification and documentation

Focused registry/query/command/presentation tests and one live managed consumer regression must cover the corrected mechanism. Register every added method/module in its exact browser/Evennia manifest owner and annotate the existing pure lineage requirement. Document catalog/index lifecycle in the existing synthetic fixture guide. The dedicated named fixture depends on this fix for its later live lineage evidence.

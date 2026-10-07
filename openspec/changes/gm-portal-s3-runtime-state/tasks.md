## 1. Safe read foundation

- [ ] 1.1 Map every S3 summary field to its existing authoritative read model; extend design.md's autocreating-property inventory through inherited descriptors, lazy handlers and called helpers. Verify missing-Attribute fixtures do not initialize state; add only necessary pure read seams in owning packages, with parity tests rather than duplicated rules.
- [ ] 1.2 Implement JSON conversion and raw.py for arbitrary Evennia objects, categorized Attributes/tags/components, typeclass/location/creation metadata, linked $ref and 200-character $unserializable markers; verify nested references, unsupported/cyclic values and non-curated object fixtures.
- [ ] 1.3 Add the AST read-only contract over readers and a reusable runtime baseline for Attribute counts and all narrative-table row counts; supplement representative indirect-helper cases with stored-value comparisons or captured domain-write SQL to detect updates as well as creation/deletion. Verify deliberately forbidden syntax is rejected and tests observe writes before any fixture teardown/rollback, allowing facade events and in-process recall caches.

## 2. Curated reader projections

- [ ] 2.1 Implement accounts.py and characters.py using account_roster/status_query/displayed_stats/title_view/lineage/relationship queries for every S3 §4 account/character field; verify fixed-fixture shapes, account raw categorized tags/Attributes/applicable components, integer currency, cross-links and true/disguised side-by-side separation.
- [ ] 2.2 Implement npcs.py and monsters.py for NPC character fields, seven-section persona/version, services/schedule/dialogue key and all monster identity/provenance/site/loot/behaviour fields; verify fixed NPC/monster fixtures and missing stored descriptor defaults remain immutable.
- [ ] 2.3 Implement rooms.py and quests.py for map/exit/occupant/instance fields and runtime/generated quest detail including payload, progress, targets/rewards/failure/owner; verify each field and owner-scoped record identity with fixed fixtures.
- [ ] 2.4 Implement narrative.py and art.py for every approved narrative subtype and art metadata/gallery thumbnail; verify events, threads/revisions, letters/state/reply work, dreams/exchanges, decisions/beats/drafts/requests and file-present/file-absent art fixtures.
- [ ] 2.5 Implement search.py with exact dbref resolution and ordered object-key/quest-id/source-id matches, using real target identities and raw fallback for non-curated objects; verify precedence and collision/unknown-target fixtures without a new transcript-search backend.

## 3. NPC narrative inspection

- [ ] 3.1 Project filtered MemoryRecord effective views and complete MemoryRevision histories, newest ten NarrativeContextSnapshot sections/token accounting/truncated/rejected sources and existing S2 evidence links; verify all filters, revision fields and snapshot cap/order.
- [ ] 3.2 Project dialogue epochs/frames grouped by player using pure queries; verify multi-player grouping and no correspondence settlement or new epoch/frame/snapshot rows.
- [ ] 3.3 Add recall projection invoking fast_recall with identical canonical NPC owner/requester, thread and inclusion options; verify core/working/lexical selections, BM25 scoring and generation against a direct call, including inaccessible threads, with unchanged row/Attribute counts.

## 4. Protected runtime transport

- [ ] 4.1 Add all five approved route families via gm_path with reserved-route precedence, explicit kind resolution and existing envelopes; verify anonymous/player/Developer/superuser matrix, URL-resolver coverage, facade request/denial events and read-only POST CSRF behavior.
- [ ] 4.2 Implement summary-only filtered cursor lists (default 50/max 200), narrative subtype/owner lists and detail/raw resolution; verify indexed query fields, deterministic tie-breakers, cursor/filter preservation, end-of-list and no full raw/history data in lists.
- [ ] 4.3 Isolate summary sections and implement 404 object_not_found/kind_mismatch plus pre-execution 400 query_too_long; verify each section fails independently, correct lookup distinction and recall boundaries at 2000/2001 characters.

## 5. Runtime frontend and existing transcript integration

- [ ] 5.1 Add GmEntityLink and collapsible GmJsonTree with $ref links and distinct $unserializable presentation; replace duplicated structured JSON rendering in GmCallDrawer without changing attempt/role/error/text/copy/expired/disabled behaviors. Verify Vitest link/marker routing and existing drawer tests.
- [ ] 5.2 Add GmFilterBar/GmPager and enable the complete runtime navigation tree/search/list routes while keeping S4/S5/S6 disabled; verify cursor/reset/filter and direct/history navigation with Vitest.
- [ ] 5.3 Build reusable entity header/overview/raw layout and every curated summary panel, including separate true/disguised panels; verify all entity shapes render, identifiers cross-link correctly and independent failures leave other panels visible.
- [ ] 5.4 Build NPC memory/history/recall/snapshot and player-grouped dialogue tabs with S2 call drawer links; verify length errors, recall controls, snapshot evidence and unavailable transcripts without full prompt assembly.
- [ ] 5.5 Provide manual refresh only on runtime pages, never reuse overview polling lifecycle; verify mounting/time passage does not schedule polling and refresh reloads the selected data through the existing API boundary.
- [ ] 5.6 Add Storybook stories for every new Gm component covering linked/unserializable/empty/error states; verify showcase coverage includes them and preserved drawer stories, with Traditional Chinese UI and unchanged token-only dependency boundary.

## 6. Complete acceptance and documentation

- [ ] 6.1 Deliver one fixed-fixture EvenniaTest module per each of the ten readers plus transport/static/runtime contracts; register every new Python module in .github/evennia-shards.json. Verify output-shape coverage for every entity and runtime count invariance across lists/details/raw/narrative tabs/recall, including missing-Attribute fixtures.
- [ ] 6.2 Add substantive canonical covers_requirement annotations and frontend evidence bridges using tools.spec_traceability list rather than constructed IDs; update developer documentation for routes, manual refresh, diagnostic errors and immutable recall limits. Verify every new requirement has meaningful matching evidence and no placeholder/skip claims.
- [ ] 6.3 Run openspec validate gm-portal-s3-runtime-state --strict, focused uv-managed reader/API/contract tests, shard ownership, tools.contract_gate, pnpm test, pnpm run test:gm-boundary, pnpm run build:gm, and the Storybook/showcase gates once the complete implementation lands. Verify all results before checking tasks complete; do not run broad CI-only browser/evidence suites locally.

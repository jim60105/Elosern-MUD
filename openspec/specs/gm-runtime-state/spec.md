# gm-runtime-state Specification

## Purpose
Provide privileged read-only inspection of persistent game entities and NPC narrative state, linked to retained operational evidence without altering the inspected world.

## Requirements

### Requirement: Protected read-only inspection boundary
All runtime inspection APIs SHALL reuse the existing Developer/superuser authorization, JSON envelope, same-origin fetch boundary, request/denial facade events, and resolver access-coverage contract. Anonymous and ordinary accounts SHALL receive existing 401 unauthenticated and 403 forbidden responses. Inspection SHALL never mutate persistent state, autocreate Attributes, repair data, call narrative writers, or recompute rules independently of authoritative read models. Narrative knowledge-scope and thread permissions SHALL remain enforced.

#### Scenario: Authorized immutable inspection
- **WHEN** anonymous, ordinary, Developer, and superuser accounts request runtime inspection
- **THEN** authorization and logging match the landed portal contract, permitted responses reflect authoritative read data, and all inspected persistent state remains unchanged

#### Scenario: Missing stored defaults
- **WHEN** a permitted inspection reads an entity missing an autocreating property's stored Attribute
- **THEN** the response uses a non-creating read/default or localized error and creates no Attribute

### Requirement: Runtime API routes and bounded lists
The portal SHALL expose GET `/gm/api/state/<kind>?cursor=&limit=&<filters>`, GET `/gm/api/state/<kind>/<id>`, GET `/gm/api/state/object/<dbref>/raw`, GET `/gm/api/state/search?q=`, and POST `/gm/api/state/npc/<dbref>/recall`. Lists SHALL return summary-only `items` and opaque `next_cursor` or null using the existing envelope; limit SHALL default to 50 and never exceed 200. Stable ordering and filters SHALL use indexed narrative fields and Evennia typeclass paths/tags. Filters SHALL support NPC location, monster species/region, and memory tier/availability/category/knowledge scope. Recall POST SHALL retain CSRF protection despite making no writes.

#### Scenario: Filtered pagination
- **WHEN** an operator follows successive cursors for a filtered entity list
- **THEN** pages have stable ordering, preserve filters, contain only summary fields, respect default/maximum limits, and terminate with null next_cursor

#### Scenario: Recall CSRF
- **WHEN** an authorized recall POST lacks a valid CSRF token
- **THEN** the existing csrf_failed transport error is returned and no recall or persistent write occurs

### Requirement: Complete curated entity summaries
Each entity page SHALL offer a curated summary and a raw representation. Curated summaries SHALL include:
- Accounts: name, permissions, created/last-login dates, live sessions, owned characters.
- Player characters: race/subrace/sex/age/apparent age; true traits; separate displayed disguise; per-trait base → skills → equipment → conditions breakdown; gauges, conditions/buffs, skills/lineage, equipment/inventory, integer-copper wallet and derived gold/silver/copper display, guild rank/merit, titles, affinity, party/possession, sexual state, and current room.
- NPCs: character fields plus title/profession, shop/guild service components, seven-section persona and version, today's schedule/current slot, dialogue key, memory and dialogue tabs.
- Monsters: species/variant/threat tier, approved-profile or interim numeric source, owning site or ambient placement, loot table, behaviour profile.
- Rooms: coordinates/map, place kind, exits, occupants grouped by kind, instance ownership/lifetime.
- Quest records: definition key, issuer, status/stage, progress counters, bound targets, deadline, rewards, failure reason, owning character; generated quests also show stored payload.
- Narrative: event content/participants/location/visibility; thread status/links/revisions; letter exchanges/state/reply work; dream sessions/exchanges; director decisions/scheduled beats; authoring drafts/creative requests.
- Art assets: subject key, status, prompt summary, source_hash, generated time, failure reason, and existing `/art/` thumbnail only when a file exists.
Stored truth and `disguised_stats` SHALL be shown side by side; disguise SHALL be labelled 僅顯示用 and SHALL never replace or merge into true traits. Currency SHALL remain integer-based. Missing or failed sources SHALL not be fabricated.

#### Scenario: Entity inventory coverage
- **WHEN** fixed fixtures for every listed kind and narrative subtype are inspected
- **THEN** each curated summary exposes all applicable named fields and real relationships, including generated payload and available art thumbnail

#### Scenario: Disguised character and NPC
- **WHEN** a character or NPC has disguise values different from true traits
- **THEN** both are independently emitted and rendered side by side, the disguise is labelled display-only, and breakdowns retain true values

### Requirement: Universal Evennia raw inspection
Every Evennia object, including objects outside curated kinds, SHALL have a raw tab/route showing all Attributes with key/category/converted value, categorized tags, components, typeclass path, location, and creation date. Object references SHALL serialize as `{"$ref":"#123","typeclass":"…","key":"…"}`. Unconvertible values SHALL serialize as `{"$unserializable":"<type name>","repr":"<repr truncated to 200 chars>"}` and SHALL not prevent inspection of other values. Non-Evennia records SHALL expose their stored record fields as raw data without pretending they have Evennia Attributes.

#### Scenario: Arbitrary object and non-JSON values
- **WHEN** a non-curated Evennia object contains categorized Attributes/tags, object references, and an unconvertible value
- **THEN** its complete raw inventory is visible, references are linked, unconvertible values are distinct with bounded repr, and the remaining data renders normally

### Requirement: Runtime navigation search and cross-links
The runtime navigation tree SHALL enable search, accounts, player characters, NPCs, monsters, rooms, runtime/generated quests, narrative records, and art assets. Global search SHALL jump to an exact #dbref; other text SHALL match object key, quest id, then source_id in that precedence. Every displayed identifier SHALL link to its corresponding entity, source event, or retained S2 call drawer, including room, quests, memories, letters, party members, possession partner, memory source_id and available call_id. Call identifiers SHALL use the existing transcript detail contract rather than a new transcript search backend.

#### Scenario: Search precedence and links
- **WHEN** an operator searches an exact dbref or text matching object keys, quest ids and source ids, and follows a relationship identifier
- **THEN** dbref opens its object, text results retain the required precedence, and relationship/source/call links reach the correct existing target

### Requirement: NPC memory and dialogue inspection
The NPC memory tab SHALL show filtered memory content, salience, confidence, subjects, linked source_id, effective tier/availability, and complete expandable revision history including availability/tier/decay metadata/supersedes. Recall input SHALL accept query text up to 2000 characters, optional thread, include-superseded and include-inactive toggles. Recall SHALL use the NPC as owner and requester and return the same core/working/lexical selections and BM25 scores as the authoritative read-only recall query, plus current owner memory generation. The newest ten context snapshots SHALL show sections, token accounting, truncated/rejected sources and available trace_id/call_id links to S2 evidence. The dialogue tab SHALL group epochs and frames by player. Full dialogue prompt preview SHALL NOT assemble new context, persist snapshots/epochs/frames, or settle correspondence.

#### Scenario: Memory history and recall equivalence
- **WHEN** a permitted operator filters memories, expands a revision history and requests recall with thread and inclusion toggles
- **THEN** effective fields and full history are visible, recall selections/scores/generation equal a direct authoritative call under the same NPC permissions, and no persistent rows or Attributes change

#### Scenario: Existing narrative evidence only
- **WHEN** more than ten snapshots and dialogue frames for multiple players exist
- **THEN** the memory tab shows only the newest ten snapshots with available evidence links, dialogue groups epochs/frames by player, and viewing either tab produces no new dialogue context or correspondence settlement

### Requirement: Independent failures and precise lookup errors
Each curated summary section SHALL compute independently. A failed section SHALL carry `{"error":{"code":"<snake_case>","message":"<zh-TW>"}}` in its own slot while unaffected sections render in the success envelope. Unknown objects SHALL return HTTP 404 object_not_found; objects incompatible with the requested kind SHALL return HTTP 404 kind_mismatch. Recall query text over 2000 characters SHALL return HTTP 400 query_too_long before recall execution. Errors SHALL remain visible diagnostic evidence and clients SHALL branch on codes only.

#### Scenario: Corrupt section isolation
- **WHEN** each summary section is independently made to fail, including a corrupt status-query source
- **THEN** only that slot exposes its stable error and all unaffected sections remain readable

#### Scenario: Lookup and length error matrix
- **WHEN** requests target an absent object, an existing object of the wrong kind, a 2000-character recall query, or a 2001-character recall query
- **THEN** they respectively receive 404 object_not_found, 404 kind_mismatch, valid recall, and 400 query_too_long with no recall execution for the oversized request

### Requirement: Shared runtime presentation without polling
The frontend SHALL provide GmEntityLink, collapsible GmJsonTree, GmFilterBar and GmPager. GmJsonTree SHALL render $ref links and distinct $unserializable values and SHALL also serve the S2 payload drawer while preserving its attempt/message/error/copy behavior. Entity pages SHALL show name/identifiers above 概要 and 原始資料 tabs, with NPC 記憶 and 對話 tabs. Runtime pages SHALL offer manual refresh and SHALL NOT auto-poll. The separate GM bundle, token-only game imports, Traditional Chinese UI, and verbatim monospace identifiers SHALL remain unchanged.

#### Scenario: Shared JSON and manual freshness
- **WHEN** runtime pages mount, remain open, refresh manually, or display raw/S2 payload JSON
- **THEN** no polling timer is created, manual refresh reloads data, and both JSON surfaces share linked-reference/unserializable rendering without regressing S2 drawer behavior

### Requirement: Two-layer immutable inspection acceptance
Reader acceptance SHALL include one fixed-fixture EvenniaTest module per reader, output-shape checks, and an AST contract over web/gm/readers forbidding save/create/delete/update calls, assignments to db fields or Attribute properties, and imports of known writers. Runtime acceptance SHALL read every entity kind and assert unchanged Attribute counts and row counts for every narrative table; missing-Attribute fixtures SHALL exercise indirect autocreation risks. Tests SHALL establish disguise separation and authoritative recall equivalence with no writes. Vitest SHALL cover entity-link routing and JSON markers; new components SHALL have Storybook coverage. Every new Python test module SHALL be registered in .github/evennia-shards.json, and requirement coverage SHALL follow canonical repository traceability annotations.

#### Scenario: Static and indirect-write defense
- **WHEN** forbidden writer syntax is introduced or a read helper autocreates an Attribute/narrative row in a fixture
- **THEN** the respective static/runtime contract fails rather than masking or rolling back the write to pass the assertion

#### Scenario: Complete delivery evidence
- **WHEN** S3 acceptance runs
- **THEN** all readers, API/error cases, disguise/recall invariants, frontend marker/link behavior, component stories, shard ownership and substantive requirement annotations are covered

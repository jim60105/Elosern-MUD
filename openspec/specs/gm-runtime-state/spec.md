# gm-runtime-state Specification

## Purpose
Provide privileged read-only inspection of persistent game entities and NPC narrative state, linked to retained operational evidence without altering the inspected world.

## Requirements

### Requirement: Protected read-only inspection boundary

All runtime inspection APIs SHALL reuse the existing Developer/superuser authorization, JSON envelope, same-origin fetch boundary, request/denial facade events, and resolver access-coverage contract. Inspection SHALL never mutate persistent state, autocreate Attributes, repair data, call narrative writers, or recompute rules independently of authoritative read models.

#### Scenario: Authorized immutable inspection
- **WHEN** anonymous, ordinary, Developer, and superuser accounts request runtime inspection
- **THEN** authorization and logging match the landed portal contract, permitted responses reflect authoritative read data, and all inspected persistent state remains unchanged

#### Scenario: Missing stored defaults
- **WHEN** a permitted inspection reads an entity missing an autocreating property's stored Attribute
- **THEN** the response uses a non-creating read/default or localized error and creates no Attribute

#### Scenario: Console write exception stays outside readers
- **WHEN** a permitted operator POSTs a raw batch to the object raw URL and subsequently GETs it or requests recall
- **THEN** only the POST invokes the server raw boundary through the console gate, and readers, GET and recall remain immutable under existing AST/runtime contracts

#### Scenario: Unauthenticated and forbidden callers
- **WHEN** anonymous or ordinary accounts request runtime inspection
- **THEN** they receive the existing 401 unauthenticated and 403 forbidden responses

#### Scenario: Narrative permissions remain enforced
- **WHEN** an authorized inspection reads narrative state
- **THEN** narrative knowledge-scope and thread permissions remain enforced

#### Scenario: Raw-edit POST follows the console spec
- **WHEN** the separately dispatched raw-edit POST is served at the existing raw URL
- **THEN** it follows gm-developer-console, and this write capability authorizes no mutations in any inspection reader, GET or recall path

### Requirement: Runtime API routes and bounded lists

The portal SHALL expose GET `/gm/api/state/<kind>?cursor=&limit=&<filters>`, GET `/gm/api/state/<kind>/<id>`, GET `/gm/api/state/object/<dbref>/raw`, GET `/gm/api/state/search?q=`, and POST `/gm/api/state/npc/<dbref>/recall`. Lists SHALL return summary-only `items` and opaque `next_cursor` or null using the existing envelope; limit SHALL default to 50 and never exceed 200.

#### Scenario: Filtered pagination
- **WHEN** an operator follows successive cursors for a filtered entity list
- **THEN** pages have stable ordering, preserve filters, contain only summary fields, respect default/maximum limits, and terminate with null next_cursor

#### Scenario: Recall CSRF
- **WHEN** an authorized recall POST lacks a valid CSRF token
- **THEN** the existing csrf_failed transport error is returned and no recall or persistent write occurs

#### Scenario: Raw URL method dispatch
- **WHEN** the same existing object raw URL receives GET, protected valid-CSRF POST or an unsupported method
- **THEN** GET retains S3 serialization/lookup behavior, POST uses the console snapshot/raw-write contract and console errors, and unsupported methods receive the existing method_not_allowed envelope

#### Scenario: Raw URL accepts console POST batches
- **WHEN** the existing object raw URL receives a protected POST raw batch through gm-developer-console
- **THEN** the batch is accepted and its GET payload and lookup errors remain unchanged

#### Scenario: Indexed ordering and filter backing
- **WHEN** a list is ordered or filtered
- **THEN** stable ordering and filters use indexed narrative fields and Evennia typeclass paths/tags

#### Scenario: Supported filter dimensions
- **WHEN** an operator applies list filters
- **THEN** filters support NPC location, monster species/region, and memory tier/availability/category/knowledge scope

#### Scenario: Recall POST keeps CSRF protection
- **WHEN** a recall POST is processed
- **THEN** CSRF protection is retained even though the recall makes no writes

### Requirement: Complete curated entity summaries
Each entity page SHALL offer a curated summary and a raw representation. Curated summaries SHALL include the kind-specific fields stated in the scenarios below.
Stored truth and `disguised_stats` SHALL be shown side by side; disguise SHALL be labelled 僅顯示用 and SHALL never replace or merge into true traits. Currency SHALL remain integer-based. Missing or failed sources SHALL not be fabricated.

#### Scenario: Entity inventory coverage
- **WHEN** fixed fixtures for every listed kind and narrative subtype are inspected
- **THEN** each curated summary exposes all applicable named fields and real relationships, including generated payload and available art thumbnail

#### Scenario: Disguised character and NPC
- **WHEN** a character or NPC has disguise values different from true traits
- **THEN** both are independently emitted and rendered side by side, the disguise is labelled display-only, and breakdowns retain true values

#### Scenario: Accounts summary fields
- **WHEN** an account curated summary is rendered
- **THEN** it includes name, permissions, created/last-login dates, live sessions, owned characters

#### Scenario: Player character summary fields
- **WHEN** a player character curated summary is rendered
- **THEN** it includes race/subrace/sex/age/apparent age; true traits; separate displayed disguise; per-trait base → skills → equipment → conditions breakdown; gauges, conditions/buffs, skills/lineage, equipment/inventory, integer-copper wallet and derived gold/silver/copper display, guild rank/merit, titles, affinity, party/possession, sexual state, and current room

#### Scenario: NPC summary fields
- **WHEN** an NPC curated summary is rendered
- **THEN** it includes character fields plus title/profession, shop/guild service components, seven-section persona and version, today's schedule/current slot, dialogue key, memory and dialogue tabs

#### Scenario: Monster summary fields
- **WHEN** a monster curated summary is rendered
- **THEN** it includes species/variant/threat tier, approved-profile or interim numeric source, owning site or ambient placement, loot table, behaviour profile, and the shared resource, condition, and true-trait sections read through the authoritative status/character read model

#### Scenario: A monster with sanctioned zero-maximum gauges renders its shared sections
- **WHEN** a monster whose numeric source carries a zero MP/SP maximum (an approved-profile or tier-band zero) is rendered
- **THEN** its resource, condition, and trait sections render from the stored state — the zero gauge shown as its stored value over a zero maximum — rather than degrading those sections to their unavailable form

#### Scenario: Room summary fields
- **WHEN** a room curated summary is rendered
- **THEN** it includes coordinates/map, place kind, exits, occupants grouped by kind, instance ownership/lifetime

#### Scenario: Quest record summary fields
- **WHEN** a quest record curated summary is rendered
- **THEN** it includes definition key, issuer, status/stage, progress counters, bound targets, deadline, rewards, failure reason, owning character; generated quests also show stored payload

#### Scenario: Narrative summary fields
- **WHEN** a narrative curated summary is rendered
- **THEN** it includes event content/participants/location/visibility; thread status/links/revisions; letter exchanges/state/reply work; dream sessions/exchanges; director decisions/scheduled beats; authoring drafts/creative requests

#### Scenario: Art asset summary fields
- **WHEN** an art asset curated summary is rendered
- **THEN** it includes subject key, status, prompt summary, source_hash, generated time, failure reason, and existing `/art/` thumbnail only when a file exists

### Requirement: Universal Evennia raw inspection
Every Evennia object, including objects outside curated kinds, SHALL have a raw tab/route showing all Attributes with key/category/converted value, categorized tags, components, typeclass path, location, and creation date.

#### Scenario: Arbitrary object and non-JSON values
- **WHEN** a non-curated Evennia object contains categorized Attributes/tags, object references, and an unconvertible value
- **THEN** its complete raw inventory is visible, references are linked, unconvertible values are distinct with bounded repr, and the remaining data renders normally

#### Scenario: Object reference serialization
- **WHEN** a raw payload contains an object reference
- **THEN** it serializes as `{"$ref":"#123","typeclass":"…","key":"…"}`

#### Scenario: Unconvertible value serialization
- **WHEN** a raw payload contains an unconvertible value
- **THEN** it serializes as `{"$unserializable":"<type name>","repr":"<repr truncated to 200 chars>"}` and does not prevent inspection of other values

#### Scenario: Non-Evennia records as raw data
- **WHEN** a non-Evennia record is inspected through a raw view
- **THEN** it exposes its stored record fields as raw data without pretending they have Evennia Attributes

### Requirement: Runtime navigation search and cross-links
The runtime navigation tree SHALL enable search, accounts, player characters, NPCs, monsters, rooms, runtime/generated quests, narrative records, and art assets. Global search SHALL jump to an exact #dbref; other text SHALL match object key, quest id, then source_id in that precedence.

#### Scenario: Search precedence and links
- **WHEN** an operator searches an exact dbref or text matching object keys, quest ids and source ids, and follows a relationship identifier
- **THEN** dbref opens its object, text results retain the required precedence, and relationship/source/call links reach the correct existing target

#### Scenario: Identifier cross-links
- **WHEN** a page displays an identifier
- **THEN** it links to its corresponding entity, source event, or retained S2 call drawer, including room, quests, memories, letters, party members, possession partner, memory source_id and available call_id

#### Scenario: Call identifiers reuse the transcript detail contract
- **WHEN** a call identifier is rendered
- **THEN** it uses the existing transcript detail contract rather than a new transcript search backend

### Requirement: NPC memory and dialogue inspection
The NPC memory tab SHALL show filtered memory content, salience, confidence, subjects, linked source_id, effective tier/availability, and complete expandable revision history including availability/tier/decay metadata/supersedes. Recall SHALL use the NPC as owner and requester and return the same core/working/lexical selections and BM25 scores as the authoritative read-only recall query, plus current owner memory generation.

#### Scenario: Memory history and recall equivalence
- **WHEN** a permitted operator filters memories, expands a revision history and requests recall with thread and inclusion toggles
- **THEN** effective fields and full history are visible, recall selections/scores/generation equal a direct authoritative call under the same NPC permissions, and no persistent rows or Attributes change

#### Scenario: Existing narrative evidence only
- **WHEN** more than ten snapshots and dialogue frames for multiple players exist
- **THEN** the memory tab shows only the newest ten snapshots with available evidence links, dialogue groups epochs/frames by player, and viewing either tab produces no new dialogue context or correspondence settlement

#### Scenario: Recall input bounds
- **WHEN** an operator submits a recall request
- **THEN** the input accepts query text up to 2000 characters, an optional thread, and include-superseded and include-inactive toggles

#### Scenario: Context snapshot evidence detail
- **WHEN** the newest ten context snapshots are displayed
- **THEN** they show sections, token accounting, truncated/rejected sources and available trace_id/call_id links to S2 evidence

#### Scenario: Dialogue prompt preview performs no side effects
- **WHEN** a full dialogue prompt preview is shown
- **THEN** it does not assemble new context, persist snapshots/epochs/frames, or settle correspondence

### Requirement: Independent failures and precise lookup errors
Each curated summary section SHALL compute independently. A failed section SHALL carry `{"error":{"code":"<snake_case>","message":"<zh-TW>"}}` in its own slot while unaffected sections render in the success envelope. Errors SHALL remain visible diagnostic evidence and clients SHALL branch on codes only.

#### Scenario: Corrupt section isolation
- **WHEN** each summary section is independently made to fail, including a corrupt status-query source
- **THEN** only that slot exposes its stable error and all unaffected sections remain readable

#### Scenario: A sanctioned zero-maximum gauge is not a section failure
- **WHEN** a monster summary's shared sections read a gauge whose maximum is a sanctioned zero
- **THEN** no section slot carries an error and none reports `source_unavailable` for that reason

#### Scenario: A negative-maximum gauge still fails its sections closed
- **WHEN** a stored gauge's modifiers compute to a negative maximum
- **THEN** each section routed through the status/character read model carries its stable error while unaffected sections remain readable

#### Scenario: Lookup and length error matrix
- **WHEN** requests target an absent object, an existing object of the wrong kind, a 2000-character recall query, or a 2001-character recall query
- **THEN** they respectively receive 404 object_not_found, 404 kind_mismatch, valid recall, and 400 query_too_long with no recall execution for the oversized request

#### Scenario: Unknown object lookup error
- **WHEN** a request targets an unknown object
- **THEN** the API returns HTTP 404 object_not_found

#### Scenario: Kind mismatch lookup error
- **WHEN** a requested object is incompatible with the requested kind
- **THEN** the API returns HTTP 404 kind_mismatch

#### Scenario: Oversized recall query rejected before execution
- **WHEN** recall query text exceeds 2000 characters
- **THEN** the API returns HTTP 400 query_too_long before recall execution

### Requirement: Shared runtime presentation without polling
The frontend SHALL provide GmEntityLink, collapsible GmJsonTree, GmFilterBar and GmPager. Entity pages SHALL show name/identifiers above 概要 and 原始資料 tabs, with NPC 記憶 and 對話 tabs. Runtime pages SHALL offer manual refresh and SHALL NOT auto-poll.

#### Scenario: Shared JSON and manual freshness
- **WHEN** runtime pages mount, remain open, refresh manually, or display raw/S2 payload JSON
- **THEN** no polling timer is created, manual refresh reloads data, and both JSON surfaces share linked-reference/unserializable rendering without regressing S2 drawer behavior

#### Scenario: GmJsonTree serves the S2 drawer
- **WHEN** the S2 payload drawer renders JSON
- **THEN** GmJsonTree renders $ref links and distinct $unserializable values there while preserving the drawer's attempt/message/error/copy behavior

#### Scenario: Existing frontend conventions unchanged
- **WHEN** runtime frontend pages are delivered
- **THEN** the separate GM bundle, token-only game imports, Traditional Chinese UI, and verbatim monospace identifiers remain unchanged

### Requirement: Two-layer immutable inspection acceptance
Reader acceptance SHALL include one fixed-fixture EvenniaTest module per reader, output-shape checks, and an AST contract over web/gm/readers forbidding save/create/delete/update calls, assignments to db fields or Attribute properties, and imports of known writers. Runtime acceptance SHALL read every entity kind and assert unchanged Attribute counts and row counts for every narrative table.

#### Scenario: Static and indirect-write defense
- **WHEN** forbidden writer syntax is introduced or a read helper autocreates an Attribute/narrative row in a fixture
- **THEN** the respective static/runtime contract fails rather than masking or rolling back the write to pass the assertion

#### Scenario: Complete delivery evidence
- **WHEN** S3 acceptance runs
- **THEN** all readers, API/error cases, disguise/recall invariants, frontend marker/link behavior, component stories, shard ownership and substantive requirement annotations are covered

#### Scenario: Indirect autocreation fixtures
- **WHEN** runtime acceptance fixtures are authored
- **THEN** missing-Attribute fixtures exercise indirect autocreation risks

#### Scenario: Invariant tests without writes
- **WHEN** reader tests establish disguise separation and authoritative recall equivalence
- **THEN** they do so with no writes

#### Scenario: Frontend test and story coverage
- **WHEN** frontend components ship
- **THEN** Vitest covers entity-link routing and JSON markers, and new components have Storybook coverage

#### Scenario: Shard registration and traceability
- **WHEN** a new Python test module is added
- **THEN** it is registered in .github/evennia-shards.json, and requirement coverage follows canonical repository traceability annotations

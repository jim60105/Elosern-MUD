## MODIFIED Requirements

### Requirement: Protected read-only inspection boundary

All runtime inspection APIs SHALL reuse the existing Developer/superuser authorization, JSON envelope, same-origin fetch boundary, request/denial facade events, and resolver access-coverage contract. Anonymous and ordinary accounts SHALL receive existing 401 unauthenticated and 403 forbidden responses. Inspection SHALL never mutate persistent state, autocreate Attributes, repair data, call narrative writers, or recompute rules independently of authoritative read models. Narrative knowledge-scope and thread permissions SHALL remain enforced. The separately dispatched raw-edit POST at the existing raw URL SHALL follow gm-developer-console; this write capability SHALL NOT authorize mutations in any inspection reader, GET or recall path.

#### Scenario: Authorized immutable inspection
- **WHEN** anonymous, ordinary, Developer, and superuser accounts request runtime inspection
- **THEN** authorization and logging match the landed portal contract, permitted responses reflect authoritative read data, and all inspected persistent state remains unchanged

#### Scenario: Missing stored defaults
- **WHEN** a permitted inspection reads an entity missing an autocreating property's stored Attribute
- **THEN** the response uses a non-creating read/default or localized error and creates no Attribute

#### Scenario: Console write exception stays outside readers
- **WHEN** a permitted operator POSTs a raw batch to the object raw URL and subsequently GETs it or requests recall
- **THEN** only the POST invokes the server raw boundary through the console gate, and readers, GET and recall remain immutable under existing AST/runtime contracts

### Requirement: Runtime API routes and bounded lists

The portal SHALL expose GET `/gm/api/state/<kind>?cursor=&limit=&<filters>`, GET `/gm/api/state/<kind>/<id>`, GET `/gm/api/state/object/<dbref>/raw`, GET `/gm/api/state/search?q=`, and POST `/gm/api/state/npc/<dbref>/recall`. The existing object raw URL SHALL additionally accept protected POST raw batches through gm-developer-console, with its GET payload and lookup errors unchanged. Lists SHALL return summary-only `items` and opaque `next_cursor` or null using the existing envelope; limit SHALL default to 50 and never exceed 200. Stable ordering and filters SHALL use indexed narrative fields and Evennia typeclass paths/tags. Filters SHALL support NPC location, monster species/region, and memory tier/availability/category/knowledge scope. Recall POST SHALL retain CSRF protection despite making no writes.

#### Scenario: Filtered pagination
- **WHEN** an operator follows successive cursors for a filtered entity list
- **THEN** pages have stable ordering, preserve filters, contain only summary fields, respect default/maximum limits, and terminate with null next_cursor

#### Scenario: Recall CSRF
- **WHEN** an authorized recall POST lacks a valid CSRF token
- **THEN** the existing csrf_failed transport error is returned and no recall or persistent write occurs

#### Scenario: Raw URL method dispatch
- **WHEN** the same existing object raw URL receives GET, protected valid-CSRF POST or an unsupported method
- **THEN** GET retains S3 serialization/lookup behavior, POST uses the console snapshot/raw-write contract and console errors, and unsupported methods receive the existing method_not_allowed envelope

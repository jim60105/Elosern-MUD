# gm-world-data Specification

## Purpose
Let authorized operators inspect loaded authored entries and their relationships, safely view source YAML, and reload the in-memory prompt library.

## Requirements

### Requirement: Protected immutable offline boundary
Every S4 page and API SHALL require an authenticated account whose check_permstring("Developer") succeeds, including superusers. Readers SHALL obey the existing S3 read-only AST contract. No web/gm path SHALL mutate persistent state or write source files; authored entries SHALL remain immutable.

#### Scenario: Authorization and no writes
- **WHEN** anonymous, ordinary, Developer, and superuser accounts request S4 pages and each API
- **THEN** access matches the stated matrix, authorized reads leave source bytes, registries, persistent rows and Attributes unchanged, and reader AST protection applies

#### Scenario: Offline authoring inspection
- **WHEN** LLM and SD services are unavailable
- **THEN** registry browsing, source viewing and local prompt reload remain usable without external requests

#### Scenario: Anonymous and forbidden response matrix
- **WHEN** anonymous users request S4 pages or APIs, or authenticated non-Developers request them
- **THEN** anonymous pages redirect to LOGIN_URL with next
- **AND** anonymous APIs return 401 unauthenticated and authenticated non-Developers receive 403 forbidden

#### Scenario: Prompt reload is the only S4 action
- **WHEN** any S4 action is performed
- **THEN** prompt reload is the only action, and it only changes the in-memory prompt library

#### Scenario: Project-origin serving with services offline
- **WHEN** LLM and SD are offline
- **THEN** all surfaces remain usable and are served from the project origin without service calls

### Requirement: Registry API envelope search and pagination
S4 SHALL expose GET /gm/api/registry/ for inventory and, with q, cross-registry search; GET /gm/api/registry/<registry>?cursor=&limit=&q= for entries; and GET /gm/api/registry/<registry>/<key> for detail. Entry lists SHALL use the existing success envelope with items and opaque next_cursor or null.

#### Scenario: Loaded inventory and filtered pages
- **WHEN** a Developer browses inventory and follows cursors for a searched registry
- **THEN** inventory metadata reflects loaded data, items remain stably ordered and query-filtered within inherited limits, and the last page has null next_cursor

#### Scenario: Cross-registry nested search and details
- **WHEN** a query matches a key or nested string field and an entry is opened
- **THEN** cross-registry search returns all matches as data.items containing registry/key identities sorted by registry name then key without pagination (an empty array for no matches), and detail exposes all converted fields plus correct forward and inverse relationships

#### Scenario: Registry lookup errors
- **WHEN** a Developer requests an unknown registry or absent key in a known registry
- **THEN** the response respectively has 404 registry_not_found or 404 entry_not_found in the shared failure envelope

#### Scenario: Inventory metadata
- **WHEN** the registry inventory is returned
- **THEN** it includes name, label, group, entry count and source path per registry

#### Scenario: Pagination bounds and query persistence
- **WHEN** entry lists are paginated
- **THEN** key ordering is stable, the default limit is 50 and the maximum 200, and the search query is preserved across pages

#### Scenario: Search runs over loaded indexed entries
- **WHEN** a search is executed
- **THEN** it matches keys and string field values, including nested dataclasses, across loaded indexed entries rather than reimporting source

#### Scenario: Detail completeness and conversion semantics
- **WHEN** an entry detail is returned
- **THEN** it includes every field, references by field path, and referrers grouped by inverse name
- **AND** conversion follows existing authored serialization semantics, including enum values, tuple-to-list and nested dataclasses

#### Scenario: Shared response envelope shapes
- **WHEN** any S4 registry API responds
- **THEN** all successes are {"ok":true,"data":...} and failures are {"ok":false,"error":{"code":"<snake_case>","message":"<zh-TW>"}} with matching status
- **AND** clients branch on code only and retain existing invalid-cursor/limit transport handling

### Requirement: Authored browser and runtime links
World-data navigation SHALL show registries grouped by approved group with label, name, count and source path; /gm/world/<registry> SHALL show searchable/filterable key and summary-field lists. /gm/world/<registry>/<key> SHALL show fields, outgoing references by field and incoming referrers by inverse name.

#### Scenario: Fields and relationships presentation
- **WHEN** an operator opens entries with nested values, no summary configuration, and multiple reference/referrer groups
- **THEN** fallback summaries, every field, clickable reference fields, outgoing references and inverse-grouped referrers render correctly with source provenance and application instructions

#### Scenario: Runtime to authored navigation
- **WHEN** an operator follows a race, species, variant or definition_key from S3
- **THEN** the existing link component opens the correct registry/key detail without changing runtime data or other link kinds

#### Scenario: Summary-field fallback
- **WHEN** an entry list is shown for a registry with no summaries declared
- **THEN** it falls back to the first string field

#### Scenario: Dataclass values and navigable references
- **WHEN** entry pages render dataclass values or declared references
- **THEN** dataclass values use the existing GmJsonTree, and declared references render as navigable links

#### Scenario: Runtime registry-key fields link via GmEntityLink
- **WHEN** S3 runtime pages show registry-key fields, including character race, monster species/variant and quest definition_key
- **THEN** they use GmEntityLink to reach the corresponding authored entry

#### Scenario: Source provenance and editing instructions
- **WHEN** any authored-data page is shown
- **THEN** it discloses repository-relative source paths and explains source editing plus restart for authored changes
- **AND** prompt source pages explain their explicit reload exception

#### Scenario: UI language and identifier rendering
- **WHEN** world-data UI copy or identifiers render
- **THEN** UI copy is Traditional Chinese and identifiers are verbatim monospace

### Requirement: Allowlisted source text
GET /gm/api/sources/ SHALL return an allowlist built at request time from world/rules/rulebook/*.yaml including commerce/ and prompts/*.yaml. Names SHALL uniquely identify files across both roots.

#### Scenario: Source listing and provenance
- **WHEN** a valid YAML file is added in an allowed directory and the source list is requested again
- **THEN** it appears without a process restart, opens as read-only line-numbered text, and its path/disk-content provenance is visible

#### Scenario: Source escape attempts
- **WHEN** a request names an unlisted file, ../ traversal, encoded traversal, an absolute path or an escaping symlink
- **THEN** it receives 404 source_not_found in the failure envelope and no outside file is read

#### Scenario: Single-source read and rendering
- **WHEN** GET /gm/api/sources/<name> is requested for an allowlisted file
- **THEN** it returns only that file's text and repository-relative source path
- **AND** /gm/world/sources/<name> shows read-only monospace line-numbered text

#### Scenario: Escape rejection
- **WHEN** a request uses arbitrary paths, traversal (including encoded traversal), absolute paths, or symlinks escaping the approved roots
- **THEN** it is rejected with 404 source_not_found

#### Scenario: Disk-content provenance
- **WHEN** source text is displayed
- **THEN** it is explicitly disk content, not a claim that loaded registry values have changed

### Requirement: CSRF-protected prompt reload and diagnostics
POST /gm/api/sources/prompts/reload SHALL require the existing Django CSRF token sent as X-CSRFToken. Reload SHALL reset then load through the authoritative prompt loader, rereading prompts into memory only.

#### Scenario: Reload success and failure
- **WHEN** a Developer submits valid-CSRF reload for valid then invalid prompt fixtures
- **THEN** reset precedes load, diagnostics show each outcome, game prompt behavior matches the loader's own result, and no source or persistent world state changes

#### Scenario: Reload transport protection
- **WHEN** reload is requested without valid CSRF or through GET
- **THEN** CSRF failures use the inherited csrf_failed response, unsupported methods use the inherited method error, and neither resets or loads the library

#### Scenario: Reload offered with diagnostics
- **WHEN** the prompt source view is shown
- **THEN** it offers reload and displays returned load diagnostics

#### Scenario: Failed loads preserve loader semantics
- **WHEN** a prompt reload fails
- **THEN** diagnostics remain visible and the loader's startup failure semantics are preserved exactly, without an invented rollback or fallback

#### Scenario: CSRF failure skips the loader
- **WHEN** CSRF is missing or invalid
- **THEN** the existing csrf_failed envelope is returned and the loader is not invoked

#### Scenario: GET never reloads prompts
- **WHEN** any GET request is made
- **THEN** it does not reload prompts

### Requirement: Facade observability and isolated delivery
All S4 APIs SHALL retain gm_request with account/route/status and denials SHALL retain gm_denied. Prompt reload SHALL emit gm_prompts_reloaded with outcome and gm_action with operator account, action/target identifiers and outcome in context, through the world.observability facade; diagnostics SHALL NOT leak credentials to logs. There SHALL be no audit model.

#### Scenario: Reload event evidence
- **WHEN** reload succeeds or fails and an unauthorized request is denied
- **THEN** the facade records reload outcome/action context, request account/route/status, and denial account/route without source prose or credentials in log context

#### Scenario: Complete isolated acceptance
- **WHEN** S4 implementation is verified
- **THEN** focused backend/frontend contracts and stories, shard ownership, substantive traceability and GM import-boundary checks pass without altering the game bundle, frozen contracts or OOB behavior

#### Scenario: GM bundle stays isolated
- **WHEN** the GM bundle is built
- **THEN** it remains separate, importing only game tokens.css and fonts*.css
- **AND** game frozen contracts, .elosern-root styles and OOB protocol remain untouched

#### Scenario: Acceptance coverage
- **WHEN** S4 acceptance is defined
- **THEN** it covers registry contracts, API shapes/search/pagination/errors/access/CSRF/source traversal, unchanged state, field/reference/referrer and runtime-link Vitest behavior, and Storybook stories for new components

#### Scenario: Shard ownership and traceability
- **WHEN** S4 code and data contracts ship
- **THEN** new Python modules have exact shard ownership, shipped-data contracts follow the existing data-contract tagging/manifest convention, and every new requirement has substantive traceability coverage at implementation/archive

# gm-world-data Specification

## Purpose
Let authorized operators inspect loaded authored entries and their relationships, safely view source YAML, and reload the in-memory prompt library.

## Requirements

### Requirement: Protected immutable offline boundary
Every S4 page and API SHALL require an authenticated account whose check_permstring("Developer") succeeds, including superusers. Anonymous pages SHALL redirect to LOGIN_URL with next; anonymous APIs SHALL return 401 unauthenticated and authenticated non-Developers SHALL receive 403 forbidden. Readers SHALL obey the existing S3 read-only AST contract. No web/gm path SHALL mutate persistent state or write source files; authored entries SHALL remain immutable. Prompt reload SHALL be the only S4 action and SHALL only change the in-memory prompt library. All surfaces SHALL remain usable with LLM and SD offline, served from the project origin without service calls.

#### Scenario: Authorization and no writes
- **WHEN** anonymous, ordinary, Developer, and superuser accounts request S4 pages and each API
- **THEN** access matches the stated matrix, authorized reads leave source bytes, registries, persistent rows and Attributes unchanged, and reader AST protection applies

#### Scenario: Offline authoring inspection
- **WHEN** LLM and SD services are unavailable
- **THEN** registry browsing, source viewing and local prompt reload remain usable without external requests

### Requirement: Registry API envelope search and pagination
S4 SHALL expose GET /gm/api/registry/ for inventory and, with q, cross-registry search; GET /gm/api/registry/<registry>?cursor=&limit=&q= for entries; and GET /gm/api/registry/<registry>/<key> for detail. Inventory SHALL include name, label, group, entry count and source path. Entry lists SHALL use the existing success envelope with items and opaque next_cursor or null, stable key ordering, default limit 50 and maximum 200, and preserve the search query across pages. Search SHALL match keys and string field values, including nested dataclasses, across loaded indexed entries rather than reimporting source. Details SHALL include every field, references by field path, and referrers grouped by inverse name. Conversion SHALL follow existing authored serialization semantics, including enum values, tuple-to-list and nested dataclasses. Unknown registries SHALL return 404 registry_not_found, unknown keys 404 entry_not_found. All successes SHALL be {"ok":true,"data":...}; failures SHALL be {"ok":false,"error":{"code":"<snake_case>","message":"<zh-TW>"}} with matching status; clients SHALL branch on code only and retain existing invalid-cursor/limit transport handling.

#### Scenario: Loaded inventory and filtered pages
- **WHEN** a Developer browses inventory and follows cursors for a searched registry
- **THEN** inventory metadata reflects loaded data, items remain stably ordered and query-filtered within inherited limits, and the last page has null next_cursor

#### Scenario: Cross-registry nested search and details
- **WHEN** a query matches a key or nested string field and an entry is opened
- **THEN** cross-registry search returns all matches as data.items containing registry/key identities sorted by registry name then key without pagination (an empty array for no matches), and detail exposes all converted fields plus correct forward and inverse relationships

#### Scenario: Registry lookup errors
- **WHEN** a Developer requests an unknown registry or absent key in a known registry
- **THEN** the response respectively has 404 registry_not_found or 404 entry_not_found in the shared failure envelope

### Requirement: Authored browser and runtime links
World-data navigation SHALL show registries grouped by approved group with label, name, count and source path; /gm/world/<registry> SHALL show searchable/filterable key and summary-field lists, falling back to the first string field when no summaries are declared. /gm/world/<registry>/<key> SHALL show fields, outgoing references by field and incoming referrers by inverse name. Dataclass values SHALL use the existing GmJsonTree, and declared references SHALL render as navigable links. S3 runtime registry-key fields, including character race, monster species/variant and quest definition_key, SHALL use GmEntityLink to reach the corresponding authored entry. Each page SHALL disclose repository-relative source paths and explain source editing plus restart for authored changes; prompt source pages SHALL explain their explicit reload exception. UI copy SHALL be Traditional Chinese and identifiers verbatim monospace.

#### Scenario: Fields and relationships presentation
- **WHEN** an operator opens entries with nested values, no summary configuration, and multiple reference/referrer groups
- **THEN** fallback summaries, every field, clickable reference fields, outgoing references and inverse-grouped referrers render correctly with source provenance and application instructions

#### Scenario: Runtime to authored navigation
- **WHEN** an operator follows a race, species, variant or definition_key from S3
- **THEN** the existing link component opens the correct registry/key detail without changing runtime data or other link kinds

### Requirement: Allowlisted source text
GET /gm/api/sources/ SHALL return an allowlist built at request time from world/rules/rulebook/*.yaml including commerce/ and prompts/*.yaml. GET /gm/api/sources/<name> SHALL return only an allowlisted file's text and repository-relative source path. /gm/world/sources/<name> SHALL show read-only monospace line-numbered text. Names SHALL uniquely identify files across both roots. Arbitrary paths, traversal (including encoded traversal), absolute paths, and symlinks escaping the approved roots SHALL be rejected with 404 source_not_found. Source text SHALL be explicitly disk content, not a claim that loaded registry values have changed.

#### Scenario: Source listing and provenance
- **WHEN** a valid YAML file is added in an allowed directory and the source list is requested again
- **THEN** it appears without a process restart, opens as read-only line-numbered text, and its path/disk-content provenance is visible

#### Scenario: Source escape attempts
- **WHEN** a request names an unlisted file, ../ traversal, encoded traversal, an absolute path or an escaping symlink
- **THEN** it receives 404 source_not_found in the failure envelope and no outside file is read

### Requirement: CSRF-protected prompt reload and diagnostics
POST /gm/api/sources/prompts/reload SHALL require the existing Django CSRF token sent as X-CSRFToken. The prompt source view SHALL offer reload and display returned load diagnostics. Reload SHALL reset then load through the authoritative prompt loader, rereading prompts into memory only. Failed loads SHALL leave diagnostics visible and preserve exactly the loader's startup failure semantics, without an invented rollback or fallback. Missing/invalid CSRF SHALL return the existing csrf_failed envelope and SHALL NOT invoke the loader. No GET SHALL reload prompts.

#### Scenario: Reload success and failure
- **WHEN** a Developer submits valid-CSRF reload for valid then invalid prompt fixtures
- **THEN** reset precedes load, diagnostics show each outcome, game prompt behavior matches the loader's own result, and no source or persistent world state changes

#### Scenario: Reload transport protection
- **WHEN** reload is requested without valid CSRF or through GET
- **THEN** CSRF failures use the inherited csrf_failed response, unsupported methods use the inherited method error, and neither resets or loads the library

### Requirement: Facade observability and isolated delivery
All S4 APIs SHALL retain gm_request with account/route/status and denials SHALL retain gm_denied. Prompt reload SHALL emit gm_prompts_reloaded with outcome and gm_action with operator account, action/target identifiers and outcome in context, through the world.observability facade; diagnostics SHALL NOT leak credentials to logs. There SHALL be no audit model. The GM bundle SHALL remain separate, importing only game tokens.css and fonts*.css; game frozen contracts, .elosern-root styles and OOB protocol SHALL remain untouched. Acceptance SHALL cover registry contracts, API shapes/search/pagination/errors/access/CSRF/source traversal, unchanged state, field/reference/referrer and runtime-link Vitest behavior, and Storybook stories for new components. New Python modules SHALL have exact shard ownership; shipped-data contracts SHALL follow the existing data-contract tagging/manifest convention, and every new requirement SHALL have substantive traceability coverage at implementation/archive.

#### Scenario: Reload event evidence
- **WHEN** reload succeeds or fails and an unauthorized request is denied
- **THEN** the facade records reload outcome/action context, request account/route/status, and denial account/route without source prose or credentials in log context

#### Scenario: Complete isolated acceptance
- **WHEN** S4 implementation is verified
- **THEN** focused backend/frontend contracts and stories, shard ownership, substantive traceability and GM import-boundary checks pass without altering the game bundle, frozen contracts or OOB behavior

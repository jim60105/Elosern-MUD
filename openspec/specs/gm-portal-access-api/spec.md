## Purpose

Provide a Developer-only GM portal entry and a minimal read-only API with consistent transport and operational logging, isolated from the player interface.

## Requirements

### Requirement: Protected GM namespace
Every page and API request under /gm/ MUST require an authenticated account whose check_permstring("Developer") passes; superusers MUST pass. Anonymous pages SHALL redirect to LOGIN_URL with next; unauthorized authenticated pages SHALL return 403. Anonymous APIs SHALL return 401 unauthenticated; unauthorized authenticated APIs SHALL return 403 forbidden in error envelopes. All resolved views, including new dashboard/detail and fallback routes, MUST be covered by the access wrapper.

#### Scenario: Anonymous page access
- **WHEN** an anonymous visitor requests a GM page
- **THEN** login redirects preserve the requested path

#### Scenario: Ordinary account denied
- **WHEN** an authenticated ordinary account requests GM pages or session, dashboard or detail APIs
- **THEN** pages return 403 and APIs return the 403 forbidden envelope

#### Scenario: Anonymous API denied
- **WHEN** an anonymous visitor requests session, dashboard, detail or an unknown GM API
- **THEN** it receives the 401 unauthenticated envelope rather than a redirect or shell

#### Scenario: Privileged access
- **WHEN** anonymous, ordinary, Developer and superuser accounts request session, dashboard or detail
- **THEN** anonymous requests return 401, ordinary requests return 403, and privileged requests reach the endpoint independently of staff status

#### Scenario: URL coverage regression
- **WHEN** a GM URL is registered without the access wrapper
- **THEN** the resolver coverage test fails, including fallback routes

### Requirement: S1 route and payload scope
The GM API SHALL expose GET /gm/api/session, GET /gm/api/dashboard and GET /gm/api/llm/calls/<call_id>. Session SHALL retain account name, permission level, server time and game version. Dashboard SHALL fold Django responsiveness and real read-only database health into its process section and provide the operations snapshot specified by gm-operations-dashboard. /gm/ and non-API history paths SHALL serve the shell; unknown APIs SHALL return JSON 404, never the shell.

#### Scenario: Operator session
- **WHEN** a permitted account requests session
- **THEN** its success envelope retains actual identity, permission, time and version

#### Scenario: Minimal health
- **WHEN** a permitted account requests dashboard with a readable database
- **THEN** process reports Django responding and database readable without LLM probes or state changes

#### Scenario: Unreadable database
- **WHEN** a permitted account requests dashboard with readable or unreadable database
- **THEN** process health reports the real result, with a section error on failure and other sections preserved

#### Scenario: History routing and API miss
- **WHEN** a permitted account requests /gm/api/health or a non-API history path
- **THEN** health returns the protected JSON 404 envelope and the history path serves the SPA shell

#### Scenario: Health route fully removed
- **WHEN** the former /gm/api/health route is examined after S1
- **THEN** it is removed without alias or compatibility handler

#### Scenario: Route prerequisites
- **WHEN** the S1 routes are landed
- **THEN** they require the landed S1 access/envelope foundation and S2a transcript contract

### Requirement: Consistent JSON transport
Success responses SHALL use `{"ok":true,"data":<payload>}`; failures SHALL use `{"ok":false,"error":{"code":"<snake_case>","message":"<zh-TW>"}}` with the matching HTTP status. Clients SHALL branch on codes rather than messages. The pagination convention SHALL be `cursor=<opaque>&limit=<n>` and data `{"items":[...],"next_cursor":<opaque|null>}`.

#### Scenario: Transport envelope
- **WHEN** either S1 API succeeds or GM transport returns an authentication, authorization, or not-found failure
- **THEN** its JSON body follows the corresponding envelope and its HTTP status matches the outcome

#### Scenario: CSRF contract without production writes
- **WHEN** a permitted operator loads the shell and a test-only protected POST view is exercised with CSRF checks enabled
- **THEN** the shell supplies the CSRF cookie, missing/invalid tokens return HTTP 403 with a `csrf_failed` JSON error envelope and zh-TW message, each rejection emits exactly one `gm_request` with the final status, and the POST with the matching token succeeds without exposing a production S1 write route

#### Scenario: Anonymous test POST
- **WHEN** an anonymous visitor requests the test-only GM POST view with or without a CSRF token
- **THEN** authentication takes precedence and returns the HTTP 401 `unauthenticated` envelope, with one `gm_request` and the access-denial event

#### Scenario: No paginated endpoint in S1
- **WHEN** the S1 API surface is enumerated
- **THEN** S1 adds no paginated endpoint, only the pagination convention above

#### Scenario: Writes are POST with CSRF, none in production
- **WHEN** a state-changing request is made or the S1 surface is enumerated
- **THEN** state-changing requests use POST with Django CSRF protection, S1 adds no production write endpoint, and serving the shell establishes a readable CSRF cookie

#### Scenario: Django REST API stays disabled
- **WHEN** the S1 deployment configuration is checked
- **THEN** Django REST API enablement remains false

### Requirement: Facade request and denial events
Every GM API request SHALL emit an info-level `gm_request` facade event with `account`, `route`, and final `status` in context, including denied and unknown-route requests. Every access denial SHALL emit a warn-level `gm_denied` with `account` or `anonymous` and `route`. New GM modules SHALL use the facade and SHALL NOT be added to the observability freeze file. S1 SHALL add no audit model or `gm_action` write behavior.

#### Scenario: API request outcomes logged
- **WHEN** GM APIs succeed, deny access, or return an unknown-route 404
- **THEN** each request emits `gm_request` with its final status and account/route context

#### Scenario: Page and API denial logged
- **WHEN** access is denied to an anonymous or insufficiently privileged visitor on a page or API
- **THEN** `gm_denied` records the visitor identity or `anonymous` and route through the facade

### Requirement: Registered backend acceptance coverage
GM backend tests SHALL use `EvenniaTest`, cover anonymous, ordinary player, Developer, and superuser access to pages and both S1 endpoints, unknown API routing, envelopes, CSRF wiring, events, and resolver access coverage. Every new test module SHALL be registered in `.github/evennia-shards.json` in the same implementation change.

#### Scenario: CI registration
- **WHEN** S1 backend test modules are introduced
- **THEN** the shard manifest includes all of them and the acceptance matrix covers the four account classes

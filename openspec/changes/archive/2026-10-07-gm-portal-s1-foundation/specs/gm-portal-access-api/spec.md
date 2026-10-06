## Purpose

Provide a Developer-only GM portal entry and a minimal read-only API with consistent transport and operational logging, isolated from the player interface.

## ADDED Requirements

### Requirement: Protected GM namespace
Every page and API request under `/gm/` MUST require an authenticated account whose `check_permstring("Developer")` passes; superusers MUST pass. Anonymous pages SHALL redirect to `LOGIN_URL` with the requested path in `next`; unauthorized authenticated pages SHALL return HTTP 403. Anonymous APIs SHALL return HTTP 401 with `unauthenticated`; unauthorized authenticated APIs SHALL return HTTP 403 with `forbidden`, both in the error envelope. All resolved GM views, including fallback routes, MUST be covered by the access wrapper.

#### Scenario: Anonymous page access
- **WHEN** an anonymous visitor requests `/gm/` or a GM history-route page
- **THEN** the response redirects to the configured login URL with the requested path encoded as `next`

#### Scenario: Ordinary account denied
- **WHEN** an authenticated non-Developer requests a GM page or either S1 API
- **THEN** the page returns 403 and the API returns the 403 `forbidden` envelope

#### Scenario: Anonymous API denied
- **WHEN** an anonymous visitor requests either S1 API or an unknown GM API path
- **THEN** the response is the 401 `unauthenticated` envelope rather than a redirect or SPA shell

#### Scenario: Privileged access
- **WHEN** a Developer or superuser requests GM pages and the session and health APIs
- **THEN** access succeeds independently of ordinary staff status

#### Scenario: URL coverage regression
- **WHEN** a GM URL is added without the required access wrapper
- **THEN** the URL-resolver contract test fails, including for API and page fallback patterns

### Requirement: S1 route and payload scope
S1 SHALL expose only `GET /gm/api/session` and `GET /gm/api/health` as concrete API endpoints. Session data SHALL contain the current account name, permission level, server time, and game version. Health SHALL report Django responding and database readability using a real read, without external-service probes or state changes. `/gm/` and non-API history paths SHALL serve the SPA shell. Unknown API paths SHALL return a JSON 404 error envelope, never the shell.

#### Scenario: Operator session
- **WHEN** a permitted account requests the session API
- **THEN** HTTP 200 contains the success envelope with that account's name and permission level, current server time, and actual game version

#### Scenario: Minimal health
- **WHEN** a permitted account requests health with a readable database
- **THEN** HTTP 200 reports Django responding and database readable without calling LLM or SD services

#### Scenario: Unreadable database
- **WHEN** the health database read fails
- **THEN** the response indicates failure with a matching non-success HTTP status and error envelope, without claiming the database is readable

#### Scenario: History routing and API miss
- **WHEN** a permitted account requests a non-API GM history path and `/gm/api/missing`
- **THEN** the history path serves the SPA shell and the API miss returns HTTP 404 with an error envelope

### Requirement: Consistent JSON transport
Success responses SHALL use `{"ok":true,"data":<payload>}`; failures SHALL use `{"ok":false,"error":{"code":"<snake_case>","message":"<zh-TW>"}}` with the matching HTTP status. Clients SHALL branch on codes rather than messages. The pagination convention SHALL be `cursor=<opaque>&limit=<n>` and data `{"items":[...],"next_cursor":<opaque|null>}`; S1 SHALL add no paginated endpoint. State-changing requests SHALL use POST with Django CSRF protection; S1 SHALL add no production write endpoint and SHALL establish a readable CSRF cookie when serving the shell. Django REST API enablement SHALL remain false.

#### Scenario: Transport envelope
- **WHEN** either S1 API succeeds or GM transport returns an authentication, authorization, or not-found failure
- **THEN** its JSON body follows the corresponding envelope and its HTTP status matches the outcome

#### Scenario: CSRF contract without production writes
- **WHEN** a permitted operator loads the shell and a test-only protected POST view is exercised with CSRF checks enabled
- **THEN** the shell supplies the CSRF cookie, missing/invalid tokens return HTTP 403 with a `csrf_failed` JSON error envelope and zh-TW message, each rejection emits exactly one `gm_request` with the final status, and the POST with the matching token succeeds without exposing a production S1 write route

#### Scenario: Anonymous test POST
- **WHEN** an anonymous visitor requests the test-only GM POST view with or without a CSRF token
- **THEN** authentication takes precedence and returns the HTTP 401 `unauthenticated` envelope, with one `gm_request` and the access-denial event

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

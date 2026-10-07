## MODIFIED Requirements

### Requirement: S1 route and payload scope
The GM API SHALL expose GET /gm/api/session, GET /gm/api/dashboard and GET /gm/api/llm/calls/<call_id>. Session SHALL retain account name, permission level, server time and game version. Dashboard SHALL fold Django responsiveness and real read-only database health into its process section and provide the operations snapshot specified by gm-operations-dashboard. The former /gm/api/health SHALL be removed, without alias or compatibility handler. /gm/ and non-API history paths SHALL serve the shell; unknown APIs SHALL return JSON 404, never the shell. These routes SHALL require the landed S1 access/envelope foundation and S2a transcript contract.

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

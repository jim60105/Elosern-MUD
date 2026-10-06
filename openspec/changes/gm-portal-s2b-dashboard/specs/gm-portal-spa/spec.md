## MODIFIED Requirements

### Requirement: S1 navigation and history routing
The SPA SHALL retain history routing at /gm/ and session identity/time/version. The home overview SHALL render the gm-operations-dashboard snapshot instead of calling the removed health endpoint, using the landed S1 fetch boundary and component layer and S2a transcript-detail contract. Navigation SHALL retain the approved future sections; undelivered sections SHALL remain disabled with 尚未開放 and no placeholder pages. Router guards SHALL handle authorization failures without redirect loops.

#### Scenario: Foundation overview
- **WHEN** a permitted operator loads /gm/
- **THEN** session information and dashboard sections render and no request targets /gm/api/health

#### Scenario: Future sections disabled
- **WHEN** pointer or keyboard activation targets an undelivered section
- **THEN** it remains disabled and cannot navigate to a placeholder

#### Scenario: History and authorization guard
- **WHEN** a client route is entered directly, through history, or receives a forbidden API outcome
- **THEN** routing stays under /gm/ and permission denial never exposes protected content or loops

### Requirement: Independent same-origin GM build
The GM SPA SHALL remain separately built from web/admin-app/ through vite.gm.config.js and pnpm run build:gm into web/static/gm/dist/ with stable index.js/index.css referenced by its shell. CI/container builds SHALL build both GM and game bundles from sources. Game Vite entry, frozen contracts, .elosern-root styles, OOB and /admin/ SHALL remain untouched. LLM/SD offline conditions SHALL not prevent the GM shell or dashboard from loading; services SHALL show offline/critical states without requiring active LLM probes.

#### Scenario: Production assets
- **WHEN** CI or container builds run
- **THEN** both bundles are built and GM assets load independently from the project origin

#### Scenario: External services offline
- **WHEN** LLM and SD are unavailable
- **THEN** the dashboard remains usable with truthful service states and sends no LLM probes

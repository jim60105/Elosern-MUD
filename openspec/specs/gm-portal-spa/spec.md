## Purpose

Provide a separately built operator SPA that shares only approved visual tokens with the game client and supplies the component, routing, and fetch contracts for future GM sections.

## Requirements

### Requirement: Independent same-origin GM build
The GM SPA SHALL remain separately built from web/admin-app/ through vite.gm.config.js and pnpm run build:gm into web/static/gm/dist/ with stable index.js/index.css referenced by its shell. CI/container builds SHALL build both GM and game bundles from sources. Game Vite entry, frozen contracts, .elosern-root styles, OOB and /admin/ SHALL remain untouched. LLM/SD offline conditions SHALL not prevent the GM shell or dashboard from loading; services SHALL show offline/critical states without requiring active LLM probes.

#### Scenario: Production assets
- **WHEN** CI or container builds run
- **THEN** both bundles are built and GM assets load independently from the project origin

#### Scenario: External services offline
- **WHEN** LLM and SD are unavailable
- **THEN** the dashboard remains usable with truthful service states and sends no LLM probes

### Requirement: Enforced token-only game dependency boundary
The GM application SHALL import from `web/webclient-app/` only `styles/tokens.css` and `styles/fonts*.css`. All other game-tree imports, including `app-shell.css`, components, stores, transport, and utilities, SHALL be forbidden. A dependency-free Node test SHALL scan imports throughout `web/admin-app/` and enforce the resolved-path allowlist, including JavaScript/Vue imports and CSS imports.

#### Scenario: Allowed visual reuse
- **WHEN** GM sources import shared tokens and font styles
- **THEN** the boundary test passes and GM styling uses the shared palette, typography, spacing, motion, and utility classes

#### Scenario: Forbidden dependency
- **WHEN** a GM source imports a game component, app-shell stylesheet, or any other non-allowlisted game-tree source, including an alternate relative path
- **THEN** the boundary test fails and identifies the importing source and forbidden dependency

### Requirement: Operator component layer
The GM application SHALL supply `GmShell`, `GmNav`, `GmPageHeader`, `GmPanel`, `GmTable`, `GmEmpty`, `GmError`, and `GmStatusBadge`, built only on approved tokens; the badge SHALL wrap `.status-marker`. The desktop-first shell SHALL have side navigation, a page header with operator account and logout, and a panel/table content area. Narrow viewports SHALL remain usable without dedicated mobile layouts. UI copy SHALL use Traditional Chinese; data identifiers SHALL remain verbatim in a monospace face. Danger buttons and seal-red SHALL be reserved for destructive or state-changing actions.

#### Scenario: Component coverage
- **WHEN** the component layer is delivered
- **THEN** every named component has Storybook stories included in the showcase coverage gate

#### Scenario: Operator presentation
- **WHEN** an operator opens the S1 home view at a desktop or narrow viewport
- **THEN** account/logout, navigation, and content remain usable, UI copy is Traditional Chinese, and any identifiers are unmodified and monospace

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

### Requirement: Single GM fetch boundary
All GM API calls SHALL use `web/admin-app/lib/api.js` with same-origin Django session credentials. The boundary SHALL unwrap success data, attach the `csrftoken` cookie as `X-CSRFToken` for POST writes, redirect 401 responses to the configured login destination with a GM return path, route 403 `forbidden` responses to the permission-denied view, and surface other errors by stable code; a 403 `csrf_failed` is a transport failure and SHALL surface by its code rather than selecting the permission-denied view. Network failure and malformed bodies SHALL produce explicit client errors, never fabricated success data. S1 SHALL test POST header wiring without introducing a production write endpoint.

#### Scenario: Success and POST wiring
- **WHEN** a success envelope is fetched or a test POST is issued with a CSRF cookie
- **THEN** the caller receives only success data and the POST includes matching `X-CSRFToken` and session credentials

#### Scenario: Authentication and permission outcomes
- **WHEN** an API call receives 401 or 403
- **THEN** 401 initiates login with a GM return path and a 403 `forbidden` selects the permission-denied view rather than login, while a 403 `csrf_failed` surfaces its code without either

#### Scenario: Other error outcomes
- **WHEN** an API call receives a 404 envelope, a network failure, or a malformed JSON/envelope body
- **THEN** it surfaces the server error code or an explicit client failure code and does not treat the response as data

### Requirement: Frontend acceptance gates
Vitest SHALL cover envelope handling, 401/403/404, network failure, malformed bodies, CSRF header wiring, router guards, and shell navigation including disabled sections. The dependency-boundary test and all GM component stories SHALL run in their respective CI coverage gates without removing game-client coverage.

#### Scenario: Complete foundation coverage
- **WHEN** frontend acceptance gates run for S1
- **THEN** API, router, shell, boundary, and all eight component showcase checks are included alongside existing game checks

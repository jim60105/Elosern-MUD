## Purpose

Provide a separately built operator SPA that shares only approved visual tokens with the game client and supplies the component, routing, and fetch contracts for future GM sections.

## ADDED Requirements

### Requirement: Independent same-origin GM build
The GM SPA SHALL be a separate Vue 3 application in `web/admin-app/`, built through `vite.gm.config.js` by `pnpm run build:gm` into `web/static/gm/dist/` with stable `index.js` and `index.css`. The GM shell template SHALL reference those assets. CI and container builds SHALL run the GM build alongside the game build; generated output SHALL come from sources, never hand-authored. The existing game Vite entry, frozen contracts, `.elosern-root` styles, OOB protocol, and `/admin/` SHALL remain untouched.

#### Scenario: Production assets
- **WHEN** CI or the container image builds the frontend
- **THEN** both bundles are built and the GM shell can load its stable GM asset names from the project origin without depending on the game bundle

#### Scenario: External services offline
- **WHEN** LLM and SD services are offline
- **THEN** the GM shell and S1 session/health overview still load without contacting those services; S1 adds no service-status dashboard

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
The SPA SHALL use history routing with base `/gm/`. The home section SHALL be the overview and SHALL render actual session and health responses. Navigation SHALL expose the overview and the future operations, runtime-state, world-data, operations/action, and GM-intervention sections defined by the design; sections not delivered SHALL be disabled with `尚未開放` and SHALL NOT have placeholder pages. Router guards SHALL handle authorization failures without redirect loops.

#### Scenario: Foundation overview
- **WHEN** a permitted operator loads `/gm/`
- **THEN** the overview renders session identity/time/version and skeleton Django/database health from the two S1 APIs

#### Scenario: Future sections disabled
- **WHEN** an operator attempts keyboard or pointer activation of an undelivered section
- **THEN** it is visibly disabled with `尚未開放` and does not navigate to a placeholder page

#### Scenario: History and authorization guard
- **WHEN** a GM client route is entered directly, navigated through history, or receives a 403 API outcome
- **THEN** routing stays under `/gm/` and authorization failure reaches the permission-denied view without repeated redirects or protected content display

### Requirement: Single GM fetch boundary
All GM API calls SHALL use `web/admin-app/lib/api.js` with same-origin Django session credentials. The boundary SHALL unwrap success data, attach the `csrftoken` cookie as `X-CSRFToken` for POST writes, redirect 401 responses to the configured login destination with a GM return path, route 403 responses to the permission-denied view, and surface other errors by stable code. Network failure and malformed bodies SHALL produce explicit client errors, never fabricated success data. S1 SHALL test POST header wiring without introducing a production write endpoint.

#### Scenario: Success and POST wiring
- **WHEN** a success envelope is fetched or a test POST is issued with a CSRF cookie
- **THEN** the caller receives only success data and the POST includes matching `X-CSRFToken` and session credentials

#### Scenario: Authentication and permission outcomes
- **WHEN** an API call receives 401 or 403
- **THEN** 401 initiates login with a GM return path and 403 selects the permission-denied view rather than login

#### Scenario: Other error outcomes
- **WHEN** an API call receives a 404 envelope, a network failure, or a malformed JSON/envelope body
- **THEN** it surfaces the server error code or an explicit client failure code and does not treat the response as data

### Requirement: Frontend acceptance gates
Vitest SHALL cover envelope handling, 401/403/404, network failure, malformed bodies, CSRF header wiring, router guards, and shell navigation including disabled sections. The dependency-boundary test and all GM component stories SHALL run in their respective CI coverage gates without removing game-client coverage.

#### Scenario: Complete foundation coverage
- **WHEN** frontend acceptance gates run for S1
- **THEN** API, router, shell, boundary, and all eight component showcase checks are included alongside existing game checks

## Purpose

Establishes the offline loading contract for the WebClient's Vue 3 single-page application: a locally built, self-contained Vite bundle served entirely from the project origin with no remote runtime UI dependencies, desktop-only bounded rendering at 1440x900 and 1280x720, and the retirement of the replaced stock and pre-Js text fallback on mount. It also carries the design system over from the 設計稿: the ink-night palette with a single seal-red accent, self-hosted display, serif, and sans typefaces, focus, selection, and motion tokens, status and health information never conveyed by color alone, and reduced-motion honor.

## Requirements

### Requirement: The WebClient loads a self-contained offline Vue SPA
The project WebClient SHALL load a locally built, self-contained Vue 3 single-page application produced
by a Vite build and served entirely from the project origin. The page SHALL make no remote request for
a runtime UI dependency (no CDN JavaScript, CSS, or font). The application SHALL target desktop only and
SHALL NOT claim mobile acceptance; every required surface SHALL be visible and usable at 1440x900 and
at 1280x720. When the application mounts into its container, the stock and pre-Js text fallback it
replaces SHALL be retired so it cannot stack in document flow and push required surfaces below the
visible viewport. (The live evennia-transport mount and the always-playable text path are established by
later changes in this migration; this change establishes the offline build and render of the app.)

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the Vue application is loaded with all non-local network requests blocked
- **THEN** the Vite-built Vue bundle, its styles, and its self-hosted fonts load from the project origin without a CDN failure

#### Scenario: Desktop-only bounded render at each supported viewport
- **WHEN** the Vue application renders at 1440x900 and at 1280x720
- **THEN** every required surface is visible and usable without overlapping the input path, and the application makes no mobile-behavior claim

#### Scenario: Mount retires the replaced text fallback
- **WHEN** the Vue application mounts into its container
- **THEN** the stock and pre-Js text fallback it replaces is hidden so it does not stack with the mounted application

### Requirement: The design system carries over from the design draft and stays offline
The Vue application SHALL render with the approved design system derived from the 設計稿: the ink-night
palette with a single seal-red accent, the self-hosted display, serif, and sans typefaces, and the
focus, selection, and motion tokens. Status and health information SHALL never be conveyed by color
alone (an icon or symbol plus a numeric value or an explicit text label is required), SHALL honor
`prefers-reduced-motion`, and SHALL remain legible for common color-vision differences. No design asset
or font SHALL be fetched from a remote origin at render time.

#### Scenario: Self-hosted fonts load offline
- **WHEN** the application loads with remote requests blocked
- **THEN** the display, serif, and body fonts render from the project origin

#### Scenario: Status is not color-only
- **WHEN** a gauge, condition, or health state is displayed
- **THEN** it pairs an icon or symbol with a numeric value or an explicit text label instead of relying on color alone

#### Scenario: Reduced motion is honored
- **WHEN** `prefers-reduced-motion` is set
- **THEN** non-essential animation transitions are disabled

### Requirement: The Vue app binds the preserved strict DOM-independent logic to a reactive store
The Vue application SHALL use a single reactive store (Pinia) as the sole writer of client view state.
The store SHALL consume the preserved DOM-independent logic — the protocol reducer, the keyboard router,
the narrative markup pipeline, the local-map model, and the choice-point and option-card logic — through
ES-module wrappers rather than reimplementing it. The store SHALL publish committed state atomically so
that no subscriber observes partially applied panel state, and it SHALL hold only data derived from the
OOB panel allowlist (art, status, context_actions, local_map, services, creation, exploration,
character) and the transport text stream; it SHALL NOT invent data. Components emit only user-intent
dispatches, and the store is driven in tests by raw reducer inputs; binding the live transport and the
components to this store are established by later changes.

#### Scenario: Renderers observe only committed state
- **WHEN** a valid snapshot or update is accepted by the preserved protocol reducer through the store
- **THEN** the store publishes one commit of completely replaced panel state and no subscriber observes partially applied state

#### Scenario: Stale epochs and revisions are rejected
- **WHEN** an old-epoch snapshot or a stale active-epoch revision is presented to the store
- **THEN** the store discards it and preserves the last committed state

#### Scenario: The store holds only backed data
- **WHEN** the store receives panel data
- **THEN** it holds only data sourced from the OOB allowlist or the transport text stream and holds no invented data

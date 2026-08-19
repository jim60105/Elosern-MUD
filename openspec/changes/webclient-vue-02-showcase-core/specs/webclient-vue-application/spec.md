## ADDED Requirements

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
alone (an icon or symbol plus a numeric value are required), SHALL honor `prefers-reduced-motion`, and
SHALL remain legible for common color-vision differences. No design asset or font SHALL be fetched from a
remote origin at render time.

#### Scenario: Self-hosted fonts load offline
- **WHEN** the application loads with remote requests blocked
- **THEN** the display, serif, and body fonts render from the project origin

#### Scenario: Status is not color-only
- **WHEN** a gauge, condition, or health state is displayed
- **THEN** it pairs an icon or symbol with a numeric value instead of relying on color alone

#### Scenario: Reduced motion is honored
- **WHEN** `prefers-reduced-motion` is set
- **THEN** non-essential animation transitions are disabled

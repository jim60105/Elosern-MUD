## Purpose

Establishes the offline loading contract for the WebClient's Vue 3 single-page application: a locally built, self-contained Vite bundle served entirely from the project origin with no remote runtime UI dependencies, desktop-only bounded rendering at 1440x900 and 1280x720, and the retirement of the replaced stock and pre-Js text fallback on mount. It also carries the design system over from the 設計稿: the ink-night palette with a single seal-red accent, self-hosted display, serif, and sans typefaces, focus, selection, and motion tokens, status and health information never conveyed by color alone, and reduced-motion honor. It also preserves the client DOM contract hooks (action-dock target, item keys, `data-testid` hooks) and the stable public façades as browser-bridge shims. It also fixes the C4 flip contract: the view layer is fully reactive and store-bound, no legacy imperative view-plugin code remains in the load path, and every activation emits at most one request.

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

### Requirement: The app preserves the client DOM contract hooks and exposes stable test hooks
The Vue application SHALL preserve the DOM contract identifiers that the OOB and browser contract depend
on: the focusable action-dock target that the keyboard router dispatches into, the `action-` and `target-`
item keys selected by pointer or keyboard, and the identity of the required panel surfaces. The application
SHALL expose a stable `data-testid` hook on every remaining interactive surface so behavioral browser
acceptance targets deterministic hooks rather than styling selectors. The application SHALL also preserve
the stable public façades that existing OOB and browser contracts reference — the narrative input/append
path (`window.Elosern.narrativeInput`), the action submission entry point (`window.Elosern.actions.submit`),
and the keyboard-router consumption contract — implemented as browser-bridge shims over the store and the
imported logic, so existing behavioral tests and the choice-point/narrative append path keep their single,
non-duplicated entry points while the DOM is implemented in Vue.

#### Scenario: Keyboard router reaches the same dock
- **WHEN** the application renders the active menu frame and the player focuses the preserved action-dock target
- **THEN** a key press dispatches through the keyboard router to the focused item

#### Scenario: Pointer chooses by the stored key with keyboard parity
- **WHEN** the player clicks an action or target row
- **THEN** the `action-` or `target-` item key is used and the chosen item equals the item a keyboard journey would reach

#### Scenario: Interactive surfaces carry stable hooks
- **WHEN** any required interactive surface renders
- **THEN** it exposes a stable, unique `data-testid` identifier usable by automation

#### Scenario: Existing façade contracts hold
- **WHEN** an existing browser test or spec references the `window.Elosern.narrativeInput` narrative append path or the `window.Elosern.actions.submit` action entry point
- **THEN** those contracts resolve and route through the store and the single bridge dispatch path (the live transport round-trip is proven by a later change) with no duplicated append or action path

### Requirement: Degraded text remains playable alongside the Vue shell
The application SHALL remain fully playable by ordinary text commands when the Vue graphical surfaces are
unavailable, when the Vite bundle fails to load, or when the OOB channel is incompatible. An incompatible
or failed OOB presentation SHALL lock the graphical controls while leaving the text path functional.
Narrative and command output SHALL remain the authoritative text surface and SHALL degrade a message that
cannot be fully tokenized to readable literal text rather than suppressing the log.

#### Scenario: Bundle blocked keeps text playable
- **WHEN** the Vue bundle cannot load
- **THEN** ordinary text commands can still be sent and rendered and no required input path is lost

#### Scenario: Incompatible OOB locks graphical, keeps text
- **WHEN** the application receives an unsupported protocol version
- **THEN** graphical actions are disabled and locked while a text command round-trips and renders normally

#### Scenario: Unparseable message degrades to literal text
- **WHEN** a message cannot be fully tokenized by the markup pipeline
- **THEN** the narrative shows readable literal text rather than being suppressed

### Requirement: The view layer is fully reactive and store-bound with no legacy imperative view plugin
Every player-facing Vue surface SHALL be a reactive component that renders committed state from the Pinia
store and dispatches only through the allowlisted action path; no component SHALL mutate store or server
state directly, and no legacy imperative view-plugin code (the retired GoldenLayout/jQuery dock and
`elosern_ui` view files) SHALL remain in the client load path. The keyboard router SHALL keep focusing the
preserved action-dock target, and every activation SHALL emit at most one request.

#### Scenario: A control emits one dispatch only
- **WHEN** the player activates a dock item, verb, skill, or target control
- **THEN** exactly one allowlisted OOB action envelope is dispatched and no local model mutation occurs

#### Scenario: No legacy view code is loaded
- **WHEN** the production client load path is inspected
- **THEN** the retired GoldenLayout/jQuery dock and `elosern_ui` view files are not loaded and every
  interactive surface is a store-bound Vue component

#### Scenario: Single request per deliberate activation
- **WHEN** a mutation control is activated rapidly or a held key repeats while a submission is in flight
- **THEN** at most one request is emitted until the action's declared presentation revision is accepted

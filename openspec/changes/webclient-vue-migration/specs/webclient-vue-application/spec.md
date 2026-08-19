## ADDED Requirements

### Requirement: The WebClient loads a self-contained offline Vue SPA
The project WebClient SHALL load Evennia's existing transport together with a locally built, self-contained Vue 3 single-page application. The application SHALL be produced by a Vite build and SHALL be served entirely from the project origin; the page SHALL make no remote request for a runtime UI dependency (no CDN JavaScript, CSS, or font). The application SHALL target desktop only and SHALL NOT claim mobile acceptance; every required surface SHALL be visible and usable at 1440x900 and at 1280x720. The application mount SHALL retire the pre-Js and stock text fallback so it cannot stack in document flow and push required surfaces below the visible viewport.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the evennia transport, the Vite-built Vue bundle, its styles, and its self-hosted fonts load from the project origin without a CDN failure

#### Scenario: Desktop-only bounded render at each supported viewport
- **WHEN** the Vue application renders at 1440x900 and at 1280x720
- **THEN** every required surface is visible and usable without overlapping the input path, and the application makes no mobile-behavior claim

#### Scenario: Mount retires the text fallback
- **WHEN** the Vue application mounts into its container
- **THEN** the stock and pre-Js text fallback is hidden so it does not stack with the mounted application

### Requirement: The Vue app binds the preserved strict DOM-independent logic to a reactive store
The application SHALL use a single reactive store (Pinia) as the writer of client view state. The store SHALL consume the preserved DOM-independent logic — the protocol reducer, the keyboard router, the narrative markup pipeline, the local-map model, and the choice-point and option-card logic — through ES-module wrappers rather than reimplementing it. Every component SHALL be a pure consumer of the store and SHALL submit changes only as validated action dispatches through the evennia transport; no component SHALL mutate store state or server state directly. The store SHALL derive view state only from the OOB panel allowlist (art, status, context_actions, local_map, services, creation, exploration, character) and the transport text stream, and the app SHALL NOT present data that has no backing read model.

#### Scenario: Renderers observe only committed state
- **WHEN** a valid snapshot or update is accepted by the preserved protocol reducer
- **THEN** renderers receive one commit of completely replaced panel state and no subscriber observes partially applied state

#### Scenario: Action submission is dispatch-only
- **WHEN** the player activates a dock item, verb, skill, or target control
- **THEN** the application enqueues the exact OOB action envelope through the evennia transport and performs no local model mutation

#### Scenario: Components never mutate state directly
- **WHEN** a component receives a store payload
- **THEN** it renders the payload read-only and emits only user-intent events that are consumed by the store/dispatch path

### Requirement: Degraded text remains playable alongside the Vue shell
The application SHALL remain fully playable by ordinary text commands when the Vue graphical surfaces are unavailable, when the Vite bundle fails to load, or when the OOB channel is incompatible. An incompatible or failed OOB presentation SHALL lock the graphical controls while leaving the text path functional. Narrative and command output SHALL remain the authoritative text surface and SHALL degrade a message that cannot be fully tokenized to readable literal text rather than suppressing the log.

#### Scenario: Bundle blocked keeps text playable
- **WHEN** the Vue bundle cannot load
- **THEN** ordinary text commands can still be sent and rendered and no required input path is lost

#### Scenario: Incompatible OOB locks graphical, keeps text
- **WHEN** the application receives an unsupported protocol version
- **THEN** graphical actions are disabled and locked while a text command round-trips and renders normally

#### Scenario: Unparseable message degrades to literal text
- **WHEN** a message cannot be fully tokenized by the markup pipeline
- **THEN** the narrative shows readable literal text rather than being suppressed

### Requirement: The app preserves the client DOM contract hooks and exposes stable test hooks
The Vue application SHALL preserve the DOM contract identifiers that the OOB and browser contract depend on: the focusable action-dock target that the keyboard router dispatches into, the `action-` and `target-` item keys selected by pointer or keyboard, and the identity of the required panel surfaces. The application SHALL expose a stable `data-testid` hook on every remaining interactive surface so behavioral browser acceptance targets deterministic hooks rather than styling selectors. The application SHALL also preserve the stable public façades that existing OOB and browser contracts reference — the narrative input/append path (`window.Elosern.narrativeInput`), the action submission entry point (`window.Elosern.actions.submit`), and the keyboard-router consumption contract — so existing behavioral tests and the choice-point/narrative append path keep their single, non-duplicated entry points while the DOM is implemented in Vue.

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
- **THEN** those contracts resolve and route through the Vue store and the transport with no duplicated append or action path

### Requirement: The design system carries over from the design draft and stays offline
The application SHALL render with the approved design system derived from the 設計稿: the ink-night palette with a single seal-red accent, the self-hosted display, serif, and sans typefaces, and the focus, selection, and motion tokens. Status and health information SHALL never be conveyed by color alone (an icon or symbol plus a numeric value are required), SHALL honor `prefers-reduced-motion`, and SHALL remain legible for common color-vision differences. No design asset or font SHALL be fetched from a remote origin at runtime.

#### Scenario: Self-hosted fonts load offline
- **WHEN** the application loads with remote requests blocked
- **THEN** the display, serif, and body fonts render from the project origin

#### Scenario: Status is not color-only
- **WHEN** a gauge, condition, or health state is displayed
- **THEN** it pairs an icon or symbol with a numeric value instead of relying on color alone

#### Scenario: Reduced motion is honored
- **WHEN** `prefers-reduced-motion` is set
- **THEN** non-essential animation transitions are disabled

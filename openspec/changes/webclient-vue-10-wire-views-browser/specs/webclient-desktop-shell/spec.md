## RENAMED Requirements

- FROM: `### Requirement: The WebClient loads a local desktop GoldenLayout shell`
- TO: `### Requirement: The WebClient loads a local Vue SPA desktop shell`

## MODIFIED Requirements

### Requirement: The WebClient loads a local Vue SPA desktop shell
The project WebClient SHALL load Evennia's existing transport together with a locally built, self-contained
Vue 3 single-page application. It SHALL make no remote request for a runtime UI dependency. The
application SHALL provide the required header, narrative, art, status, local-map, action-dock, and
command-drawer components and SHALL render them as self-identifying surfaces — the narrative log, status
resources, map legend, art caption, dock menu, and prompt line — never as a tab-title component strip. The
`local-map` surface SHALL render the `webclient-local-map` panel owned by the `map-knowledge-minimap`
delivery unit. The `art` surface SHALL render the validated `webclient-art-panel` payload: the current
scene and its contextual portrait overlay when the panel is available, and a truthful scene placeholder
(never an invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or
the OOB channel is unavailable.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, the Vite-built Vue application, the project modules, and the theme load from the project origin without a CDN failure

#### Scenario: The minimap renders while art degrades to its placeholder
- **WHEN** the shell renders the local_map payload and the art panel is unavailable, missing, or failed
- **THEN** the local-map surface renders the validated `local_map` payload, and the art surface renders the truthful scene placeholder with no invented image

#### Scenario: Art renders when the validated panel is available
- **WHEN** the `webclient-art-panel` payload is available in the current snapshot
- **THEN** the art surface renders the scene with cover-style 16:9 layout and its contextual portrait overlay, with the scene label and alternative text outside the bitmap

#### Scenario: The shell renders self-identifying surfaces without a tab strip
- **WHEN** the shell mounts
- **THEN** no tab-title chrome is rendered anywhere, every required component is present, and each surface carries its own self-identifying content instead of a component-name tab title

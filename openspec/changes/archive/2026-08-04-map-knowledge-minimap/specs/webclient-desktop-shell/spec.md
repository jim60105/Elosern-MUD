## MODIFIED Requirements

### Requirement: The WebClient loads a local desktop GoldenLayout shell
The project WebClient SHALL load Evennia's existing transport together with locally served, pinned,
license-documented jQuery and GoldenLayout assets. It SHALL make no remote request for a runtime UI
dependency. Layout version 1 SHALL provide required header, narrative, art placeholder, status,
local-map, action-dock, and command-drawer components. The `local-map` component SHALL render the
`webclient-local-map` panel owned by the `map-knowledge-minimap` delivery unit; the art component
remains a placeholder until the art delivery unit lands.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, GoldenLayout shell, project modules, and theme load from the project
  origin without a CDN failure

#### Scenario: The minimap renders instead of a placeholder while art stays unavailable
- **WHEN** the version-1 shell renders after the map-knowledge-minimap change
- **THEN** the local-map surface renders the validated `local_map` payload, and the art surface still
  identifies itself as unavailable with no invented image

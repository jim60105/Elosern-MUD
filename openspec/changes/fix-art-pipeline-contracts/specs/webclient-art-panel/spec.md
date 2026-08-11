## ADDED Requirements

### Requirement: The art panel accepts the normalized in-flight state

The Web art panel schema (Python and JavaScript) SHALL accept every status the presenter can emit — including the normalized in-flight state — so a generation-in-progress snapshot renders a placeholder instead of degrading the panel.

#### Scenario: In-flight snapshot renders instead of degrading

- **WHEN** a WebClient receives an art panel payload whose scene or catalog entry carries the normalized in-flight status
- **THEN** the panel renders a placeholder and remains available

## ADDED Requirements

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be complete.
The settings overlay SHALL expose fonts, type scale, reduced-motion, the text-to-HTML toggle, and colorblind
options and SHALL emit `options.*`. The creation overlay SHALL implement a presets/custom/concept wizard
with the adult gate applied to BOTH the age and the apparent_age fields and an activate transition, and
SHALL emit `creation.*`. The `MapOverlay` SHALL re-render its available/unavailable branch whenever the
`local_map` OOB read model is updated, so a replaced payload never leaves a stale state. A surface
with no backing OOB read model today — a dedicated Party/companion panel, the intimate/adult status
collapsible, a full inventory bag, and the event-log Toasts surface — MUST NOT be built here or mocked to
look real. On completion of the showcase wave the required-component manifest SHALL be frozen at the
complete set and the component-coverage gate SHALL enforce that frozen set.

#### Scenario: Creation gate rejects both underage fields
- **WHEN** the creation wizard submits an age or an apparent_age below 18
- **THEN** the adult gate rejects the record before activation

#### Scenario: Settings emit options and honor reduced motion
- **WHEN** a settings control changes
- **THEN** it emits the matching `options.*` envelope and reduced-motion is reflected in the app-wide motion tokens

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no Party panel, intimate/adult collapsible, full inventory bag, or event-log Toasts surface is present and none presents invented data

#### Scenario: The manifest is frozen
- **WHEN** the showcase wave completes
- **THEN** the required-component manifest is frozen at the complete set and the component-coverage gate enforces it

## MODIFIED Requirements

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be complete
and SHALL each be reachable from a real control in the running application — a built overlay that no
surface can open does not satisfy this requirement. The settings overlay SHALL expose fonts, type scale,
reduced-motion, the text-to-HTML toggle, and colorblind options and SHALL emit `options.*`. The creation
overlay SHALL implement a presets/custom/concept wizard with the adult gate applied to BOTH the age and
the apparent_age fields and an activate transition, and SHALL emit `creation.*`. The `MapOverlay` SHALL
re-render its available/unavailable branch whenever the `local_map` OOB read model is updated, so a
replaced payload never leaves a stale state. A surface with no backing OOB read model today — a
dedicated Party/companion panel, the intimate/adult status collapsible, the event-log Toasts surface,
and a persistent objective tracker — MUST NOT be built or mocked to look real, and each SHALL be named
in the deferred-surface assertion together with the read model it waits on. The held-item bag is NOT in
that set: it is backed by `services.inventory.rows` and is built. On completion of the contextual HUD
redesign the required-component manifest SHALL be re-frozen at the complete redesign set and the
component-coverage gate SHALL enforce that frozen set.

#### Scenario: Creation gate rejects both underage fields
- **WHEN** the creation wizard submits an age or an apparent_age below 18
- **THEN** the adult gate rejects the record before activation

#### Scenario: Settings emit options and honor reduced motion
- **WHEN** a settings control changes
- **THEN** it emits the matching `options.*` envelope and reduced-motion is reflected in the app-wide motion tokens

#### Scenario: Every full overlay is reachable from a control
- **WHEN** the running application is enumerated for overlay entry points
- **THEN** each of the map, settings, help, and creation overlays is opened by a real control in the live surface tree, and none is present in the bundle without a trigger

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no Party panel, intimate/adult collapsible, event-log Toasts surface, or persistent objective tracker is present and none presents invented data

#### Scenario: The held-item bag is built from its read model
- **WHEN** the `services` panel carries an `inventory` section
- **THEN** the bag renders those rows with their held counts and equipped flags, bounded to the payload's row cap with the true total surfaced, and never invents a row

#### Scenario: The manifest is re-frozen at the redesign set
- **WHEN** the contextual HUD redesign completes
- **THEN** the required-component manifest is re-frozen at the complete redesign set and the component-coverage gate enforces it

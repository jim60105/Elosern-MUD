## MODIFIED Requirements

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be complete,
and the first three SHALL be mounted and reachable from the running client by a labelled control — a
built, tested, manifest-listed overlay that nothing imports is not complete.
The settings overlay SHALL expose the narrative prose scale, the reduced-motion preference, the
text-to-HTML narrative toggle, and the colourblind-safe status palette as **client-local presentation
state**. It SHALL NOT dispatch a `ui_action` for any of them: `options.dismiss` — the suggestions
dismissal — is the only allowlisted `options.*` action, and widening the action allowlist is a
server-side change that no showcase or redesign wave makes. Each setting SHALL be applied to the
document's presentation tokens immediately, SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference, and SHALL be re-applied at load and
reset with that store when its stored version is unrecognised. The reduced-motion preference SHALL be
optional in the stored wrapper: when the key is absent the operating system's `prefers-reduced-motion`
preference SHALL continue to apply, and an explicit stored value — either direction — SHALL override it. The surface SHALL offer no control it
does not implement, so a control with no outcome — a typeface choice the design system's role-assigned
faces do not support, an audio level with no audio subsystem, an interface-scale slider, or a key
remapping — SHALL NOT be rendered. The creation overlay SHALL implement a presets/custom/concept wizard
with the adult gate applied to BOTH the age and the apparent_age fields and an activate transition, and
SHALL emit `creation.*`. The `MapOverlay` SHALL re-render its available/unavailable branch whenever the
`local_map` OOB read model is updated, so a replaced payload never leaves a stale state; because the
overlay is mounted in the running client, this SHALL hold against live read-model replacement and not
only against a story's args. A surface with
no backing OOB read model today — a dedicated Party/companion panel, the intimate/adult status collapsible,
the event-log Toasts surface, and the design draft's category-to-entry game-help browser (the `help`
command's output reaches the client only as narrative text; no committed panel carries it) — MUST NOT be
built here or mocked to look real; the help overlay SHALL therefore render the client's own control
reference, which the client authoritatively knows, and no authored game-help content. The held-item bag is
NOT among them: it is backed by the `services` panel's `inventory` section, which the server builds for
any actor in exploration mode independently of any service host, so the bag SHALL be built from
`services.inventory.rows`, bounded by the payload's row cap, with `pagination.inventory_total` surfaced
only as the count of rows actually shipped and never as a claim about untruncated holdings. On completion of the showcase wave the required-component
manifest SHALL be frozen at the complete set and the component-coverage gate SHALL enforce that frozen set.

#### Scenario: Creation gate rejects both underage fields
- **WHEN** the creation wizard submits an age or an apparent_age below 18
- **THEN** the adult gate rejects the record before activation

#### Scenario: The built overlays are reachable from the running client
- **WHEN** the running client renders in exploration mode
- **THEN** a labelled control opens each of the map, settings, and help overlays, and none of the three is reachable only from the component showcase

#### Scenario: Settings are client-local and honor reduced motion
- **WHEN** a settings control changes
- **THEN** no `ui_action` is dispatched for it, the change is applied to the app-wide presentation tokens immediately — reduced motion among them — and it is persisted through the versioned presentation-only browser store

#### Scenario: The settings surface renders nothing inert
- **WHEN** the settings overlay's controls are enumerated
- **THEN** every rendered control changes an outcome the client implements, and no typeface choice, audio level, interface-scale slider, or key-remapping control is present

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload while the mounted overlay is open
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no Party panel, intimate/adult collapsible, event-log Toasts surface, or authored game-help browser is present and none presents invented data

#### Scenario: The held-item bag is built from its backing section
- **WHEN** the `services` panel commits an `inventory` section
- **THEN** the bag renders that section's rows with their display names, held counts and equipped flags, bounded by the payload's row cap, and states the cap in words when the listing reaches it

#### Scenario: The manifest is frozen
- **WHEN** the showcase wave completes
- **THEN** the required-component manifest is frozen at the complete set and the component-coverage gate enforces it

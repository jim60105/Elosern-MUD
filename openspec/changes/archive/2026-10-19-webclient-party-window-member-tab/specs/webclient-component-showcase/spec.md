# Spec Delta

## MODIFIED Requirements

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be
complete, and SHALL each have a live mount path in the running application — a built, tested,
manifest-listed overlay that nothing imports is not complete.

#### Scenario: Creation gate rejects both out-of-range fields
- **WHEN** the creation wizard submits an age or an apparent_age outside the 0..10000 range
- **THEN** the age-range gate rejects the record before activation

#### Scenario: Settings are client-local and honor reduced motion
- **WHEN** a settings control changes
- **THEN** no `ui_action` is dispatched for it, the change is applied to the app-wide presentation tokens immediately — the motion level among them, which resolves every motion token for the whole document at once — and it is persisted through the versioned presentation-only browser store

#### Scenario: The settings surface renders nothing inert
- **WHEN** the settings overlay's controls are enumerated
- **THEN** every rendered control changes an outcome the client implements, and no typeface choice, audio level, interface-scale slider, or key-remapping control is present

#### Scenario: Every full overlay has a live mount path
- **WHEN** the running application is enumerated for overlay mount paths
- **THEN** each of the map, settings, and help overlays is opened by a real control in the live surface tree, the creation overlay is mounted on the committed `creation` panel's availability predicate, and none is present in the bundle without a live mount path

#### Scenario: The creation overlay renders no dismissal control
- **WHEN** the mounted creation overlay's chrome is enumerated
- **THEN** no close, exit, or dismiss control is rendered in its header or body, and the overlay stops rendering only when the committed `creation` panel stops being available

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload while the mounted overlay is open
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no event-log Toasts surface or authored game-help browser is present and none presents invented data

#### Scenario: The objective tracker is no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the persistent objective tracker is absent from the deferred-surface list, because it now has a backing OOB read model (the `objectives` panel), its component is manifest-listed with a deterministic offline story, and its behaviour is asserted by `webclient-contextual-hud`'s objective tracker requirement instead

#### Scenario: The party surfaces are no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the party quickbar and the party window are absent from the deferred-surface list, because they now have backing OOB read models (the `party` and `party_member` panels), their components are manifest-listed with deterministic offline stories, and their behaviour is asserted by `webclient-contextual-hud`'s party requirements and `webclient-party-window` instead

#### Scenario: The action-feedback queue is built while the event-log queue stays deferred
- **WHEN** the complete component set and the deferred-surface assertion are enumerated
- **THEN** the client-local `ToastQueue` with its `feedback-` test-id family is present and manifest-listed, while the `event-log-`/`toast-` bound game-event queue remains named in the deferred-surface assertion waiting on the `event-log` read model

#### Scenario: The intimate/adult status collapsible is no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the intimate/adult status collapsible is absent from the deferred-surface list, because it now has a backing OOB read model (`character.intimate`), and its presence/absence behaviour is asserted by `webclient-contextual-hud`'s character-status drawer requirement instead

#### Scenario: The held-item bag is built from its backing section
- **WHEN** the `services` panel commits an `inventory` section
- **THEN** the bag renders that section's rows with their display names, held counts and equipped flags, bounded by the payload's row cap, and states the cap in words when the listing reaches it

#### Scenario: The manifest is re-frozen at the redesign set
- **WHEN** the contextual HUD redesign completes
- **THEN** the required-component manifest is re-frozen at the complete redesign set and the component-coverage gate enforces it

#### Scenario: Overlay triggers follow the surface tree or panel availability
- **WHEN** the overlays' opening paths are enumerated
- **THEN** the map, settings, and help overlays each open from a real control in the live surface
  tree, and the creation overlay is mounted by the running client on the committed `creation`
  panel's availability predicate
- **AND** creation mode is entered by the server's snapshot rather than by a player-operated
  trigger, so no player control opens it

#### Scenario: Creation stories mount the live three-region workspace
- **WHEN** the `Overlays/CreationOverlay` stories render
- **THEN** they mount the same three-region creation workspace as the live client
- **AND** its `Storyboard` supplies an explicitly labelled, offline publication desk for
  save/confirmation, concept success/rejection and draft reconnect, and these controls are
  story-only and never ship as game controls

#### Scenario: The settings overlay exposes the client-local presentation settings
- **WHEN** the settings overlay renders
- **THEN** it exposes the narrative prose scale, the motion level (`完整` / `減少` / `關閉`),
  the text-to-HTML narrative toggle, and the colourblind-safe status palette as **client-local
  presentation state**

#### Scenario: Only options.dismiss stays on the action allowlist
- **WHEN** a settings change is considered for dispatch
- **THEN** no `ui_action` is dispatched for any setting: `options.dismiss` — the suggestions
  dismissal — is the only allowlisted `options.*` action, and widening the action allowlist is a
  server-side change that no showcase or redesign wave makes

#### Scenario: Settings reset with the store on an unrecognised version
- **WHEN** the client loads and the stored presentation-store version is unrecognised
- **THEN** each setting — applied to the document's presentation tokens immediately and persisted
  through the client's versioned, presentation-only browser store as a harmless display
  preference — is re-applied at load and reset with that store

#### Scenario: An absent motion-level key defers to the operating system
- **WHEN** the stored wrapper lacks the optional motion-level key
- **THEN** the operating system's `prefers-reduced-motion` preference continues to apply
  (`reduced` when it requests reduced motion, `full` otherwise)
- **AND** a stored level — any of the three — overrides the operating-system preference

#### Scenario: The creation wizard gates ages and emits creation actions
- **WHEN** the creation overlay runs its presets/custom/concept wizard
- **THEN** the age-range gate applies to BOTH the age and the apparent_age fields, the wizard has
  an activate transition, and it emits `creation.*`

#### Scenario: The dismissal bar leaves wizard actions untouched
- **WHEN** the creation overlay's actions are enumerated
- **THEN** no close, exit, or hide-the-surface affordance is rendered in its header or body and
  none is wired to a handler that only stops rendering the overlay
- **AND** this bars the dismissal affordance because the overlay's presence is owned by the
  committed `creation` panel and creation mode presents no surface behind it
- **AND** the wizard's own in-surface actions (the presets/custom/concept tab switch, the draft
  reset, the confirmation screen's cancel, and the activate transition) each carry a real outcome
  and are unaffected

#### Scenario: The map overlay holds against live read-model replacement
- **WHEN** the `local_map` OOB read model is updated while the `MapOverlay` is mounted in the
  running client
- **THEN** its available/unavailable branch re-renders so a replaced payload never leaves a stale
  state, and this holds against live read-model replacement and not only against a story's args

#### Scenario: The help overlay renders the client's own control reference
- **WHEN** the help overlay renders and the deferred-surface assertion is enumerated
- **THEN** the help overlay renders the client's own control reference, which the client
  authoritatively knows, and no authored game-help content
- **AND** the event-log Toasts surface and the design draft's category-to-entry game-help browser
  are named in the deferred-surface assertion together with the read model each waits on, and
  MUST NOT be built or mocked to look real
- **AND** the `help` command's output reaches the client only as narrative text and no committed
  panel carries it

#### Scenario: The held-item bag's total never claims untruncated holdings
- **WHEN** the held-item bag renders from `services.inventory.rows`
- **THEN** the listing is bounded by the payload's row cap and `pagination.inventory_total` is
  surfaced only as the count of rows actually shipped and never as a claim about untruncated
  holdings
- **AND** the bag's backing is the `services` panel's `inventory` section, which the server builds
  for any actor in exploration mode independently of any service host

#### Scenario: The deferred list's not-deferred exclusions name their governing specs
- **WHEN** the deferred-surface assertion excludes the intimate/adult status collapsible, the
  party quickbar and 同伴 ‧ 隊伍 drawer, the persistent objective tracker, and the client-local
  action-feedback toast queue
- **THEN** the intimate collapsible is backed by the `character` panel's `intimate` field
  (`webclient-exploration-menu`'s version-4 character-panel requirement) with completeness and
  absence-when-`null` behaviour governed by `webclient-contextual-hud`'s character-status drawer
  requirement; the party surfaces by the `party` panel (`webclient-party-panel`) with rendering
  and mutation behaviour governed by `webclient-contextual-hud`'s party quickbar and party drawer
  requirements; the objective tracker by the `objectives` panel
  (`webclient-objectives-panel`) with rendering governed by `webclient-contextual-hud`'s
  objective tracker requirement; and the action-feedback queue (`webclient-action-feedback`)
  presents only client-composed or verbatim server-authored action messages rather than a backend
  read model, so its `ToastQueue` component and `feedback-` test-id family are built and
  manifest-listed
- **AND** the deferred event-log Toasts surface remains deferred by its own identity — the
  game-event toast queue bound to a not-yet-existing `event-log` read model, asserted absent by
  its `event-log-`/`toast-` test-id binding — and is distinct from the action-feedback queue

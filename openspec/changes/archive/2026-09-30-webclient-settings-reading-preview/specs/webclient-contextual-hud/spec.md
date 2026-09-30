## MODIFIED Requirements

### Requirement: Narrative prose scale is a client-local preference the settings surface owns
The client SHALL expose a narrative prose scale with three steps, selectable from the settings surface,
whose current step is marked by an indicator that does not rely on colour alone. The scale SHALL apply
to narrative and dialogue prose only — the message window's page text, the complete-log surface's lines,
the prompt line and the settings surface's reading sample, which previews the page text — and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text, so the
stage's measured anchor geometry is unaffected at either supported viewport.

The prose scale and every other setting the surface offers SHALL be client-local presentation state. No
settings control SHALL dispatch an action: the client's action allowlist carries exactly one `options.*`
action, the suggestions dismissal, and this capability adds none. Each setting SHALL be applied
immediately to the presentation it governs — the document's presentation tokens for the prose scale,
the motion level, the text-to-HTML toggle and the colourblind palette, and the message window for the
reading preferences and the motion level — and SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference. Each setting SHALL be re-applied at
load, and SHALL be reset to its default — fully applied, never half-applied — whenever that store
resets. The motion level SHALL follow "The motion level is a client-local preference that governs every
client animation": a stored level overrides the operating system's reduced-motion preference, which
SHALL continue to apply while no level is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the message window's page text, the complete-log surface's lines, the prompt line and the settings surface's reading sample render larger, every other HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1440x900 or 1280x720

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale, the text speed, and the motion level, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale, text speed, and motion level are re-applied after the reload, and after the reset every setting is applied at its default, the motion level following the operating system again, with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no motion level is stored and the operating system requests reduced motion
- **THEN** the effective motion level is `reduced`, so looping and travelling motion stops and message pages appear in full at once; and when the player then selects `完整`, the client honours that stored level over the operating system

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect

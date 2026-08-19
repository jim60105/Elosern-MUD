## ADDED Requirements

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

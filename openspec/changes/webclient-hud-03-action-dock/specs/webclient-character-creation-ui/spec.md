## MODIFIED Requirements

### Requirement: Creation browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at
1440x900 and 1280x720: preset selection, confirmation, activation, and the exploration
snapshot; custom finite controls and free-text field focus; reconnect at each saved draft
stage; server rejection of both underage fields despite bypassed client validation; the
destructive reset confirmation; and stale and duplicate submission behavior. Tests SHALL use
deterministic fixtures, SHALL make no remote, LLM, or image-generation request, SHALL assert
the creation dock is the sole action-dock owner in creation mode and re-renders on
exploration (the shared `#action-dock` node may persist with `data-mode` switching), and SHALL
assert no persona/import field is rendered. That shared node is the floating dock panel itself, so
the panel SHALL NOT be remounted at a mode change; in creation mode it SHALL render neither the tab
bar's tabs nor the breadcrumb, because the creation surface is a modal form rather than a router
frame, while keeping its own chrome, its `data-mode="creation"` attribute, and its role as the
surface's documented focus target. Test waits SHALL gate on
deterministic state — polling the committed store view and the creation-surface DOM with a
bounded deadline — rather than on the raw `#action-dock` element becoming visible, so the
suite stays stable under a loaded CI runner.

#### Scenario: Preset journey completes in Chromium
- **WHEN** a seeded pending character uses arrows and Enter to open a preset card, confirms, and activates
- **THEN** the flow submits `creation.preset` then `creation.activate` once each and the refreshed snapshot shows exploration mode with the creation dock removed

#### Scenario: Underage custom journey is rejected end to end
- **WHEN** a browser fills the custom form with `age=17` after disabling the client-side minimum
- **THEN** the server rejects, the character stays pending, and the error is announced without leaving the creation dock

#### Scenario: Reconnect restores the saved stage in Chromium
- **WHEN** the transport disconnects after a validated `creation.custom` save and reconnects
- **THEN** the new-epoch snapshot rebuilds the form at the `custom_filled` stage and no automatic activation is sent

#### Scenario: Minimum viewport retains creation essentials
- **WHEN** the creation dock renders at 1280x720 with a focused disabled control
- **THEN** the player can read the preset cards, the form fields, the disabled explanation, and the confirmation controls without overlap preventing operation

#### Scenario: Creation dock is the sole owner in creation mode and re-renders in exploration
- **WHEN** the browser is in creation mode with the `creation` panel available
- **THEN** exactly one `#action-dock` element is rendered with `data-mode="creation"` (the creation dock is its sole owner), and after activation hands off to exploration no creation-mode dock remains: the shared dock re-renders as `data-mode="exploration"` when `context_actions` is available, so the shared DOM node may persist rather than being fully removed

#### Scenario: The floating dock panel is the persistent node across a mode change
- **WHEN** the browser hands off from creation mode to exploration mode after activation
- **THEN** the same single `#action-dock` panel element persists with its `data-mode` switched from `creation` to `exploration`, and it is not removed and re-created

#### Scenario: Creation mode renders no tab bar and no breadcrumb
- **WHEN** the dock is rendered in creation mode
- **THEN** it renders the creation surface with no root tabs, no count badge, and no breadcrumb line, and the creation form keeps its own key capture exactly as before

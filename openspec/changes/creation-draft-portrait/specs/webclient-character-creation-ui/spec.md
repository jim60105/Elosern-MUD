# Spec Delta

## ADDED Requirements

### Requirement: Creation portrait controls use committed state and the shared drawer
The creation portrait slot SHALL render server portrait state and emit generation intent without dispatching itself. Its host SHALL reuse the generation drawer with free-text-only capabilities and submit the current form identity through the exact creation action. Admission/results SHALL follow the existing request/revision gate without losing unsent form fields.

#### Scenario: Opening the drawer performs no request
- **WHEN** the player opens the slot’s generation control
- **THEN** the real drawer receives `supports_field_selection: false`, `supports_free_text: true`, `max_cards: 1` and creation context, offers no equipment selection, and sends no action until submit

#### Scenario: Submit reads current form identity
- **WHEN** the player submits from the drawer after editing the form
- **THEN** exactly one `creation.portrait.generate` carries current race/subrace/sex/apparent_age and only the drawer’s custom_prompt, with no concept, display-name, actual-age or stat fields

#### Scenario: Refused input remains editable
- **WHEN** admission fails or the correlated request result rejects
- **THEN** the drawer retains its editable prompt and failure surface, releases request loading through the shared gate, and never resubmits automatically; server unavailability may still disable submit

#### Scenario: All committed states remain accessible
- **WHEN** the panel reports empty, pending, ready, failed or unavailable
- **THEN** the slot uses the current server silhouette except ready uses supplied artwork; pending and unavailable disable generation, failed/unavailable display the safe server reason, failed permits retry, and all transitions have status text announced through a live region

#### Scenario: Server availability drives disabled controls without client probes
- **WHEN** the panel supplies unavailable service state, including after a stale client attempted submission
- **THEN** slot/drawer generation is disabled from that server signal and its reason is visible; the server independently refuses admission, no client probe runs, and prompt/form/optional creation remain usable

#### Scenario: Explicit status refresh does not generate
- **WHEN** the player refreshes unavailable status from the slot or within the drawer
- **THEN** intent reaches existing manual `ui_sync`, no generation request or client probe occurs, and a refreshed healthy/unknown server state permits only a new explicit submit without replaying the refused request

#### Scenario: Form state survives a full portrait journey
- **WHEN** an admitted request publishes pending and later ready or failed while the player navigates steps and edits fields
- **THEN** unsent form values and the current step survive, only the correlated result settles the request UI, and completion never activates or saves the form

#### Scenario: Creation context leaves gallery usage unchanged
- **WHEN** the drawer is mounted without creation context
- **THEN** its existing gallery capabilities, reference behavior and request payload remain unchanged

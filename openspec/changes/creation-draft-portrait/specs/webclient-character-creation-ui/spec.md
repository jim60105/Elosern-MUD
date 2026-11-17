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
- **THEN** the drawer retains its prompt, uses the existing failure surface, unlocks through the shared gate, and never resubmits automatically

#### Scenario: All committed states remain accessible
- **WHEN** the panel reports empty, pending, ready, failed or unavailable
- **THEN** the slot uses the current server silhouette except ready uses supplied artwork; pending and unavailable disable generation, failed displays the supplied safe reason and permits retry, and all transitions have status text announced through a live region

#### Scenario: Connectivity diagnostics do not gate the drawer
- **WHEN** creation has an otherwise valid request while the art client is unreachable
- **THEN** no probe is called or cached verdict consulted by the drawer or admission path; the request follows ordinary admission and the worker's actual failure becomes the retryable failed state

#### Scenario: Form state survives a full portrait journey
- **WHEN** an admitted request publishes pending and later ready or failed while the player navigates steps and edits fields
- **THEN** unsent form values and the current step survive, only the correlated result settles the request UI, and completion never activates or saves the form

#### Scenario: Creation context leaves gallery usage unchanged
- **WHEN** the drawer is mounted without creation context
- **THEN** its existing gallery capabilities, reference behavior and request payload remain unchanged

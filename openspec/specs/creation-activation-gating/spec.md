## Purpose

Guarantee the Web creation dock only shows the activation confirmation after a
save that actually succeeded, and that an activation can only ever apply to the
draft the confirmation was shown for — a rejected save or a changed stored
draft must leave the character pending with no finalization.

## Requirements

### Requirement: Activation confirmation follows a successful save
The Web creation dock SHALL switch to the activation-confirmation view only after the `creation.custom` or `creation.preset` action reports success; on a rejected or failed save it SHALL remain on the current view (the custom form or the preset list) and surface the rejection.

#### Scenario: Rejected custom save stays on the form
- **WHEN** the player submits a custom form whose save the server rejects
- **THEN** the dock remains on the form, shows the rejection, and does not show the activation confirmation

#### Scenario: Rejected preset save stays on the list
- **WHEN** the player picks a preset whose save the server rejects
- **THEN** the dock remains on the preset list, shows the rejection, and does not show the activation confirmation

#### Scenario: Successful save opens the confirmation
- **WHEN** the player submits a custom form or a preset whose save succeeds
- **THEN** the dock switches to the activation-confirmation view for the just-saved draft

### Requirement: Activation is bound to the last successfully saved draft
The system SHALL reject an activation attempt whose fingerprint does not match the draft it is about to activate, with a stable rejection code. A rejected save attempt SHALL invalidate the confirmation, so a leftover confirmation cannot activate an older stored draft.

#### Scenario: Stale confirmation cannot activate an older draft
- **WHEN** an activation is submitted while the stored draft differs from the draft the confirmation was shown for
- **THEN** the activation is rejected and no character is activated

#### Scenario: Rejected save invalidates the confirmation
- **WHEN** a save is rejected while an older draft and its confirmation remain stored
- **THEN** a subsequent activation is refused with a stable code and no character is activated

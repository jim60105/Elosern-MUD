## ADDED Requirements

### Requirement: Activation confirmation follows a successful save

The Web creation dock SHALL switch to the activation-confirmation view only after the `creation.custom` action reports success; on a rejected or failed save it SHALL remain on the form and surface the rejection.

#### Scenario: Rejected custom save stays on the form

- **WHEN** the player submits a custom form whose save the server rejects
- **THEN** the dock remains on the form, shows the rejection, and does not show the activation confirmation

#### Scenario: Successful save opens the confirmation

- **WHEN** the player submits a custom form whose save succeeds
- **THEN** the dock switches to the activation-confirmation view for the just-saved draft

### Requirement: Activation is bound to the last successfully saved draft

The system SHALL reject an activation attempt whose fingerprint does not match the draft it is about to activate, with a stable rejection code.

#### Scenario: Stale confirmation cannot activate an older draft

- **WHEN** an activation is submitted while the stored draft differs from the draft the confirmation was shown for
- **THEN** the activation is rejected and no character is activated

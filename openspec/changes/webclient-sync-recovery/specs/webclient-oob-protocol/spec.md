# Spec Delta

## MODIFIED Requirements

### Requirement: Protocol failures degrade without disabling text play
Before a valid full snapshot, the WebClient SHALL disable graphical mutation controls. A malformed/incompatible-base/incomplete publication SHALL preserve the last committed presentation, mark it unavailable for graphical mutation, and coalesce at most one automatic complete resynchronization per failure episode. A failed repair SHALL remain locked without automatic retry. An incompatible protocol SHALL disable all graphical mutation controls and offer reload. OOB initialization failure SHALL leave narrative output and ordinary text input usable.

#### Scenario: Repeated malformed panel does not loop synchronization
- **WHEN** a malformed status payload is received again after the renderer's single recovery sync
- **THEN** the prior complete presentation remains unavailable for graphical mutations and no additional automatic sync loop starts

#### Scenario: Protocol mismatch preserves command access
- **WHEN** the browser receives an unsupported protocol version
- **THEN** graphical mutations are locked and a reload notice is shown while ordinary text input remains usable

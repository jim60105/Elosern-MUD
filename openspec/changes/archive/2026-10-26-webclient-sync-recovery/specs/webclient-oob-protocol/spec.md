# Spec Delta

## MODIFIED Requirements

### Requirement: Protocol failures degrade without disabling text play
Before a valid full snapshot the WebClient SHALL disable graphical mutations. A malformed, incompatible-base or incomplete publication SHALL keep the last committed presentation unchanged and unavailable for graphical mutation, coalescing one automatic complete resync per failure episode. A failed repair SHALL stay locked without retry. An incompatible protocol SHALL disable all graphical mutations and offer reload. OOB initialization failure SHALL leave narrative output and text input usable.

#### Scenario: Repeated malformed panel does not loop synchronization
- **WHEN** a malformed status payload is received again after the renderer's single recovery sync
- **THEN** the prior complete presentation remains unavailable for graphical mutations and no additional automatic sync loop starts

#### Scenario: Protocol mismatch preserves command access
- **WHEN** the browser receives an unsupported protocol version
- **THEN** graphical mutations are locked and a reload notice is shown while ordinary text input remains usable

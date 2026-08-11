## ADDED Requirements

### Requirement: Unpuppet retires the active presentation and dispatch sequence

When a session unpuppets (OOC), the system SHALL retire the session's presentation coordinator and dispatch sequence (epoch, request cache, in-flight marker) and SHALL notify the client to clear character panels and lock mutations until the next puppet.

#### Scenario: OOC clears character UI and mutation access

- **WHEN** a WebClient session executes `ooc` (unpuppet)
- **THEN** the client receives a state transition that clears character panels and blocks further mutations, and the server retires the old sequence

#### Scenario: Repuppet of the same character starts a fresh sequence

- **WHEN** a session unpuppets and later repuppets the same character
- **THEN** the server publishes a new epoch/revision, does not reuse the old completed-result cache or in-flight marker, and the client applies the fresh snapshot

### Requirement: No-puppet actions receive a bounded rejection

When a `ui_action` arrives without a puppet, the system SHALL respond with a bounded protocol rejection (no character state) so the client can release its in-flight mutation lock.

#### Scenario: Stale click after OOC releases the client lock

- **WHEN** the client sends a `ui_action` while the session has no puppet
- **THEN** the server returns a bounded rejection envelope, and the client's mutation lock is released

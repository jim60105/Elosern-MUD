## ADDED Requirements

### Requirement: Every host-authoring place names its host's NPC profile
The host profile key SHALL be part of a place's all-or-nothing host group: a place that authors a host SHALL name a host profile key that resolves in the NPC profile registry, and a hostless place SHALL name none. A hosted place without a profile key SHALL fail load as a partially authored host, naming the place and the missing field; no generic or placeholder profile SHALL be substituted.

#### Scenario: A hosted place without a profile fails load
- **WHEN** a synthetic place authors a complete host but no host profile key
- **THEN** place-registry validation raises naming the place and listing the host profile key as missing

#### Scenario: Every shipped hosted place names a resolvable profile
- **WHEN** the shipped place registry is validated
- **THEN** every place that authors a host names a host profile key that resolves to a valid profile

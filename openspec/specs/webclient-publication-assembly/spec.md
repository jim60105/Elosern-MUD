# webclient-publication-assembly Specification

## Purpose
Keep bounded multipart presentation data invisible until a complete validated publication can atomically become the authoritative browser state.

## Requirements

### Requirement: General assembly adopts one complete validated publication
The receiver SHALL stage one general transfer per active transport and commit only after exact ordered parts, declared sizes, strict decode, logical schemas and final baseline admission all pass. Partial parts SHALL NOT establish epoch or change presentation, metadata, revision or subscriber-visible state.

#### Scenario: Initial multipart snapshot establishes state once
- **WHEN** snapshot parts arrive on a transport awaiting initial state
- **THEN** no epoch is active until the final valid logical snapshot commits and subscribers observe one adoption

#### Scenario: Multipart delta is atomic
- **WHEN** a valid multi-part delta changes panels mode and time
- **THEN** all old fields remain until complete validation and one staged commit adopts the target

#### Scenario: Header or body contradiction discards transfer
- **WHEN** a part changes base/count/length/transfer identity or decoded logical metadata disagrees
- **THEN** buffers are discarded, prior complete state is preserved and recovery is signaled

#### Scenario: Missing duplicate and reordered parts cannot commit
- **WHEN** the next part index is duplicated or skips the expected index
- **THEN** the incomplete transfer is abandoned with no adoption

### Requirement: Assembly lifetime and teardown are explicit
General assembly SHALL retain <=16MiB in one live transfer for a fixed30000ms deadline from its first accepted part. Later traffic SHALL NOT extend it. Disconnect, epoch retirement, detach, expiry and supersession SHALL release buffers/timers independently of specialized map assembly.

#### Scenario: Deadline expires without traffic
- **WHEN** the final part never arrives and first-part deadline passes
- **THEN** the transfer is freed and one recovery-needed event occurs without requiring another frame

#### Scenario: New snapshot supersedes old incomplete data
- **WHEN** a valid newer same-epoch snapshot begins at part0 or arrives intact
- **THEN** obsolete assembly is freed and only a complete valid newer snapshot may commit

#### Scenario: Later delta cannot skip predecessor
- **WHEN** a delta arrives while an earlier publication remains incomplete
- **THEN** no later delta commits and complete synchronization is requested

#### Scenario: Old transport callbacks cannot change state
- **WHEN** an old generation part or expiry callback fires after reconnect
- **THEN** it cannot allocate buffers mutate the live state or initiate live-generation recovery

#### Scenario: Both assembly owners release on disconnect
- **WHEN** one general and one specialized map assembly are buffered
- **THEN** disconnect frees both owners and timers while their bounds remain separately enforced

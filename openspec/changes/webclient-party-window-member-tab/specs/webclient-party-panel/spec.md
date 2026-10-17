# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The party drawer offers possession controls per companion`
- TO: `### Requirement: The party window member tab offers possession controls per companion`

## MODIFIED Requirements

### Requirement: The party window member tab offers possession controls per companion
The party window's 成員 tab SHALL render the `party_member` panel's server-authored possess or release descriptor, with its enablement and reason, for every effective companion selected on the member rail, including temporary actors beyond the general quota. Dispatch SHALL remain through the shared action path. No dedicated escort-control screen SHALL be introduced. Source-aware dismissal SHALL route to existing quest abandonment choices when an effective escort reason would be removed.

#### Scenario: Beyond-quota temporary actor remains controllable
- **WHEN** a temporary-only sixth companion is selected on the rail and passes possession gates
- **THEN** its 附身 control dispatches `explore.possess` for its exact identity and the normal 解除附身 control remains available while possessing

#### Scenario: A possessable companion row offers the action
- **WHEN** the 成員 tab shows a co-located bound companion whose possess descriptor is enabled
- **THEN** the action bar carries the 附身 control and dispatching it submits `explore.possess` with the companion's id

#### Scenario: A gated companion row shows the gate honestly
- **WHEN** the companion's possess descriptor is disabled with a gate reason
- **THEN** the control renders disabled with the committed reason in the action bar's reason slot, never hidden

#### Scenario: The panel payload schema is untouched
- **WHEN** possession controls render for general and temporary companions
- **THEN** they read only the `party_member` descriptors and the `party` v3 rows, and server and client validators agree on both

#### Scenario: Possession state rides the vocabulary and banner only
- **WHEN** possession control state is displayed
- **THEN** control permission comes only from the `party_member` descriptor and the possession banner, the rail carries no possession marker and no "you" marker, and the window is otherwise identical while possessing

# Spec Delta

## MODIFIED Requirements

### Requirement: sync_grid() is distinct from sync_all() and instantiates real rooms and exits
Without an explicit settlement selection, grid synchronization SHALL instantiate every declared sparse node and directed road as real rooms and exits through the existing deterministic synchronizer, remaining distinct from the lore-record mirror.

#### Scenario: sync_grid produces real, puppetable-adjacent room objects
- **GIVEN** a synthetic published world containing multiple settlement graphs
- **WHEN** grid synchronization runs without a settlement selection against an empty database
- **THEN** every declared graph materializes its rooms and directed roads through the shared planner and writer
- **AND** production runtime synchronization invokes this default full-roster path

#### Scenario: sync_all's own behavior is unaffected
- **WHEN** lore-record synchronization runs
- **THEN** it creates or updates lore mirror records without creating grid rooms or exits

## ADDED Requirements

### Requirement: Explicit settlement selection bounds test synchronization
Explicitly selected settlement synchronization SHALL use the shared validated planning and transactional writing path for the declared maps, reject unknown or malformed selections before mutation, and leave unselected managed settlement state unchanged except for the existing global reverse-starting-room exit prune.

#### Scenario: Unrelated roster growth does not add selected graph work
- **GIVEN** synthetic settlements A and B and a test declaration selecting A
- **WHEN** selected grid synchronization runs and then runs again after unrelated synthetic graphs are added
- **THEN** only A reaches graph planning and application on each call
- **AND** A has its independently declared room and road topology with stable identities and an empty repeat-change report
- **AND** B and the added graphs gain no rooms, roads or forward starting-room bridges

#### Scenario: Selection is explicit and deterministic
- **GIVEN** synthetic settlements A and B declared in a one-shot iterable in reverse order and with duplicates
- **WHEN** selected grid synchronization runs
- **THEN** each selected graph is planned and applied once in deterministic map-ID order
- **AND** the published complete map-world bundle is unchanged

#### Scenario: Malformed selection rejects before planning
- **WHEN** a declaration is a bare string or contains a non-string member
- **THEN** it is rejected as malformed before any planner or persistent writer runs
- **AND** rooms, exits, tags and cached coordinates retain their prior state

#### Scenario: Unknown selection rejects atomically
- **WHEN** a declaration contains both a valid map and an unknown map
- **THEN** rejection names the unknown map before any planner or persistent writer runs
- **AND** rooms, exits, tags and cached coordinates retain their prior state

#### Scenario: Explicit empty selection performs no persistent synchronization
- **WHEN** a test supplies an empty settlement selection
- **THEN** no settlement graph, art, forward bridge, display registration, wilderness script or reverse exit is created, changed or deleted

#### Scenario: Selected batch failure preserves the prior state
- **GIVEN** two selected synthetic settlements with occupied and referenced rooms
- **WHEN** application fails in the later selected graph after the earlier graph has written
- **THEN** the entire selected batch rolls back durable and cached coordinates, occupant locations, homes, inbound references and knowledge state

#### Scenario: Ancillary settlement work respects the selection
- **GIVEN** selected A and materialized unselected B, each carrying drifted ordinary managed state on its art, legacy display registration and forward starting-room bridge
- **WHEN** selected synchronization runs
- **THEN** only selected maps receive art convergence, legacy display cleanup, forward starting-room bridges and wilderness gate provisioning
- **AND** A's drifted ancillary state converges
- **AND** B's rooms, directed roads, art, display registration and forward bridge remain unchanged
- **AND** omitted maps produce no missing-gate warning merely because they were not materialized

#### Scenario: Global reverse-entry pruning remains in force
- **GIVEN** an unselected map has an exit pointing into the starting room
- **WHEN** a nonempty selected grid synchronization runs
- **THEN** the existing global prune removes that reverse exit and emits its existing event

#### Scenario: Wilderness selection uses destination map identity
- **GIVEN** a synthetic wilderness entry whose anchor key differs from its destination settlement ID
- **WHEN** the destination settlement is selected for wilderness synchronization
- **THEN** its gate is provisioned through the existing gate writer and unselected destination gates are untouched
- **AND** omitted selection retains complete production gate provisioning

#### Scenario: Startup test selection retains the production writer
- **WHEN** a non-browser startup test declares settlements and executes real startup inside its selection adapter
- **THEN** the real grid and wilderness synchronizers receive that fixed selection
- **AND** their original bindings are restored after success or failure
- **AND** production startup outside the adapter still synchronizes the complete roster

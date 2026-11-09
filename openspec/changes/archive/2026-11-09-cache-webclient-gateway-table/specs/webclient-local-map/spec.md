## ADDED Requirements

### Requirement: Registered gateway resolution is built once per published map world
The map presenters SHALL resolve registered wilderness gateways from one table derived once per published map world, built with a single settlement reference index, and SHALL rebuild it only when a different map world, entry registry or settlement graph set is published. Table rows and lookups SHALL keep registry order, skip gates without an approach cell, and return the first matching gate.

#### Scenario: Repeated lookups reuse one table
- **WHEN** gateway rows, approach-cell lookups and gate-room lookups are requested any number of times while one map world stays published
- **THEN** the gateway table SHALL be built at most once and the settlement reference index SHALL be built at most once for that table, never once per registered gate

#### Scenario: A newly published input set rebuilds the table
- **WHEN** a different wilderness entry registry or settlement graph set is published after the table was built
- **THEN** the next lookup SHALL rebuild the table from the newly published values, and no lookup SHALL return a row derived from the previously published values

#### Scenario: Gates without an approach cell are skipped
- **WHEN** a registered gate has no approach cell
- **THEN** it SHALL be absent from the gateway rows and from both lookups, and no error SHALL be raised

#### Scenario: Duplicate cells keep the first registered gate
- **WHEN** two registered gates share an approach cell, or share a gate room and map key
- **THEN** the corresponding lookup SHALL return the gate that comes first in registry order, and the gateway rows SHALL list every gate in registry order

#### Scenario: Callers receive an independent row list
- **WHEN** a caller mutates the gateway row list it received
- **THEN** a later request for the gateway rows SHALL return the unmodified rows

### Requirement: Remembered wilderness boundaries do not probe every visited cell
On the wilderness layer, the remembered-boundary scan SHALL consider only visited nodes whose canonical ID is a registered gateway approach cell, so the number of gateway lookups per render SHALL NOT grow with the number of visited cells, while the emitted payload stays identical to resolving every visited cell individually.

#### Scenario: Lookup count is independent of exploration
- **WHEN** the same wilderness position is rendered once with few visited ordinary cells and once with many more visited ordinary cells
- **THEN** both renders SHALL perform the same number of per-cell approach-cell lookups, bounded by the eight in-view neighbours

#### Scenario: Remembered boundaries are unchanged
- **WHEN** a character has stood on registered approach cells and ordinary cells and is rendered outside the field of view of those approach cells
- **THEN** the remembered nodes SHALL be exactly the disclosed approach cells it visited outside the drawn 3x3 field, ordered by descending last-seen tick then ascending node ID, bounded by the remembered ceiling after filtering, and labelled with the far-side name qualified on collision

#### Scenario: An approach cell outside the wilderness bounds is ignored
- **WHEN** a registered gate's approach cell lies outside the published wilderness bounds and the wilderness layer is rendered
- **THEN** the render SHALL succeed, and that gate SHALL never appear as a remembered boundary

# Spec Delta

## MODIFIED Requirements

### Requirement: Replacing a settlement preserves every referenced node identity
A replace operation SHALL require a binding for every protected node. Protected nodes are those named by an interior doorway, a district landmark, or an external incoming reference, plus the anchor; with no reference index, every existing node is protected. Unknown, duplicate or missing bindings SHALL be refused with no write. A bound node SHALL keep its identifier, key and description, with its position, roads and directions taken from the plan.

#### Scenario: Missing binding
- **WHEN** a synthetic replace omits the binding for a node that an interior doorway names
- **THEN** the command exits with status 1 naming that node and the workspace digest is unchanged

#### Scenario: Bound identities survive
- **WHEN** a synthetic replace binds every protected node
- **THEN** each bound node keeps its identifier, key and description. The interior doorway and district landmark still resolve to it, the anchor binding stays the anchor, and the written map passes the terrain-fit lint with no error.

#### Scenario: Refused bindings
- **WHEN** a replace binds the existing anchor to a non-anchor slot, binds two nodes to one slot, or names a node or slot that does not exist
- **THEN** each is refused with an error naming the binding and no file changes

#### Scenario: Dropped and missing-index cases
- **WHEN** an unreferenced existing node is left unbound with a current reference index, and separately the reference index is absent
- **THEN** the first replace drops that node and reports it, and the second refuses until every existing node is bound

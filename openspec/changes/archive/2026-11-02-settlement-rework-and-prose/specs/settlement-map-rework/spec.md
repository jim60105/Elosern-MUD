## Purpose

Rework an existing settlement local map from a generated plan without losing any node identity that other documents or code join on, and write zh-TW node prose as a separate pass that only ever changes node names and descriptions.

## ADDED Requirements

### Requirement: Replacing a settlement preserves every referenced node identity
A replace operation SHALL require a binding for every protected node. Protected nodes are those named by an interior doorway, a district landmark, an external incoming reference or the city gate, plus the anchor; with no reference index, every existing node is protected. Unknown, duplicate or missing bindings SHALL be refused with no write. A bound node SHALL keep its identifier, key and description, with its position, roads and directions taken from the plan.

#### Scenario: Missing binding
- **WHEN** a synthetic replace omits the binding for a node that an interior doorway names
- **THEN** the command exits with status 1 naming that node and the workspace digest is unchanged

#### Scenario: Bound identities survive
- **WHEN** a synthetic replace binds every protected node
- **THEN** each bound node keeps its identifier, key and description. The interior doorway, district landmark and city gate still resolve to it, the anchor binding stays the anchor, and the written map passes the terrain-fit lint with no error.

#### Scenario: Refused bindings
- **WHEN** a replace binds the existing anchor to a non-anchor slot, binds two nodes to one slot, or names a node or slot that does not exist
- **THEN** each is refused with an error naming the binding and no file changes

#### Scenario: Dropped and missing-index cases
- **WHEN** an unreferenced existing node is left unbound with a current reference index, and separately the reference index is absent
- **THEN** the first replace drops that node and reports it, and the second refuses until every existing node is bound

### Requirement: Nearest bindings resolve deterministically
A binding written as nearest to a slot SHALL resolve, in binding-file order, to the closest still-unbound approach or filler slot of the plan. Ties SHALL be broken by plan order. An unbound generated slot whose identifier collides with a final identifier SHALL take the first free numeric suffix. Identical inputs SHALL give byte-identical output.

#### Scenario: Nearest resolution and repeat
- **WHEN** two existing nodes are bound as nearest to the same slot, in a fixed order, and the replace runs twice from the same original document
- **THEN** the first takes the closest filler or approach slot and the second the next closest, and both outputs are byte-identical

#### Scenario: Identifier collision
- **WHEN** an unbound generated slot has the same identifier as an existing node bound elsewhere
- **THEN** the generated slot receives the first free `_2`, `_3`… suffix and every identifier in the map is unique

### Requirement: Prose briefs and prose application touch only names and descriptions
The brief command SHALL describe, without writing, each node's identifier, current key, role, bearing and distance from the anchor and whether its description is empty, together with the settlement's site summary. The prose command SHALL replace the key and description of the listed nodes only, and SHALL reject unknown identifiers or empty text atomically.

#### Scenario: Brief is read-only
- **WHEN** the brief command runs on a synthetic map
- **THEN** it prints one entry per node with the documented fields, and the workspace digest is unchanged

#### Scenario: Prose application
- **WHEN** a prose file sets the key and description of two nodes
- **THEN** only those two nodes' key and description change, and every other byte of the document's data is unchanged

#### Scenario: Atomic rejection
- **WHEN** a prose file names one unknown node, or gives one node an empty key or description, alongside valid entries
- **THEN** the command exits with status 1 naming each defect and the document is unchanged

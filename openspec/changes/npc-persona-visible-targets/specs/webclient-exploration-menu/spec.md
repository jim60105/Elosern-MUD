## ADDED Requirements

### Requirement: Interaction publication and shared local target resolution use visible candidates
The interaction target list SHALL include only room-content targets visible to the actor under the existing room view/search policy, applied before deterministic ordering and list limits. Excluded targets SHALL contribute no identity, display name, portrait, disabled affordance or editor-availability information. Local host uniqueness used by these target affordances SHALL be evaluated over those visible candidates. Id-based exploration actions using the shared local-presence policy SHALL re-resolve through that same current visible candidate set, preserving each action's existing missing-target outcome and later capability, possession and schedule checks. A previously published id SHALL NOT serve as continuing authorization.

#### Scenario: Denied targets never publish
- **WHEN** the actor's room contains visible and view-denied or search-denied NPCs and Monsters
- **THEN** interaction descriptors include only visible eligible targets and no identifier, label or disabled row for denied targets

#### Scenario: Hidden targets cannot crowd out the visible roster
- **WHEN** enough denied targets precede a visible NPC by identity to fill the interaction limit before filtering
- **THEN** the visible NPC still appears within the bounded filtered list

#### Scenario: Hidden duplicate host does not disable visible host navigation
- **WHEN** a room contains one visible merchant host and another merchant host denied to the actor
- **THEN** the visible target retains its uniquely local shop affordance and the hidden host is not disclosed

#### Scenario: Forged hidden talk target rejects
- **WHEN** a client submits talk-open for a co-located conversable NPC denied by current visibility
- **THEN** the existing no-NPC result is returned and no dialogue session or speech is emitted

## ADDED Requirements

### Requirement: Persona target admission revalidates current room visibility
Both persona actions SHALL resolve the target from the actor's currently visible co-located NPC-family candidates on every request. Visibility SHALL follow the same existing room visibility policy as ordinary room appearance, including view and search authorization and the policy's default semantics and overrides. A target denied either check SHALL be treated as absent with `npc_persona.no_target`, the ordinary generic missing-target message, and no result data or private target details. Visibility SHALL NOT replace authenticated active account-owned character admission, NPC-family validation, possession/mode gates, or revalidation on update; it SHALL NOT introduce a talk-schedule requirement.

#### Scenario: View-denied NPC cannot expose its card
- **WHEN** an ordinary authenticated activated actor submits read or update for a co-located NPC whose view access denies that actor
- **THEN** both requests reject as `npc_persona.no_target` without card, hidden identity, greeting, target name or version data and with no persisted change

#### Scenario: Search denial also blocks author access
- **WHEN** a co-located NPC allows view but denies search to the actor
- **THEN** read and update reject with the same non-disclosing missing-target outcome

#### Scenario: Visibility lost after opening invalidates save
- **WHEN** an actor reads a visible NPC and view or search access becomes denied before update
- **THEN** update rejects as absent without changing persona, greeting or version

#### Scenario: Visible sleeping NPC remains author-editable
- **WHEN** ordinary view access permits a co-located NPC, its search lock is absent under the standard permissive search default, and its schedule blocks talking
- **THEN** persona read and valid version-checked update succeed for the authorized actor without requiring a conversation or schedule permission

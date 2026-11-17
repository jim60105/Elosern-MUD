# Spec Delta

## MODIFIED Requirements

### Requirement: Cross-layer relationships edit one owner and expose both meanings
Entrance tools SHALL identify and navigate both qualified endpoints and their directional meaning while saving the relationship exactly once in its owning document.

#### Scenario: Edit an entrance
- **WHEN** a two-way exterior/interior relationship endpoint or return label changes
- **THEN** one source document records both meanings and navigation reaches either endpoint with return context

#### Scenario: Protected start and invalid target
- **WHEN** an entrance selects an absent/wrong-domain target, or the entrance tool's kinds are listed
- **THEN** invalid fields identify their relationship without saving, and no starting-room entry kind is offered or saved, because settlements declare no starting-room entrance

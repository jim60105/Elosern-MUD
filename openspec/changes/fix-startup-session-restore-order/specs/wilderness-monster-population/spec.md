## ADDED Requirements

### Requirement: Population reconciliation never destroys an active-session participant

Wilderness population reconciliation SHALL skip deleting or replacing any monster that a persisted active combat session still references, until that session is restored and settled.

#### Scenario: Session-referenced monster is preserved during reconciliation

- **WHEN** `sync_wilderness` reconciliation runs while a persisted session references a wilderness monster (including one with zero HP after a committed terminal round)
- **THEN** the referenced monster is neither deleted nor respawned by the reconciliation; it is left for session restoration to settle

#### Scenario: Settled monsters are reconciled normally

- **WHEN** no persisted session references a wilderness monster
- **THEN** normal living-conformance reconciliation (delete defeated, respawn expected) proceeds unchanged

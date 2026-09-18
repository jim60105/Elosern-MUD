## ADDED Requirements

### Requirement: The conferral store has a revocation primitive reachable from a skill
A deterministic-core revocation primitive SHALL exist in the same module as the conferral write. It
SHALL clear the target's recorded skill grants and remove every `conferred_growth_rate` buff instance
on that target, regardless of which source wrote them, leaving the target's own owned skills and every
other buff untouched. Revocation SHALL be reachable from a skill through a `revoke_grants` effect
prefix whose handler declares the `skill_grants` and `buffs` surfaces, so both writes ride the existing
snapshot/restore face. Revocation SHALL be total rather than selective: it takes no source filter and
no skill filter.

#### Scenario: Revocation clears both halves of the conferral vocabulary
- **WHEN** the revocation primitive runs on a target holding grants from two different sources and an
  active `conferred_growth_rate` buff
- **THEN** the target holds no conferred grant, no `conferred_growth_rate` buff instance remains, and
  `effective_value()` returns the unmultiplied base for the affected traits

#### Scenario: Revocation leaves the target's own skills and unrelated buffs alone
- **WHEN** revocation runs on a target that owns its own multiplier passive and carries an unrelated
  active buff
- **THEN** the owned passive still folds into `effective_value()` and the unrelated buff instance is
  still active

#### Scenario: Revocation on a target with nothing conferred is a clean no-op
- **WHEN** revocation runs on a target holding no grant and no conferred growth-rate buff
- **THEN** it completes without raising and changes no stored state

#### Scenario: A rolled-back revocation restores both stores
- **WHEN** a resolution that revoked grants has a later pending effect fail, restoring the action
  snapshot
- **THEN** the target's `skill_grants` and buff store are byte-equal to their pre-action values

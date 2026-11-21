# Spec Delta

## MODIFIED Requirements

### Requirement: Activation follows complete accepted evidence
Existing production variants SHALL remain reflex until attack/tactics regressions, real production smoke, the approved manual campaign, selector threshold, complete-policy performance and repository contract gate pass. Initial deliberation activation SHALL name a small explicit registered variant set with independently authored intelligence.

#### Scenario: Release prerequisite
- **WHEN** any required behavior evidence, valid-action rate or performance criterion is missing or fails
- **THEN** production activation does not proceed and no configuration-only completion claim is made

#### Scenario: Named first activation
- **WHEN** all prerequisites pass and selected variants are enabled
- **THEN** the loaded startup tuning names the exact variants and their independently authored intelligence values, its configuration fingerprint matches, and a real affected encounter exists; other variants remain reflex

### Requirement: Expansion and retuning require affected evidence
Expansion SHALL follow review of valid-action rates, wait/exclusion causes, resource use and observed behavior. Changed mode values, reflex metric/sampling or temperature SHALL produce new fingerprints and fresh affected evidence. Old-fingerprint acceptance claims SHALL NOT be presented for changed tuning.

#### Scenario: Rename and metric invalidate evidence
- **WHEN** mode values or reflex algorithm/temperature/primary damage coefficient changes
- **THEN** current evidence is regenerated under the resulting fingerprints; old-fingerprint acceptance claims are not reused for the changed tuning

#### Scenario: Focused retuning
- **WHEN** weights or temperature of an affected profile change later
- **THEN** focused scenarios rerun without an automatic all-archetype campaign or combat stat rebalance

### Requirement: Legacy mode rollback is demonstrated
Selected variants SHALL be switchable to permanent reflex without data migration or DB restoration. Disk tuning edits SHALL require restart validation/loading. New sessions SHALL use loaded startup tuning without reloading disk. Existing sessions SHALL retain recorded tuning until termination or restart. Restart SHALL clear tactical history. Rollback SHALL use the current reflex skill contract rather than historical skill-dice behavior.

#### Scenario: Rollback encounter
- **WHEN** an activated variant mode is edited to reflex and restart loads it
- **THEN** real smoke exercises retained target/flee behavior and current first_owned or independently seeded output sampling; non-monster delegation and transactions remain unchanged

#### Scenario: A new session does not reload configuration
- **WHEN** a disk mode is edited while the process stays active and a new session begins
- **THEN** it uses already-loaded startup tuning; only a process that loaded reflex supplies valid reflex rollback evidence

#### Scenario: Rollback error boundary
- **WHEN** a DB or resolver exception occurs during rollback verification
- **THEN** it retains its existing boundary and is never reported as an AI invalid-state warning

## REMOVED Requirements

### Requirement: Release evidence is reproducible and scoped
**Reason**: A committed release-evidence directory duplicated git history and the owning change archive. `docs/` describes current state only, so the reproducible-evidence record is no longer part of the current contract.

**Migration**: Use `git log` and the archived changes under `openspec/changes/archive/2026-10-14-monster-ai-*` for the original record. Delete `docs/development/monster-ai-activation-evidence/`, `docs/development/monster-ai-manual-evidence/` and the evidence-file assertions in `world/rules/tests/test_monster_ai_activation.py`; the live-tuning activation assertions remain.

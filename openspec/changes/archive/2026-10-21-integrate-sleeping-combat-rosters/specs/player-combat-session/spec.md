# Spec Delta

## ADDED Requirements

### Requirement: Sleeping roster members remain present without commands
Otherwise eligible living present sleeping allies SHALL join and rebuild in the roster, separate from knockout/defeat sets. Sleep SHALL exclude required command collection and execution without an automatic attack. Owner/commander identity and actor-scoped skill/resource costs SHALL remain unchanged.

#### Scenario: Mixed sleeping party
- **WHEN** a sleeping commander and awake companion engage valid local hostiles
- **THEN** the commander stays session owner and targetable; only eligible awake allies require commands and pay their own costs

#### Scenario: Reload draft
- **WHEN** a session with a sleeping member and unfinished draft reconnects
- **THEN** sleep restriction and valid draft entries restore without time, automatic action or synthetic knockout

### Requirement: Live rounds do not simulate natural fatigue or awakening
Ordinary completed rounds SHALL change neither reserve nor projected fatigue merely through elapsed time. The clock SHALL remain terminal-only, with six-second round accounting and the existing 100-round cap. Sleep SHALL persist until terminal settlement unless a future explicit state effect changes it.

#### Scenario: Threshold sleeper
- **WHEN** a sleeper just below the wake threshold completes multiple nonterminal rounds
- **THEN** reserve and posture remain unchanged, no natural wake timer runs, and normal targeting remains available

#### Scenario: Future explicit boundary
- **WHEN** a synthetic explicit posture change is recorded at a round boundary
- **THEN** eligibility can change without a permanent sleep lock, without ticking fatigue or advancing the clock; no waking ability is authored


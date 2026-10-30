# Spec Delta

## Purpose

Publish commit-qualified structured travel notices and render the travel band log without parsing room prose. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Travel notices are committed structured events
The server SHALL publish bounded typed travel notices with stable causal IDs and server-rendered text only for committed observed wilderness effects or a successful look, without deriving importance from prose.

#### Scenario: Commit and replay
- **WHEN** synthetic move/skip/look effects commit, roll back or deliver the same causal fact twice
- **THEN** only committed effects publish once with stable IDs, reads create none and ordinary narration remains available

#### Scenario: Closed wire union
- **WHEN** every supported kind and malformed, extra-key or oversize entries cross Python and JS validation
- **THEN** only exact bounded kind-specific records adopt, with no hidden source metadata or invented camp outcome

### Requirement: Travel log retains typed chronological entries
The travel band SHALL render a bounded chronological day-grouped typed log with time and non-colour kind cues in a polite live region, retaining ordinary prose only in the full log.

#### Scenario: Replay and lifecycle
- **WHEN** duplicate batches, refusal messages and a new epoch arrive
- **THEN** entries append once in chronological order, the bounded history retires with the epoch and raw room prose never becomes a travel event

#### Scenario: Safe full look
- **WHEN** a look event contains multiline prose or markup-like text
- **THEN** the summary remains one entry and full prose stays safely readable without executing markup


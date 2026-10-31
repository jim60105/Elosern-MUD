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

#### Scenario: Concurrent causal groups do not overwrite notices
- **WHEN** two groups queue before one drain and one group contains repeated or additional source facts
- **THEN** each drained publication contains its own immutable ID-stable ordered batch, exact duplicate facts are inert and snapshot replay exposes only the latest published batch

### Requirement: Travel log retains typed chronological entries
The travel band SHALL render a bounded chronological day-grouped typed log with time and non-colour kind cues in a polite live region, retaining ordinary prose only in the full log.

#### Scenario: Replay and lifecycle
- **WHEN** duplicate batches, refusal messages and a new epoch arrive
- **THEN** entries append once in chronological order, the bounded history retires with the epoch and raw room prose never becomes a travel event

#### Scenario: Safe full look
- **WHEN** a look event contains multiline prose or markup-like text
- **THEN** the summary remains one entry and full prose stays safely readable without executing markup

#### Scenario: Discrete refusal before queued walking exists
- **WHEN** a matching ordinary explore.move fails during travel and its result repeats before or after walking UI is installed
- **THEN** the common recognized-result hook adds one travel refusal and retains exactly the existing single full-log refusal; foreign results add neither


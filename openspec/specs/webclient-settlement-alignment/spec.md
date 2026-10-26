# webclient-settlement-alignment Specification

## Purpose
Align complete canonical presentation after terminal combat and completed explicit time-skipping while retaining incremental ordinary action settlement.

## Requirements

### Requirement: Every completed combat termination is a fresh checkpoint
Newly committed combat termination SHALL replace its settlement delta with one freshly rendered complete eager snapshot, including terminal openings, successful escape and other terminal outcomes. Ordinary combat start and nonterminal rounds SHALL remain incremental. Terminal round presentation context SHALL remain action-local.

#### Scenario: Terminal opening aligns
- **WHEN** combat resolves terminally during its opening or a field cast starts and ends it
- **THEN** one fresh complete snapshot carries the committed terminal state and precedes its result

#### Scenario: Ordinary nonterminal round stays incremental
- **WHEN** combat starts or a normal continuing round completes
- **THEN** only actual changed candidates and metadata publish, with no checkpoint snapshot

#### Scenario: Successful escape and exam completion align
- **WHEN** a confirmed party exit succeeds or a guild exam settles terminally
- **THEN** both paths publish one final fresh complete snapshot, with unchanged deterministic settlement authority

#### Scenario: Text terminal path aligns without replay beats
- **WHEN** a text command terminates combat and later reconnect occurs
- **THEN** the text settlement aligns canonical eager state and reconnect does not replay an old action-local round

### Requirement: Completed explicit skips align after authoritative settlement
Completed rest sleep or explicit player-driven time skip SHALL freshly align once after final committed settlement. Sleep entry, choice opening, retained incomplete continuation, rejected actions and replayed receipts SHALL NOT independently qualify. Classification SHALL use actual committed outcomes through both text and graphical paths.

#### Scenario: Rest and wait settle explicit interval
- **WHEN** a successful awake rest or wait settles a positive accepted interval including a final truncated interval
- **THEN** one fresh complete checkpoint follows its committed stages

#### Scenario: Sleep choice does not align
- **WHEN** a sleep request commits entry-only or opens dream/handoff choices without completed receipt
- **THEN** the ordinary candidate comparison runs and no sleep checkpoint is invented

#### Scenario: Retained sleep completes later
- **WHEN** a partial sleep retains continuation then a later newly committed result marks it completed
- **THEN** the partial settlement stays incremental and the completion freshly aligns once

#### Scenario: Dream departure resumes completed sleep
- **WHEN** a committed dream departure callback completes the retained sleep receipt
- **THEN** its own ordered publication uses the same fresh checkpoint rule

#### Scenario: Rollback and receipt replay do not realign
- **WHEN** a skip rejects rolls back or returns an already committed duplicate receipt
- **THEN** no new checkpoint is attributed to that unsuccessful or replayed operation

#### Scenario: Multiple causes retain one result revision
- **WHEN** terminal combat and completed skip/movement facts belong to one serialized settlement
- **THEN** one complete final snapshot replaces the delta and the result names its target revision

# webclient-incremental-publication Specification

## Purpose
Publish only changed validated presentation candidates through one isolated per-session baseline while retaining complete authoritative recovery.

## Requirements

### Requirement: Candidate equality follows JSON value semantics
Change detection SHALL compare validated candidate contents without whole-presentation serialization or hashes. Object key order SHALL be irrelevant, array order significant, and booleans distinct from numbers. Published baseline values SHALL be isolated from presenter mutation.

#### Scenario: JSON type and ordering distinctions
- **WHEN** candidates reorder dictionary keys, reorder a list, and replace true with1
- **THEN** dictionary-only reorder is suppressed while list order and bool-to-number changes are published

#### Scenario: Mutable presenter alias cannot corrupt baseline
- **WHEN** a presenter mutates its previously returned nested list after publication
- **THEN** the baseline keeps the published content and the next changed candidate is detected

#### Scenario: Unchanged candidate is omitted
- **WHEN** only one of several declared candidate panels changes
- **THEN** the delta includes that replacement and preserves every untouched panel

### Requirement: Unknown scope recomputes all eager panels without full retransmission
An absent empty or invalid affected declaration SHALL cause fresh rendering of all eager panels, with only actual differences transmitted. Required mode/dialogue companion candidates SHALL remain covered; on-demand maps SHALL NOT be force-rendered.

#### Scenario: Unknown scope publishes only differences
- **WHEN** an adapter declares no affected scope and one eager panel changed
- **THEN** every eager presenter runs, only that difference is sent and unopened map presenters do not run

#### Scenario: Unchanged dialogue companion stays consistent
- **WHEN** an update in dialogue mode changes status but dialogue renders equal
- **THEN** dialogue may be omitted and staged mode/dialogue remains consistent

### Requirement: Publication baseline belongs to one live session sequence
Every graphical text sync and asynchronous publisher SHALL use the same per-session publication owner and isolated ephemeral baseline. A baseline SHALL advance only after complete successful publication. Partial send failure SHALL invalidate it for deltas.

#### Scenario: Two viewers keep isolated baselines
- **WHEN** two live sessions watch one puppet and only one received a prior publication
- **THEN** each next delta is compared and based on its own published sequence

#### Scenario: Preflight fails before sends
- **WHEN** a planned publication or associated result is invalid before sending
- **THEN** no presentation frame is sent and no new revision is consumed

#### Scenario: Partial send invalidates baseline
- **WHEN** a middle frame send raises after earlier frames escaped
- **THEN** the issued target is never reused, no incomplete publication becomes a valid baseline and the next publication freshly snapshots

#### Scenario: Unchanged action completion consumes no revision
- **WHEN** panels and common metadata match the published baseline
- **THEN** no presentation message is sent and the ordered result references the current revision

#### Scenario: Metadata alone changes
- **WHEN** all eager content matches but current common metadata differs
- **THEN** one metadata-only delta advances the revision

#### Scenario: Complete batch cannot interleave
- **WHEN** sync or async push reenters while action presentation frames/result are being sent
- **THEN** it executes wholly before or after that action batch and never between presentation and result

# Spec Delta

## Purpose

Execute locked plans through the commit/dwell queue, consume every server interrupt and present landmark arrival cards. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Route walking consumes plans and committed interrupts
Route walking SHALL execute only the departed plan prefix through current guarded single-step descriptors, preserving commit/dwell pacing and stopping on every supplied interrupt or cancellation without automatic restart.

#### Scenario: Inclusive prefix and current descriptors
- **WHEN** a synthetic locked plan has stop_index before destination and successive commits supply new exit references
- **THEN** exactly the inclusive prefix can send, each payload uses the current descriptor and frozen walk context, and spent ticks advance once per commit

#### Scenario: All stop causes
- **WHEN** each interrupt alone or combined, refusal, new key, disconnect, epoch change or Stop occurs before or during dwell
- **THEN** no next step sends, late results cannot restart and a short stop replans its surviving lock without departing

### Requirement: Landmark arrivals own focus through committed typed events
A committed typed landmark-arrival notice SHALL open one accessible arrival card with supplied art/prose/disclosure, respect higher-priority cards and return focus to the current map on dismissal.

#### Scenario: Deduplication and priority
- **WHEN** one arrival event repeats while a forced-sleep or dialogue card already owns choices
- **THEN** no duplicate opens, the higher-priority card keeps focus and the pending arrival opens only if its cell remains current

#### Scenario: Card dismissal and retirement
- **WHEN** Enter/Escape closes an arrival or its epoch/room retires
- **THEN** the card releases its trap, current-map focus returns only when appropriate and retired arrival content never reappears

#### Scenario: Delayed arrival remains bound to its reached node
- **WHEN** a typed arrival reaches the client after another move or a higher-priority card closes after departure
- **THEN** its canonical arrival_node differs from current and no stale card opens, regardless of matching display name or artwork


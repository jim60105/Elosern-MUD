# Spec Delta

## Purpose

Announce newly explored districts only after a first landmark arrival commits, using the existing visited-node record as the sole discovery state.

## ADDED Requirements

### Requirement: First committed landmark arrival adds one discovery narrative
A successful first arrival at a previously unvisited landmark SHALL append 已探明：<district> to the movement narrative. Failed movement, repeat arrivals, map reads and reconnects SHALL not emit discovery. Lighting SHALL derive only from the unchanged knowledge writer and visited record.

#### Scenario: Discovery follows successful settlement
- **WHEN** a first landmark traversal commits and records the canonical node
- **THEN** that movement narrative includes one 已探明：<district> message and a later return emits none

#### Scenario: Failed movement emits no exploration announcement
- **WHEN** a traversal is blocked, vetoed or rolled back, or a map read/reconnect occurs
- **THEN** no exploration announcement is emitted and no new discovery state is persisted

# webclient-immutable-presentation Specification

## Purpose
Provide immutable reference-preserving committed presentation reads while retaining explicit detached snapshot isolation and valid client-local UI state.

## Requirements

### Requirement: Ordinary committed notifications reuse immutable unchanged payloads
Subscriber and live view reads SHALL receive immutable committed data without unconditional complete-state cloning or serialization. Unchanged delta panels SHALL retain object identity. Transport inputs and consumers SHALL NOT hold mutable aliases into the committed state.

#### Scenario: Unchanged panel retains reference
- **WHEN** a delta replaces status while another eager panel stays unchanged
- **THEN** the unchanged panel is the identical object in consecutive committed views and status is replaced

#### Scenario: Hostile subscriber cannot corrupt state
- **WHEN** a subscriber mutates a nested committed list or property
- **THEN** the write fails or has no effect and future subscribers/reducer reads retain authoritative content

#### Scenario: Source mutation cannot corrupt adoption
- **WHEN** the transport caller mutates its original envelope after receive returns
- **THEN** the adopted immutable state remains unchanged

#### Scenario: Retained old committed record stays stable
- **WHEN** a listener retains a committed record across later replacement and removal
- **THEN** that earlier record and its nested values remain the earlier committed state

### Requirement: Explicit detached snapshots retain isolation
An explicit mutable snapshot read SHALL remain detached from reducer internals and future commits. Immutable shared reads and detached snapshots SHALL refer to the same authoritative reducer rather than separate stores.

#### Scenario: Snapshot edits stay local
- **WHEN** a consumer edits a nested field in its detached mutable snapshot
- **THEN** neither current reducer state nor another snapshot changes

#### Scenario: Later commit cannot mutate prior snapshot
- **WHEN** a consumer retains a detached snapshot and the reducer commits new panels
- **THEN** the retained snapshot remains byte-for-byte equivalent to its original value

### Requirement: Complete alignment preserves valid local interaction state
A complete same-mode same-identity alignment SHALL update authoritative presentation without application remount or independent focus/menu/form/playback reset. Existing semantic teardown for mode epoch transport identity availability or invalid selection changes SHALL remain.

#### Scenario: Valid local edits survive alignment
- **WHEN** a same-mode checkpoint arrives while a valid drawer/menu is open and unsaved text is entered
- **THEN** open state focused key and local text survive without replaying the current delivery/animation

#### Scenario: Semantic invalidation still closes
- **WHEN** the checkpoint changes mode or removes the selected service identity/backing panel
- **THEN** existing teardown/selection validation runs and invalid selection cannot dispatch

#### Scenario: Maps preserve same epoch identity
- **WHEN** a same-epoch complete eager snapshot commits
- **THEN** complete on-demand maps retain their references and lifecycle while a new epoch clears them

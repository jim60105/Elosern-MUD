# Spec Delta

## Purpose

Define ordered resource loading and retained source failures shared by preview, figure, avatar and scene renderers without retry or global-cache behavior.

## ADDED Requirements

### Requirement: One load lifecycle resolves ordered attempts
A shared lifecycle SHALL process attempts in order until real-image success, accumulate only reached faults, observe actual load/decode failure, deduplicate canonical identity/version and end safely without recursive fallbacks or broken images. Successful lower sources SHALL retain earlier relevant faults.

#### Scenario: Lower success retains earlier failure
- **WHEN** the first image returns 404 and the next image decodes
- **THEN** the next image displays with the first source failure still locally indicated

#### Scenario: Unreached faults stay invisible
- **WHEN** a higher-priority image succeeds before a later failed-generation fact
- **THEN** the later fault has no effect

#### Scenario: Exhaustion remains usable
- **WHEN** all permitted images and terminal resources fail
- **THEN** text or non-image background remains with a persistent local failure indication

### Requirement: Attempt callbacks belong to the active revision
Callbacks SHALL be bound to active subject, descriptor revision and attempt. Superseded callbacks SHALL be ignored and listeners/resources disposed on replacement or unmount. Re-rendering unchanged descriptors SHALL preserve results; a relevant new revision or fresh page SHALL allow a new attempt without timer retries or global negative cache.

#### Scenario: Late callback cannot overwrite a new subject
- **WHEN** subject A is replaced by B while A loads or decodes
- **THEN** A's completion or error cannot change B's source, dimensions or failure state

#### Scenario: Same render does not retry
- **WHEN** an unchanged descriptor re-renders after a source failure
- **THEN** there is no new request and the reached failure remains

#### Scenario: Repaired new version clears matching fault
- **WHEN** a repaired source arrives in a new descriptor revision and loads successfully
- **THEN** that revision recomputes attempts and clears its repaired applicable fault

### Requirement: Unexpected failures remain locally accessible
Unexpected reached failures SHALL have persistent non-modal indication at the affected image position with a keyboard and assistive-technology explanation. Messages SHALL use shared bounded category mapping without raw exception, filesystem, credential or prompt content. Expected absence/loading/pending/disabled generation SHALL NOT use error styling.

#### Scenario: Fallback does not hide failure
- **WHEN** a lower image succeeds after a reached backend or browser failure
- **THEN** the local marker remains readable without hover or color-only meaning

#### Scenario: Disabled generation remains factual
- **WHEN** generation is deliberately disabled with no independent fault
- **THEN** normal fallback appears without claiming generation is underway

#### Scenario: Browser failures have no invented telemetry
- **WHEN** a browser-only decode fails
- **THEN** the local indication appears and no new transport or backend-log claim is made


### Requirement: Geometry-only changes reuse successful bytes
A descriptor revision changing only geometry SHALL reuse already decoded successful bytes for unchanged resource identity/version, apply new geometry immediately and avoid source crossfade or loading flash. New source bytes and repaired fault revisions SHALL follow normal ordered resolution.

#### Scenario: Placement changes without another load
- **WHEN** stage geometry changes on the same resource id/version
- **THEN** the immediate new placement uses known-success pixels with no request or source-key animation


### Requirement: Required panel failures enter the common availability state
The shared lifecycle SHALL distinguish ready artwork, expected surface/admission absence and actual required-panel availability failure. A failed availability input SHALL retain a local panel_unavailable indication, invalidate stale callbacks/save eligibility and permit only safely authorized matching content or text/non-image fallback without invented generation.

#### Scenario: Unavailable first render is visible
- **WHEN** a required image panel cannot supply data on initial render
- **THEN** safe fallback and local availability explanation appear without pending-generation claim

#### Scenario: A move with unavailable artwork never retains old pixels
- **WHEN** scene identity or current retained-source authorization cannot be trusted when art is unavailable
- **THEN** the old scene is immediately discarded for safe non-image background and local availability indication

#### Scenario: Expected hidden surface remains normal
- **WHEN** art is not required in creation or a reference was deliberately excluded from an available view
- **THEN** absence contributes no availability error


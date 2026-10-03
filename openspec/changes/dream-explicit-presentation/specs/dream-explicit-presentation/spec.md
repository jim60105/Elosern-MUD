## Purpose

Provides the approved explicit dream scene through validated generation while keeping a server-computed session arousal track separate from live sexual state.

## ADDED Requirements

### Requirement: Dream collaboration uses the approved explicit frame

The collaborator SHALL inhabit a pure-white space with a bed and an obscured goddess-like counterpart of stable persona, not an identified deity/material NPC. Each validated exchange SHALL combine explicit sexual scene prose and counterpart dialogue during story negotiation using established canonical vocabulary. Explicit content SHALL be accepted for this capability; sanitizing it SHALL NOT substitute for approved presentation.

#### Scenario: Recorded explicit response validates
- **WHEN** a recorded response combines approved explicit scene prose and spoiler-free dialogue
- **THEN** the capability accepts it and presents one response

#### Scenario: Divine identity is asserted
- **WHEN** a response identifies a canonical deity or discloses divine mysteries
- **THEN** validation rejects the assertion without authorizing a world fact

### Requirement: Server-owned dream arousal advances only with completed exchanges

A deterministic session-only pleasure/arousal/climax track SHALL advance configured deltas once per completed exchange across canonical five bands. The generated response SHALL describe the server-supplied phase and SHALL NOT advance it. Failed/retried/duplicate responses SHALL NOT advance the track. Climax SHALL be eligible in convergence/ending, not forced on early departure.

#### Scenario: Model attempts arbitrary advancement
- **WHEN** the response declares a phase beyond the server-supplied phase
- **THEN** validation rejects it and the track remains unchanged

#### Scenario: Five-band progression
- **WHEN** six distinct exchanges complete using configured deltas
- **THEN** the server-computed track follows canonical bands with one increment per exchange

#### Scenario: Early exit below climax
- **WHEN** the player leaves before the server track reaches climax
- **THEN** the scene fades without forcing climax

### Requirement: Dream presentation changes no live character effects

The dream track SHALL NOT write a live SexualState handler, persistent traits/pleasure/sensitivity, virginity/experience, lifetime counters, climax_today, relationship state, buffs, skills or codex. Existing committed sleep SHALL be the sole restoration. At reached climax the deterministic ending SHALL render canonical post-climax phase before fading/awakening with no additional model call.

#### Scenario: Completed climax has no live side effects
- **WHEN** a session reaches climax then ends
- **THEN** all live character effects equal the post-sleep baseline and only private authoring/session data changed

#### Scenario: Offline ending at climax
- **WHEN** generation fails after the server track reached climax
- **THEN** ending presents the canonical post-climax phase and permits awakening without a model

### Requirement: Collaborator has separate spoiler-filtered capability access

The collaborator SHALL receive creative preferences and a spoiler-filtered adventure summary, excluding StoryDirector hidden answers, system fields and other owners private cognition. The guardrail SHALL reject leaked metadata/spoilers and claimed authoritative mutations while permitting explicit scene prose. A shared deployment profile SHALL NOT share capability history or permissions.

#### Scenario: Hidden director context exists
- **WHEN** StoryDirector has a secret solution for the same thread
- **THEN** collaborator context excludes it and a response attempting to disclose forbidden metadata rejects


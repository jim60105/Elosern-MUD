# dream-explicit-presentation Specification

## Purpose
Provides the approved explicit dream scene through validated generation while keeping a server-computed session arousal track (owned by the dream's goddess counterpart, whose climax ends the dream) separate from live sexual state.

## Requirements

### Requirement: Dream collaboration uses the approved explicit frame

The dream SHALL stage an obscured goddess-like counterpart of stable persona, seated on a white throne that stands on a sea of clouds above an ankle-deep flood of her own gushing fluids, who pleases herself and speaks with the player standing in that flood, spurting visibly from her exaggerated well-used genitals. Each validated exchange SHALL combine explicit sexual scene prose and counterpart dialogue during story negotiation using established canonical vocabulary.

#### Scenario: Recorded explicit response validates
- **WHEN** a recorded response combines approved explicit scene prose and spoiler-free dialogue
- **THEN** the capability accepts it and presents one response

#### Scenario: Divine identity is asserted
- **WHEN** a response identifies a canonical deity or discloses divine mysteries
- **THEN** validation rejects the assertion without authorizing a world fact

#### Scenario: The counterpart is never an identified deity or material NPC
- **WHEN** the dream's counterpart is staged
- **THEN** it is an obscured, stable-persona counterpart — not an identified deity or material NPC

#### Scenario: Scene artwork comes from the official-artwork system
- **WHEN** the dream stage's scene artwork is presented
- **THEN** it is served from the external official-artwork system as a server-resolved same-origin URL, never bundled into the client

#### Scenario: Explicit content is accepted, sanitizing is no substitute
- **WHEN** the capability's presentation is validated
- **THEN** explicit content is accepted for this capability, and sanitizing it is never substituted for the approved presentation

### Requirement: Server-owned dream arousal advances only with completed exchanges

A deterministic session-only pleasure/arousal/climax track of the goddess counterpart (not the player) SHALL advance configured deltas once per completed exchange across canonical five bands; her climax ends the dream. The generated response SHALL describe the server-supplied phase and SHALL NOT advance it. Failed/retried/duplicate responses SHALL NOT advance the track. Climax SHALL be eligible in convergence/ending, not forced on early departure.

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

The collaborator SHALL receive the player's current message, the current dream proposal with line numbers, the chosen thread's label when one is chosen, creative preferences and a spoiler-filtered adventure summary, and SHALL receive no transcript of earlier exchanges. It SHALL exclude StoryDirector hidden answers, system fields and owner-private cognition. The guardrail SHALL reject leaked metadata/spoilers and claimed authoritative mutations while permitting explicit scene prose.

#### Scenario: Hidden director context exists
- **WHEN** StoryDirector has a secret solution for the same thread
- **THEN** collaborator context excludes it and a response attempting to disclose forbidden metadata rejects

#### Scenario: Current proposal enters the prompt with line numbers
- **WHEN** a prompt is built for a proposal that holds a summary and two list items in one field
- **THEN** the request carries every proposal field, each line paired with its line number starting at one, and the closed edit vocabulary

#### Scenario: Chosen thread label enters the prompt
- **WHEN** a prompt is built with a chosen thread label, and again with none
- **THEN** the first request carries that label and the second carries no thread entry

#### Scenario: No transcript
- **WHEN** a prompt is built for a later exchange of a session
- **THEN** the request's context keys are exactly the permitted set and none of them carries an earlier message, scene or line

#### Scenario: A shared deployment profile keeps capabilities separate
- **WHEN** two sessions run under one shared deployment profile
- **THEN** neither shares capability history or permissions with the other

### Requirement: Collaborator responses carry proposal edits validated by application

A response SHALL be able to carry an ordered set of proposal edit commands. The set SHALL be validated by applying it to the proposal the prompt carried; a set that does not apply SHALL invalidate the whole response and go through the existing validation retry. Edit text SHALL pass the same forbidden-content validators as scene and dialogue. An accepted response SHALL yield the resulting proposal and its change report; the layer itself SHALL write no state.

#### Scenario: Valid edits yield the new proposal and report
- **WHEN** a response edits two fields of the supplied proposal with commands that apply
- **THEN** the accepted exchange carries the proposal after those edits and a change report naming exactly those changes

#### Scenario: No edits
- **WHEN** a response carries an empty edit set or none
- **THEN** it is accepted, the resulting proposal equals the supplied one and the report shows no change

#### Scenario: Invalid edits retry
- **WHEN** the first response's edit set does not apply and the retried response's set does
- **THEN** exactly one exchange is accepted, built from the retried response

#### Scenario: Retries exhausted
- **WHEN** every attempt returns an edit set that does not apply
- **THEN** the call degrades to the unavailable result and no proposal is produced

#### Scenario: Forbidden content inside an edit
- **WHEN** an edit's new text contains a forbidden metadata, state-change or divine-identity marker while scene and dialogue are clean
- **THEN** validation rejects the response

#### Scenario: Legacy requirement list is refused
- **WHEN** a response carries a whole requirement list field instead of edits
- **THEN** the output schema rejects it

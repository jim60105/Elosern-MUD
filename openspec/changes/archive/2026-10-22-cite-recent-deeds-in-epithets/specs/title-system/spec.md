# Spec Delta

## ADDED Requirements

### Requirement: Nomination prompts contain authorized structured deeds and advisory identity
Prompts SHALL contain rendered deed provenance, times, location, participants with roles and labels, actual actions and outcomes. They SHALL retain player name, current full title and advisory declined/removed-name preferences. Fixed-title names, live owned-epithet collections, live entities and unrestricted raw content SHALL remain outside prompt material.

#### Scenario: Adult outcome survives construction
- **WHEN** an authorized adult act is rendered
- **THEN** its actual structured outcome and actor/recipient roles appear in detached prompt data

#### Scenario: Preferences remain advisory
- **WHEN** declined and removed-name preferences accompany current title identity
- **THEN** they guide generation without becoming blacklists or exposing collision collections

#### Scenario: Factual prompt instructions
- **WHEN** a request contains private experience or numerical adult effects
- **THEN** the prompt forbids fabricated outcomes, role reversals, unwarranted consent/relationship conclusions and invented public recognition

### Requirement: Candidate citations refer only to actually rendered sources
Each candidate SHALL supply nonempty distinct source_ids from the request's rendered material. Citation arrays SHALL be bounded by the supplied source count. Empty, duplicate, unknown or omitted-source citations SHALL eliminate the candidate. Shape, count and field-size violations SHALL retain whole-round invalidation behavior.

#### Scenario: Only visible rendered IDs qualify
- **WHEN** a candidate cites an unknown, authorization-removed or budget-omitted source
- **THEN** that candidate cannot enter the ballot

#### Scenario: Empty or duplicate citations
- **WHEN** otherwise well-shaped candidates have empty or repeated source IDs
- **THEN** those candidates are eliminated without invalidating unrelated valid candidates

#### Scenario: Oversized citation array
- **WHEN** a response array exceeds the request's supplied source count
- **THEN** the response violates the field-size contract and the round is void

#### Scenario: Citation-invalid duplicate cannot reserve display
- **WHEN** a citation-invalid candidate precedes a valid candidate with the same display
- **THEN** the valid candidate remains eligible under first-surviving duplicate behavior

### Requirement: Citation provenance stops at the generation boundary
The generation boundary SHALL validate source_ids and pass only display and basis to the existing ballot writer. Stored ballots and titles SHALL retain their current shapes and consent behavior. Existing transcripts SHALL retain cited request/response provenance. Citation validation SHALL establish membership only, without claiming semantic proof.

#### Scenario: Stored ballot is unchanged
- **WHEN** cited survivors are persisted and reloaded
- **THEN** the ballot contains only display/basis and adoption still requires explicit acceptance

#### Scenario: Traceability without private operational prose
- **WHEN** a cited request and response are recorded
- **THEN** transcripts retain provenance under current policy and credential exclusions, while operational logs omit full private deed text


## MODIFIED Requirements

### Requirement: The nomination pipeline is 5 candidates through schema and collision filters
The generative stage SHALL request exactly five candidates with display, basis and source_ids from rendered recent deeds. Closed response shape, count and field-size violations SHALL void the round. Existing ordered form and collision filters SHALL remain deterministic; invalid citations SHALL eliminate a candidate before ballot admission. The first three survivors SHALL form the ballot; one or two SHALL remain valid and zero SHALL void it.

#### Scenario: Malformed schema voids the round
- **WHEN** the model returns four candidates, six candidates, or unparseable JSON
- **THEN** no ballot is stored

#### Scenario: The per-candidate filters are deterministic
- **WHEN** the per-candidate filters run
- **THEN** they enforce zh-tw form (2–8 characters, no whitespace, no player-name substring), reject equality with any `FixedTitleDef.display_name_zh`, reject equality with any epithet in the entity's live collection, and keep the first of in-batch duplicates

#### Scenario: A nameless survivor survives deletion history
- **WHEN** a candidate equals an epithet previously deleted from the collection
- **THEN** the live-collection filter passes it (deleted names are renominable)

#### Scenario: Batch duplicates keep the first
- **WHEN** two otherwise eligible candidates carry the same display
- **THEN** only the first surviving candidate is kept for the top-three cut

#### Scenario: The generative module persists nothing
- **WHEN** the proposer completes a round with survivors
- **THEN** no attribute outside the rules-layer writer's transaction changed during the proposal

#### Scenario: Survivor count decides the ballot
- **WHEN** the filters run over the five candidates
- **THEN** the first three survivors form the ballot, one to three survivors ballot as-is, and zero survivors void the round silently

#### Scenario: Collision rules stay out of the prompt
- **WHEN** the nomination prompt text is inspected
- **THEN** no collision rule appears in it

#### Scenario: Only the rules-layer writer persists the ballot
- **WHEN** the pure-proposal module returns the filtered candidates (or nothing)
- **THEN** persisting a ballot is performed solely by the rules-layer nomination writer, which re-checks suppression after the proposal returns

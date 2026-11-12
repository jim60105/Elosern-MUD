# Spec Delta

Archive handoff: after syncing this delta, re-list canonical IDs and annotate every new or changed substantive requirement test. Existing requirement headings are intentionally unchanged, including the historical Utility heading. This delta preserves flee behavior while adopting the new mode names.

## MODIFIED Requirements

### Requirement: Flee tuning follows existing tier defaults and instance overrides

Reflex flee SHALL use the actual resolved behavior profile, taking its tier default when no override exists and its valid instance override otherwise. No separate tier or monster-key flee mapping SHALL exist. Deliberation SHALL NOT derive voluntary flee from this tuning. Only configured typed-invalid-state reflex fallback MAY reach the reflex flee body for a deliberation-mode monster.

#### Scenario: Tier default controls an unoverridden monster
- **WHEN** a reflex monster has no behavior override
- **THEN** its flee threshold equals its authored tier-default profile threshold

#### Scenario: Instance override controls the flee decision
- **WHEN** two otherwise identical reflex monsters share a tier but one has a valid behavior override with a different threshold
- **THEN** each uses its own resolved threshold

### Requirement: The policy checks current-to-maximum true HP at an inclusive boundary

For a living non-fled monster with a living non-fled enemy, reflex SHALL choose flee exactly when its resolved threshold is non-null, stored maximum HP is positive and stored current HP divided by stored maximum HP is at most the threshold. It SHALL read true stored HP without regeneration or disguised stats. Deliberation SHALL NOT evaluate this predicate except through configured typed-invalid-state reflex fallback.

#### Scenario: Exact threshold chooses flee
- **WHEN** a reflex monster is at its non-null inclusive threshold
- **THEN** the policy returns the canonical flee skill request

#### Scenario: Above threshold preserves attack behavior
- **WHEN** a reflex monster is above its threshold and has a usable damage skill
- **THEN** the current reflex skill strategy selects the attack without changing the threshold contract

#### Scenario: A non-positive maximum does not divide or choose flee
- **WHEN** stored maximum HP is non-positive
- **THEN** the flee predicate is false without division or a flee request

#### Scenario: Reading the predicate does not advance regeneration
- **WHEN** a valid gauge has a pending regeneration timestamp
- **THEN** reading the flee predicate leaves its complete backing data and timestamp unchanged

### Requirement: Flee selection has priority over attack selection without consuming decision dice

After non-monster delegation and finding living enemies, reflex SHALL evaluate flee before enumerating attack skills, choosing targets or shapes, or sampling a skill. Meeting the threshold SHALL choose flee even without affordable damage skills. A flee decision SHALL consume neither combat dice nor independent skill-selection RNG. With no living non-fled enemy it SHALL return None. Deliberation SHALL NOT evaluate voluntary flee.

#### Scenario: Threshold flee does not require a damage skill
- **WHEN** a reflex monster meets its threshold with either no usable damage kit or multiple kits requiring stochastic skill selection
- **THEN** it returns flee without calling either combat dice or the independent selection RNG

#### Scenario: Threshold flee consumes no policy tie-break roll
- **WHEN** a threshold-triggered reflex decision would otherwise require tied target or stochastic skill selection
- **THEN** flee returns before any target tie roll or independent skill-selection draw

#### Scenario: No enemy means no flee action
- **WHEN** every opponent is dead or fled
- **THEN** the policy returns None

#### Scenario: Non-monsters retain 10b delegation
- **WHEN** the entity has no monster threat tier
- **THEN** it delegates to the existing default attack policy without evaluating flee

### Requirement: Monster flee decisions remain deterministic, offline, and YAML-tuned

The flee predicate SHALL use no LLM, network or random draw. Archetype thresholds SHALL remain rulebook-authored. Fixed profile and stored HP state SHALL reproduce the flee-versus-attack decision; fixed resolver dice SHALL reproduce a chosen flee's resolution. Attack skill sampling after a false flee predicate SHALL follow the current reflex contract and SHALL NOT redefine the deterministic flee boundary.

#### Scenario: Fixed state reproduces the same decision
- **WHEN** equivalent battlefields use identical profiles and stored HP with different injected skill-selection RNG states
- **THEN** both make the same flee-versus-attack decision; a chosen flee consumes no selection draw

#### Scenario: Deterministic core has no generative dependency
- **WHEN** external model and network access are unavailable and the flee predicate is evaluated
- **THEN** its decision succeeds without persistent state changes and reads the authored threshold

### Requirement: Utility mode never voluntarily flees

A deliberation monster SHALL NOT voluntarily flee at any HP fraction. Its deliberation candidates, scores and returned requests SHALL exclude the canonical flee skill, selecting its scored action when available and returning None when no scored action exists. Configured typed-invalid-state reflex fallback SHALL retain its inclusive flee contract and diagnostic identity.

#### Scenario: The same authored boundary decides differently by effective mode
- **WHEN** otherwise identical synthetic registered monsters meet a non-null threshold with a living enemy and legal damage action, one in reflex and one in deliberation
- **THEN** reflex returns flee and deliberation returns its scored damage action, never flee

#### Scenario: Below the boundary the utility decision still scores
- **WHEN** deliberation is below its profile threshold with a legal scored candidate
- **THEN** it returns its scored request; identical state, configuration and selection inputs replay that request

#### Scenario: An empty utility candidate set stays no action
- **WHEN** a living deliberation monster at or below the threshold has no legal scored candidate
- **THEN** it returns None without reflex flee fallback

#### Scenario: The owned flee key is no enumerated candidate
- **WHEN** deliberation owns innate flee and reports its enumeration at different HP fractions
- **THEN** no candidate, rejected proposal, exclusion, unusable skill, score term or returned request names flee

#### Scenario: The typed-invalid-state fallback keeps the legacy body
- **WHEN** deliberation raises its typed invalid-state error at or below the threshold with configured reflex fallback
- **THEN** the fallback returns its inclusive reflex flee request and the diagnostic identifies reflex

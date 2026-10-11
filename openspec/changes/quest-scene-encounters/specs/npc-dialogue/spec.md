# Spec Delta

## MODIFIED Requirements

### Requirement: Async dialogue intents revalidate context at completion

Async exchanges SHALL revalidate co-location and NPC interactability before applying intents. For separated context without a source phase change, existing speech-kept/intent-discarded behavior SHALL remain. Every generated-phase exchange SHALL capture the current phase revision with its context; a revision mismatch SHALL supersede speech-kept behavior and reject speech, intent, and dialogue/memory append together, refreshing the current phase. Existing stale-persona rejection SHALL remain independent and unchanged.

#### Scenario: Presence-only invalidation preserves existing behavior
- **WHEN** the actor leaves during an exchange whose source phase revision is unchanged
- **THEN** speech follows existing separated-context handling and no intent is applied

#### Scenario: Phase revision rejects the entire obsolete exchange
- **WHEN** a generated role's phase changes while a reply is pending
- **THEN** settlement delivers no speech, applies no intent, appends no obsolete exchange or memory, and refreshes current phase content

#### Scenario: Intent is dropped after separation
- **WHEN** an async reply completes after separation and its captured phase revision remains current
- **THEN** speech follows existing handling and no intent is applied; a phase mismatch instead rejects the entire exchange

#### Scenario: Intent is dropped when the NPC becomes busy
- **WHEN** an async reply completes after the NPC becomes busy/resting and its captured phase revision remains current
- **THEN** speech follows existing handling and no intent is applied; a phase mismatch instead rejects the entire exchange

#### Scenario: Co-located interactive completion applies the intent
- **WHEN** an async reply completes with both parties co-located, the NPC interactable and captured phase revision current
- **THEN** its intent applies through existing per-kind validation and generated commission scope checks

### Requirement: NPC dialogue degrades to greeting or silence offline

Disabled, unreachable, or exhausted generative dialogue SHALL return its existing degraded marker without unintended game mutations. Authored hosts SHALL retain literal per-instance greeting override, table greeting, profile greeting, then silence precedence. Generated hosts SHALL use their current permitted phase offline response through the shared resolver. Offline play SHALL keep fixed greetings, scripted topics and authorized deterministic commission interactions available without network calls when profiles are disabled.

#### Scenario: Generated conversation remains playable offline
- **WHEN** profiles are disabled and a generated conversational role is opened or addressed
- **THEN** fixed greeting/topics and current phase offline response remain available without a network request

#### Scenario: Authored fallback precedence is preserved
- **WHEN** an authored NPC has an override, table, and profile greeting, or has none of them
- **THEN** the override renders literally first, subsequent defaults retain their order, and no available greeting yields silence

#### Scenario: Offline dialogue falls back to the authored greeting
- **WHEN** the LLM is offline and the NPC has an authored greeting
- **THEN** the player receives the authored greeting with no state change and no network request

#### Scenario: Offline dialogue with no greeting is silence
- **WHEN** the LLM is offline and the NPC has no table greeting, no offline-greeting field text, and no profile greeting
- **THEN** the NPC stays silent and no state changes

#### Scenario: An NPC with an offline-greeting field speaks it offline
- **WHEN** the LLM is offline and a free-form NPC without a scripted table carries a non-empty offline-greeting field
- **THEN** the player receives that field's greeting verbatim, distinct from another such NPC's greeting, with no state change and without resolving any profile

#### Scenario: A profiled host speaks its profile greeting offline
- **WHEN** the LLM is offline, an NPC has no table greeting and an empty offline-greeting field, and its persona provenance names a profile that authors a greeting
- **THEN** the player receives that profile greeting verbatim with no state change

#### Scenario: Greeting resolution follows the fixed order
- **WHEN** an offline NPC's authored greeting is resolved
- **THEN** it resolves in order: the greeting stored in the NPC's own bounded per-instance offline-greeting field, then the NPC's dialogue-table greeting when its table authors one, then the greeting authored by the NPC profile named in its persona provenance

#### Scenario: The instance offline-greeting field overrides every default
- **WHEN** the NPC's per-instance offline-greeting field is set
- **THEN** the field is seeded at build, is author-editable, and overrides every authored default when set

#### Scenario: A runtime card edit does not alter shared defaults
- **WHEN** a card is edited at runtime
- **THEN** the edit changes neither the table nor the profile greeting default, and the instance field speaks exactly its stored text

## ADDED Requirements

### Requirement: Generated free-form dialogue includes only permitted current phase context

Generated prompts SHALL combine baseline persona, permitted current-phase context, owner-permitted memories and append-only pair history under existing budgets. Phase revision SHALL participate in freshness without replacing persona/history or granting private knowledge. Speech SHALL confer no committed outcome; free-form effects SHALL share scripted topic authorization.

#### Scenario: Phase context changes without persona or memory replacement
- **WHEN** a role's supported committed observation selects a new phase and a new prompt is captured
- **THEN** its current permitted situation changes, its baseline persona and prior turns remain, and another owner's hidden facts stay absent

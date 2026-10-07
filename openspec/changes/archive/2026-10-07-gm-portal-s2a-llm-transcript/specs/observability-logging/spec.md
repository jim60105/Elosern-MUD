## MODIFIED Requirements

### Requirement: Facade renders one structured grep-friendly line
Every facade emission MUST be a single line of the form `[level] event | mod.func:line | k=v ... [ | tb: summary]`. The caller segment MUST be derived by the facade from its own call stack, never passed by callers. Context keys MUST be sorted, None-valued keys omitted, numeric and boolean values rendered verbatim, strings with spaces double-quoted, and containers rendered with repr. Every rendered context value MUST be truncated at 200 characters and embedded newlines escaped. Events MUST remain stable English snake_case identifiers. Player prose and prompt content MAY enter logs; credentials MUST NOT. Full LLM payloads SHALL live in the transcript referenced by call_id rather than being duplicated unbounded in operational lines.

#### Scenario: Context ordering and formatting are deterministic
- **WHEN** the same event is logged twice with the same context
- **THEN** both lines are byte-identical with sorted keys and the truncation and quoting rules applied

#### Scenario: Long multiline player prose
- **WHEN** a context string contains more than 200 characters and embedded newlines
- **THEN** its bounded representation occupies one operational line without blanket prose redaction

## ADDED Requirements

### Requirement: LLM and narrative diagnostic correlation
llm_call, llm_call_retry, and llm_cached_tokens_reported SHALL include the guarded call_id. The letter command cmd_in SHALL record truncated args rather than args_count. correspondence_reply_captured and correspondence_reply_failed SHALL carry the letter body; correspondence_reply_failed and dream_surface_generation_failed SHALL carry call_id when generation was attempted, and dream failures SHALL carry player input. Failures before a guarded call exists SHALL not fabricate an identifier. Full prompts SHALL be retrieved through the transcript, not duplicated into these failure events. All game-code operational logging SHALL continue through named facade imports with caller-binding patches in tests. Private visibility, PRIVATE_AUTHORING_CATEGORIES, memory/recall/thread access controls and all in-world knowledge boundaries SHALL remain unchanged.

#### Scenario: Letter and dream failures explainable
- **WHEN** guarded generation fails for a letter reply or dream input
- **THEN** the operational event includes bounded body or player input and the actual call_id that retrieves the transcript

#### Scenario: Letter command and cached usage
- **WHEN** a letter command begins or provider cached-token usage is reported
- **THEN** cmd_in contains bounded args rather than args_count and cached usage carries its guarded call_id

#### Scenario: Logging does not widen narrative access
- **WHEN** an actor attempts private memory, recall, or thread access previously denied
- **THEN** the same denial remains in force despite prose being permitted in logs

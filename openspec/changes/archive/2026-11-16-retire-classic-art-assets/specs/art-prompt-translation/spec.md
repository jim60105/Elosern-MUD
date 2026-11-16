## ADDED Requirements

### Requirement: Gallery descriptions pass through configured prompt translation
`world/art/worker.py` SHALL apply the prompt-translation stage to a claimed record's
`source_description` AFTER the description is read and BEFORE the sd-webui client is called, when
and only when `ART_TRANSLATE_ENABLED` is true. The value passed to `client.generate(...)` SHALL be
the stage's result.

#### Scenario: An enabled stage changes what the client is asked to generate
- **WHEN** a claimed record whose description needs translating is generated with the stage enabled
- **THEN** the client receives the translated description, the stored `source_description` and
  `source_hash` are unchanged, and the embedded generation metadata quotes the prompt built from the
  translated text

#### Scenario: A disabled stage is byte-identical to no stage at all
- **WHEN** the same record is generated with `ART_TRANSLATE_ENABLED` false
- **THEN** the client receives the description verbatim, no backend is resolved, no translation
  event is emitted, and the stored bytes equal those produced before this capability existed

#### Scenario: Gallery jobs use the translation stage
- **WHEN** two gallery jobs for the same subject are generated with
  the stage enabled
- **THEN** both clients receive translated text and both settle through their existing publication
  paths unchanged

#### Scenario: Downstream consumers describe the generated text
- **WHEN** the stage's result is passed to `client.generate(...)`
- **THEN** every downstream consumer — the rendered prompt pair, the request the server serves, and
  the `GeneratedImage` provenance the worker embeds as metadata — describes the text that was
  actually generated from

#### Scenario: Every subject kind is prompt text
- **WHEN** the stage runs
- **THEN** it applies identically to gallery jobs for every subject kind:
  a scene sentence, a bestiary description, and a composed character description are all prompt text

#### Scenario: The stage never writes the translated text back
- **WHEN** the stage translates a claimed record's description
- **THEN** it does not write the translated text back to the queue record: the record's
  `source_description` and its `source_hash` remain the authored text, so the stored description
  stays auditable in its original language
- **AND** enabling or disabling the stage never rewrites a record or invalidates a digest

## REMOVED Requirements

### Requirement: The translation stage sits between the claimed description and the generation call
**Reason**: Replaced by Gallery descriptions pass through configured prompt translation; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

## Purpose

Defines the prompt-translation stage of the art pipeline: the bounded, injectable seam that
renders a subject's deterministic description into the language the image model is prompted in,
its per-line language gate, the backend contract and output validation, the non-fatal failure
semantics that keep a degraded prompt from costing an image, and the boundary events the worker
emits for it.

## ADDED Requirements

### Requirement: The translation stage sits between the claimed description and the generation call
`world/art/worker.py` SHALL apply the prompt-translation stage to a claimed record's
`source_description` AFTER the description is read and BEFORE the sd-webui client is called, when
and only when `ART_TRANSLATE_ENABLED` is true. The value passed to `client.generate(...)` SHALL be
the stage's result, so every downstream consumer — the rendered prompt pair, the request the server
serves, and the `GeneratedImage` provenance the worker embeds as metadata — describes the text that
was actually generated from. The stage SHALL apply identically to classic records and to gallery
jobs, and to every subject kind: a scene sentence, a bestiary description, and a composed character
description are all prompt text.

The stage SHALL NOT write the translated text back to the queue record. The record's
`source_description` and its `source_hash` remain the authored text, so the stored description stays
auditable in its original language and enabling or disabling the stage never rewrites a record or
invalidates a digest.

#### Scenario: An enabled stage changes what the client is asked to generate
- **WHEN** a claimed record whose description needs translating is generated with the stage enabled
- **THEN** the client receives the translated description, the stored `source_description` and
  `source_hash` are unchanged, and the embedded generation metadata quotes the prompt built from the
  translated text

#### Scenario: A disabled stage is byte-identical to no stage at all
- **WHEN** the same record is generated with `ART_TRANSLATE_ENABLED` false
- **THEN** the client receives the description verbatim, no backend is resolved, no translation
  event is emitted, and the stored bytes equal those produced before this capability existed

#### Scenario: Classic records and gallery jobs are treated alike
- **WHEN** a classic portrait record and a gallery job for the same subject are both generated with
  the stage enabled
- **THEN** both clients receive translated text and both settle through their existing publication
  paths unchanged

### Requirement: A per-line language gate skips text that needs no translation
The stage SHALL split the description into lines and decide per line whether that line needs
translating: a line containing at least one Han character SHALL be offered to the backend, and a
line containing none SHALL be passed through UNTOUCHED and SHALL NEVER be sent to the backend.
Line structure SHALL be preserved exactly — the result SHALL carry the same number of lines in the
same order, so the composed description's section layout survives the stage.

A description in which no line needs translating SHALL short-circuit: no backend SHALL be resolved,
no backend call SHALL be made, and the original string SHALL be returned identically. This is the
path a player who types English into the gallery free-text box takes, and it SHALL cost nothing.

The gate SHALL be a property of the TEXT, never of the field it came from: the stage receives one
composed description and SHALL NOT be told which part was registry text, persona text, or player
text.

#### Scenario: Latin-script lines are returned byte-identical
- **WHEN** a description whose every line is Latin script is passed through the enabled stage
- **THEN** the returned string is identical to the input, no backend is resolved, and no backend
  call is recorded

#### Scenario: A mixed description translates only the lines that need it
- **WHEN** a description carries some Han-bearing lines and some Latin-only lines
- **THEN** only the Han-bearing lines are offered to the backend, the Latin-only lines appear in the
  result unchanged, and the line count and order match the input

#### Scenario: Line structure survives translation
- **WHEN** a multi-line composed character description is translated
- **THEN** the result has the same number of lines in the same order, so the appearance, equipment,
  and free-text sections stay separated exactly as composed

### Requirement: The translation backend is an injectable seam whose output is validated
The backend SHALL be resolved from the `ART_TRANSLATE_BACKEND` dotted-path setting, instantiated
per the same pattern as the sd-webui client and the background-removal backend. Every resolution
failure — a non-dotted path, an import error, a missing attribute, or a constructor failure — SHALL
raise the bounded code `art_translate_unavailable`. Every failure inside a backend call SHALL raise
the bounded code `art_translate_error`. No unbounded exception SHALL escape the stage.

The stage SHALL validate what a backend returns before using it: the result SHALL be a sequence of
strings of exactly the length it was given, and every element SHALL be a string. Anything else SHALL
raise `art_translate_error` rather than reaching the generation call, so a malformed backend cannot
corrupt a prompt or silently drop a line. A returned line that still carries Han characters SHALL
NOT be an error — a proper noun a translator legitimately leaves alone is not a failure — but the
stage SHALL make the count of such lines available to the caller so the worker can report it.

The stage module SHALL contain no observability call: it raises, and the worker logs, so a stage
outcome is never reported twice.

#### Scenario: An unresolvable backend path is a bounded code, not a crash
- **WHEN** `ART_TRANSLATE_BACKEND` names a module that does not exist, an attribute that does not
  exist, or a class whose constructor raises
- **THEN** the stage raises `art_translate_unavailable` and no unbounded exception escapes

#### Scenario: An arbitrary backend exception is bounded
- **WHEN** a resolved backend raises an arbitrary exception during a call
- **THEN** the stage raises `art_translate_error` and no unbounded exception escapes

#### Scenario: A malformed backend result never reaches the generation call
- **WHEN** a backend returns a non-sequence, a sequence of the wrong length, or a sequence
  containing a non-string element
- **THEN** the stage raises `art_translate_error` and the generation call is never made with that
  value

#### Scenario: A legitimately untranslated line is reported, not rejected
- **WHEN** a backend returns a line that still carries Han characters
- **THEN** the stage accepts the result and reports how many returned lines were left in the source
  script

### Requirement: Translation failure degrades the prompt and never costs the image
A translation failure SHALL NOT fail the job. When the stage raises any bounded code, the worker
SHALL log the failure once, SHALL fall back to the ORIGINAL description, and SHALL continue to
generate and settle that record exactly as it would with the stage disabled. No `art_translate_*`
code SHALL ever appear as a record's settle error.

This is a deliberate divergence from the background-removal stage, whose failure settles the record
`failed`: a failed cutout means the stored image is not the image that was asked for, while a failed
translation means the prompt was less good than it could have been. The first is worth losing an
image over; the second is not.

#### Scenario: An unavailable backend still produces an image
- **WHEN** the stage is enabled, the backend cannot be resolved, and a portrait record is generated
- **THEN** exactly one `art_translate_failed` warn event is emitted, the client receives the
  original description, and the record settles `done` with its image

#### Scenario: No translation code can settle a record
- **WHEN** every bounded translation failure mode is exercised across a batch
- **THEN** no record settles `failed`, and no record carries `art_translate_unavailable` or
  `art_translate_error` as its error code

### Requirement: The stage emits exactly one boundary event per non-skipped outcome
The worker SHALL emit exactly one `art_translate_done` info event when the stage ran and produced a
result, carrying the job key, the subject, the gallery image id where one applies, the total line
count, the count of lines offered to the backend, the count of returned lines still in the source
script, and the elapsed duration. It SHALL emit exactly one `art_translate_failed` warn event
carrying the bounded code and the exception chain when the stage raised.

It SHALL emit NEITHER for a subject the stage skipped — the stage disabled, or no line needing
translation — so a deployment that does not run the stage and a description that needs nothing both
stay silent.

#### Scenario: A successful stage emits one done event with its counts
- **WHEN** a description with Han-bearing and Latin-only lines is translated successfully
- **THEN** exactly one `art_translate_done` is emitted carrying the job, subject, total line count,
  offered line count, source-script-remaining count, and duration, and no `art_translate_failed`

#### Scenario: A failed stage emits one failure event and no success event
- **WHEN** the stage raises a bounded code
- **THEN** exactly one `art_translate_failed` is emitted carrying that code and the exception
  chain, and no `art_translate_done` is emitted for that subject

#### Scenario: Skipped subjects are silent
- **WHEN** a record is generated with the stage disabled, and separately when a fully Latin-script
  description is generated with the stage enabled
- **THEN** neither run emits any `art_translate_*` event

### Requirement: The server reports which optional art stages are active at startup
Startup SHALL emit exactly one info event naming, for each optional art stage that has an
enablement setting, whether it is currently active — at minimum the background-removal stage and
the prompt-translation stage. The report SHALL be one line regardless of how many stages exist and
SHALL name the setting that controls each stage.

An optional stage that is off looks exactly like a stage that is broken: both produce no output and
no events. This report is what distinguishes them for an operator, and it exists because a shipped,
correctly wired opt-in stage was believed to be running while its default-off setting had never been
set.

#### Scenario: The boot report names each optional stage and its state
- **WHEN** the server starts with the background-removal stage enabled and the prompt-translation
  stage disabled
- **THEN** exactly one info event is emitted naming both stages, reporting the first active and the
  second inactive, and naming the setting that controls each

#### Scenario: The report is emitted regardless of the stages' states
- **WHEN** the server starts with every optional art stage disabled
- **THEN** the report is still emitted, naming every stage as inactive

### Requirement: The translation backend is injectable and tests never load a translation library
The seam SHALL ship a deterministic test double that records every call it received, can be
scripted to raise any bounded code, and applies a fixed, observable transformation to the text it
is given. The double SHALL NOT return its input unchanged, so an assertion that translation
occurred cannot pass against a pass-through. It SHALL import no translation library and SHALL make
no network call. The browser harness settings SHALL declare the stage disabled and the double as
the backend, so a harness run can never reach a real engine.

#### Scenario: The double is observably not a pass-through
- **WHEN** the double translates a Han-bearing line
- **THEN** the returned line differs from the input and the call is recorded

#### Scenario: The test suite loads no translation library
- **WHEN** the art test suite runs at default settings
- **THEN** no translation library is imported, no network call is attempted, and the stage records
  no backend call

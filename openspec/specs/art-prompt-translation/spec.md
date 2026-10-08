# art-prompt-translation Specification

## Purpose
Defines the prompt-translation stage of the art pipeline: the bounded, injectable seam that
renders a subject's deterministic description into the language the image model is prompted in,
its per-line language gate, the backend contract and output validation, the non-fatal failure
semantics that keep a degraded prompt from costing an image, and the boundary events the worker
emits for it.

## Requirements

### Requirement: The translation stage sits between the claimed description and the generation call
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

#### Scenario: Classic records and gallery jobs are treated alike
- **WHEN** a classic portrait record and a gallery job for the same subject are both generated with
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
- **THEN** it applies identically to classic records and to gallery jobs, and to every subject kind:
  a scene sentence, a bestiary description, and a composed character description are all prompt text

#### Scenario: The stage never writes the translated text back
- **WHEN** the stage translates a claimed record's description
- **THEN** it does not write the translated text back to the queue record: the record's
  `source_description` and its `source_hash` remain the authored text, so the stored description
  stays auditable in its original language
- **AND** enabling or disabling the stage never rewrites a record or invalidates a digest

### Requirement: A per-line language gate skips text that needs no translation
The stage SHALL split the description into lines and decide per line whether that line needs
translating: a line containing at least one Han character SHALL be offered to the backend, and a
line containing none SHALL be passed through UNTOUCHED and SHALL NEVER be sent to the backend.
Line structure SHALL be preserved exactly — the result SHALL carry the same number of lines in the
same order, so the composed description's section layout survives the stage.

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

#### Scenario: The English free-text path costs nothing
- **WHEN** a player types English into the gallery free-text box
- **THEN** the short-circuit path is taken and it costs nothing

#### Scenario: The gate reads the text, never its field of origin
- **WHEN** the stage receives a description
- **THEN** the gate is a property of the TEXT, never of the field it came from: the stage receives
  one composed description and is not told which part was registry text, persona text, or player
  text

#### Scenario: A description needing no translation short-circuits
- **WHEN** a description is processed in which no line needs translating
- **THEN** no backend is resolved, no backend call is made, and the original string is returned
  identically

### Requirement: The translation backend is an injectable seam whose output is validated
The backend SHALL be resolved from the `ART_TRANSLATE_BACKEND` dotted-path setting, instantiated
per the same pattern as the sd-webui client and the background-removal backend. Every resolution
failure — a non-dotted path, an import error, a missing attribute, or a constructor failure — SHALL
raise the bounded code `art_translate_unavailable`. Every failure inside a backend call SHALL raise
the bounded code `art_translate_error`. No unbounded exception SHALL escape the stage.

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

#### Scenario: A malformed backend cannot corrupt or drop prompt lines
- **WHEN** validation rejects a malformed backend result with `art_translate_error`
- **THEN** a malformed backend cannot corrupt a prompt or silently drop a line
- **AND** a returned line that still carries Han characters is not an error — a proper noun a
  translator legitimately leaves alone is not a failure — but the stage makes the count of such
  lines available to the caller so the worker can report it

#### Scenario: The stage module itself never logs
- **WHEN** a stage outcome needs reporting
- **THEN** the stage module contains no observability call: it raises, and the worker logs, so a
  stage outcome is never reported twice

#### Scenario: The stage validates backend output before use
- **WHEN** a backend returns a result
- **THEN** the stage validates it before using it: the result must be a sequence of strings of
  exactly the length it was given, and every element must be a string
- **AND** anything else raises `art_translate_error` rather than reaching the generation call

### Requirement: Translation failure degrades the prompt and never costs the image
A translation failure SHALL NOT fail the job. When the stage raises any bounded code, the worker
SHALL log the failure once, SHALL fall back to the ORIGINAL description, and SHALL continue to
generate and settle that record exactly as it would with the stage disabled. No `art_translate_*`
code SHALL ever appear as a record's settle error.


#### Scenario: An unavailable backend still produces an image
- **WHEN** the stage is enabled, the backend cannot be resolved, and a portrait record is generated
- **THEN** exactly one `art_translate_failed` warn event is emitted, the client receives the
  original description, and the record settles `done` with its image

#### Scenario: No translation code can settle a record
- **WHEN** every bounded translation failure mode is exercised across a batch
- **THEN** no record settles `failed`, and no record carries `art_translate_unavailable` or
  `art_translate_error` as its error code

#### Scenario: Deliberate divergence from the background-removal stage
- **WHEN** translation failure semantics are compared to the background-removal stage, whose
  failure settles the record `failed`
- **THEN** the divergence is deliberate: a failed cutout means the stored image is not the image
  that was asked for, while a failed translation means the prompt was less good than it could have
  been — the first is worth losing an image over, the second is not

### Requirement: The stage emits exactly one boundary event per non-skipped outcome
The worker SHALL emit exactly one `art_translate_done` info event when the stage ran and produced a
result, and exactly one `art_translate_failed` warn event when the stage raised.

It SHALL emit NEITHER for a subject the stage skipped — the stage disabled, or no line needing
translation.

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

#### Scenario: Silent deployments and silent descriptions
- **WHEN** a stage is skipped because it is disabled or no line needs translation
- **THEN** no event is emitted, so a deployment that does not run the stage and a description that
  needs nothing both stay silent

#### Scenario: The done and failed events' payloads
- **WHEN** the worker emits the boundary events
- **THEN** the `art_translate_done` info event carries the job key, the subject, the gallery image id
  where one applies, the total line count, the count of lines offered to the backend, the count of
  returned lines still in the source script, and the elapsed duration
- **AND** the `art_translate_failed` warn event carries the bounded code and the exception chain

### Requirement: The server reports which optional art stages are active at startup
Startup SHALL emit exactly one info event naming, for each optional art stage that has an
enablement setting, whether it is currently active — at minimum the background-removal stage and
the prompt-translation stage. The report SHALL be one line regardless of how many stages exist and
SHALL name the setting that controls each stage.


#### Scenario: The boot report names each optional stage and its state
- **WHEN** the server starts with the background-removal stage enabled and the prompt-translation
  stage disabled
- **THEN** exactly one info event is emitted naming both stages, reporting the first active and the
  second inactive, and naming the setting that controls each

#### Scenario: The report is emitted regardless of the stages' states
- **WHEN** the server starts with every optional art stage disabled
- **THEN** the report is still emitted, naming every stage as inactive

#### Scenario: The report distinguishes an off stage from a broken one
- **WHEN** an operator reads the startup report
- **THEN** it distinguishes an off stage from a broken one — both produce no output and no events —
  and it exists because a shipped, correctly wired opt-in stage was believed to be running while its
  default-off setting had never been set

### Requirement: The translation backend is injectable and tests never load a translation library
The seam SHALL ship a deterministic test double that records every call it received, can be
scripted to raise any bounded code, and applies a fixed, observable transformation to the text it
is given. The double SHALL NOT return its input unchanged, so an assertion that translation
occurred cannot pass against a pass-through.

#### Scenario: The double is observably not a pass-through
- **WHEN** the double translates a Han-bearing line
- **THEN** the returned line differs from the input and the call is recorded

#### Scenario: The test suite loads no translation library
- **WHEN** the art test suite runs at default settings
- **THEN** no translation library is imported, no network call is attempted, and the stage records
  no backend call

#### Scenario: The double is inert by construction
- **WHEN** the double is used
- **THEN** it imports no translation library and makes no network call

#### Scenario: The browser harness can never reach a real engine
- **WHEN** the browser harness settings are loaded
- **THEN** they declare the stage disabled and the double as the backend, so a harness run can never
  reach a real engine

### Requirement: The shipped backend is a neural machine translator, never a chat model
The shipped translation backend SHALL be a sequence-to-sequence neural machine
translation model executed locally on the CPU. It SHALL NOT be an instruction-tuned
or chat-completion model, and the stage SHALL NOT call the project's LLM client,
any `LLM_*` profile, or any remote completion endpoint.

The reachability ban this requirement enforces SHALL cover the generative layer
and any general-purpose transport.

#### Scenario: No generative-layer transport is reachable from the stage
- **WHEN** the translation stage and its shipped backend are exercised
- **THEN** no `world.ai` client, no `LLM_*` profile, and no completion endpoint is consulted, and
  the only model invoked is the local translation model

#### Scenario: The acquisition transport is the pinned model URL only
- **WHEN** the backend module's source is inspected for outbound capability
- **THEN** `world.ai`, `requests`, and `http` are absent, no `LLM_*` setting is
  read, and the only URL present is the pinned `https://argos-net.com` model URL

#### Scenario: The chat-model ban is a correctness property
- **WHEN** the ban on chat models is justified
- **THEN** it is a correctness property of this project, not a preference: the descriptions this
  stage translates are adult content, and an aligned chat model refuses some fraction of them
- **AND** a refusal string substituted into an image prompt is a strictly worse outcome than the
  untranslated text, and it would arrive through the SUCCESS path where the stage's failure handling
  cannot see it, while a translation model has no refusal behaviour available to it

#### Scenario: The reachability ban's exact scope
- **WHEN** the ban's scope is stated
- **THEN** the backend module SHALL NEVER import `world.ai`, `requests`, or `http.client`/`http`,
  SHALL NEVER read any `LLM_*` setting, and any outbound request it makes SHALL be exclusively the
  pinned model URL at `https://argos-net.com`

#### Scenario: Acquisition-lifecycle imports are permitted
- **WHEN** the backend implements the acquisition lifecycle
- **THEN** importing `urllib.request` (the stdlib fetch of the dual-track download policy) and
  `world.observability` (the bounded download lifecycle events) is PERMITTED, and the ban on
  `socket`/`importlib` imports is likewise lifted for the acquisition path, which needs neither

### Requirement: The model artifact follows the dual-track download policy
The backend SHALL load its model from the code-only `ART_TRANSLATE_MODEL_DIR`
directory, which SHALL contain a CTranslate2 model directory and a SentencePiece
source model. Acquisition SHALL follow `ART_TRANSLATE_DOWNLOAD_ENABLED`, exactly
mirroring the background-removal stage's dual-track policy.

#### Scenario: A complete layout never triggers a fetch
- **WHEN** the stage is enabled with downloads enabled and `ART_TRANSLATE_MODEL_DIR`
  already holds the complete layout
- **THEN** no network request is attempted and translation proceeds on the seeded
  bytes exactly as before this change

#### Scenario: An unseeded volume with downloads enabled fetches once
- **WHEN** the stage is enabled with `ART_TRANSLATE_DOWNLOAD_ENABLED=true` against
  an absent or incomplete model directory
- **THEN** the backend fetches the package once, verifies archive and layout,
  unpacks exactly the required pieces keeping the provenance `README.md`, emits
  exactly one download info event, and the same call then translates with the
  built engine

#### Scenario: A fetch failure degrades and latches
- **WHEN** the download times out, exceeds the size cap, fails verification,
  cannot be unpacked, or cannot be written (e.g. ENOSPC on a full volume)
- **THEN** the backend raises `art_translate_unavailable` and the worker emits its
  normal `art_translate_failed` warn with the record settling `done` on the
  untranslated description, exactly one download-failure warn event is emitted,
  and every later call in the same process fails immediately without a second
  network attempt

#### Scenario: An unseeded model directory degrades without a fetch
- **WHEN** the stage is enabled with `ART_TRANSLATE_DOWNLOAD_ENABLED=false` and
  `ART_TRANSLATE_MODEL_DIR` is absent or empty
- **THEN** the backend raises `art_translate_unavailable` before any translation
  library import, no network request is attempted, and the record still settles
  `done` with its untranslated description

#### Scenario: A malformed model directory is bounded, not fatal
- **WHEN** the model directory exists but lacks the CTranslate2 model or the
  SentencePiece model, or the load raises
- **THEN** the backend raises `art_translate_unavailable` and no unbounded
  exception escapes

#### Scenario: The server never fetches a translation model
- **WHEN** the whole art suite runs with `ART_TRANSLATE_DOWNLOAD_ENABLED=false`
  against seeded and unseeded directories
- **THEN** no outbound network call is attempted for the model in any run

#### Scenario: Tests never download
- **WHEN** the art test suite and the browser harness run at their own settings
- **THEN** no translation library is imported and no network call is attempted,
  because the test and browser settings force the air-gapped track
  (`ART_TRANSLATE_DOWNLOAD_ENABLED=False`) and both harnesses keep the recorded
  fake translator as the backend seam

#### Scenario: The fetch is lazy and lock-guarded
- **WHEN** `ART_TRANSLATE_DOWNLOAD_ENABLED` is true (the default) and the layout
  check fails
- **THEN** the backend MAY fetch and unpack the model package into that directory
  at first use
- **AND** the fetch is LAZY — never at module import and never at server startup —
  and runs only on the engine-construction path under the construction lock (the
  worker thread): the layout check, the engine-cache re-check, the fetch, and the
  post-fetch re-check ALL run under that lock, so concurrent callers block and then
  observe the completed layout instead of degrading mid-fetch

#### Scenario: The fetch is bounded and verified before landing
- **WHEN** the fetch runs
- **THEN** it is bounded by request timeouts and a hard response-size cap enforced
  while streaming — an oversize `Content-Length` is rejected before reading and the
  read aborts at the cap — with no retries
- **AND** it verifies zip integrity, member-path safety, and the required layout
  before any required file becomes visible at its final name
- **AND** it keeps the package's `README.md` (provenance; the packaged model is
  CC-BY 4.0)
- **AND** it lands each required file by atomic replacement so a complete layout is
  never destroyed and an interrupted fetch leaves a directory that simply fails the
  layout check again

#### Scenario: Temp files stay inside the model directory
- **WHEN** the fetch writes temporary files
- **THEN** they are written inside `ART_TRANSLATE_MODEL_DIR` — never a
  cross-filesystem temporary — and deleted on failure

#### Scenario: A successful fetch emits one info event
- **WHEN** a fetch completes successfully
- **THEN** it is observable through exactly one bounded info event carrying the
  source URL, byte count, and duration

#### Scenario: The air-gapped track makes fetching structurally impossible
- **WHEN** `ART_TRANSLATE_DOWNLOAD_ENABLED` is false and the layout check fails
- **THEN** the backend raises the bounded `art_translate_unavailable` immediately,
  BEFORE any translation library is imported: the supported air-gapped
  configuration (pre-seed the volume with `scripts/fetch-translate-model.sh` from a
  trusted machine, disable runtime downloads — the fetch then becomes structurally
  impossible)

#### Scenario: Every acquisition failure is bounded and latches the process
- **WHEN** any download, verification, unpacking, or write failure occurs
  (including `OSError`/ENOSPC on a full volume)
- **THEN** the backend raises the bounded `art_translate_unavailable` — never an
  unbounded exception, never a worker crash
- **AND** the failure is observable through exactly one bounded warn event carrying
  the source URL and the failure chain on the first failure, and takes the stage's
  existing degraded path (the record settles `done` with its untranslated
  description)
- **AND** a process whose fetch has failed does not attempt another download for
  the rest of its process lifetime (a per-process global latch, not
  per-model-directory): subsequent calls fail immediately with
  `art_translate_unavailable`, recovery being a restart or an operator seed

#### Scenario: Model provenance is operator-chosen, never refreshed
- **WHEN** a model component is missing or unreadable on the air-gapped track, or a
  load fails after acquisition
- **THEN** the backend raises the bounded `art_translate_unavailable` where the
  check can be made without importing a translation library
- **AND** the backend is agnostic about which model occupies the directory, so an
  operator MAY seed it from any source producing that layout, and an
  already-complete layout is NEVER re-fetched, refreshed, or upgraded by the server

### Requirement: The translator is built once per process and decodes deterministically on the CPU
The backend SHALL construct at most one translator per configured model directory per process,
under a lock guarding CONSTRUCTION only and never the translation call. The device SHALL be pinned
to the CPU; the backend SHALL NOT select or fall back to a GPU device.

Decoding SHALL be deterministic: the backend SHALL use beam search and SHALL NOT enable sampling,
so the same source text and the same model always produce the same translation.

#### Scenario: One translator serves consecutive calls
- **WHEN** three consecutive translations run in one process against the same model directory
- **THEN** exactly one translator is constructed and the CPU device is pinned on it

#### Scenario: The same input always yields the same output
- **WHEN** the same source lines are translated twice in one process and again after the translator
  is rebuilt
- **THEN** every run returns byte-identical output

#### Scenario: The thread cap reaches the translator only when set
- **WHEN** the backend builds a translator with `ART_TRANSLATE_THREADS=4`, and again with `0`
- **THEN** the first passes `4` as the intra-op thread count and the second passes none, leaving
  the library default

#### Scenario: Importing the module loads no translation library
- **WHEN** `world/art/translate_ct2.py` is imported with the translation packages absent from the
  module cache
- **THEN** the import succeeds, no translation package enters the module cache, and the first
  actual translation attempt is what raises the bounded unavailable code

#### Scenario: Translation libraries import lazily
- **WHEN** the backend module is loaded
- **THEN** translation libraries are imported LAZILY inside the first backend call, never at module
  import, so the module stays importable and the settings module stays loadable on a checkout where
  the optional stack is absent

#### Scenario: Determinism replaces the persistent cache
- **WHEN** deterministic decoding is considered against caching
- **THEN** it is what lets the stage carry no persistent cache — repeat determinism is a property of
  the decoder, not of stored state

#### Scenario: The thread setting reaches the translator conditionally
- **WHEN** the backend constructs a translator under a given `ART_TRANSLATE_THREADS`
- **THEN** the setting reaches the translator's intra-op thread count when non-zero and leaves the
  library default in place when zero

### Requirement: The operator seeding helper names the volume compose actually created
`scripts/fetch-translate-model.sh` SHALL print a volume-seeding command whose
volume name is the one `podman compose` actually created, never an unprefixed
guess: compose project prefixing means the real volume is
`<project>_evennia-translate` (default project `mud`, overridable through
`COMPOSE_PROJECT_NAME`), and a command naming only `evennia-translate` seeds a
silently orphaned volume.

#### Scenario: The printed command seeds the real volume
- **WHEN** compose has created `mud_evennia-translate` and the operator runs the
  script
- **THEN** the printed busybox seeding command references `mud_evennia-translate`,
  not the unprefixed `evennia-translate`

#### Scenario: An unresolved name is annotated, not guessed silently
- **WHEN** the script runs with no `podman` on PATH or with no matching volume
- **THEN** the printed command uses the project-prefixed default with an explicit
  note that the name could not be resolved, and the script exits with its normal
  success status

#### Scenario: Dynamic name resolution order
- **WHEN** `podman` is available
- **THEN** the script resolves the name dynamically — the exact name, then the
  project-prefixed name, then a `podman volume ls` suffix match on
  `(^|_)evennia-translate$` — and prints the first match
- **AND** a failing `podman volume ls` is treated as no match, never an error

#### Scenario: Name resolution never changes script behavior
- **WHEN** name resolution runs
- **THEN** it does not change the script's exit status or its download/verify
  behavior

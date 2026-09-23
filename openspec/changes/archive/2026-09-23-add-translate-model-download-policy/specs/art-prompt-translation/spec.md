# art-prompt-translation delta

## RENAMED Requirements

- FROM: `### Requirement: The model artifact is operator-seeded and its absence is bounded`
- TO: `### Requirement: The model artifact follows the dual-track download policy`

## MODIFIED Requirements

(Note: the two rewritten scenarios of the acquisition requirement —
"The server never fetches a translation model" and "A malformed model directory
is bounded, not fatal" — intentionally KEEP their names, so existing
`covers_requirement` annotations and scenario IDs do not break.)

### Requirement: The model artifact follows the dual-track download policy
The backend SHALL load its model from the code-only `ART_TRANSLATE_MODEL_DIR`
directory, which SHALL contain a CTranslate2 model directory and a SentencePiece
source model. Acquisition SHALL follow `ART_TRANSLATE_DOWNLOAD_ENABLED`, exactly
mirroring the background-removal stage's dual-track policy:

When `ART_TRANSLATE_DOWNLOAD_ENABLED` is true (the default) and the layout check
fails, the backend MAY fetch and unpack the model package into that directory at
first use. The fetch SHALL be LAZY — never at module import and never at server
startup — SHALL run only on the engine-construction path under the construction
lock (the worker thread): the layout check, the engine-cache re-check, the fetch,
and the post-fetch re-check SHALL ALL run under that lock, so concurrent callers
block and then observe the completed layout instead of degrading mid-fetch. The
fetch SHALL be bounded by request timeouts and a hard
response-size cap enforced while streaming — an oversize `Content-Length` is
rejected before reading and the read aborts at the cap — with no retries, SHALL verify zip integrity, member-path safety,
and the required layout before any required file becomes visible at its final
name, SHALL keep the package's `README.md` (provenance; the packaged model is
CC-BY 4.0), and SHALL land each required file by atomic replacement so a complete
layout is never destroyed and an interrupted fetch leaves a directory that simply
fails the layout check again. Temp files SHALL be written inside
`ART_TRANSLATE_MODEL_DIR` — never a cross-filesystem temporary — and deleted on
failure. A successful fetch SHALL be observable through
exactly one bounded info event carrying the source URL, byte count, and duration.

When `ART_TRANSLATE_DOWNLOAD_ENABLED` is false, a failing layout check SHALL raise
the bounded `art_translate_unavailable` immediately, BEFORE any translation
library is imported: the supported air-gapped configuration (pre-seed the volume
with `scripts/fetch-translate-model.sh` from a trusted machine, disable runtime
downloads — the fetch then becomes structurally impossible).

Every download, verification, unpacking, or write failure (including
`OSError`/ENOSPC on a full volume) SHALL raise the bounded
`art_translate_unavailable` — never an unbounded exception, never a worker crash —
SHALL be observable through exactly one bounded warn event carrying the source URL
and the failure chain on the first failure, and SHALL take the stage's existing
degraded path (the record settles `done` with its untranslated description). A
process whose fetch has failed SHALL NOT attempt another download for the rest of
its process lifetime (a per-process global latch, not per-model-directory):
subsequent calls fail immediately with
`art_translate_unavailable`, recovery being a restart or an operator seed.

A missing or unreadable model component on the air-gapped track, or a load
failure after acquisition, SHALL raise the bounded `art_translate_unavailable`
where the check can be made without importing a translation library. The backend
SHALL be agnostic about which model occupies the directory, so an operator MAY
seed it from any source producing that layout, and an already-complete layout
SHALL NEVER be re-fetched, refreshed, or upgraded by the server.

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

### Requirement: The shipped backend is a neural machine translator, never a chat model
The shipped translation backend SHALL be a sequence-to-sequence neural machine
translation model executed locally on the CPU. It SHALL NOT be an instruction-tuned
or chat-completion model, and the stage SHALL NOT call the project's LLM client,
any `LLM_*` profile, or any remote completion endpoint.

The reason is a correctness property of this project, not a preference: the
descriptions this stage translates are adult content, and an aligned chat model
refuses some fraction of them. A refusal string substituted into an image prompt is
a strictly worse outcome than the untranslated text, and it would arrive through
the SUCCESS path where the stage's failure handling cannot see it. A translation
model has no refusal behaviour available to it.

The reachability ban this requirement enforces SHALL cover the generative layer
and any general-purpose transport: the backend module SHALL NEVER import
`world.ai`, `requests`, or `http.client`/`http`, SHALL NEVER read any `LLM_*`
setting, and any outbound request it makes SHALL be exclusively the pinned model
URL at `https://argos-net.com`. Importing `urllib.request` (the stdlib fetch of
the dual-track download policy) and `world.observability` (the bounded download
lifecycle events) is PERMITTED for the acquisition lifecycle; the ban on
`socket`/`importlib` imports is likewise lifted for the acquisition path, which
needs neither.

#### Scenario: No generative-layer transport is reachable from the stage
- **WHEN** the translation stage and its shipped backend are exercised
- **THEN** no `world.ai` client, no `LLM_*` profile, and no completion endpoint is consulted, and
  the only model invoked is the local translation model

#### Scenario: The acquisition transport is the pinned model URL only
- **WHEN** the backend module's source is inspected for outbound capability
- **THEN** `world.ai`, `requests`, and `http` are absent, no `LLM_*` setting is
  read, and the only URL present is the pinned `https://argos-net.com` model URL

## ADDED Requirements

### Requirement: The operator seeding helper names the volume compose actually created
`scripts/fetch-translate-model.sh` SHALL print a volume-seeding command whose
volume name is the one `podman compose` actually created, never an unprefixed
guess: compose project prefixing means the real volume is
`<project>_evennia-translate` (default project `mud`, overridable through
`COMPOSE_PROJECT_NAME`), and a command naming only `evennia-translate` seeds a
silently orphaned volume. When `podman` is available the script SHALL resolve the
name dynamically — the exact name, then the project-prefixed name, then a
`podman volume ls` suffix match on `(^|_)evennia-translate$` — and print the first
match (a failing `podman volume ls` is treated as no match, never an error); when
`podman` is absent or no volume matches it SHALL print the
project-prefixed default annotated as unresolved. Name resolution SHALL NOT
change the script's exit status or its download/verify behavior.

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

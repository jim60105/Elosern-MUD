# art-prompt-translation delta

## ADDED Requirements

### Requirement: The shipped backend is a neural machine translator, never a chat model
The shipped translation backend SHALL be a sequence-to-sequence neural machine translation model
executed locally on the CPU. It SHALL NOT be an instruction-tuned or chat-completion model, and the
stage SHALL NOT call the project's LLM client, any `LLM_*` profile, or any remote completion
endpoint.

The reason is a correctness property of this project, not a preference: the descriptions this stage
translates are adult content, and an aligned chat model refuses some fraction of them. A refusal
string substituted into an image prompt is a strictly worse outcome than the untranslated text,
and it would arrive through the SUCCESS path where the stage's failure handling cannot see it. A
translation model has no refusal behaviour available to it.

#### Scenario: No generative-layer transport is reachable from the stage
- **WHEN** the translation stage and its shipped backend are exercised
- **THEN** no `world.ai` client, no `LLM_*` profile, and no completion endpoint is consulted, and
  the only model invoked is the local translation model

### Requirement: The model artifact is operator-seeded and its absence is bounded
The backend SHALL load its model from the code-only `ART_TRANSLATE_MODEL_DIR` directory, which SHALL
contain a CTranslate2 model directory and a SentencePiece source model. The backend SHALL NOT
download, fetch, or otherwise populate that directory at run time: the game server performs no
outbound request for it.

A missing directory, a missing or unreadable model component, or a load failure SHALL raise the
bounded `art_translate_unavailable` BEFORE any translation library is imported where the check can
be made without one, so an unseeded deployment pays no import cost and takes the specified
degraded path. The backend SHALL be agnostic about which model occupies the directory, so an
operator MAY seed it from any source producing that layout.

#### Scenario: An unseeded model directory degrades without a fetch
- **WHEN** the stage is enabled and `ART_TRANSLATE_MODEL_DIR` is absent or empty
- **THEN** the backend raises `art_translate_unavailable`, no network request is attempted, and the
  record still settles `done` with its untranslated description

#### Scenario: A malformed model directory is bounded, not fatal
- **WHEN** the model directory exists but lacks the CTranslate2 model or the SentencePiece model,
  or the load raises
- **THEN** the backend raises `art_translate_unavailable` and no unbounded exception escapes

#### Scenario: The server never fetches a translation model
- **WHEN** the whole art suite runs with the stage enabled against a seeded and an unseeded
  directory
- **THEN** no outbound network call is attempted for the model in either run

### Requirement: The translator is built once per process and decodes deterministically on the CPU
The backend SHALL construct at most one translator per configured model directory per process,
under a lock guarding CONSTRUCTION only and never the translation call. The device SHALL be pinned
to the CPU; the backend SHALL NOT select or fall back to a GPU device. `ART_TRANSLATE_THREADS` SHALL
reach the translator's intra-op thread count when non-zero and SHALL leave the library default in
place when zero.

Decoding SHALL be deterministic: the backend SHALL use beam search and SHALL NOT enable sampling,
so the same source text and the same model always produce the same translation. This is what lets
the stage carry no persistent cache — repeat determinism is a property of the decoder, not of
stored state.

Translation libraries SHALL be imported LAZILY inside the first backend call, never at module
import, so the module stays importable and the settings module stays loadable on a checkout where
the optional stack is absent.

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

## Why

`add-art-prompt-translation-seam` ships the prompt-translation stage complete
except for the one thing that translates: the gate, the boundary, the failure
contract, the events, and the harness double are all in place, and
`ART_TRANSLATE_BACKEND` already names the class this change creates. Until it
exists, enabling the stage produces `art_translate_unavailable` and the
untranslated description.

The engine has to be a plain sequence-to-sequence machine translator rather than
a chat model. This is an adult game: an instruction-tuned LLM with safety
alignment will refuse some fraction of these descriptions, and a refusal string
is a far worse prompt than untranslated Chinese. A neural MT model has no
refusal behaviour to exhibit — it maps a token sequence to a token sequence and
that is all it can do.

## What Changes

- New dependency **`ctranslate2` + `sentencepiece`**, and deliberately NOT
  `argostranslate`. The obvious package pulls 83 transitive packages including
  `torch`, the full `nvidia-*` CUDA stack, `spacy`, `thinc`, and `blis`,
  because it carries a sentence segmenter this pipeline does not need — the
  seam already splits on lines. `ctranslate2` + `sentencepiece` resolve to four
  packages total (`numpy` and `pyyaml` being the other two, and `numpy` is
  already in the lock via SciPy and Pillow), on a sub-40 MB CPU wheel.
- New `world/art/translate_ct2.py::CTranslate2Backend`: lazy imports, one
  process-wide translator per model directory, CPU device pinned, deterministic
  beam-search decoding, and the batch `translate(lines) -> lines` contract the
  seam specified.
- New code-only `ART_TRANSLATE_MODEL_DIR` (`server/.translate`), on the same
  rule that keeps `ART_STORE_ROOT` and `ART_REMBG_MODEL_DIR` off the
  environment — a mistyped value would silently relocate the model artifact off
  its persistent volume.
- New environment-backed `ART_TRANSLATE_THREADS`, mirroring
  `ART_REMBG_THREADS`.
- **No runtime download.** Unlike the background-removal stage, this change
  fetches nothing at run time: the model is operator-seeded into a persistent
  volume and a missing or malformed model directory is the bounded
  `art_translate_unavailable`. The game server therefore gains no new outbound
  network behaviour at all. A `scripts/` helper and a documented one-line recipe
  do the seeding.
- The backend is model-agnostic: it requires a CTranslate2 model directory plus
  a SentencePiece source model, which is exactly what an Argos Open Tech
  `.argosmodel` archive contains once unzipped, and also what
  `ct2-transformers-converter` produces from `Helsinki-NLP/opus-mt-zh-en`. Both
  routes are documented; neither is baked into the code.
- Container: the persistent volume for `server/.translate`, matching the
  `server/.rembg` precedent.

## Capabilities

### New Capabilities
None. This change implements the backend contract that
`art-prompt-translation` already specifies.

### Modified Capabilities
- `art-prompt-translation`: gains the backend's own requirements — the model
  artifact contract and its bounded absence, one translator per process,
  CPU-pinned deterministic decoding, and the no-runtime-download guarantee.
- `settings-environment-overrides`: `ART_TRANSLATE_THREADS` joins the
  environment-backed inventory; `ART_TRANSLATE_MODEL_DIR` joins the code-only
  list.
- `container-image`: the `server/.translate` volume joins the writable-path and
  compose-volume sets.


## Dependencies

depends-on: add-art-prompt-translation-seam

Needs the seam this change plugs into: the `translate(lines) -> lines` contract,
the bounded codes, the `ART_TRANSLATE_BACKEND` setting whose default already
names this change's class, and `world/art/tests/test_translate.py` with its shard
registration. Implementing it first would mean writing a backend for an interface
that does not exist.

Independent of `recut-art-portrait-prompt` in both directions.

Size: 37 tasks / one engineer-day.

## Batch:

Batch 2, after `add-art-prompt-translation-seam`.

Code-conflict notes: owns `world/art/translate_ct2.py`,
`scripts/fetch-translate-model.sh`, the `ctranslate2`/`sentencepiece` lock entries,
the `/app/server/.translate` volume, and the `CTranslate2Backend` test class. It
APPENDS to `server/conf/settings.py`, `server/conf/tests/test_env_overrides/`,
`.env.example`, `docs/development/settings-and-environment.md`, and
`docs/gm/prompts.md` where the seam change already added entries, and its
`settings-environment-overrides` delta is written against the post-seam text —
so it must not be implemented before that change lands.

## Impact

- New: `world/art/translate_ct2.py`, `scripts/fetch-translate-model.sh`, tests
  in `world/art/tests/test_translate.py` (existing module, new class).
- Edited: `pyproject.toml` / `uv.lock` (`uv add`), `server/conf/settings.py`,
  `server/conf/test_settings.py`, `server/conf/tests/test_env_overrides/`,
  `Containerfile`, `compose.yaml`, `tests/test_container_contract.py`,
  `web/tests/browser/browser_settings.py` (unchanged behaviour — the harness
  keeps the double), `.env.example`,
  `docs/development/settings-and-environment.md`, `docs/gm/prompts.md`.
- Depends on `add-art-prompt-translation-seam`: this change's class is the one
  that change's `ART_TRANSLATE_BACKEND` default already names, and its tests
  build on that change's `test_translate.py`.

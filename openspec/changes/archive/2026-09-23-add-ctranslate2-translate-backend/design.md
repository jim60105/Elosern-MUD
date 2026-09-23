## Context

`add-art-prompt-translation-seam` defined `translate(lines) -> lines`, the
bounded codes `art_translate_unavailable` / `art_translate_error`, the per-line
language gate, the non-fatal failure semantics, and the `ART_TRANSLATE_BACKEND`
dotted-path seam whose default already names
`world.art.translate_ct2.CTranslate2Backend`. This change writes that class.

The one hard constraint the owner set: the engine must not be able to refuse.
This is an adult game, and an aligned chat model will decline a share of these
descriptions. Critically, a refusal arrives through the SUCCESS path — the model
returns a string, the stage validates it as a string, and a sentence about being
unable to help is substituted into an image prompt. None of the seam's failure
handling can catch that, because nothing failed. A neural MT model closes the
hole structurally rather than by prompt engineering.

See `proposal.md` for motivation and the delta specs for requirements.

## Goals / Non-Goals

**Goals:**
- A local, CPU, refusal-incapable translator behind the existing seam.
- No new outbound network behaviour in the game server, at all.
- A dependency footprint proportionate to "translate a dozen short lines".

**Non-Goals:**
- No Traditional-to-Simplified normalization and no domain glossary in this
  change (D4). Both are named, measured follow-ups rather than speculation.
- No GPU path, no batching across jobs, no persistent cache (the seam's D5
  already settled that).
- No change to the seam, the gate, the events, or the failure semantics.

## Decisions

**D1 — `ctranslate2` + `sentencepiece`, explicitly NOT `argostranslate`.**
Argos Translate is the obvious choice and the wrong one here. Resolved against
this project's Python 3.13 floor it brings **83 packages**, including `torch`
and the full `nvidia-*` CUDA stack, `spacy`, `thinc`, `blis`, and
`cuda-bindings` — almost all of it to support sentence boundary detection, work
this pipeline does not need, because `add-art-prompt-translation-seam`'s gate
already splits the description into lines and the lines are short. Dropping the
wrapper and calling CTranslate2 directly resolves to **four packages**:
`ctranslate2`, `sentencepiece`, `numpy`, and `pyyaml`, and `numpy` is already in
`uv.lock` via SciPy and Pillow. The CPU wheel for cp313 x86_64 is under 40 MB,
comparable to the `onnxruntime` the project already carries for background
removal. The resolution numbers above were measured with `uv pip compile` while
writing this design, not estimated; task 1.2 makes re-verifying them a gate
rather than trusting this paragraph.

**D2 — The model is operator-seeded; the server never fetches.** The
background-removal stage lets its library download a ~1 GB model at first use,
gated by `ART_REMBG_DOWNLOAD_ENABLED`. This change deliberately does not offer
that. Without the Argos wrapper there is no download machinery to inherit, so
implementing one would mean writing HTTP fetch, archive extraction, and
integrity checking into the game server — new outbound network behaviour, new
attack surface, and new failure modes, to save an operator one `curl | unzip`.
The seam already specifies exactly what an unseeded deployment does
(`art_translate_unavailable`, one warn line, untranslated prompt, image still
produced), so the degraded path is free. `scripts/fetch-translate-model.sh` puts
the recipe in the repo where it can be read and audited, run by a human, on the
host.

**D3 — The backend is model-agnostic; the layout is the contract.** It requires
a CTranslate2 model directory plus a SentencePiece source model under
`ART_TRANSLATE_MODEL_DIR`, and nothing else. That layout is what an Argos Open
Tech `.argosmodel` archive contains once unzipped (Argos publishes CTranslate2
models; only its Python wrapper is heavy), and it is also what
`ct2-transformers-converter` emits from `Helsinki-NLP/opus-mt-zh-en`. Both
routes get documented and neither gets hard-coded, so replacing the model is an
operator action rather than a code change.

**D4 — No Traditional-to-Simplified normalization, and no glossary, on
speculation.** OPUS-derived zh→en models are trained on a corpus that skews
simplified, so normalizing Traditional input plausibly improves output. But
"plausibly" is the whole of the evidence: the SentencePiece vocabulary covers
Traditional characters, and the alternative costs a vendored ~20k-entry Unihan
table, its build script, and its license notices. The same applies to a
project-specific fantasy/adult glossary — the standard techniques for forcing
terminology through NMT (placeholder substitution, constrained decoding) are
real machinery, and mixed-script pre-substitution makes MT output worse, not
better. Task 7.3 therefore makes measuring this an explicit acceptance step with
recorded samples, and names the follow-up change to open if the measurement
justifies it. Guessing here would add permanent surface for an unmeasured gain.

**D5 — One translator per process, lock on construction only.** Copied from
`world/art/cutout.py`'s session cache, including the check-lock-recheck shape
and the deliberate decision not to hold the lock across inference. Model load is
seconds; translation is milliseconds; only one drain runs at a time anyway
because of the worker slot, so contention is theoretical — but the pattern is
already in the codebase and diverging from it would cost a reader more than it
saves.

**D6 — Beam search, no sampling.** Deterministic decoding is what makes the
seam's "no persistent cache" decision correct (its D5). It is also what makes
the regression tests assertable at all. Sampling would buy nothing here — there
is no diversity requirement on a translation.

**D7 — CPU device pinned, never auto-selected.** `ctranslate2` will use CUDA if
asked. This process is the Evennia server; a GPU grab would contend with the
sd-webui server that is the actual point of the pipeline, and the workload is
milliseconds of CPU. `device="cpu"` is passed explicitly rather than left to a
default that could change.

## Risks / Trade-offs

- **Translation quality on Traditional Chinese fantasy and adult vocabulary is
  unmeasured.** This is the real risk and D4 is the honest answer: it is
  measured in acceptance, with samples recorded in the task, and a named
  follow-up if it fails. A bad translation still produces an image; the failure
  mode is a weaker prompt, not a broken pipeline.
- **A 39.6 MB wheel and a few hundred MB of model in a volume.** Proportionate
  next to the background-removal stack already present, and both are opt-in.
- **`numpy` becomes a direct transitive of an art dependency.** It is already in
  the lock via SciPy and Pillow, so the resolution should be a no-op; task 1.2
  makes verifying that a gate rather than an assumption.
- **An operator who never seeds the volume sees no translation and no error in
  the game.** Mitigated by the seam's startup stage report, by the one
  `art_translate_failed` warn per generation, and by the documented recipe. This
  is the same failure shape the background-removal stage had, which is exactly
  why that report was added.

## Migration Plan

None. New settings default to off and to an empty directory; with the stage
disabled the pipeline is byte-identical to before. An operator opts in by
seeding the volume and setting `ART_TRANSLATE_ENABLED=true`.

## Open Questions

One, deliberately deferred to measurement rather than guessed (D4): whether
Traditional-to-Simplified normalization measurably improves this model's output
on this project's text. Task 7.3 answers it with recorded samples.

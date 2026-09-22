## Context

`world/art/worker.py::_settle_one` opens by reading
`description = str(record.db.source_description or "")` and later calls
`client.generate(subject, description)`. Between those two lines is the only
place in the pipeline where the prompt text exists, is complete, and has not yet
been sent anywhere. That gap is this change's entire footprint.

The text arriving there is Traditional Chinese from six independent sources:
`SCENE_ARCHETYPE_REGISTRY[...].scene_sentence`, `MonsterTier.description` /
`display_name_zh` / `example_monsters_zh`, `Subrace.display_name_zh`,
`ItemPresentation.summary_zh`, the persona `appearance` block, and the gallery
`custom_prompt`. The last two are authored by a player at runtime.

`world/art/cutout.py` already solved the identical architectural problem on the
other side of `client.generate(...)`: an optional, local, CPU-bound stage with an
injectable backend, bounded error codes, lazy imports, a non-importing test
double, and worker-owned events. This change is that shape again, with one
deliberate difference in failure semantics (D3).

See `proposal.md` for motivation and `specs/art-prompt-translation/spec.md` for
the requirements.

## Goals / Non-Goals

**Goals:**
- Put the translation call in the one correct place and define, in the spec,
  exactly what happens on every failure.
- Make "already English" free: a player's English tags must cost zero backend
  calls, not one round-trip that happens to be an identity.
- Ship the seam complete enough that `add-ctranslate2-translate-backend` adds one
  class and one dependency and nothing else.
- Make an optional-but-disabled art stage visible at boot.

**Non-Goals:**
- No translation engine, no dependency, no model, no container volume. That is
  `add-ctranslate2-translate-backend`.
- No Traditional-to-Simplified normalization. That exists because of a specific
  engine's training corpus, so it belongs with that engine.
- No changes to the description composition (that is
  `recut-art-portrait-prompt`), to the prompt templates, to the queue, or to any
  player-facing surface.
- No persistent translation cache (D5).

## Decisions

**D1 — The stage runs in the worker, not in `sd_worker`.** Both are on the
background thread and both would work, but the worker is where every other
pipeline stage lives, where the job key and image id needed for events are in
scope, and where the existing `try/except` already maps outcomes to settles.
Putting it in `sd_worker.build_txt2img_request()` would push a non-transport
concern into the transport module and would hide the translated text from
`FakeSDWebUIClient`, which records the description it was handed — the single
most useful assertion point in the whole change.

**D2 — The record keeps the authored text.** The stage returns a value; it does
not write back. `source_description` and `source_hash` stay the authored
Chinese, so the record remains auditable in the language it was written in,
`@art status` keeps showing what a human authored, and toggling
`ART_TRANSLATE_ENABLED` never rewrites records or invalidates digests. The cost
is re-translating on every regeneration, which D5 shows is affordable.

**D3 — Translation failure is non-fatal; cutout failure is fatal. Both are
right.** A failed cutout means the bytes on disk are not what was asked for, so
the record must not claim success. A failed translation means the prompt was
less good than it could have been — and the untranslated prompt is exactly what
ships today. Falling back and generating is strictly better than refusing. The
spec states this divergence explicitly so a future reader does not "fix" the
asymmetry.

**D4 — The gate is per line and keyed on script, not on field provenance.** The
composed description is already line-structured (the persona block renders one
line per sub-key, equipment one line per item, free text one line). A line with
no Han character is Latin-script and is passed through untouched without a
backend call. Two consequences worth naming: a player typing `1girl, blue hair,
smile` into the gallery box gets those exact tokens back, and a fully-English
description short-circuits the whole stage including backend resolution. The
gate deliberately does NOT ask which part of the description a line came from —
the stage receives one string, and a provenance-aware gate would couple it to
the composition rules it must not know about.

**D5 — No persistent cache; a bounded in-process memo at most.** The first draft
of this design called a cache a correctness requirement, on the grounds that
regenerating a subject twice must produce the same prompt. That was wrong: a
sequence-to-sequence translator decoding with beam search is deterministic for a
given input and model, so repeat determinism comes from the engine, not from a
cache. That leaves only performance, and the numbers do not justify persistence
— translating a dozen short lines on CPU is well under a second against a
generation that takes tens of seconds. A process-lifetime memo keyed on the
line is a legitimate later optimization; a cache file, its format, its
invalidation, and its volume are not worth owning.

**D6 — No lease-allowance term.** `_lease_timeout()` already charges
`ART_SD_TIMEOUT_SECONDS` (600 by default) plus a 60-second local-conversion
allowance per item. A sub-second translation fits inside that with enormous
margin. The one genuinely slow event — a cold model load on the first
translation of a process — is the exact situation the background-removal design
already put deliberately OUTSIDE the lease bound, relying on the claim-token
rule to make an overrun safe rather than corrupting. Adding a knob and a term
for a cost that does not exist would be spec surface with no behaviour behind
it. If measurement later contradicts this, a follow-up change adds the term with
evidence.

**D7 — The default backend names a class that does not exist yet.**
`ART_TRANSLATE_BACKEND` defaults to the dotted path
`add-ctranslate2-translate-backend` will create. Until then, an operator who enables
the stage gets `art_translate_unavailable`, one warn line, and the untranslated
description — today's behaviour plus a log line. This is the forward-declared
seam AGENTS.md prefers over a fake implementation: the unavailable path is a
real, specified, tested behaviour, not a stub. The alternative — shipping an
identity backend as the default — would make the stage silently claim to work.

**D8 — Backend contract is batch, not per line.** `translate(lines) -> lines`
takes the tuple of lines that need translating and returns one result per input.
A real engine decodes a batch far more efficiently than a loop of single calls,
and a length-checked batch is trivially validated. The stage owns the split, the
gate, the reassembly, and the validation; the backend owns nothing but the
mapping.

**D9 — A returned line still carrying Han is reported, not rejected.** The
background-removal stage rejects a pass-through result, because an unchanged
image proves the stage did nothing. Text is different: a translator that
correctly leaves a proper noun alone returns a Han-bearing line, and rejecting
that would turn a correct result into a failure. The stage counts such lines and
hands the count to the worker's event instead, which is the useful signal
without the false positive.

**D10 — One boot line for optional art stages.** The background-removal stage
shipped correctly wired, with a default-off setting, and was believed to be
running for weeks while it was not — there is no observable difference between
"off" and "broken" for a stage whose only output is an absence. One
`startup_step`-family info event naming each optional stage and its state makes
that distinguishable at a glance. It is added here, covering both stages, rather
than in a separate change, because this change would otherwise reintroduce the
exact same trap.

## Risks / Trade-offs

- **English expansion.** A translated description is roughly 1.5–2x the source
  length. The deployment's checkpoint carries a Qwen3 text encoder rather than a
  77-token CLIP, so long prompts are not the cliff they would be on an SDXL
  model, and the source is already bounded (the persona block by its own field
  and block caps, `custom_prompt` by `CUSTOM_PROMPT_MAX`). No length knob is
  added because none is currently justified; if real prompts turn out to be
  truncated at the server, that is a measured follow-up, not a guess now.
- **The stage is off by default, which is how the last optional stage got
  missed.** Mitigated by D10's boot line, by the `.env.example` entry, and by
  `add-ctranslate2-translate-backend` shipping the operator recipe. Defaulting it on
  is not an option while the backend does not exist.
- **Re-translating on every regeneration** (D2's cost). Bounded by D5's
  measurement; a memo is available if it ever matters.
- **A backend could mangle line structure.** The length check catches a dropped
  or invented line; it cannot catch a backend that returns the right number of
  wrong lines. That is the backend's contract to keep, and change 3's tests are
  where it is kept.

## Migration Plan

None. New setting defaults to off; with it off the pipeline is byte-identical to
today. No data migration, no compatibility shim (unreleased project).

## Open Questions

None blocking. One deferred measurement: whether a process-lifetime memo (D5) is
worth adding is answerable only once a real engine exists, so it is explicitly
left to `add-ctranslate2-translate-backend`'s manual acceptance step.

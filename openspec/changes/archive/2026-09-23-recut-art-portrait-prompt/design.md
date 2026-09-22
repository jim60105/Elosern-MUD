## Context

The art pipeline composes an sd-webui request in two layers. `world/art/subjects.py`
builds a deterministic `{description}` at ENQUEUE time (it is stored on the queue
record and hashed into `source_hash`), and `world/art/sd_worker.py::render_prompt_pair`
wraps that description in `art.portrait_prompt` / `art.scene_prompt` plus the shared
`art.negative_prompt` at GENERATE time. All five template keys live in
`prompts/art.yaml`; `world/prompts/registry.py` declares each key's allowed
placeholders.

Three facts make this change small and safe:

- `description_for()` has exactly three call sites, all in `world/art/service.py`
  (397, 418, 586), all art-only. The description is never shown to a player, so
  narrowing it touches no player-facing prose and no zh-TW content rule.
- Only ONE of those call sites passes an age (`service.py:582-586`); the other
  `character_ages()` calls in `service.py` and `presenter.py` are validation-only
  and discard both values.
- `art-portrait-cutout` already ships the matting stage, gated on
  `ART_REMBG_ENABLED` and `CUTOUT_SUBJECT_KINDS = {CHARACTER, MONSTER}` —
  precisely the subject kinds `art.portrait_prompt` serves. The prompt and the
  stage were designed in different changes and never reconciled.

See `proposal.md` for motivation and the three delta specs for the requirements.

## Goals / Non-Goals

**Goals:**
- Ship a portrait prompt that contains only the subject's visual truth, composes a
  full-body figure, and hands the cutout stage a flat white backdrop.
- Make the apparent age the one age that can reach a prompt, structurally — by
  renaming the parameter, not by a comment.
- Delete `art.style` rather than retune it, and say in the spec why: style is
  already a first-class request field (`ART_SD_STYLES`).

**Non-Goals:**
- No translation. The description stays whatever language its sources are in;
  `translate-art-prompt-locally` owns that seam and is deliberately separate.
- No change to `art.scene_prompt`'s composition, to `art.monster_description`,
  to the cutout stage, to any setting, or to any dependency.
- No `_en` sibling fields on any lore registry. That idea was considered and
  dropped (D5).
- No compatibility shim for existing `source_hash` values (unreleased project).

## Decisions

**D1 — Delete `art.style`, do not retune it.** Its shipped value is the literal
string `approved visual style`, so the rendered sentence has always been "in the
approved visual style." — a phrase that instructs nothing. The deployment's real
style knob is `ART_SD_STYLES` (this box runs
`anima-best-quality,anima-style,turbo-anima`), which sd-webui applies as a
first-class `styles` field, not as prose competing for attention with the
subject description. Keeping an empty-but-present key would leave a slot for the
defect to grow back; the registry `PromptSpec` goes with it so library
validation fails loudly if a template still names `{style}`.

**D2 — The name goes, the race and the apparent age stay.** The owner's rule is
"appearance, worn equipment, and the player's own text — nothing irrelevant, e.g.
the name." Race/subrace and apparent age are not identity metadata: beastfolk ears
and tail, elf ears, and the body of a twenty-year-old versus a fifty-year-old are
literally what the image must show. A Traditional-Chinese proper noun is not. The
line is "does this constrain pixels", and the name is the only field that fails it.

**D3 — Apparent age is enforced by renaming, not by discipline.**
`character_description(entity, age, ...)` and `description_for(..., age=...)`
become `apparent_age`. `service.py` changes `age, _apparent_age = character_ages(entity)`
to `_age, apparent_age = character_ages(entity)`. Both ages keep being validated
by `character_ages()` before any queue write — the rejection contract in
`art-subject-model` is untouched; only which value reaches the template moves.
A keyword rename makes every future call site state which age it means.

**D4 — The white backdrop is unconditional, not gated on `ART_REMBG_ENABLED`.**
Gating the prompt on the setting would make the rendered prompt — and therefore
the digest, the stored metadata, and every regression fixture — depend on a
deployment knob, and would mean enabling the cutout silently rewrites the prompt
for already-generated subjects. A white-backdrop full-body portrait is a good
portrait with the stage off; it is merely also a keyable one with the stage on.
The delta spec pins this with a byte-identical-across-the-setting scenario.

**D5 — Rejected: authored `_en` sibling fields on the lore registries.** The
first cut of this work proposed `scene_sentence_en`, `summary_en`,
`display_name_en` beside the existing `_zh` fields, so registry-sourced prompt
text would never need translating. Dropped for two reasons. First, it cannot
cover the two sources that matter most — the persona `appearance` block and the
gallery `custom_prompt` are authored by the player at runtime, so no compile-time
English exists for them and a translation seam is required regardless. Second,
paying for a second authored copy of every registry string buys nothing once that
seam exists, while doubling the surface every future lore edit has to keep in
sync. The whole-description translator in `translate-art-prompt-locally` handles
registry text and free text with one mechanism.

**D6 — Tags ride beside the prose.** The deployment's checkpoint accepts natural
language plus danbooru tags, so `simple background, white background, plain white
backdrop, isolated on white` is appended as a tag run rather than expanded into a
sentence. Tags are what that vocabulary is trained on; a sentence saying the same
thing is longer and weaker. The prose sections stay prose.

**D7 — Templates are shipped text, not a code constant, so the spec constrains
composition rather than bytes.** The delta requirement says what
`art.portrait_prompt` must ASK FOR (full body, flat light backdrop, the two
tags), not what its exact characters are. An admin retuning wording in the
mounted `prompts/` folder stays legal; the existing rendered-prompt digest
already surfaces such an edit for staff review. Tests assert the composition
properties, not a golden string, so ordinary wording tuning does not churn the
suite.

## Risks / Trade-offs

- **Every existing character/scene queue record's `source_hash` changes.**
  `queue.py:237` flags `hash_changed` for staff review and leaves completed
  images untouched; `@art requeue` regenerates. This is the designed behaviour of
  a template edit, not a regression, and the project has no released users. Say
  so in the task list so the implementer does not treat the churn as a bug.
- **Tests embedding literal `art.yaml` text will fail.**
  `world/art/tests/test_subjects.py:476` embeds an `art.yaml` fragment, and the
  gallery-prompt and age tests assert on composed strings. Those are the tests
  that SHOULD fail; the task list names them so the implementer updates rather
  than discovers them.
- **A white backdrop is a real aesthetic change** for deployments that never
  enable the cutout. Accepted: the owner asked for it, the gallery presents cut
  figures, and the negative-prompt additions keep the subject from being washed
  out. If a future deployment wants painted portrait backgrounds it edits the
  mounted template — D7 keeps that legal.
- **`art.monster_description` stays as-is**, so monster prompts keep their
  Chinese `；例如：` connective and their example-monster list. That text is
  in-scope for the translation change, not this one; splitting it here would
  mean touching the monster template twice.

## Migration Plan

None. No data migration, no setting, no compatibility shim (unreleased project,
zero users). After merge, an operator who wants the visible effect runs
`@art requeue` for the subjects whose `hash_changed` flag is now set.

## Open Questions

None. The one judgement call — whether race and apparent age survive alongside
appearance/equipment/free text — was put to the owner and approved (D2).

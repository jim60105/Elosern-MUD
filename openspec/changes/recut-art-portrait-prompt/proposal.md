## Why

Three defects ship in every sd-webui portrait request today, and one of them
actively fights a feature this project already built.

1. **Dead tokens.** `art.character_description` opens with the character's
   display name — a Traditional-Chinese proper noun no checkpoint can render —
   and renders `art.style`, whose library value is the literal string
   `approved visual style`, so every portrait prompt contains the phrase
   "in the approved visual style." Neither contributes a pixel. Visual style is
   already configured per deployment through `ART_SD_STYLES`, which reaches the
   server as a first-class `styles` field, not as prose.
2. **The background fights the cutout.** `art.portrait_prompt` asks for "a
   simple out-of-focus background". `art-portrait-cutout` (shipped, opt-in via
   `ART_REMBG_ENABLED`) then has to key a subject out of a painted, blurred,
   colour-varying backdrop — the hardest input a matting model can be handed. A
   flat white backdrop is the configuration that stage was designed for.
3. **Wrong age, wrong crop.** The character description renders the canonical
   `age`, not `apparent_age`, so a long-lived elf's portrait asks for the wrong
   body while the game's own displayed-stats surface shows the apparent one.
   And the template asks for a "medium half-body portrait" although the gallery
   presents full-figure character art.

## What Changes

- `art.character_description` becomes `{race}, {age} years old.` plus the three
  existing self-framed slots: **`{name}` and `{style}` are removed**. The
  description carries exactly the character's visual truth — race label,
  apparent age, authored appearance, equipped-item presentation text, and the
  player's free text — and nothing else.
- `{age}` is fed from `apparent_age`, never the canonical `age`.
  `character_description` and `description_for` rename the parameter to
  `apparent_age` so the seam cannot be mis-fed silently.
- **`art.style` is deleted** from `prompts/art.yaml` and from the
  `world/prompts/registry.py` spec table. Style belongs to `ART_SD_STYLES`.
- `art.portrait_prompt` is re-cut for a **full-body** figure (head to feet in
  frame) on a **flat white backdrop**, carrying `simple background,
  white background` as trailing tags — the generation model accepts natural
  language plus danbooru tags, so the tags ride beside the prose.
- `art.negative_prompt` gains the background and crop negatives the new
  composition needs (`detailed background`, `scenery`, `gradient background`,
  `close-up`, `cropped legs`, ...).
- The `PromptUnavailableError` fallback description drops the name too, so the
  degraded path cannot reintroduce what the template removed.
- `art.scene_prompt` is **unchanged**: scenes are outside `CUTOUT_SUBJECT_KINDS`
  and want their painted background.

Every character description already in a queue record hashes differently after
this change; `source_hash` comparison surfaces that for staff requeue exactly
as designed. No compatibility shim — the project is unreleased.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `art-subject-model`: the deterministic-description requirement changes — the
  description no longer carries `display_name`, no longer renders an
  `art.style` fragment, and renders apparent age rather than canonical age.
- `art-gallery-prompt-fields`: the prompt-library requirement's degraded-path
  scenario currently promises a fallback "built from the display name, race
  label, and age"; the fallback loses the name and takes apparent age.
- `internal-art-worker`: gains a requirement pinning what the portrait positive
  and negative templates must compose — a full-body figure on a flat backdrop
  the cutout stage can key — so a later prompt edit cannot silently reintroduce
  a painted background under the shipped cutout feature.


## Dependencies

depends-on: (none)

Size: 35 tasks / one engineer-day.

## Batch:

Batch 1, in parallel with `add-art-prompt-translation-seam`.

Code-conflict notes: owns `prompts/art.yaml`, `world/prompts/registry.py`,
`world/art/subjects.py`, `world/art/service.py`, and the prompt-library tests.
`add-art-prompt-translation-seam` owns `world/art/translate.py`,
`world/art/worker.py`, and `server/conf/settings.py` — no shared file. Both
touch `world/art/tests/test_worker.py` only if task 3.8 lands its composition
tests there rather than in `test_sd_worker.py`; landing them in
`test_sd_worker.py` as written keeps the two changes file-disjoint.

## Impact

- Edited: `prompts/art.yaml` (three templates rewritten, one key deleted),
  `world/prompts/registry.py` (`art.style` spec removed,
  `art.character_description` placeholders narrowed to
  `race`/`age`/`appearance`/`equipment`/`custom`), `world/art/subjects.py`
  (`character_description`, `description_for`, the degraded fallback),
  `world/art/service.py` (the gallery seam passes `apparent_age`),
  `docs/gm/prompts.md` (the operator placeholder table, already stale for
  `{equipment}`/`{custom}`).
- Tests edited: `world/art/tests/test_subjects.py`,
  `world/art/tests/test_gallery_prompt.py`,
  `world/art/tests/test_subject_ages.py`, `world/prompts/tests/`, and the
  `art.yaml` literal fixtures those modules embed. No new test module, so no
  `.github/evennia-shards.json` edit is expected.
- No new dependency, no new setting, no runtime cost, no network. The change is
  data plus three small function bodies.
- Unblocks nothing technically, but shrinks the text that
  `translate-art-prompt-locally` will have to translate to exactly the text
  that matters.

## Why

`gallery-generation-jobs` can put a second image in a character's gallery, but
every image is built from the same deterministic sentence. The whole point of a
gallery is choosing what the picture is *of*: this character in their armour,
this character with their staff, this character with nothing on, plus whatever
the player wants to ask for in their own words.

Today `character_description` always includes the persona appearance block and
never mentions equipment, even though `world/lore/items.py::ItemPresentation`
already owns exactly the right registry-authored visual text for every equipped
item.

## What Changes

- New closed field catalog in `world/art/gallery_prompt.py`: `appearance`,
  `weapon_main`, `weapon_off`, `armor`, `accessories`. An unknown field id is a
  typed rejection at the service boundary.
- `request_gallery_image` gains `fields=()` and `custom_prompt=""`. The selected
  ids are stored verbatim on the card's `requested_fields` for provenance, in the
  declared catalog order.
- `world/art/subjects.py::character_description` becomes selection-aware: the
  appearance block is contributed only when `appearance` is selected, so an
  unselected description reproduces the pre-appearance text exactly.
- Selected equipment fields contribute the equipped items' registry
  `ItemPresentation` visual text, read read-only from `world/lore/items.py`. An
  empty slot and an item key absent from the registry contribute nothing; no item
  mechanics, stat, or price data is ever rendered.
- Free-form `custom_prompt` is validated (bounded length, no control characters,
  whitespace-normalized) and appended verbatim after every field contribution.
- `prompts/art.yaml` gains `{equipment}` and `{custom}` slots on
  `art.character_description`, and `world/prompts/registry.py` extends that spec's
  `allowed_placeholders` — the prompt library stays the sole source of template
  text.
- The existing deterministic seams keep today's output by selecting `appearance`,
  so no already-specified description changes.

No backward compatibility or data migration: no released users; the change is
additive to a description builder whose output is regenerated on demand.

## Capabilities

### New Capabilities

- `art-gallery-prompt-fields`: the closed field catalog, its validation, the
  equipment-presentation fragment contract, the free-text bound, and the
  `requested_fields` provenance recorded on each card.

### Modified Capabilities

- `art-subject-model`: the deterministic-description requirement becomes
  composable by explicit field selection, admits registry-owned equipment
  presentation text for selected slots, and admits bounded appended free text —
  while keeping every existing exclusion (other persona keys, both identity
  layers, secret state, combat resources, disguised stats) intact.

## Impact

**Sequencing note.** Land this AFTER `gallery-autogen-retrofit`: both edit
`world/art/service.py::_ensure_character_portrait` and the recovery scan, and this
change's job there is to make the already-retrofitted request's field selection
explicit.

`ItemPresentation.summary_zh` is a player-facing item blurb rather than an
authored visual-appearance field. Spot checks read as visually descriptive, but
this change records any entry that reads poorly as prompt text rather than
rewriting the registry.

- `world/art/gallery_prompt.py` — new module: catalog, validation, fragments,
  composition.
- `world/art/subjects.py` — `character_description` gains the selection and the
  equipment/custom fragments.
- `world/art/service.py` — `request_gallery_image` gains `fields` and
  `custom_prompt` and stores `requested_fields` on the pending job.
- `prompts/art.yaml`, `world/prompts/registry.py` — two new placeholders.
- `world/art/tests/`, `world/prompts/tests/` — composition, determinism,
  exclusion, and bound coverage.
- Reads `world/lore/items.py` and stored equipment state; writes neither.
- Unaffected: the queue, the worker, the SD client, the store, scene and monster
  descriptions, the gallery record contract, and the resolution chain.

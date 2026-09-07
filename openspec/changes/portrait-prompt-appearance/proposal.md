## Why

`world/art/subjects.py::character_description` builds a portrait prompt from
exactly four things: the display name, the race/subrace label, the canonical
age, and the approved style fragment. Two characters of the same race and age
therefore produce nearly identical prompts, and every dark-elf card in the
roster would be drawn as interchangeable.

The preset registry now carries an authored `appearance` block — height, weight,
measurement, style, overview, attire, feature — and so does every imported
character card. That is exactly the physical, stable, authored data a portrait
prompt should be built from, and it is currently excluded by a rule written
before the block existed. The rule's real purpose is to keep *non-physical*
truth out of generated art: persona prose, secret identity, mutable combat
resources, disguised stats. `appearance` is none of those.

## What Changes

- `character_description` gains an appearance section derived from the entity's
  persona `appearance` block, rendered deterministically in the
  `world/rules/persona.py::_SUBKEY_ORDER` order so the same entity always
  produces the same prompt.
- Only the `appearance` sub-keys are read. `personality`, `life_story`, `habit`,
  `background`, `identity` (both layers), and `social_connection` remain
  excluded, so the boundary narrows rather than dissolves.
- The prompt template gains an `appearance` placeholder in
  `prompts/art.yaml` and in the `PromptSpec` for `art.character_description`,
  keeping the prompt library the sole source of template text.
- An entity with no appearance data renders the section empty and produces the
  same prompt it produces today, so nothing regresses for a character whose card
  is not yet authored.
- The `PromptUnavailableError` fallback keeps its current registry-driven form
  and gains no persona read, so a broken library key still degrades
  deterministically.
- Changing the template changes the description's source hash. The existing
  staff-review path already reports a changed hash instead of silently replacing
  a completed image; no additional mechanism is introduced.

No backward compatibility or data migration: the project has no released users,
and the art store holds no generated character portraits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-subject-model`: the deterministic-description requirement narrows its
  exclusion from "no persona text" to "no non-physical persona text", admitting
  the `appearance` block by name while keeping every other persona key, the
  hidden identity layer, combat resources, and disguised stats excluded.

## Impact

- `world/art/subjects.py` — `character_description` reads the entity's
  `appearance` block through `PersonaStore` and passes it into the template.
- `prompts/art.yaml` — the `art.character_description` template gains an
  `{appearance}` slot.
- `world/prompts/registry.py` — the `art.character_description` spec's
  `allowed_placeholders` gains `appearance`.
- `world/art/tests/` and `world/prompts/tests/` — determinism, ordering,
  exclusion, and empty-appearance coverage.
- Unaffected: the queue, the worker, the SD client, the store, scene and monster
  descriptions, the portrait policy model, and the age eligibility gate.

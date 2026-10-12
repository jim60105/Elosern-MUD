# Proposal

## Why

The character image prompt flattened the whole persona `appearance` block — the `外觀：` section label, per-sub-key labels, numeric body data (`height`/`weight`/`measurement`) no image backend can consume, and `attire`/`feature` setting clothing that fights the equipment-slot fragment — and the base sentence named the project-invented subrace display label (e.g. 基亞蘭) that image models do not recognize. The render prompt should carry only visual prose an image backend can draw.

## What Changes

Implemented and verified on `master` in commit `63993c5b` (`feat(art): render persona appearance as label-free visual prose`); this change records the behavior in the specification.

- The prompt-facing race label resolves a subrace to its **parent race** display name (`SUBRACE_REGISTRY[key].race_key` → `RACE_REGISTRY[...].display_name_zh`); a bare race key resolves directly and an unregistered key falls back to the stored string as before. **BREAKING** for prompt text: project-invented subrace labels (e.g. 基亞蘭/暮歌支系) never enter an image prompt again.
- The persona `appearance` contribution is filtered to the image-usable sub-keys `APPEARANCE_PROMPT_SUBKEYS = ("style", "overview")` in the declared order mirroring `world/rules/persona.py::_SUBKEY_ORDER`. `height`/`weight`/`measurement` are numeric body data no prompt consumes; `attire`/`feature` describe setting clothing and accessories that would fight the equipment-slot fragment — the equipped combination is the only clothing source for a render. A compact NPC card's one-paragraph string appearance has no sub-keys and passes through whole; other shapes contribute nothing.
- The fragment is **label-free**: neither the `外觀` section label nor any sub-key label enters the prompt; it carries only the authored capped values, one per line. The store's shipped per-field 600-code-point cap is preserved by flattening each kept value through `PersonaStore` and stripping the imported `_FIELD_LABELS["appearance"]` prefix.
- A character whose only appearance data is body numbers or setting clothing contributes an empty appearance fragment (the bare template stem, no dangling separator).
- Affected tests re-pinned to the logic rather than shipped-template literals (test-owned `art.yaml` fixtures remain the module convention): the synthetic race label is sourced via `SYNTH_RACES[SYNTH_SUBRACES[k].race_key].display_name_zh` and the `synthetic_registries` scopes widened with `"races"`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-subject-model`: the *Subject descriptions are deterministic and exclude non-physical truth* requirement currently pins "the race/subrace label" and "the authored appearance sub-keys" — both now diverge from implemented behavior. The delta re-pins it to the parent-race label and the label-free, visual-only style/overview prose.

`art-gallery-prompt-fields` was inspected and needs no delta: it governs the closed field catalog, provenance, equipment/free-text contributions, and the template-owned `{appearance}` slot — none of its scenario text pins the labeled block or the subrace label (the shipped `art.character_description` template carries no section label; the fragment always owned its own framing). `persona-store` is untouched: `flatten` still renders labeled blocks; only the art prompt strips the label back off.

## Impact

Implementation (already landed): `world/art/subjects.py` (`_race_label`, `APPEARANCE_PROMPT_SUBKEYS`, `_appearance_fragment`) and its tests `world/art/tests/test_subjects.py`, `world/art/tests/test_gallery_prompt.py`, `world/prompts/tests/test_degrade.py`, `world/prompts/tests/test_verbatim_shipment.py`. Requirement name and slug are unchanged, so existing `covers_requirement` annotations stay valid.

No player command surface, protocol, settings, or prompt-library change; `docs/gm/prompts.md`'s slot description remains accurate. Regenerated or new images simply carry the cleaner prompt; existing settled cards are unaffected.

## Batch:

depends-on: none

code-conflicts: none within this batch (one change; implementation already committed). Serialize with any future change editing `world/art/subjects.py`'s appearance/race-label seams or the `art-subject-model` specification.

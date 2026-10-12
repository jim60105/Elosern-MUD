# Design

## Context

See proposal.md — Why. The behavior is implemented and verified on `master` (commit `63993c5b`);
this document records the technical decisions behind it. The character prompt composes through
the `art.character_description` template whose `{appearance}` slot carries a whole fragment that
brings its own leading newline (`prompts/art.yaml`). `PersonaStore.flatten` is the shipped,
capped, labeled renderer for persona blocks; `world/rules/persona.py::_SUBKEY_ORDER` owns the
declared appearance sub-key order; `world/lore/races.py` owns `RACE_REGISTRY` and
`SUBRACE_REGISTRY` (each subrace row carries its parent `race_key`).

## Goals / Non-Goals

**Goals:**
- The prompt carries only renderable visual prose: stable, deterministic, capped, label-free.
- The race token is an image-backend-recognizable RACE display name.

**Non-Goals:**
- No change to `PersonaStore` itself — `flatten` still renders labeled blocks for dialogue
  injection and the NPC card, which *want* labels.
- No change to the prompt-library template, the field catalog, or equipment-slot composition.

## Decisions

- **Parent-race resolution chain** (`_race_label`): subrace key → `SUBRACE_REGISTRY[key].race_key`
  → `RACE_REGISTRY[race_key].display_name_zh`; otherwise `RACE_REGISTRY[str(db.race)]`; otherwise
  the stored string (`"unknown race"` when empty), exactly the old fallback. Alternative
  considered: keep the subrace label and append the race — rejected because image models have no
  grounding for invented subrace names and the extra token only dilutes the prompt. Subrace
  distinctiveness stays out of the image prompt by design; the race is the visual identity the
  backend can honor.
- **Sub-key allowlist, not denylist**: `APPEARANCE_PROMPT_SUBKEYS = ("style", "overview")` in
  `world/art/subjects.py`, order mirroring `_SUBKEY_ORDER`. Future persona sub-keys therefore
  never leak into prompts without an explicit decision. `height`/`weight`/`measurement` are body
  numbers no prompt consumes; `attire`/`feature` are setting clothing/accessories that would
  contradict the equipment-slot fragment — the equipped combination is the only clothing source
  for a render. The label is imported as `_FIELD_LABELS["appearance"]` from its persona.py owner
  rather than restated, so a label edit cannot silently resurrect it in prompts.
- **Reuse the store's cap by round-tripping each kept value**: each value is flattened through
  `PersonaStore` on a throwaway holder and the imported section-label prefix is stripped, so the
  shipped per-field 600-code-point cap and normalization apply unchanged instead of being
  duplicated in `world/art/`. Alternative considered: filter `flatten(("appearance",))` output
  lines — rejected because line filtering couples the prompt to label text and cannot
  distinguish an authored value containing a colon-like prefix.
- **Shape handling**: mapping-shaped appearance is filtered; string-shaped appearance (compact
  NPC card prose from `world/lore/npc_card.py`) has no sub-keys and passes through whole; any
  other shape contributes nothing.
- **Tests pinned to logic, not shipped-template literals**: synthetic race expectations source
  `SYNTH_RACES[SYNTH_SUBRACES[k].race_key].display_name_zh` and `synthetic_registries` scopes
  gained `"races"`; composition tests keep the test-owned `art.yaml` fixture convention (already
  the module norm) and assert exact label-free output as a byte contract, plus dedicated tests
  that body/attire-only appearance contributes nothing and excluded sub-keys never reach the
  prompt.

## Risks / Trade-offs

- Prompt text for existing subjects changes, so a subject regenerated after this commit yields a
  different source hash than its settled card — the existing hash-change review flow already
  reports that for staff review; no silent replacement.
- Subrace visual flavor (e.g. 暮歌支系 mannerisms) no longer reaches renders; accepted, since the
  authored label was uninterpretable to the backend anyway. Authored `style`/`overview` prose
  remains the channel for species-visual detail.

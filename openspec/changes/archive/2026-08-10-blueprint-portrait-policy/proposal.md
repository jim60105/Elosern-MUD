# blueprint-portrait-policy Proposal

## Why

Generated quests today can only spawn role-based occupants (victim, guard, merchant) with mechanical
keys — the art-assets portrait seam exists on the spawn side, but no blueprint surface can request a
named portrait or story-driven characterization. The art-portrait design explicitly defers this: an
optional per-NPC portrait-policy field on `QuestBlueprint`/`StageSpawnRequirement` is the missing
link between the scenario director's story and the portrait machinery.

## What Changes

- `BlueprintNpcReq` gains optional `display_name`, paired `age`/`apparent_age`, and a frozen
  `portrait` value object (`stable_key`) so the story can name an NPC and say how old it looks.
- The full blueprint lifecycle is extended: the output jsonschema, `to_payload()` /
  `from_payload()` round-trip, the canonical digest serialization, and the compiled per-stage
  spawn requirements all carry the new fields — no field loss at any boundary.
- Deterministic validation at the proposal boundary: `stable_key` non-empty / no colon / bounded;
  `display_name` bounded text; `age`/`apparent_age` paired integers (`type(value) is int`, so
  booleans and `None` reject) with an adult floor of 18 and a race-aware upper bound resolved
  through `NPC_TIER_REGISTRY` → `RACE_REGISTRY` lifespan; `portrait` must be a mapping with
  exactly one `stable_key` field.
- The compile boundary (`StageSpawnRequirement`) carries the fields through with mirrored
  validation, factored into a shared bound helper under `world/quests/` that the scenario director
  imports read-only.
- One elven NPC tier (`elven_civilian`, elf / `elf_common`) joins `NPC_TIER_REGISTRY` so the
  race-band rules are exercised by shipped content, not fixtures.
- The main-spec anti-hallucination requirement is narrowed: the number ban covers mechanical
  values; validated characterization ages are authored content.
- The hand-written template pool may carry portrait fields for deterministic offline quests.

## Capabilities

### New Capabilities
- `blueprint-portrait-policy`: optional per-occupant portrait policy and characterization fields on
  quest blueprints, validated deterministically at the proposal and compile boundaries and
  preserved through the whole blueprint lifecycle.

### Modified Capabilities
- `scenario-director`: `npc_req` entries gain the optional portrait/characterization fields and
  their bounded validation rules; the deterministic compile boundary carries them into the
  compiled per-stage spawn requirements.
- `scene-builder`: the anti-hallucination number ban is narrowed to mechanical values, explicitly
  excluding validated characterization ages.

## Impact

- `world/ai/scenario_director.py` — `BlueprintNpcReq` shape, `BlueprintPortrait` value object,
  output jsonschema, `to_payload()` / `from_payload()` round-trip.
- `world/ai/director_templates.py` — template pool may declare portrait fields.
- `world/quests/compile.py` — `StageSpawnRequirement` carry-through and validation; shared bound
  helper.
- `world/lore/npc_tiers.py` — one new elven NPC tier (content).
- `world/lore/races.py` / `world/lore/npc_tiers.py` — read-only consumers of the lifespan bounds.
- Tests: `world/ai/tests/test_scenario_director.py`, `world/quests/tests/test_compile.py`.

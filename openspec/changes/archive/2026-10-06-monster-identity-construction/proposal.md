## Batch:

- depends-on: monster-species-registry (the variant registry is the identity and threat source this change resolves from)
- conflicts: `world/quests/planner.py` and `world/quests/tests/test_planner.py` with `monster-quest-objectives` — this change owns the counting-identity/dedupe edit (per-record counted identities), the objectives change owns the selector-matching edit; serialize this change first, the later one rebases on the rewritten counter. `typeclasses/monsters.py` is shared with `monster-site-placement` and `monster-quest-objectives`, both of which only call the construction entry point this change establishes (no competing edits). `world/rules/traits.py` is touched only here within the monster wave; the six artwork changes touch `world/art/` and `web/` only, so no overlap.
- external-prerequisite: user balance approval for per-variant numeric combat profiles. Until it lands, the only approved numeric source is the existing `MONSTER_TIER_REGISTRY` band applied at a variant's declared threat tier, and this change's construction path documents that as the interim resolution rule — it never fabricates per-species numbers, and a balance-approved profile replaces the interim path without a schema change.

## Why

Design §4 keeps the existing `Monster` typeclass and adds `species_key`/`variant_key` persistent identity, threat tier and individual danger resolved from the variant registry rather than independently editable truth, no player-level scaling, no skill multipliers baked into stored traits, and kill accounting that keys on persistent individual identity with duplicate defeat events deduped. Today `Monster` carries only `threat_tier`, callers assign it freely, `world/rules/traits.py::initial_trait_config_for_monster_tier` is the only stat source, and defeat progress counts by database row per event batch, so a redelivered defeat event can double-count one quest's progress. Without this change the placement and quest changes have no legal way to create or count a species-backed individual.

## What Changes

- Add persistent `species_key` / `variant_key` identity to the existing `Monster` typeclass plus one construction entry point in the deterministic owner that validates both references and their species/variant membership before any persistence, then applies the approved combat configuration. Species or variant identity is never inferred from a display name, a key string, or a threat tier.
- Make the variant registry the single truth for a species-backed individual's threat tier and individual danger grade: they resolve from the variant record on read, and assigning a value that contradicts the variant is rejected — the fields are not independently editable truth for such individuals. Tier-only monsters (population/materializer callers that have not switched identity yet) keep the existing tier path unchanged until their own changes land.
- Resolve stored traits without invention: use the variant's balance-approved complete profile when one exists, otherwise the existing threat-tier band construction at the variant's declared tier (the only currently approved numeric source), with the interim resolution recorded as a boundary event. No player-level scaling exists anywhere on this path, and skill multipliers are never pre-merged into stored traits — they stay applied at resolution time by the existing combat path.
- Kill accounting: the `target_defeated` event additionally carries the individual's species/variant identity, the persistent individual identity stays the database row (never display name or tier), and the quest planner dedupes by recording counted identities per quest record, so a duplicate or redelivered defeat event cannot advance the same objective twice.

## Capabilities

### New Capabilities

- `monster-individual-construction`: species-backed individual identity on the existing `Monster` typeclass — validated construction, variant-resolved threat tier and danger grade as non-editable truth, balance-gated profile with the documented interim tier-band numeric rule, no player-level scaling, no baked multipliers, and duplicate-safe kill accounting keyed on persistent individual identity.

### Modified Capabilities

- `action-resolution-pipeline`: the `target_defeated` entry additionally carries the defeated individual's registered species/variant keys when it is a species-backed monster, so selectors resolve identity without display-name or tier inference (additive fields; dbref and tier carriage unchanged).
- `quest-progress-tracking`: DEFEAT progress dedupes by persistent individual identity per quest record, so duplicate or redelivered `target_defeated` events grant no additional progress.
- `quest-lifecycle`: `QuestRecord` gains the JSON-safe `counted_defeat_ids` tuple (per-record already-credited persistent identities for the current objective, cleared with the existing bindings on stage transition).

## Impact

- Code: `typeclasses/monsters.py` (identity fields, variant-aware read helpers), `world/rules/traits.py` (variant-config resolution beside the existing tier function), the individual construction entry point in `world/rules/` (action/creation owner), `world/rules/action/event_log.py` (event carries species/variant identity), `world/quests/planner.py` (per-record counted identities), `world/rules/combat_initiation.py` and `world/maps/wilderness_population.py` callers verified unchanged in behaviour, new test modules under `typeclasses/tests/` and `world/rules/tests/`, `.github/evennia-shards.json` registrations.
- No player-command surface change, so `docs/game/commands.md` and `docs/game/command-reference.md` are untouched. No migration, no compatibility shim: pre-identity monsters keep working through the existing tier path, which is unchanged behaviour, not a shim.

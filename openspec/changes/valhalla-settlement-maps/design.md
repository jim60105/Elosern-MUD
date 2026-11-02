# Design

## Context

See proposal.md (Why). This change uses the same tools as `grandia-settlement-maps`. All of them have landed. In `tools.settlement_synthesis.generate`, nation `valhalla` is in `GenerationConfig().beast_nations`, so it gets these classes:

- `beast_capital` for `capital_valhalla`;
- `beast_town` for every other Valhalla settlement.

Both classes use the `tribal_ring` morphology. The beast-class role rows of `DEFAULT_CATALOGUE` are `market_street`, `tribal_hall`, `assembly_ground`, `training_ground`, `guild_forecourt`, `ancestral_altar`, `tavern_lane`, `ferry_landing` (river only) and `craft_alley`.

## Goals / Non-Goals

**Goals:**
- every Valhalla national settlement has a local map that passes the lint and has complete prose.

**Non-Goals:**
- relocations;
- city gates;
- interiors;
- Python lore;
- fine fitting.

## Decisions

### D1. Order of work

Plan, generate, write prose, then verify. There is no relocation step: `water_gap` only applies to ports, and Valhalla has none. A plan failure of any other kind is reported, and that location is not generated.

### D2. Prose

Follow `docs/development/settlement-synthesis.md` § Prose pass, with these beast-folk rules from `docs/lore/settlement-locations.md` § 聚落差異深論:

- **Society.** Tribal society, with a tribal hall (部族議事廳). Leaders are chosen by consensus among the tribes, never by inheritance.
- **Rites.** The training ground is where the coming-of-age hunt and the 獸魂 rites take place. The ancestral altar or totem ground honours nature and ancestor spirits.
- **What does not exist.** There is no church, no alchemist and no magic academy. Smithing is heavy and suited to each subspecies.
- **Trade.** Trade happens at markets and through barter, but currency is still in use.
- **Tone.** Write with a robust, frank tone. It is in-world prose only, never 武俠 vocabulary.

### D3. Test-suite timing record (never blocks)

Apply the same rule as `grandia-settlement-maps` D4. The baseline is taken at the start of this change. The timing is reported in the hand-off and never stops the commit.

## Risks / Trade-offs

- [Footprints from `altoria-settlement-maps` along the border river block Valhalla cells such as `town_west_ford_camp` and `town_east_ford_camp`] → The generator grows around blocked cells. A `footprint_short` failure is reported, and that location is not generated.

## Migration Plan

None, because the project is pre-release. To roll back, revert the commit and regenerate the partition.

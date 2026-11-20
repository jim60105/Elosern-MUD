# Design

## Context

The catalog separates presentation from use mechanics. Food can retain its existing presentation and trading identity while gaining an ordinary consumable profile. This design records the balance choices separately from the durable item-use contract.

## Goals / Non-Goals

**Goals:** Give every in-scope item an explicit, flat recovery profile shared by all shops selling that item.

**Non-Goals:** Change potion profiles, shop pricing, sleep recovery, or the shared item-use timing.

## Decisions

Declare the effects on the existing rows in `content/items/core_items.yaml`, `content/items/inspect_only_codex.yaml`, and `content/items/elven_village_goods.yaml`. Set `consumable: true` and `combat_allowed: false`. Use positive stat adjustments with the existing default self scope. List multiple effects in HP, MP, SP order. A dash means no effect.

| Item key | HP | MP | SP |
|---|---:|---:|---:|
| `meal` | 4 | — | 6 |
| `kingdom_rye_hardtack` | — | — | 8 |
| `adventurer_field_ration` | — | — | 12 |
| `imperial_candied_fruit` | — | 6 | — |
| `beastfolk_smoked_jerky` | 6 | — | 14 |
| `harbor_lobster_bisque` | 18 | — | 6 |
| `elven_candied_blossom` | — | 12 | — |
| `eolas_kiln_flatbread` | — | — | 12 |
| `fionnen_wildflower_honey` | — | 4 | 6 |
| `ciaran_nightbloom_preserve` | — | 10 | — |
| `ciaran_ember_mushroom_skewer` | 6 | — | 8 |

Reuse the current action instead of introducing an eat action or deriving recovery from the food kind. Explicit profiles preserve the recovery identity across differently priced shops and leave food without a profile inert. `miners_bracing_broth` is outside scope.

## Risks / Trade-offs

- Cheap food can displace potions between fights. Keep individual food effects below the comparable 40-point potion or tonic and reserve combat use for eligible consumables.
- Per-item amounts are balance data. Keep the production numbers in the catalog at implementation time; use independent synthetic values in behavior tests.

## Migration Plan

No saved-state migration is required. Publish the revised catalog and regenerate `content/map-reference-context.json` in the same change.

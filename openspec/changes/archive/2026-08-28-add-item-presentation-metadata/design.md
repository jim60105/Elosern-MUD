## Context

`world/lore/items.py` is the immutable source of identity for the three registered items used by economy, quests, and services. Its `ItemDefinition` currently has no player-facing visual identity beyond `display_name_zh`, so the Vue client would have to infer an icon, rarity, or category from an unstable key or localized name. Such inference would violate the registry source-of-truth rule and become incorrect as the registry grows.

The binding inventory design at `docs/design/elosern-redesign/index.html:960-985` needs an item glyph, a rarity treatment, and concise item context. It also illustrates numeric stat lines and equipped-item comparisons. The deterministic equipment implementation currently records slots and item keys only; it neither stores nor resolves item modifiers. Displaying invented numeric values would contradict the single-writer and truthful-presentation boundaries.

## Goals / Non-Goals

**Goals:**

- Give every registered item an immutable, typed visual identity that read-only presenters can expose unchanged.
- Keep icon selection finite and renderer-owned: the server emits an icon key, while the Vue client maps that key to self-hosted inline SVG.
- Make rarity and item-kind treatment reviewable as registry data rather than inferred from localized text.
- Establish a bounded summary for an accessible item inspector without requiring a new runtime action or an item image service.

**Non-Goals:**

- No persistent inventory or equipment shape change, importer change, data migration, new command, or new action ID.
- No item artwork, emoji, URLs, arbitrary SVG, HTML, or remote asset delivery in item data.
- No numeric item modifier, recovery amount, combat bonus, requirement, set bonus, sort field, or comparison value until a deterministic rules change makes that fact authoritative.
- No Vue, OOB, or protocol validation change. The following change owns projection of this metadata to the WebClient.

## Decisions

### Put visual identity on the frozen item definition

`ItemDefinition` gains a frozen `presentation` value object rather than adding unrelated top-level fields. The value contains `kind`, `icon_key`, `rarity`, and `summary_zh`; every field is required for registered items. This keeps the economy identity, localized name, and visual identity together while exact trade numbers remain in `guild_economy.yaml` as required by `shop-economy`.

An item instance does not persist a copy of this data. Inventory and equipment continue to store only item keys; every reader resolves the immutable registry value. This avoids drift when a definition's wording or visual treatment changes before release.

### Use closed Python enums and an SVG icon key, not free-form symbols

The module defines closed `StrEnum` types for item kind, rarity, and icon key. The first vocabulary covers the current and intended inventory views: `food`, `potion`, `weapon`, `armor`, `accessory`, `ammunition`, `tool`, `material`, and `misc`. The renderer maps only these icon keys to its local SVG paths.

Free-form emoji and SVG strings were rejected because their metrics, color, accessibility labels, and browser rendering vary. Inferring a glyph from `item_key` or `display_name_zh` was rejected because keys are implementation identifiers and names are localized prose, not type contracts.

### Treat rarity as visual classification, not a hidden balance multiplier

`rarity` is an explicit closed identity classification used only for presentation in this change. It does not alter prices, stock, loot odds, combat, or the deterministic resolver. Future mechanics that need rarity must introduce their own reviewed rules contract instead of silently reusing a UI label as balance input.

### Keep detailed numeric comparison out of this change

The future item-inspection schema may contain ordered attribute entries only when each entry names an existing deterministic source and that source resolves the shown value. The initial registry metadata intentionally has no generic `stats` dictionary and no stringly typed `"Attack +7"` field. A loose description field would permit UI numbers to diverge from combat; a numeric dictionary would imply a rule effect that no current resolver applies.

The UI can render its structural inspection region conditionally when a later item-effects capability supplies verified entries. It must otherwise render the real category, rarity, summary, quantity, and equipped state only.

## Risks / Trade-offs

- [A new item omits presentation metadata] -> Registry-construction tests assert every enum member and summary bound, so the missing value fails before a presenter can emit it.
- [The client receives an unknown future icon key] -> The later wire contract must reject it at the protocol boundary; the client also needs a neutral, labelled fallback rather than executing arbitrary SVG.
- [Rarity becomes a gameplay input by accident] -> Keep the enum under immutable lore metadata and test that economy and resolution results are unchanged by presentation-only values.
- [Authors add misleading numbers to summaries] -> Summary guidance prohibits numeric gameplay claims; a dedicated deterministic item-effects proposal owns numeric facts and comparisons.

## Migration Plan

The registry is source-controlled, immutable data and there are no released saves to migrate. Add complete metadata to every existing definition, run focused registry and economy tests, and land the change before the WebClient projection change. Reverting the change restores the prior registry shape because no persistent record or wire payload depends on it yet.

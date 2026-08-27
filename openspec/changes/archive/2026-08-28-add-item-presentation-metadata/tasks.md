## 1. Immutable Item Presentation Model

- [x] 1.1 Define the closed item-kind, icon-key, and rarity enums plus a frozen presentation value object in `world/lore/items.py`.
- [x] 1.2 Add complete presentation metadata to every existing `ITEM_REGISTRY` definition without changing its identity, price-table key, or sellability.
- [x] 1.3 Document in code that presentation metadata is read-only and cannot carry numeric gameplay claims until a deterministic item-effects capability owns them.

## 2. Registry Contract Tests

- [x] 2.1 Extend the focused lore/economy tests to assert every registry item resolves complete, valid, bounded visual metadata.
- [x] 2.2 Add regression coverage proving malformed enum or summary data is rejected and presentation-only metadata cannot alter existing economy or equipment outcomes.
- [x] 2.3 Annotate the extended economy test with the modified `shop-economy` requirement ID (the main spec already carries it). The new `item-presentation-metadata` capability's main spec is synced in the archive workflow; its `@covers_requirement` annotations, `tools.spec_traceability check`, and CI `verify --evidence` are completed there. Run the focused `world` tests and `uv run --locked python -m tools.spec_traceability check` before handoff.

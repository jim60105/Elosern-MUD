# Proposal: gallery category sources and subject admission

## Batch:

Gallery window programme, stage 1 (design D1, D2, D3 and the D6 "Authority"
rule of `docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: remove-baseline-visual-species
- conflict: none; adds one new module and its test module (new shard entry in
  `.github/evennia-shards.json`).

## Why

The 24-row rail starves one subject kind whenever another grows. The design
replaces it with five closed categories, each bounded by its own source. This
change builds those sources as a pure, read-only module with no wire change, so
the later presenter, cutover and admission changes consume one tested origin.

## What Changes

- New read-only module `web/webclient/presentation/gallery_categories.py`:
  - the closed category list `mine`, `party`, `people`, `monster`, `scene` with
    per-category count, enabled flag and disabled reason (`people` and `scene`
    disabled in this programme stage);
  - `mine`: every character of the account that owns the rendered puppet (the
    roster's set), the live one first and marked current;
  - `party`: the owning character's live companions in party order;
  - `monster`: sighted visual species grouped by the threat tier of their
    default variant in tier-registry order, each tier with a registered species
    carrying `seen / total`;
  - an admission predicate: a subject is admitted for an actor when it belongs
    to any enabled category.
- Not wired into the `gallery` panel or any action yet (see
  `gallery-v4-presenter`, `gallery-mutation-admission`).

## Capabilities

### New Capabilities

- `webclient-gallery-categories`: which subjects each gallery category lists,
  in which groups and order, and which subjects are admitted for an actor.

### Modified Capabilities

None.

## Impact

- New: `web/webclient/presentation/gallery_categories.py`,
  `web/webclient/presentation/tests/test_gallery_categories.py`, one entry in
  `.github/evennia-shards.json`.
- Reads: `world/rules/account_roster.build_account_roster`,
  `world/rules/party.live_companions` / `bound_owner_of`,
  `world/rules/lore_knowledge.list_discovered`,
  `world/lore/monster_visuals.get_monster_visual_registry`,
  `MONSTER_VARIANT_REGISTRY`, `MONSTER_TIER_REGISTRY`.
- Estimate: 6 hours (module 2.5 h, synthetic presenter tests for the four
  rules and admission 2.5 h, shard registration, spec and gates 1 h).

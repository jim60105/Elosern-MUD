## Why

The one-time cutover must give every existing NPC a complete card, including dynamic, imported, and generated-quest NPCs whose provenance maps to no authored profile, and it must do so offline and deterministically without carrying the old provisional prose forward (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §6.1 "offline quest generation", §6.2, §11.1 case 3). That requires authored, coherent whole-card bundles chosen by stable identity — never independently drawn adjectives — with more than one voice per repeated role. Authoring those bundles and the pure selector is a self-contained workday that can run in parallel with the settlement content.

## What Changes

- Add `world/lore/npc_profiles/bundles.py`: frozen `NpcPersonaBundle` (key, complete compact card, eligible race) grouped into `NpcBundlePool`s, exported as the read-only `NPC_PERSONA_BUNDLE_POOLS`, validated at import through the card contract.
- Author one pool per NPC role tier (the ten `NPC_TIER_REGISTRY` tiers) with at least two coherent bundles each, and one generic pool per race without a tier pool (`beastfolk_generic`); the generic resolution for `human` and `elf` uses the `civilian` and `elven_civilian` tier pools.
- Add the pure, deterministic selector `select_offline_bundle(pool_key, stable_seed)` (SHA-256 of the pool key and seed modulo pool size) and `offline_pool_for(tier_key, race_key)` (tier pool when the tier's race matches, otherwise the race's generic pool), returning the bundle key and its card for the caller to persist once with `offline_bundle` provenance.
- Load-time validation: every tier and every race resolves to a pool of at least two bundles, every bundle is eligible for its pool's race, and no two bundles in a pool share a personality or speech-style text.

No caller writes bundle cards in this change; `npc-persona-roster-cutover` is the consumer.

## Capabilities

### New Capabilities

- `npc-persona-offline-bundles`: authored offline persona bundle pools and the deterministic, persisted-once selection of a coherent whole card for an NPC without an authored profile.

### Modified Capabilities

None.

## Impact

- New: `world/lore/npc_profiles/bundles.py` (vocabulary, selector, ~22 authored cards), `world/lore/tests/test_npc_persona_bundles.py` (behavior with synthetic pools) and a data-contract test over the shipped pools.
- No state writes, no schema, prompt, or UI change; no edit to the profile assembly module.

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: creates `world/lore/npc_profiles/bundles.py` alone and does not edit `world/lore/npc_profiles/__init__.py` (bundles are a separate registry imported directly). Shared append-only file: `tools/test_data_freeze.json`. Prerequisite of `npc-persona-roster-cutover`; independent of every other change.

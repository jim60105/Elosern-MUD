## Context

See proposal.md for motivation. `world/lore/npc_tiers.py` defines ten role tiers, each bound to a race (`civilian`, `guard`, `merchant`, `adventurer`, `mage`, `noble`, `bandit`, `priest`, `knight` → human; `elven_civilian` → elf). `RACE_REGISTRY` holds `human`, `beastfolk`, `elf`. Scene occupants persist their tier as `npc.db.npc_tier_key`; imported and other dynamic NPCs carry only race, sex, ages, name, and title.

## Goals / Non-Goals

**Goals:** coherent whole-card offline voices for every role tier and every race; deterministic selection by stable identity; at least two voices per pool so repeated roles vary.

**Non-Goals:** unique personalities for an unbounded population; selection at read time (selection is persisted once by the caller); using bundles for authored hosts, examiners, companions, imports, or generated-quest occupants that carry their own card.

## Decisions

### D1. Bundles are whole cards, name- and title-agnostic

Each bundle is a complete compact card written for its role and race: `identity.public` describes the role without naming anyone; `social_connection` and `identity.hidden` are empty (a bundle cannot know real relationships or secrets); appearance, personality, speech style, life story, and habit form one coherent person. Alternative rejected: composing cards from independent adjective/history/speech lists — explicitly forbidden by the product design because it yields contradictions.

### D2. Pool resolution prefers the tier, falls back to the race

`offline_pool_for(tier_key, race_key)` returns the tier's pool when `tier_key` is a registered tier whose race equals `race_key`; otherwise the race's generic pool: `human` → `civilian`, `elf` → `elven_civilian`, `beastfolk` → `beastfolk_generic`. A race without a resolvable pool is a load error, so a new race cannot ship without offline voices.

### D3. Selection is a pure hash, persisted once by the caller

`select_offline_bundle(pool_key, stable_seed)` hashes `f"{pool_key}\0{stable_seed}"` with SHA-256 and indexes the pool's fixed bundle order. The caller supplies a stable seed (the cutover uses the NPC's database id, or `quest:stage:occupant` for a durable generated-quest occupant) and persists the chosen card with provenance `{"kind": "offline_bundle", "pool": …, "bundle": …}` exactly once; later reads never re-select. Alternative rejected: Python `random` with a seed (implementation-defined across versions) and `hash()` (salted per process).

### D4. Authoring quota and review

Ten tier pools × 2 bundles + `beastfolk_generic` × 2 = 22 cards. Each pool's two bundles must differ in outlook and speech behavior, not only in wording; the bandit, guard, and knight pools are combat roles and should still read as people. Prose follows the race's established culture (`docs/lore/overview.md`, `world/lore/races.py`). Every card stays inside the contract budget (import fails otherwise).

## Risks / Trade-offs

- [Two voices per pool repeat quickly in a large world] → acceptable per the product design (variation, not unbounded uniqueness); pools can grow later without changing the selector contract, though growth reorders future selections only, never persisted ones.
- [A tier's race changes later] → the resolution rule falls back to the race pool and validation keeps every race covered.

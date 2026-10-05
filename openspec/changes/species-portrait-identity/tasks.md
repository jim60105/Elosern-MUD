## 1. Reference producer

- [ ] 1.1 Derive the `monster` official content reference from a species-backed monster's stored `species_key` inside the existing reference-derivation owner (`official-content-provenance`'s module), with tier-only individuals yielding no reference, and verify: species key resolves `(monster, <key>)`, variant differences never change the reference, a tier or display name never produces a reference, and resolution reads only stored identity plus the startup snapshot (no I/O, no mutation — database before/after comparison)
- [ ] 1.2 Confirm the presentation chain's official-default step now resolves for monsters without editing the chain, and verify with mounted-snapshot fixtures that a catalog-backed species presents its official image and a species absent from the snapshot falls through byte-identically to the runtime/silhouette chain

## 2. Anti-substitution guards

- [ ] 2.1 Verify with rejection tests that threat-tier strings named where a species key is required stay unregistered (no alias table exists), that a forged species key inside a `portrait:monster` subject still raises `ArtSubjectError` via `MONSTER_TIER_REGISTRY` validation, and that no code path reaches another species' official bytes for an unmatched species
- [ ] 2.2 Assert individual independence through the existing personalization machinery: two same-species individuals share the read-only reference while personal selection/geometry stay per-entity and the mounted source is unchanged

## 3. Verification

- [ ] 3.1 Register the new test module in exactly one shard of `.github/evennia-shards.json`, run the focused `world/art/tests/` modules plus the shard-ownership contract, and run `uv run --locked python -m tools.contract_gate` for the changed wire-adjacent modules; confirm no player-command docs update is required (no surface change)

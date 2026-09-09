## 1. Share the automatic path across kinds

- [ ] 1.1 Generalize the automatic-ensure helper in `world/art/service.py` so one function serves every gallery-bearing kind: the same gallery-empty-and-no-job-in-flight guard, the same typed rejections, the same bounded failure isolation. Rename it off `_ensure_character_portrait` — it no longer serves only characters.
- [ ] 1.2 Make the canonical-age check one declared precondition inside that helper rather than a hardcoded step, so a kind that does not declare it reads no age attribute at all.
- [ ] 1.3 Keep every existing character guarantee byte-for-byte: the age check at schedule time and again immediately before the queue write, the `transaction.on_commit` registration, and the failure isolation that never rolls back creation, import, spawn, or movement.

## 2. Route monster startup synchronization

- [ ] 2.1 Route `_sync_registry_subjects`'s `MONSTER_TIER_REGISTRY` loop through the shared helper and **stop writing a classic asset record for monster tiers**.
- [ ] 2.2 Leave the `SCENE_ARCHETYPE_REGISTRY` loop on the classic `queue_ensure` path unchanged — the scene kind becomes the only classic-record producer.
- [ ] 2.3 Keep every monster failure bounded so a failing tier never aborts startup and the remaining tiers still synchronize.
- [ ] 2.4 Leave pre-existing classic monster records in place — not deleted, not reset — so they keep resolving through the chain's classic step and no migration is needed.

## 3. Tests

- [ ] 3.1 Cover startup on a fresh database: every monster tier gets one gallery request and no classic monster record; every scene still gets a classic record.
- [ ] 3.2 Cover idempotency: consecutive startups never stack a second card and never replace a monster tier's existing card or its stored file.
- [ ] 3.3 Cover the in-flight guard: a tier whose gallery job is already pending or in progress gets no second job.
- [ ] 3.4 Cover the seed interaction: a tier whose only card came from seed synchronization is left alone.
- [ ] 3.5 Cover failure isolation: a tier whose gallery request raises leaves startup intact and the remaining tiers synchronized.
- [ ] 3.6 Cover the pre-existing classic record: it is neither deleted nor reset, and it still resolves through the chain's classic step.
- [ ] 3.7 Confirm every character automatic path still behaves exactly as before — creation, validated import, named-NPC spawn, and startup recovery.
- [ ] 3.8 Annotate every new test with `@covers_requirement`, and register any new test module in `.github/evennia-shards.json` in this change.

## 4. Verification

- [ ] 4.1 `openspec validate gallery-monster-autogen --strict` passes.
- [ ] 4.2 `uv run --locked python -m tools.spec_traceability check` reports zero uncovered requirements.
- [ ] 4.3 `uv run --locked python -m tools.observability_lint check` passes with no new waiver.
- [ ] 4.4 The `world.art` Evennia shard passes.
- [ ] 4.5 Confirm the generic monster kind no longer produces a classic asset record on any path, and that the only remaining classic-record producer is the scene kind.
- [ ] 4.6 Update `docs/superpowers/specs/2026-09-08-character-gallery-art-design.md` §12: record that monster generation reached the gallery through this change and retire the recorded gap.

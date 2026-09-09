## 1. Share the automatic path across kinds

- [x] 1.1 Generalize the automatic-ensure helper in `world/art/service.py` so one function serves every gallery-bearing kind: the same gallery-empty-and-no-job-in-flight guard, the same typed rejections, the same bounded failure isolation. Rename it off `_ensure_character_portrait` — it no longer serves only characters.
- [x] 1.2 Make the canonical-age check one declared precondition inside that helper rather than a hardcoded step, so a kind that does not declare it reads no age attribute at all.
- [x] 1.3 Keep every existing character guarantee byte-for-byte: the age check at schedule time and again immediately before the queue write, the `transaction.on_commit` registration, and the failure isolation that never rolls back creation, import, spawn, or movement.

## 2. Route monster startup synchronization

- [x] 2.1 Route `_sync_registry_subjects`'s `MONSTER_TIER_REGISTRY` loop through the shared helper and **stop writing a classic asset record for monster tiers**.
- [x] 2.2 Leave the `SCENE_ARCHETYPE_REGISTRY` loop on the classic `queue_ensure` path unchanged — the scene kind becomes the only classic-record producer.
- [x] 2.3 Keep every monster failure bounded so a failing tier never aborts startup and the remaining tiers still synchronize.
- [x] 2.4 Leave pre-existing classic monster records in place — not deleted, not reset — so they keep resolving through the chain's classic step and no migration is needed.
- [x] 2.5 Reorder the startup step catalog so `art_sync_all` runs AFTER `art_gallery_prune` and `art_seed_sync` (prune → seed → sync), so a seed card already occupies a tier's gallery before the automatic guard reads it; update the catalog, comments, and the startup-step guard coverage.
- [x] 2.6 Make `@art retry`'s classic arm skip every gallery-bearing kind (`gallery_kinds.has_gallery`) so a legacy failed monster record is never reset or re-enqueued and gallery failures retry only through the gallery seam; update `docs/game/command-reference.md`'s `art retry` description.

## 3. Tests

- [x] 3.1 Cover startup on a fresh database: every monster tier gets one gallery request and no classic monster record; every scene still gets a classic record.
- [x] 3.2 Cover idempotency: consecutive startups never stack a second card and never replace a monster tier's existing card or its stored file.
- [x] 3.3 Cover the in-flight guard: a tier whose gallery job is already pending or in progress gets no second job.
- [x] 3.4 Cover the seed interaction: a tier whose only card came from seed synchronization is left alone — via the real startup step order (prune → seed → sync) with a later drain proving the seed card and file survive.
- [x] 3.5 Cover failure isolation: a tier whose gallery request raises leaves startup intact and the remaining tiers synchronized.
- [x] 3.6 Cover the pre-existing classic record: it is neither deleted nor reset, and it still resolves through the chain's classic step.
- [x] 3.7 Confirm every character automatic path still behaves exactly as before — creation, validated import, named-NPC spawn, and startup recovery.
- [x] 3.8 Cover `@art retry` never reactivating a legacy failed monster classic record while a failed scene still re-enqueues.
- [x] 3.9 Annotate every new test with `@covers_requirement`, and register any new test module in `.github/evennia-shards.json` in this change.

## 4. Verification

- [x] 4.1 `openspec validate gallery-monster-autogen --strict` passes.
- [x] 4.2 `uv run --locked python -m tools.spec_traceability check` reports zero uncovered requirements.
- [x] 4.3 `uv run --locked python -m tools.observability_lint check` passes with no new waiver.
- [x] 4.4 The `world.art` Evennia shard passes.
- [x] 4.5 Confirm the generic monster kind no longer produces a classic asset record on any path, and that the only remaining classic-record producer is the scene kind.
- [x] 4.6 Update `docs/superpowers/specs/2026-09-08-character-gallery-art-design.md` §12: record that monster generation reached the gallery through this change and retire the recorded gap — while KEEPING the §12.3.2 qualification that already-existing classic records (monsters included) remain a lower-priority display-chain step and are never migrated, reset, or newly produced.

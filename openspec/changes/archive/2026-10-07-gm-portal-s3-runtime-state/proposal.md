## Why

The landed GM portal exposes operations and retained LLM calls but cannot explain persistent entity state or NPC memory behind a failing play session. S3 supplies omniscient, read-only inspection without changing gameplay, reconstructing rules, or triggering narrative writes.

## What Changes

- Add `web/gm/readers/` modules for accounts, characters, NPCs, monsters, rooms, quests, narrative, art, raw objects, and search; reuse existing read models with non-autocreating Attribute access.
- Add protected runtime list/detail/raw/search APIs and read-only NPC recall preview, independent summary-section errors, and existing cursor/limit envelopes.
- Enable runtime navigation, filtered lists, cross-linked identifiers, all approved entity summaries, universal Evennia raw inspection, and separate true/disguised traits.
- Add NPC memory/revision/recall/snapshot and player-grouped dialogue tabs; link existing S2 transcripts without assembling new dialogue prompts.
- Add shared entity-link, JSON-tree, filter-bar, and pager components; reuse the JSON tree in the existing S2 drawer. Runtime pages refresh manually, never poll.
- Add fixed-fixture reader tests, static and runtime read-only contracts, API tests, Vitest/Storybook coverage, shard registration, and requirement traceability.

## Capabilities

### New Capabilities
- `gm-runtime-state`: Read-only runtime readers, curated/raw entity inspection, protected APIs, navigation/search/linking, NPC narrative tabs, and acceptance contracts.

### Modified Capabilities
None. S1 explicitly reserves later data endpoints and enabling delivered navigation sections; S2's drawer behavior remains intact when its JSON renderer is shared.

## Impact

Implementation touches `web/gm/`, `web/admin-app/`, `.github/evennia-shards.json`, and the existing test/showcase/traceability integration. Owning rule, map, quest, narrative, and art packages remain authoritative read sources; no schema migration, compatibility layer, new writer, external-service call, OOB change, or game-bundle dependency is introduced. Sources: approved parent `docs/superpowers/specs/2026-10-06-gm-portal-design.md` and detail `docs/superpowers/specs/2026-10-06-gm-portal-s3-runtime-state-design.md`.

## Dependencies and conflicts

Requires archived and merged `gm-portal-s1-foundation`, `gm-portal-s2a-llm-transcript`, and `gm-portal-s2b-dashboard`; no active proposal dependency remains. Future S4/S5/S6 edits may conflict in GM URLs, router/navigation, shared components/stories, and shard manifest; S6 consumes S3 inspection but is not included. This is one bounded S3 delivery using existing read models and generic list/detail layout, not a re-proposal of foundation/dashboard or a domain redesign.

## Non-goals

Authored-data browsing (S4), saves (S5), developer writes (S6), persona editing, art requeue, dialogue prompt preview or pure/commit refactoring of `build_dialogue_context`, polling, rule recalculation, and persistent-state repair are excluded.

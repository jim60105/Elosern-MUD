# Design: title-fixed-core

Implements D1/D2/D3/D8 (§5/§6) of
`docs/superpowers/specs/2026-08-30-title-system-design.md`.

## Context

A deleted `RANK_TITLE_REGISTRY`; B retired every XP surface this could have
hooked. The lore-registry pattern (frozen dataclasses + keyed registry +
idempotent startup sync) is established (`world/lore/`), the event-effect
planner seam (`register_event_effect_planner`) is established
(`world/rules/action.py`), and guild registration/promotion already commit
atomically. G (nomination) and H (codex/removal) build strictly on this chain.

## Goals / Non-Goals

- Goals: storage model, compose, registry + predicates, deterministic grants
  (planner + guild transactions + starter pair), D8 slot invariant, equip
  command, consumer layering.
- Non-Goals: LLM epithet nomination (G), codex window / removal gates (H),
  any deletion API (fixed titles are append-only by construction; epithet
  deletion belongs to H and nowhere else).

## Decisions

### DF1: two attributes, identifiers only

`db.title_collection: list[dict]` (`kind`, `key`/`display`, `origin_quote?`,
`granted_tick`) and `db.title_equipped: {"fixed": key|None,
"epithet": display|None}`. Slots store identifiers, never copies (collection
indices shift on H's deletions). Both registered on the snapshot/restore face
before any writer runs (existing invariant raises otherwise). Missing attribute
reads equal the defaults (`[]`, both slots `None`).

### DF2: compose is a pure function, consumers decide fallback

`compose_title(fixed, epithet)` joins non-empty parts with 「　」 (full-width
space); empty string means no title, and every consumer falls back to the
character name; the LLM prompt context section is omitted entirely when empty
(not filled with 「無」). Nothing stores the composed copy.

### DF3: declarative predicate families, planner-side evaluation

`TitlePredicate` families (`lineage_complete`, `mastery_owned`,
`first_kill_tier`, `quest_completed`, `guild_rank_reached`,
`sexual_experience`, `counter_threshold`) carry only parameters; the title
planner scans the step-7 EventLog after effect resolution, re-reads the
non-EventLog faces through the same `status_query` read helpers, and stages
`PendingEffect`s writing into the triggering action's commit. Re-evaluation is
idempotent (collection already contains key → skip), so a rolled-back grant
re-grants naturally on the next matching event. Load validation: unique keys,
non-empty `hint_zh`, predicate references resolve to existing registry faces.

### DF4: guild pairing is transaction-bound, starter epithet is a normal entry

`register_guild_member`'s existing atomic transaction grants「F級冒險者」(fixed,
D3) plus the registry constant `STARTER_EPITHET`「南門新客」(a plain epithet
entry) — deterministic, no planner, no LLM; duplicate registration no-ops via
the two existing dedupe rules. E→S grants ride the promotion transaction
(planner sees the rank-up event). Demotion never revokes (append-only fixed
invariant).

### DF5: D8 slot-non-empty invariant by mutator discipline

Every mutator that can add a collection entry (fixed grant, starter pair, G's
future adopt) auto-equips its entry into an empty slot in the same transaction;
occupied slots just bank the entry. There is no unequip path, hence no
`title clear` command. The only empty-slot window is before guild registration
(character created, not yet registered). Tests assert no mutator sequence
reaches "collection non-empty and slot empty".

## Risks

- Planner overhead per action: predicate scan is registry-sized (small), and
  idempotency short-circuits on the collection set.
- Title display churn in prompts: consumers read slots live; no cached copies.

## Migration Plan

One-shot cutover (unreleased). The lore registry syncs idempotently at startup.

## Open Questions

None. Predicate content rows beyond the guild/onboarding pair are future
content work, as the design states.

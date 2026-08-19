## Context

Part **B3** (showcase wave, Wave B serial chain; depends on B2). These panels are read-heavy; the key
invariants are truthfulness (no invented fields) and non-color-only status.

## Goals / Non-Goals

**Goals** — `StatusPanel`, `CharacterPanel`, `SkillBook` as documented, offline, component-tested SFCs;
manifest extended.
**Non-Goals** — no intimate/adult block (deferred, no backing field), no store/transport/mount.

## Decisions

- **D1 — Render only the payload; never color-only.** Every gauge/counter/condition pairs an icon or
  symbol with a numeric value; conditions show derived modifiers. Disguised statistics are shown as display
  values distinct from true traits.
- **D2 — No adult/intimate block.** The 設計稿 shows one, but the current `status`/`character` OOB payload
  has no such fields (roadmap §7); B3 asserts it is absent rather than mocked.

## Risks / Trade-offs

- **Field drift** (a shown field with no backing payload) → tests assert every rendered field comes from
  the mock `status`/`character`/`skill` payload.
- **Skill search/depth** → bounded category>group>skill tree with search; no unbounded enumeration.

## Migration Plan

Offline/Storybook only; rollback = delete the family + manifest keys. B2 and all gates unaffected.

## Open Questions

- None.

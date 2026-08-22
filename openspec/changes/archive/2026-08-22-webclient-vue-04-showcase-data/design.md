## Context

Part **B3** (showcase wave, Wave B serial chain; depends on B2). These panels are read-heavy; the key
invariants are truthfulness (no invented fields) and non-color-only status.

## Goals / Non-Goals

**Goals** — `StatusPanel`, `CharacterPanel`, `SkillBook` as documented, offline, component-tested SFCs;
manifest extended.
**Non-Goals** — no intimate/adult block (deferred, no backing field), no store/transport/mount.

## Decisions

- **D1 — Render only the payload; never color-only.** Gauges pair a symbol with an explicit
  current/maximum numeric value; counters and static traits render their numeric values; conditions
  pair a severity glyph (rendered as a DOM node per severity, not a CSS pseudo-element) with the
  payload's label and every numeric/modifier value the payload carries (remaining seconds, derived
  modifiers) — a condition the payload gives no numeric for renders glyph + label only, never a
  fabricated number. Disguised statistics are shown as display values distinct from true traits.
- **D2 — No adult/intimate block.** The 設計稿 shows one, but the current `status`/`character` OOB payload
  has no such fields (roadmap §7); B3 asserts it is absent rather than mocked.
- **D3 — Props are the two OOB payloads and one derived skill slice.** `StatusPanel` receives the
  `status` panel payload (schema version 1 — gauges, conditions, `disguise_active`, combat) plus the
  `character` panel payload (schema version 3 — counters, static traits, wallet); `CharacterPanel`
  receives the `character` payload. `SkillBook` receives the character's skill data as a
  **derived slice**: `{actives, passives}` in the `character` payload's category/`groups`/`{key,
  label}` shape and ordering, where each row may additionally carry the **display subset of a
  committed `context_actions` v5 skill descriptor** — `cost` (a bounded object; the empty object is
  the v5 free form), `target_spec`, and the descriptor's optional `freeform_scales` (cast power
  scales) / `shorthands` — exactly the fields the component renders. The C1 store getter derives
  the slice by selecting those fields from the backing descriptors (combat-form skills); rows with
  no backing descriptor stay the character payload's own `{key, label}` shape (e.g. the `unknown`-
  key fallback rows) and render without detail cells. Details are display-only; combat resolution
  always uses true traits. The story fixtures mirror these shapes exactly, including both row
  forms, so the showcase and the live (C1) views cannot drift.
- **D4 — Field-level absence is hidden, the honest line is a fixed label.** Absent conditional fields
  (`remaining_seconds`, `modifiers`, `combat`, `persona.background`) render nothing. Sections whose
  payload boolean decides a fixed status line (`disguise` active/inactive, `guild` rank null →
  未加入公會) render that one fixed line, matching the legacy character-menu model.
- **D5 — The data family extends the manifest lockstep.** The manifest gains exactly
  `Data/StatusPanel`, `Data/CharacterPanel`, `Data/SkillBook`; the B2 baseline set in
  `test_vue_showcase_action_evidence.py` is updated in the same change (B5 will freeze it).

## Risks / Trade-offs

- **Field drift** (a shown field with no backing payload) → tests assert every rendered field comes from
  the mock `status`/`character`/`skill` payload.
- **Skill search/depth** → bounded category>group>skill tree with search; no unbounded enumeration.

## Migration Plan

Offline/Storybook only; rollback = delete the family + manifest keys. B2 and all gates unaffected.

## Open Questions

- None.

## Context

Design doc §7's content-completion table lists several character-sheet skills that map onto existing
registry entries with only cosmetic (label/description) drift, plus one gap (`dual_blade_mastery`) with
no existing entry. This proposal handles exactly those items not already claimed by a more specific
proposal elsewhere in the batch (`weapon-style-stance-split` owns `dual_wield_style`/`light_sword_style`
mechanically; `divine-mystery-skills` owns the 性魔法 family; `element-mastery-cast-gate` owns the four
new mastery skills).

## Goals / Non-Goals

**Goals:**
- Close the remaining character-sheet-to-registry gaps that are pure content, not mechanism.

**Non-Goals:**
- Does not touch `dual_wield_style`'s mechanism (`weapon-style-stance-split`'s job) — this change adds
  a sibling skill, `dual_blade_mastery`, and does not modify `dual_wield_style` itself.
- Does not attempt to fully re-derive every possible character-sheet skill mapping — only the items the
  approved design doc's §7 table explicitly calls out.

## Decisions

- **`dual_blade_mastery` uses `damage:dark:physical`**, matching 悠花's already-established dark
  elemental affinity via `shadow_slash`, rather than inventing an elementless damage convention whose
  existence in `ELEMENT_REGISTRY` was not confirmed while writing this proposal. Task list includes
  confirming whether a more neutral element token exists before implementation, in case a better fit
  is available.
- **Label/description edits only, no key renames**, for `guardian_instinct` and `blade_art_mastery` —
  renaming the registry key itself would be a breaking change to any import data already referencing
  the old key (harmless with zero users, but unnecessary churn when the existing key is already
  semantically fine and only the *display text* needs to better match the character-sheet flavor).

## Risks / Trade-offs

- [Risk] `damage:dark:physical` for `dual_blade_mastery` duplicates `shadow_slash`'s exact effect
  signature, making the two skills mechanically identical aside from cost/kind metadata. → Mitigation:
  this is acceptable for this pass (both are 悠花-flavored dark physical attacks at different points in
  her kit); differentiating their actual damage math is a combat-balance concern outside a
  content-completion proposal's scope.

## Migration Plan

No data migration. Lands after `skill-effects-typed-model`; independent of every other change in this
batch beyond that shared foundation.

## Open Questions

None — the `ELEMENT_REGISTRY` neutral-element question is a bounded implementation-time check, not an
open architectural question.

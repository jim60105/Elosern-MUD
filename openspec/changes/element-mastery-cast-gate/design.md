## Context

World lore (`tmp/story_settings/world_info.md`, not committed) defines five magic-level bands
(學徒 0–15, 術師 16–30, 大師 31–70, 賢者 71–90, 主宰 90+) as both a display title and (per character
data cross-referenced in the approved design doc) a mechanical gate on which tier of spell a caster may
use, with an explicit override: owning an element's mastery skill unlocks every spell of that element
regardless of numeric level. No existing code implements either half.

## Goals / Non-Goals

**Goals:**
- `magic_rank_title` and `can_cast_spell_tier` are both pure, side-effect-free queries.
- The two are independent: `can_cast_spell_tier` never consults `magic_rank_title`'s output, and vice
  versa — this is deliberate (design doc D5) to avoid conflating a display fact with a mechanical gate.

**Non-Goals:**
- Does not implement per-element numeric proficiency tracking — both functions read the single global
  `magic_level` trait, per D5's explicit rejection of per-element levels (nothing in the approved
  character data requires them).
- Does not change how `magic_level` itself accrues (that's `magic-level-progression`'s territory,
  unchanged here).
- Does not implement the actual eight new elements' spells — that is each `spell-catalog-*` proposal's
  job; this change only builds the gate they call into.

## Decisions

- **Direct ownership only for the mastery override, no conferred-grant path.** `ConferredSkillGrant`
  (generalized by `conferral-generalization`) explicitly excludes gate-type effects — a "partial spell
  unlock" has no defined meaning. This change's `can_cast_spell_tier` therefore checks
  `entity.skills.owned_keys()` directly, never `entity.skills.conferred_grants()`.
- **Gate hook reuses the existing rejection category**, not a new `RejectReason` member — from the
  resolver's perspective, "you may not cast this" is one class of rejection whether the cause is
  "you don't own the skill" or "you don't meet its tier gate" (this mirrors how `preflight` already
  treats skill-ownership and skill-kind failures as the same rejection shape).
- **Bands are a fixed constant table**, not a formula, matching `magic-level-progression`'s existing
  precedent of expressing tuning as data rather than computed curves.

## Risks / Trade-offs

- [Risk] Wiring into `ActionResolver.preflight`/`resolve` touches a well-tested, eight-step pipeline
  (`action-resolution-pipeline` spec). A careless insertion point could break an existing scenario.
  → Mitigation: task list requires reading the full pipeline before inserting, adding the gate check
  as an additional condition in the *existing* skill-validation step rather than a new step, and
  running the full existing `action-resolution-pipeline` scenario suite before/after.

## Migration Plan

No data migration for existing entities — `can_cast_spell_tier` is a pure query evaluated at cast time,
not a stored fact. Lands after `skill-effects-typed-model`; before every `spell-catalog-*` change.

## Open Questions

None.
